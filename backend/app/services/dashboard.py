from __future__ import annotations

from datetime import datetime
from random import choice

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIConversation, AIMessage, ForumComment, ForumTopic, ForumTopicLike, User
from app.schemas.dashboard import DashboardNotificationItem


class DashboardService:
    async def generate_login_mock_activity(self, db: AsyncSession, current_user: User) -> None:
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

        await db.commit()

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
