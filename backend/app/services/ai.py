from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import create_agent_session_token
from app.models import AIConversation, AIMessage, User
from app.schemas.ai import ChatHistoryResponse, ChatMessageItem, ChatSessionItem, ChatSource, DifyUploadedFile, SendChatRequest, SendChatResponse
from app.services.academic import graduation_progress_service


class AIChatService:
    async def send_message(self, db: AsyncSession, payload: SendChatRequest, current_user: User) -> SendChatResponse:
        student_id = payload.student_id or current_user.student_id
        conversation = await self._get_or_create_conversation(db, payload, current_user, student_id)
        progress_summary = await self._build_progress_summary(db, student_id)
        inputs = self._build_inputs(payload, current_user, progress_summary)

        user_message = AIMessage(
            conversation_id=conversation.id,
            role="user",
            content=payload.query,
            intent=payload.intent,
            raw_response={"inputs": self._persistable_inputs(inputs)},
        )
        db.add(user_message)
        await db.flush()

        dify_response = await self._call_dify(payload.query, conversation.dify_conversation_id, inputs, student_id, payload.files)
        answer = dify_response.get("answer") or self._fallback_answer(payload.query, progress_summary)
        sources = self._extract_sources(dify_response)
        dify_conversation_id = dify_response.get("conversation_id")

        if dify_conversation_id:
            conversation.dify_conversation_id = dify_conversation_id
        conversation.last_intent = payload.intent
        conversation.inputs_json = self._persistable_inputs(inputs)

        assistant_message = AIMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            intent=payload.intent,
            sources_json=[source.model_dump() for source in sources],
            need_personal_data=False,
            raw_response=dify_response,
        )
        db.add(assistant_message)
        await db.commit()

        return SendChatResponse(
            answer=answer,
            conversation_id=conversation.conversation_id,
            sources=sources,
            intent=payload.intent,
            need_personal_data=False,
        )

    async def stream_message(self, db: AsyncSession, payload: SendChatRequest, current_user: User) -> AsyncIterator[str]:
        student_id = payload.student_id or current_user.student_id
        yield self._sse({"event": "status", "message": "正在读取学生学业数据", "conversation_id": payload.conversation_id})
        conversation = await self._get_or_create_conversation(db, payload, current_user, student_id)
        progress_summary = await self._build_progress_summary(db, student_id)
        inputs = self._build_inputs(payload, current_user, progress_summary)
        yield self._sse({"event": "status", "message": "正在组织培养方案检索条件", "conversation_id": conversation.conversation_id})

        db.add(
            AIMessage(
                conversation_id=conversation.id,
                role="user",
                content=payload.query,
                intent=payload.intent,
                raw_response={"inputs": self._persistable_inputs(inputs)},
            )
        )
        conversation.last_intent = payload.intent
        conversation.inputs_json = self._persistable_inputs(inputs)
        await db.commit()

        if not settings.dify_app_api_key:
            fallback = self._fallback_answer(payload.query, progress_summary)
            await self._persist_stream_answer(db, conversation, payload, fallback, {"fallback": True}, [])
            yield self._sse({"event": "status", "message": "Dify 未配置，返回本地学业摘要", "conversation_id": conversation.conversation_id})
            yield self._sse({"event": "message", "answer": fallback, "conversation_id": conversation.conversation_id})
            yield self._sse({"event": "message_end", "conversation_id": conversation.conversation_id, "sources": []})
            return

        dify_payload: dict = {
            "inputs": inputs,
            "query": payload.query,
            "response_mode": "streaming",
            "user": student_id,
        }
        if payload.files:
            dify_payload["files"] = [file.model_dump() for file in payload.files]
        if conversation.dify_conversation_id:
            dify_payload["conversation_id"] = conversation.dify_conversation_id

        answer_parts: list[str] = []
        raw_events: list[dict] = []
        dify_conversation_id: str | None = None
        sources: list[ChatSource] = []
        has_streamed_answer = False

        try:
            yield self._sse({"event": "status", "message": "正在调用 Dify 知识库生成回答", "conversation_id": conversation.conversation_id})
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{settings.dify_app_api_base}/chat-messages",
                    headers={"Authorization": f"Bearer {settings.dify_app_api_key}"},
                    json=dify_payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line.removeprefix("data:").strip()
                        if not data or data == "[DONE]":
                            continue
                        event = json.loads(data)
                        raw_events.append(self._sanitize_dify_event(event))
                        event_type = event.get("event")
                        if event.get("conversation_id"):
                            dify_conversation_id = event["conversation_id"]
                        if event_type in {"message", "agent_message"}:
                            chunk = event.get("answer") or ""
                            if chunk:
                                if not has_streamed_answer:
                                    has_streamed_answer = True
                                    yield self._sse({"event": "status", "message": "已收到模型响应，正在流式输出", "conversation_id": conversation.conversation_id})
                                answer_parts.append(chunk)
                                yield self._sse({"event": "message", "answer": chunk, "conversation_id": conversation.conversation_id})
                        elif event_type in {"workflow_started", "node_started"}:
                            yield self._sse({"event": "status", "message": "正在检索知识库并整理依据", "conversation_id": conversation.conversation_id})
                        elif event_type in {"node_finished", "workflow_finished"}:
                            output_text = self._extract_output_text(event)
                            if output_text and not has_streamed_answer:
                                has_streamed_answer = True
                                answer_parts.append(output_text)
                                yield self._sse({"event": "status", "message": "已收到模型响应，正在流式输出", "conversation_id": conversation.conversation_id})
                                yield self._sse({"event": "message", "answer": output_text, "conversation_id": conversation.conversation_id})
                        elif event_type == "message_end":
                            yield self._sse({"event": "status", "message": "正在整理引用来源与会话记录", "conversation_id": conversation.conversation_id})
                            sources = self._extract_sources(event)
                        elif event_type == "message_replace":
                            replacement = event.get("answer") or ""
                            answer_parts = [replacement]
                            yield self._sse({"event": "message_replace", "answer": replacement, "conversation_id": conversation.conversation_id})
                        elif event_type == "agent_thought":
                            status_message = self._agent_thought_status(event)
                            if status_message:
                                yield self._sse({"event": "status", "message": status_message, "conversation_id": conversation.conversation_id})
                        elif event_type == "message_file":
                            yield self._sse({"event": "status", "message": "工具已生成文件，正在整理结果", "conversation_id": conversation.conversation_id})
                        elif event_type == "error":
                            message = event.get("message") or "Dify 流式响应异常"
                            yield self._sse({"event": "error", "message": message, "conversation_id": conversation.conversation_id})
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            fallback = self._fallback_answer(payload.query, progress_summary)
            raw_response = {"fallback": True, "error": str(exc)}
            await self._persist_stream_answer(db, conversation, payload, fallback, raw_response, [])
            yield self._sse({"event": "status", "message": "Dify 暂不可用，返回本地学业摘要", "conversation_id": conversation.conversation_id})
            yield self._sse({"event": "message", "answer": fallback, "conversation_id": conversation.conversation_id})
            yield self._sse({"event": "message_end", "conversation_id": conversation.conversation_id, "sources": []})
            return

        answer = "".join(answer_parts).strip() or self._fallback_answer(payload.query, progress_summary)
        if not has_streamed_answer and answer:
            yield self._sse({"event": "status", "message": "未收到模型分片，正在返回兜底摘要", "conversation_id": conversation.conversation_id})
            yield self._sse({"event": "message", "answer": answer, "conversation_id": conversation.conversation_id})
        raw_response = {"streaming": True, "events": raw_events[-20:]}
        if dify_conversation_id:
            raw_response["conversation_id"] = dify_conversation_id
        await self._persist_stream_answer(db, conversation, payload, answer, raw_response, sources, dify_conversation_id)
        yield self._sse(
            {
                "event": "message_end",
                "conversation_id": conversation.conversation_id,
                "sources": [source.model_dump() for source in sources],
                "intent": payload.intent,
            }
        )

    async def list_conversations(self, db: AsyncSession, current_user: User) -> list[ChatSessionItem]:
        result = await db.execute(
            select(AIConversation)
            .where(AIConversation.user_id == current_user.id)
            .order_by(AIConversation.updated_at.desc())
        )
        return [
            ChatSessionItem(
                id=conversation.conversation_id,
                title=conversation.title,
                time=conversation.updated_at.strftime("%Y-%m-%d %H:%M") if conversation.updated_at else None,
            )
            for conversation in result.scalars().all()
        ]

    async def delete_conversation(self, db: AsyncSession, conversation_id: str, current_user: User) -> None:
        result = await db.execute(select(AIConversation).where(AIConversation.conversation_id == conversation_id))
        conversation = result.scalar_one_or_none()
        if conversation is None or conversation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到会话")
        await db.delete(conversation)
        await db.commit()

    async def upload_file_to_dify(self, upload: UploadFile, current_user: User) -> DifyUploadedFile:
        if not settings.dify_app_api_key:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dify API Key 未配置，无法上传文件")

        content = await upload.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件为空")

        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="上传文件超过大小限制")

        filename = upload.filename or "attachment"
        mime_type = upload.content_type or "application/octet-stream"
        user_key = current_user.student_id or current_user.username or str(current_user.id)
        try:
            async with httpx.AsyncClient(timeout=settings.dify_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.dify_app_api_base}/files/upload",
                    headers={"Authorization": f"Bearer {settings.dify_app_api_key}"},
                    data={"user": user_key},
                    files={"file": (filename, content, mime_type)},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text or str(exc)
            raise HTTPException(status_code=exc.response.status_code, detail=f"Dify 文件上传失败：{detail}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Dify 文件上传失败：{exc}") from exc

        data = response.json()
        return DifyUploadedFile(
            id=data["id"],
            name=data.get("name"),
            size=data.get("size"),
            extension=data.get("extension"),
            mime_type=data.get("mime_type"),
            type=self._dify_file_type(mime_type, filename),
        )

    async def get_history(self, db: AsyncSession, conversation_id: str, current_user: User) -> ChatHistoryResponse:
        result = await db.execute(
            select(AIConversation)
            .options(selectinload(AIConversation.messages))
            .where(AIConversation.conversation_id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None or conversation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到会话")

        messages = sorted(conversation.messages, key=lambda item: item.created_at)
        return ChatHistoryResponse(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            messages=[
                ChatMessageItem(
                    role=message.role,
                    content=message.content,
                    intent=message.intent,
                    sources=[ChatSource(**source) for source in (message.sources_json or [])],
                    need_personal_data=message.need_personal_data,
                )
                for message in messages
            ],
        )

    async def _get_or_create_conversation(
        self,
        db: AsyncSession,
        payload: SendChatRequest,
        current_user: User,
        student_id: str,
    ) -> AIConversation:
        if payload.conversation_id:
            result = await db.execute(
                select(AIConversation).where(AIConversation.conversation_id == payload.conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation is not None:
                if conversation.user_id != current_user.id:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该会话")
                return conversation

        conversation = AIConversation(
            conversation_id=payload.conversation_id or f"conv-{uuid4().hex}",
            user_id=current_user.id,
            student_id=student_id,
            title=payload.query[:50],
        )
        db.add(conversation)
        await db.flush()
        return conversation

    async def _build_progress_summary(self, db: AsyncSession, student_id: str) -> dict:
        try:
            progress = await graduation_progress_service.calculate(db, student_id)
            return progress.model_dump()
        except HTTPException as exc:
            return {"error": exc.detail, "studentId": student_id}

    def _build_inputs(self, payload: SendChatRequest, current_user: User, progress_summary: dict) -> dict:
        inputs = dict(payload.inputs or {})
        inputs.setdefault("student_id", payload.student_id or current_user.student_id)
        inputs.setdefault("major_code", payload.major_code or (current_user.major.major_code if current_user.major else ""))
        inputs.setdefault("major_name", payload.major_name or (current_user.major.major_name if current_user.major else ""))
        agent_session_token, expires_at = create_agent_session_token(current_user)
        inputs["agentSessionToken"] = agent_session_token
        inputs["agentSessionExpiresAt"] = expires_at.isoformat()
        inputs["progress_summary"] = progress_summary
        return inputs

    def _persistable_inputs(self, inputs: dict) -> dict:
        safe_inputs = dict(inputs)
        safe_inputs.pop("agentSessionToken", None)
        safe_inputs.pop("agent_session_token", None)
        safe_inputs.pop("agentSessionExpiresAt", None)
        return safe_inputs

    def _agent_thought_status(self, event: dict) -> str:
        tool = event.get("tool") or event.get("tool_name")
        observation = event.get("observation")
        thought = event.get("thought")
        tool_name = self._display_tool_name(tool)
        if tool_name and observation:
            return f"{tool_name} 已返回结果，正在整理回答"
        if tool_name:
            return f"正在调用工具：{tool_name}"
        if thought:
            return "Agent 正在分析是否需要调用工具"
        return ""

    def _display_tool_name(self, tool: Any) -> str:
        if not tool:
            return ""
        if isinstance(tool, dict):
            raw_name = tool.get("name") or tool.get("tool_name") or tool.get("provider")
        else:
            raw_name = str(tool)
        name = raw_name.strip()
        tool_names = {
            "get_current_agent_user": "查询当前用户",
            "get_student_academic_info": "查询学业详情",
            "get_student_graduation_progress": "查询毕业进度",
            "get_student_schedule": "查询课表",
            "get_student_time_plan_events": "查询时间规划",
            "create_time_plan_event": "创建时间规划事件",
            "update_time_plan_event": "更新时间规划事件",
            "list_forum_majors": "查询论坛专业",
            "list_forum_topics": "查询论坛帖子",
            "get_forum_topic": "查询帖子详情",
            "create_forum_topic": "发布论坛帖子",
            "update_forum_topic": "编辑论坛帖子",
            "create_forum_comment": "发表评论",
            "moderate_forum_topic": "治理论坛帖子",
            "admin_get_student_academic_info": "管理员查询学生学业详情",
            "admin_get_student_graduation_progress": "管理员查询学生毕业进度",
            "admin_get_student_schedule": "管理员查询学生课表",
            "admin_get_student_time_plan_events": "管理员查询学生时间规划",
        }
        return tool_names.get(name, name)

    def _sanitize_dify_event(self, event: dict) -> dict:
        return self._redact_sensitive_value(event)

    def _redact_sensitive_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: ("[redacted]" if key in {"agentSessionToken", "agent_session_token", "Authorization", "authorization"} else self._redact_sensitive_value(item))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._redact_sensitive_value(item) for item in value]
        if isinstance(value, str) and "agentSessionToken" in value:
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return value.replace("agentSessionToken", "agentSessionToken[redacted]")
            return json.dumps(self._redact_sensitive_value(parsed), ensure_ascii=False)
        return value

    async def _call_dify(self, query: str, dify_conversation_id: str | None, inputs: dict, user: str, files: list | None = None) -> dict:
        if not settings.dify_app_api_key:
            return {"answer": self._fallback_answer(query, inputs.get("progress_summary", {})), "fallback": True}

        dify_payload: dict = {
            "inputs": inputs,
            "query": query,
            "response_mode": "blocking",
            "user": user,
        }
        if files:
            dify_payload["files"] = [file.model_dump() for file in files]
        if dify_conversation_id:
            dify_payload["conversation_id"] = dify_conversation_id

        try:
            async with httpx.AsyncClient(timeout=settings.dify_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.dify_app_api_base}/chat-messages",
                    headers={"Authorization": f"Bearer {settings.dify_app_api_key}"},
                    json=dify_payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            return {
                "answer": self._fallback_answer(query, inputs.get("progress_summary", {})),
                "fallback": True,
                "error": str(exc),
            }

    def _extract_sources(self, dify_response: dict) -> list[ChatSource]:
        resources = dify_response.get("metadata", {}).get("retriever_resources", [])
        return [
            ChatSource(
                documentName=item.get("document_name") or item.get("dataset_name"),
                title=item.get("title") or item.get("document_name"),
                content=item.get("content"),
                score=item.get("score"),
            )
            for item in resources
        ]

    def _extract_output_text(self, event: dict) -> str:
        outputs = event.get("data", {}).get("outputs") or {}
        if isinstance(outputs, str):
            return outputs
        if not isinstance(outputs, dict):
            return ""
        for key in ("answer", "text", "output", "result"):
            value = outputs.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return ""

    def _dify_file_type(self, mime_type: str, filename: str) -> str:
        if mime_type.startswith("image/"):
            return "image"
        if mime_type.startswith("audio/"):
            return "audio"
        if mime_type.startswith("video/"):
            return "video"
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension in {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md", "csv"}:
            return "document"
        return "custom"

    def _fallback_answer(self, query: str, progress_summary: dict) -> str:
        if progress_summary.get("error"):
            return f"我已收到你的问题：{query}。但当前缺少个人学业数据：{progress_summary['error']}。"

        total_required = progress_summary.get("totalRequired", 0)
        total_earned = progress_summary.get("totalEarned", 0)
        total_gap = progress_summary.get("totalGap", 0)
        return (
            f"我已收到你的问题：{query}。当前可用的本地学业进度为："
            f"毕业要求 {total_required} 学分，已完成 {total_earned} 学分，缺口约 {total_gap} 学分。"
            "Dify 暂不可用时先返回本地摘要。"
        )

    async def _persist_stream_answer(
        self,
        db: AsyncSession,
        conversation: AIConversation,
        payload: SendChatRequest,
        answer: str,
        raw_response: dict,
        sources: list[ChatSource],
        dify_conversation_id: str | None = None,
    ) -> None:
        if dify_conversation_id:
            conversation.dify_conversation_id = dify_conversation_id
        conversation.last_intent = payload.intent
        db.add(
            AIMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=answer,
                intent=payload.intent,
                sources_json=[source.model_dump() for source in sources],
                need_personal_data=False,
                raw_response=raw_response,
            )
        )
        await db.commit()

    def _sse(self, payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


ai_chat_service = AIChatService()
