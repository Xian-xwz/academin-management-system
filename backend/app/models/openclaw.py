from __future__ import annotations

from sqlalchemy import BigInteger, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class OpenClawToolAudit(TimestampMixin, Base):
    """OpenClaw 受控工具调用审计记录。"""

    __tablename__ = "openclaw_tool_audits"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    caller: Mapped[str] = mapped_column(String(50), nullable=False, default="openclaw", comment="调用方")
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="工具名")
    student_id: Mapped[str | None] = mapped_column(String(30), index=True, comment="目标学生学号")
    request_summary: Mapped[dict | None] = mapped_column(JSON, comment="请求摘要，不保存密钥")
    response_status: Mapped[int] = mapped_column(Integer, nullable=False, comment="HTTP 响应状态码")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="调用耗时毫秒")
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误摘要")
