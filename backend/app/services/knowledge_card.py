from __future__ import annotations

import base64
import json
import re
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import KnowledgeCard, User
from app.schemas.knowledge_card import KnowledgeCardDetail, KnowledgeCardItem, KnowledgeCardListResponse


class KnowledgeCardService:
    allowed_image_types = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    max_image_bytes = 10 * 1024 * 1024

    async def list_cards(
        self,
        db: AsyncSession,
        current_user: User,
        *,
        page: int,
        page_size: int,
        status_value: str | None = None,
        q: str | None = None,
    ) -> KnowledgeCardListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 50)
        filters = [KnowledgeCard.user_id == current_user.id]
        if status_value:
            filters.append(KnowledgeCard.status == status_value.strip())
        if q:
            keyword = q.strip()
            filters.append(or_(KnowledgeCard.title.contains(keyword), KnowledgeCard.input_text.contains(keyword)))

        total_result = await db.execute(select(func.count()).select_from(KnowledgeCard).where(*filters))
        total = int(total_result.scalar_one())
        result = await db.execute(
            select(KnowledgeCard)
            .where(*filters)
            .order_by(KnowledgeCard.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return KnowledgeCardListResponse(
            items=[self._to_item(item) for item in result.scalars().all()],
            total=total,
            page=page,
            pageSize=page_size,
        )

    async def get_card(self, db: AsyncSession, current_user: User, card_id: int) -> KnowledgeCardDetail:
        card = await self._get_owned_card(db, current_user, card_id)
        return self._to_detail(card)

    async def get_card_file(self, db: AsyncSession, current_user: User, card_id: int, kind: str) -> tuple[Path, str]:
        card = await self._get_owned_card(db, current_user, card_id)
        relative_path = card.output_image_path if kind == "output" else card.input_image_path
        if not relative_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到图片文件")
        file_path = (settings.upload_dir / relative_path).resolve()
        storage_root = settings.upload_dir.resolve()
        if storage_root not in file_path.parents or not file_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片文件不存在")
        return file_path, self._guess_mime(file_path)

    async def generate_stream(
        self,
        db: AsyncSession,
        current_user: User,
        *,
        input_text: str | None,
        extra_prompt: str | None,
        image: UploadFile | None,
    ) -> AsyncIterator[dict]:
        text = (input_text or "").strip()
        extra = (extra_prompt or "").strip()
        if not text and image is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入知识文本或上传一张图片")
        if not settings.knowledge_card_dify_api_key:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="知识卡片 Dify API Key 未配置")

        input_type = "mixed" if text and image is not None else ("image" if image is not None else "text")
        card = KnowledgeCard(
            user_id=current_user.id,
            title=self._initial_title(text),
            input_type=input_type,
            input_text=text or None,
            extra_prompt=extra or None,
            status="processing",
            raw_response={},
        )
        db.add(card)
        await db.commit()
        await db.refresh(card)
        yield {"event": "status", "message": "已创建知识卡片任务", "cardId": card.id}

        dify_file_id: str | None = None
        try:
            if image is not None:
                yield {"event": "status", "message": "正在保存输入图片", "cardId": card.id}
                saved = await self._save_input_image(card.id, image)
                card.input_image_path = saved["relative_path"]
                card.input_image_url = self._file_url(card.id, "input")
                card.input_image_mime = saved["mime_type"]
                card.input_image_size = saved["size"]
                await db.commit()

                yield {"event": "status", "message": "正在上传图片到 Dify 工作流", "cardId": card.id}
                dify_file_id = await self._upload_file_to_dify(saved["path"], saved["mime_type"], current_user)

            yield {"event": "status", "message": "正在调用 Dify 知识卡片工作流", "cardId": card.id}
            async for event in self._run_dify_workflow(card, current_user, text, extra, dify_file_id):
                await self._apply_dify_event(db, card, event)
                public_event = self._to_public_event(card, event)
                if public_event:
                    yield public_event

            if not card.output_image_url:
                outputs = card.raw_response if isinstance(card.raw_response, dict) else {}
                await self._persist_output_image(card, outputs)

            if card.output_image_url:
                card.status = "succeeded"
                card.error_message = None
                await db.commit()
                await db.refresh(card)
                yield {"event": "preview", "imageUrl": card.output_image_url, "cardId": card.id}
                yield {"event": "done", "card": self._to_detail(card).model_dump(mode="json")}
                return

            raise RuntimeError("Dify 工作流未返回可保存的图片")
        except Exception as exc:
            card.status = "failed"
            card.error_message = str(exc)
            await db.commit()
            yield {"event": "error", "message": str(exc), "cardId": card.id}

    async def _apply_dify_event(self, db: AsyncSession, card: KnowledgeCard, event: dict) -> None:
        event_type = event.get("event")
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event.get("task_id"):
            card.dify_task_id = event.get("task_id")
        if event.get("workflow_run_id"):
            card.dify_workflow_run_id = event.get("workflow_run_id")
        if data.get("workflow_run_id"):
            card.dify_workflow_run_id = data.get("workflow_run_id")

        raw = dict(card.raw_response or {})
        events = list(raw.get("events") or [])
        events.append(self._sanitize(event))
        raw["events"] = events[-30:]
        if event_type == "message" and event.get("answer"):
            raw["answer"] = f"{raw.get('answer', '')}{event.get('answer', '')}"
        if event_type == "message_file":
            files = list(raw.get("files") or [])
            files.append(self._sanitize(event))
            raw["files"] = files[-10:]

        if event_type in {"workflow_finished", "node_finished"}:
            outputs = data.get("outputs") or event.get("outputs") or {}
            if outputs:
                existing_outputs = raw.get("outputs") if isinstance(raw.get("outputs"), dict) else {}
                raw["outputs"] = {**existing_outputs, **self._sanitize(outputs)}
                self._apply_outputs_to_card(card, outputs)
        card.raw_response = raw
        await db.commit()

    def _to_public_event(self, card: KnowledgeCard, event: dict) -> dict | None:
        event_type = event.get("event")
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        node_title = data.get("title") or data.get("node_type") or data.get("node_id")
        if event_type == "workflow_started":
            return {"event": "workflow", "message": "Dify 工作流已启动", "node": "workflow", "cardId": card.id}
        if event_type == "node_started":
            return {"event": "workflow", "message": f"正在执行节点：{node_title or '未命名节点'}", "node": node_title, "cardId": card.id}
        if event_type == "node_finished":
            return {"event": "workflow", "message": f"节点完成：{node_title or '未命名节点'}", "node": node_title, "cardId": card.id}
        if event_type == "workflow_finished":
            return {"event": "status", "message": "Dify 工作流已完成，正在保存图片", "cardId": card.id}
        if event_type == "error":
            return {"event": "error", "message": event.get("message") or data.get("error") or "Dify 工作流异常", "cardId": card.id}
        return None

    async def _run_dify_workflow(
        self,
        card: KnowledgeCard,
        current_user: User,
        input_text: str,
        extra_prompt: str,
        dify_file_id: str | None,
    ) -> AsyncIterator[dict]:
        inputs: dict[str, Any] = {
            "content": input_text,
            "prompt": extra_prompt,
            "input_text": input_text,
            "extra_prompt": extra_prompt,
        }
        if dify_file_id:
            inputs["input_image"] = {
                "type": "image",
                "transfer_method": "local_file",
                "upload_file_id": dify_file_id,
            }
        payload = {
            "inputs": inputs,
            "response_mode": "streaming",
            "user": current_user.student_id or str(current_user.id),
        }
        if settings.knowledge_card_dify_workflow_id:
            payload["workflow_id"] = settings.knowledge_card_dify_workflow_id

        started_at = time.monotonic()
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{settings.knowledge_card_dify_api_base}/workflows/run",
                headers={"Authorization": f"Bearer {settings.knowledge_card_dify_api_key}"},
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", errors="replace")
                    if response.status_code == 400 and "not_workflow_app" in body:
                        async for event in self._run_dify_chat_messages(card, current_user, input_text, extra_prompt, dify_file_id):
                            yield event
                        return
                    raise RuntimeError(f"Dify Workflow 请求失败：HTTP {response.status_code} {body[:500]}")
                async for line in response.aiter_lines():
                    if time.monotonic() - started_at > settings.knowledge_card_timeout_seconds:
                        raise TimeoutError("知识卡片生成超时，请稍后重试")
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if not data or data == "[DONE]":
                        continue
                    yield json.loads(data)

    async def _run_dify_chat_messages(
        self,
        card: KnowledgeCard,
        current_user: User,
        input_text: str,
        extra_prompt: str,
        dify_file_id: str | None,
    ) -> AsyncIterator[dict]:
        inputs: dict[str, Any] = {
            "content": input_text,
            "prompt": extra_prompt,
            "input_text": input_text,
            "extra_prompt": extra_prompt,
        }
        files: list[dict[str, Any]] = []
        if dify_file_id:
            file_ref = {
                "type": "image",
                "transfer_method": "local_file",
                "upload_file_id": dify_file_id,
            }
            inputs["input_image"] = file_ref
            files.append(file_ref)
        payload = {
            "inputs": inputs,
            "query": input_text or "请根据上传图片生成知识卡片",
            "response_mode": "streaming",
            "user": current_user.student_id or str(current_user.id),
            "files": files,
        }
        started_at = time.monotonic()
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{settings.knowledge_card_dify_api_base}/chat-messages",
                headers={"Authorization": f"Bearer {settings.knowledge_card_dify_api_key}"},
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", errors="replace")
                    raise RuntimeError(f"Dify Chatflow 请求失败：HTTP {response.status_code} {body[:500]}")
                async for line in response.aiter_lines():
                    if time.monotonic() - started_at > settings.knowledge_card_timeout_seconds:
                        raise TimeoutError("知识卡片生成超时，请稍后重试")
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if not data or data == "[DONE]":
                        continue
                    yield json.loads(data)

    async def _upload_file_to_dify(self, file_path: Path, mime_type: str, current_user: User) -> str:
        async with httpx.AsyncClient(timeout=settings.knowledge_card_timeout_seconds) as client:
            with file_path.open("rb") as handle:
                response = await client.post(
                    f"{settings.knowledge_card_dify_api_base}/files/upload",
                    headers={"Authorization": f"Bearer {settings.knowledge_card_dify_api_key}"},
                    data={"user": current_user.student_id or str(current_user.id)},
                    files={"file": (file_path.name, handle, mime_type)},
                )
        response.raise_for_status()
        data = response.json()
        file_id = data.get("id")
        if not file_id:
            raise RuntimeError("Dify 文件上传未返回 id")
        return file_id

    async def _save_input_image(self, card_id: int, upload: UploadFile) -> dict:
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传图片为空")
        if len(content) > self.max_image_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="图片超过 10MB 限制")
        mime_type = upload.content_type or "application/octet-stream"
        if mime_type not in self.allowed_image_types:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 jpg、png、webp 图片")
        suffix = self.allowed_image_types[mime_type]
        relative = Path("knowledge-cards") / "inputs" / f"{card_id}_{uuid4().hex}{suffix}"
        path = settings.upload_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return {"path": path, "relative_path": relative.as_posix(), "mime_type": mime_type, "size": len(content)}

    async def _persist_output_image(self, card: KnowledgeCard, outputs: dict) -> None:
        image_url = self._extract_output_image_url(outputs)
        image_base64 = self._find_first(outputs, {"image_base64", "base64"})
        content: bytes | None = None
        suffix = ".png"
        if image_url:
            async with httpx.AsyncClient(timeout=settings.knowledge_card_timeout_seconds) as client:
                response = await client.get(str(image_url))
                response.raise_for_status()
                content = response.content
                suffix = self._suffix_from_content_type(response.headers.get("content-type"), image_url)
        elif image_base64:
            content = self._decode_base64_image(str(image_base64))
        if not content:
            return
        relative = Path("knowledge-cards") / "outputs" / f"{card.id}_{uuid4().hex}{suffix}"
        path = settings.upload_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        card.output_image_path = relative.as_posix()
        card.output_image_url = self._file_url(card.id, "output")

    def _extract_output_image_url(self, outputs: dict) -> str | None:
        """只从最终输出中提取生成图，避免把上传输入图的 file-preview 当成成品图。"""
        if not isinstance(outputs, dict):
            return None

        candidates: list[str] = []

        # Dify Chat App 常把最终图片 URL 放在 answer 文本中，这是最高优先级。
        for key in ("answer", "output", "result", "text"):
            value = outputs.get(key)
            if isinstance(value, str):
                candidates.extend(self._find_image_urls_in_text(value))

        final_outputs = outputs.get("outputs")
        if isinstance(final_outputs, dict):
            for key in ("image_url", "output_image_url", "generated_image_url", "card_image_url", "url"):
                value = final_outputs.get(key)
                if isinstance(value, str):
                    candidates.extend(self._find_image_urls_in_text(value))
            for key in ("answer", "output", "result", "text"):
                value = final_outputs.get(key)
                if isinstance(value, str):
                    candidates.extend(self._find_image_urls_in_text(value))

        for key in ("image_url", "output_image_url", "generated_image_url", "card_image_url"):
            value = self._find_first(outputs, {key})
            if isinstance(value, str):
                candidates.extend(self._find_image_urls_in_text(value))

        # 最后才检查 Dify message_file，仍然过滤输入预览和插件图标。
        files = outputs.get("files")
        if isinstance(files, list):
            for item in files:
                if isinstance(item, dict):
                    candidates.extend(self._find_image_urls_in_text(json.dumps(item, ensure_ascii=False)))

        return self._choose_output_image_url(candidates)

    def _apply_outputs_to_card(self, card: KnowledgeCard, outputs: dict) -> None:
        card.title = self._find_first(outputs, {"title", "card_title"}) or card.title
        card.prompt = self._find_first(outputs, {"prompt", "final_prompt", "image_prompt"}) or card.prompt
        card.template_id = self._find_first(outputs, {"template_id", "templateId"}) or card.template_id
        image_number = self._find_first(outputs, {"image_number", "imageNumber", "图片编号"})
        card.image_number = str(image_number) if image_number is not None else card.image_number
        card.route_reason = self._find_first(outputs, {"route_reason", "reason"}) or card.route_reason

    def _find_first(self, value: Any, keys: set[str]) -> Any:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in keys and self._present(item):
                    return item
            for item in value.values():
                found = self._find_first(item, keys)
                if self._present(found):
                    return found
        if isinstance(value, list):
            for item in value:
                found = self._find_first(item, keys)
                if self._present(found):
                    return found
        return None

    def _present(self, value: Any) -> bool:
        return value is not None and value != ""

    def _find_image_urls_in_text(self, value: str) -> list[str]:
        return re.findall(r"https?://[^\s\"')]+\.(?:png|jpe?g|webp)(?:\?[^\s\"')]*)?", value, re.I)

    def _choose_output_image_url(self, candidates: list[str]) -> str | None:
        cleaned: list[str] = []
        for candidate in candidates:
            url = candidate.strip().rstrip("，。；;、")
            if not url or url in cleaned:
                continue
            if "/file-preview" in url:
                continue
            if "/console/api/workspaces/current/plugin/icon" in url:
                continue
            cleaned.append(url)
        if not cleaned:
            return None
        for url in cleaned:
            if "/files/tools/" in url:
                return url
        return cleaned[0]

    def _sanitize(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: ("[redacted]" if key.lower() in {"authorization", "api_key", "token"} else self._sanitize(item))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._sanitize(item) for item in value]
        return value

    def _decode_base64_image(self, raw: str) -> bytes:
        payload = raw.split(",", 1)[1] if raw.startswith("data:") and "," in raw else raw
        return base64.b64decode(payload)

    def _suffix_from_content_type(self, content_type: str | None, url: str | None = None) -> str:
        if content_type:
            mime = content_type.split(";", 1)[0].strip().lower()
            if mime in self.allowed_image_types:
                return self.allowed_image_types[mime]
        if url:
            match = re.search(r"\.(png|jpe?g|webp)(?:\?|$)", str(url), re.I)
            if match:
                value = match.group(1).lower()
                return ".jpg" if value == "jpeg" else f".{value}"
        return ".png"

    def _file_url(self, card_id: int, kind: str) -> str:
        return f"/api/knowledge-cards/{card_id}/files/{kind}"

    def _guess_mime(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if suffix == ".webp":
            return "image/webp"
        return "image/png"

    def _initial_title(self, text: str) -> str:
        if not text:
            return "图片知识卡片"
        title = text.strip().splitlines()[0].strip()
        return title[:40] or "知识卡片"

    async def _get_owned_card(self, db: AsyncSession, current_user: User, card_id: int) -> KnowledgeCard:
        card = await db.get(KnowledgeCard, card_id)
        if card is None or card.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到知识卡片")
        return card

    def _to_item(self, card: KnowledgeCard) -> KnowledgeCardItem:
        return KnowledgeCardItem(
            id=card.id,
            title=card.title,
            inputType=card.input_type,
            templateId=card.template_id,
            imageNumber=card.image_number,
            routeReason=card.route_reason,
            status=card.status,
            outputImageUrl=card.output_image_url,
            errorMessage=card.error_message,
            createdAt=card.created_at,
            updatedAt=card.updated_at,
        )

    def _to_detail(self, card: KnowledgeCard) -> KnowledgeCardDetail:
        return KnowledgeCardDetail(
            **self._to_item(card).model_dump(),
            inputText=card.input_text,
            inputImageUrl=card.input_image_url,
            prompt=card.prompt,
            extraPrompt=card.extra_prompt,
            difyWorkflowRunId=card.dify_workflow_run_id,
            difyTaskId=card.dify_task_id,
            rawResponse=card.raw_response,
        )


knowledge_card_service = KnowledgeCardService()
