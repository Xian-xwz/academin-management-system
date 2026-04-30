from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ErrorCase(TimestampMixin, Base):
    """AI 问答错误案例，用于后续人工纠错和质量优化。"""

    __tablename__ = "error_cases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), comment="反馈用户 ID")
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="用户问题")
    wrong_answer: Mapped[str | None] = mapped_column(Text, comment="错误回答")
    expected_answer: Mapped[str | None] = mapped_column(Text, comment="期望回答")
    reason: Mapped[str | None] = mapped_column(Text, comment="错误原因或修正说明")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", comment="处理状态")
