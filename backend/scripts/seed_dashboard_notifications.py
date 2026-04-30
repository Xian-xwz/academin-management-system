from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import AsyncSessionLocal, async_engine
from app.models import AIConversation, AIMessage, ForumComment, ForumTopic, ForumTopicLike, User


TARGET_STUDENT_ID = "202211911001"
ACTOR_STUDENT_ID = "202211911002"


async def main() -> None:
    async with AsyncSessionLocal() as session:
        target = await _get_user(session, TARGET_STUDENT_ID)
        actor = await _get_user(session, ACTOR_STUDENT_ID)

        topic_result = await session.execute(
            select(ForumTopic)
            .where(ForumTopic.user_id == target.id, ForumTopic.status == "normal")
            .order_by(ForumTopic.created_at.desc())
        )
        topic = topic_result.scalars().first()
        if topic is None:
            raise RuntimeError(f"{TARGET_STUDENT_ID} 还没有可用于通知演示的论坛话题")

        comment_text = "我也在看这部分资料，感觉可以结合课件里的典型题一起复习。"
        comment_result = await session.execute(
            select(ForumComment).where(
                ForumComment.topic_id == topic.id,
                ForumComment.user_id == actor.id,
                ForumComment.content == comment_text,
            )
        )
        if comment_result.scalar_one_or_none() is None:
            session.add(ForumComment(topic_id=topic.id, user_id=actor.id, content=comment_text))
            topic.comment_count += 1

        like_result = await session.execute(
            select(ForumTopicLike).where(ForumTopicLike.topic_id == topic.id, ForumTopicLike.user_id == actor.id)
        )
        if like_result.scalar_one_or_none() is None:
            session.add(ForumTopicLike(topic_id=topic.id, user_id=actor.id))
            topic.like_count += 1

        title = "AI 问询：2022级电科毕业条件复核"
        conversation_result = await session.execute(
            select(AIConversation).where(AIConversation.user_id == target.id, AIConversation.title == title)
        )
        conversation = conversation_result.scalar_one_or_none()
        if conversation is None:
            conversation = AIConversation(
                conversation_id=f"conv-{uuid4().hex}",
                user_id=target.id,
                student_id=target.student_id,
                title=title,
                last_intent="graduation_requirements",
            )
            session.add(conversation)
            await session.flush()
            session.add_all(
                [
                    AIMessage(
                        conversation_id=conversation.id,
                        role="user",
                        content="我想确认 2022 级电科毕业条件和实践学分要求。",
                        intent="graduation_requirements",
                    ),
                    AIMessage(
                        conversation_id=conversation.id,
                        role="assistant",
                        content="已根据本地培养方案记录你的毕业条件问询，可在 AI 历史会话中继续追问。",
                        intent="graduation_requirements",
                    ),
                ]
            )

        await session.commit()
        print(f"dashboard_notifications_seeded target={TARGET_STUDENT_ID} topic_id={topic.id}")

    await async_engine.dispose()


async def _get_user(session, student_id: str) -> User:
    result = await session.execute(select(User).where(User.student_id == student_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise RuntimeError(f"找不到演示账号：{student_id}")
    return user


if __name__ == "__main__":
    asyncio.run(main())
