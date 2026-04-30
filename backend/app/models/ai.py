from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class AIConversation(TimestampMixin, Base):
    """本地 AI 会话，关联前端 conversation_id 与 Dify 会话 ID。"""

    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="前端会话 ID",
    )
    dify_conversation_id: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        comment="Dify 返回的会话 ID",
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        index=True,
        comment="用户 ID",
    )
    student_id: Mapped[str | None] = mapped_column(String(30), index=True, comment="学号快照")
    title: Mapped[str | None] = mapped_column(String(200), comment="会话标题")
    last_intent: Mapped[str | None] = mapped_column(String(50), comment="最近一次意图")
    inputs_json: Mapped[dict | None] = mapped_column(JSON, comment="传给 Dify 的业务变量快照")

    messages: Mapped[list["AIMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class AIMessage(TimestampMixin, Base):
    """AI 会话消息记录，保存用户问题、助手回答和知识来源。"""

    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ai_conversations.id"),
        index=True,
        nullable=False,
        comment="本地会话表 ID",
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="角色：user/assistant/system")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    intent: Mapped[str | None] = mapped_column(String(50), comment="识别出的业务意图")
    sources_json: Mapped[list | None] = mapped_column(JSON, comment="知识来源列表")
    need_personal_data: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否提示需要个人学业数据",
    )
    raw_response: Mapped[dict | None] = mapped_column(JSON, comment="Dify 或 fallback 原始响应")

    conversation: Mapped[AIConversation] = relationship(back_populates="messages")
