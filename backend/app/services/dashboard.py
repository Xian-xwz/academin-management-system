from __future__ import annotations

from datetime import datetime
from random import choice

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import AIConversation, AIMessage, ForumComment, ForumTopic, ForumTopicLike, User
from app.schemas.dashboard import DashboardNotificationItem


class DashboardService:
    async def generate_login_mock_activity(self, db: AsyncSession, current_user: User) -> None:
        if not settings.mock_dynamic_enabled or current_user.role != "student":
            return

        await self._generate_forum_dynamic(db, current_user)
        await self._generate_ai_history_hint(db, current_user)
        await db.commit()

    async def _generate_forum_dynamic(self, db: AsyncSession, current_user: User) -> None:
        if current_user.major_id is None:
            return

        major_name = current_user.major.major_name if current_user.major else "本专业"
        actor_result = await db.execute(
            select(User)
            .options(selectinload(User.major))
            .where(
                User.id != current_user.id,
                User.is_active.is_(True),
                User.role == "student",
            )
            .order_by(User.updated_at.desc())
            .limit(12)
        )
        actors = list(actor_result.scalars().all())
        actor = choice(actors) if actors else current_user

        topic_result = await db.execute(
            select(ForumTopic)
            .where(
                ForumTopic.major_id == current_user.major_id,
                ForumTopic.status == "normal",
            )
            .order_by(ForumTopic.updated_at.desc())
            .limit(6)
        )
        topics = list(topic_result.scalars().all())

        should_create_topic = len(topics) < 2 or datetime.now().second % 3 == 0
        if should_create_topic:
            title, summary, content, tags = await self._build_mock_topic(current_user, major_name)
            topic = ForumTopic(
                user_id=current_user.id,
                major_id=current_user.major_id,
                title=title,
                summary=summary,
                content=content,
                tags_json=tags,
                view_count=1,
            )
            db.add(topic)
            await db.flush()
            topics.append(topic)

        if not topics:
            return

        topic = choice(topics)
        content = await self._build_mock_comment(actor, topic, major_name)
        db.add(ForumComment(topic_id=topic.id, user_id=actor.id, content=content))
        topic.comment_count += 1
        topic.view_count += 1

        like_result = await db.execute(
            select(ForumTopicLike).where(ForumTopicLike.topic_id == topic.id, ForumTopicLike.user_id == actor.id)
        )
        if like_result.scalar_one_or_none() is None:
            db.add(ForumTopicLike(topic_id=topic.id, user_id=actor.id))
            topic.like_count += 1

    async def _generate_ai_history_hint(self, db: AsyncSession, current_user: User) -> None:
        topic_result = await db.execute(
            select(ForumTopic)
            .where(ForumTopic.user_id == current_user.id, ForumTopic.status == "normal")
            .order_by(ForumTopic.updated_at.desc())
            .limit(2)
        )
        own_topics = list(topic_result.scalars().all())

        actor_result = await db.execute(
            select(User)
            .where(User.id != current_user.id, User.is_active.is_(True))
            .order_by(User.updated_at.desc())
            .limit(6)
        )
        actors = list(actor_result.scalars().all())
        actor = choice(actors) if actors else None

        comment_templates = [
            "我也在看这部分内容，感觉这个资料对复习挺有帮助。",
            "这个问题我之前也遇到过，可以结合培养方案里的课程模块一起看。",
            "感谢分享，后面如果整理出答案我也会补充到评论区。",
        ]
        for topic in own_topics:
            topic.view_count += 1
            if actor is not None:
                content = f"{choice(comment_templates)}（模拟互动 {datetime.now().strftime('%H:%M:%S')}）"
                db.add(ForumComment(topic_id=topic.id, user_id=actor.id, content=content))
                topic.comment_count += 1
                like_result = await db.execute(
                    select(ForumTopicLike).where(ForumTopicLike.topic_id == topic.id, ForumTopicLike.user_id == actor.id)
                )
                if like_result.scalar_one_or_none() is None:
                    db.add(ForumTopicLike(topic_id=topic.id, user_id=actor.id))
                    topic.like_count += 1

        if current_user.student_id == "202211911001":
            title = f"AI 问询：登录模拟提醒 {datetime.now().strftime('%H:%M')}"
            conversation = AIConversation(
                conversation_id=f"mock-login-{current_user.id}-{int(datetime.now().timestamp())}",
                user_id=current_user.id,
                student_id=current_user.student_id,
                title=title,
                last_intent="general_qa",
            )
            db.add(conversation)
            await db.flush()
            db.add(
                AIMessage(
                    conversation_id=conversation.id,
                    role="assistant",
                    content="这是一条登录时生成的 AI 问询模拟提醒，用于首页通知演示。",
                    intent="general_qa",
                )
            )

    async def _build_mock_topic(self, current_user: User, major_name: str) -> tuple[str, str, str, list[str]]:
        prompt = (
            f"请以{major_name}学生的口吻，生成一个学业管理系统论坛帖子。"
            "要求返回 JSON：title、summary、content、tags。"
            "内容聚焦课程复习、培养方案、毕业学分、课表安排或实践环节；自然像真实学生，不要提到你是 AI。"
        )
        generated = await self._call_mock_llm(prompt)
        if generated and isinstance(generated.get("title"), str) and isinstance(generated.get("content"), str):
            title = generated["title"].strip()[:100]
            content = generated["content"].strip()[:800]
            summary = str(generated.get("summary") or content[:80]).strip()[:160]
            tags_raw = generated.get("tags") or [major_name, "学业交流"]
            tags = [str(tag).strip()[:20] for tag in tags_raw if str(tag).strip()][:5] if isinstance(tags_raw, list) else [major_name, "学业交流"]
            return title, summary, content, tags

        topic_templates = [
            (
                f"{major_name}培养方案自查：哪些模块最容易漏？",
                "登录系统看了毕业进度，想和同专业同学核对一下模块学分。",
                f"我刚用系统查了{major_name}的毕业进度，发现除了总学分，还要看通识、专业限选和实践教学这些模块。大家平时自查时最容易漏哪一块？",
                [major_name, "毕业要求", "学分自查"],
            ),
            (
                f"{major_name}这学期课表和复习节奏怎么排？",
                "想交流一下课程复习、作业和实践任务的时间安排。",
                f"这学期{major_name}的课程任务有点集中，我打算按周次把课表、作业和复习放进时间规划里。有没有同学已经整理出比较稳的安排？",
                [major_name, "课表", "时间规划"],
            ),
        ]
        return choice(topic_templates)

    async def _build_mock_comment(self, actor: User, topic: ForumTopic, major_name: str) -> str:
        prompt = (
            f"请以{major_name}学生的口吻，给论坛帖子《{topic.title}》写一条 40 字以内的自然评论。"
            "内容要具体、有同学交流感，不要提到你是 AI，不要使用 Markdown。"
        )
        generated = await self._call_mock_llm(prompt, expect_json=False)
        if isinstance(generated, str) and generated.strip():
            return generated.strip()[:120]

        templates = [
            f"我也在看{major_name}这块要求，感觉先把模块学分核清楚会稳很多。",
            "这个问题我之前也遇到过，可以结合培养方案和已修课程一起核对。",
            "感谢分享，我准备登录系统看一下自己的进度，再回来补充一下情况。",
        ]
        return f"{choice(templates)}（模拟互动 {datetime.now().strftime('%H:%M:%S')}）"

    async def _call_mock_llm(self, prompt: str, *, expect_json: bool = True) -> dict | str | None:
        if not settings.mock_dynamic_use_llm:
            return None

        payload: dict = {
            "model": settings.dashscope_model,
            "messages": [
                {"role": "system", "content": "你负责为毕业设计演示系统生成真实、克制、无敏感信息的校园论坛动态。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 500 if expect_json else 120,
        }

        content = await self._call_dashscope(payload)
        if content is None:
            content = await self._call_gemini(prompt, expect_json=expect_json)
        if content is None:
            return None

        if not expect_json:
            return content

        try:
            import json

            return json.loads(content)
        except (TypeError, ValueError):
            return None

    async def _call_dashscope(self, payload: dict) -> str | None:
        if not settings.dashscope_api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.post(
                    f"{settings.dashscope_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.dashscope_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, httpx.HTTPError):
            return None

    async def _call_gemini(self, prompt: str, *, expect_json: bool) -> str | None:
        if not settings.gemini_api_key:
            return None

        gemini_prompt = prompt
        if expect_json:
            gemini_prompt += "\n只输出 JSON 对象，不要输出 Markdown 代码块。"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": gemini_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 500 if expect_json else 120,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
                    params={"key": settings.gemini_api_key},
                    json=payload,
                )
                response.raise_for_status()
            parts = response.json()["candidates"][0]["content"]["parts"]
            return "".join(str(part.get("text", "")) for part in parts).strip()
        except (KeyError, IndexError, httpx.HTTPError):
            return None

    async def list_notifications(self, db: AsyncSession, current_user: User) -> list[DashboardNotificationItem]:
        notifications: list[DashboardNotificationItem] = []

        topic_result = await db.execute(select(ForumTopic).where(ForumTopic.user_id == current_user.id, ForumTopic.status == "normal"))
        own_topics = list(topic_result.scalars().all())
        topic_map = {topic.id: topic for topic in own_topics}
        topic_ids = list(topic_map.keys())

        if topic_ids:
            comment_result = await db.execute(
                select(ForumComment)
                .where(ForumComment.topic_id.in_(topic_ids), ForumComment.user_id != current_user.id, ForumComment.status == "normal")
                .order_by(ForumComment.created_at.desc())
                .limit(5)
            )
            for comment in comment_result.scalars().all():
                author = await self._author_name(db, comment.user_id)
                topic = topic_map.get(comment.topic_id)
                if topic:
                    notifications.append(
                        DashboardNotificationItem(
                            id=f"forum-comment-{comment.id}",
                            type="forum_comment",
                            title="论坛回复通知",
                            content=f"“{author}” 回复了你的帖子《{topic.title}》",
                            time=comment.created_at,
                            targetUrl=f"/forum/topics/{topic.id}",
                        )
                    )

            like_result = await db.execute(
                select(ForumTopicLike)
                .where(ForumTopicLike.topic_id.in_(topic_ids), ForumTopicLike.user_id != current_user.id)
                .order_by(ForumTopicLike.created_at.desc())
                .limit(5)
            )
            for like in like_result.scalars().all():
                topic = topic_map.get(like.topic_id)
                if topic:
                    notifications.append(
                        DashboardNotificationItem(
                            id=f"forum-like-{like.id}",
                            type="forum_like",
                            title="收到点赞",
                            content=f"你的帖子《{topic.title}》收到了新的点赞",
                            time=like.created_at,
                            targetUrl=f"/forum/topics/{topic.id}",
                        )
                    )

        ai_result = await db.execute(
            select(AIConversation)
            .where(AIConversation.user_id == current_user.id)
            .order_by(AIConversation.updated_at.desc())
            .limit(3)
        )
        for conversation in ai_result.scalars().all():
            notifications.append(
                DashboardNotificationItem(
                    id=f"ai-conversation-{conversation.id}",
                    type="ai_chat",
                    title="AI 问询记录",
                    content=f"最近一次问询《{conversation.title or '未命名会话'}》已保存到历史会话",
                    time=conversation.updated_at,
                    targetUrl="/ai-chat",
                )
            )

        notifications.sort(key=lambda item: item.time or datetime.min, reverse=True)
        return notifications[:8]

    async def _author_name(self, db: AsyncSession, user_id: int) -> str:
        user = await db.get(User, user_id)
        return user.real_name or user.username if user else "同学"


dashboard_service = DashboardService()
