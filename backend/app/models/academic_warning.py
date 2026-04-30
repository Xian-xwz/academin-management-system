from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class AcademicWarning(TimestampMixin, Base):
    """管理员发送给学生的一次性登录弹窗预警。"""

    __tablename__ = "academic_warnings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        index=True,
        nullable=False,
        comment="接收预警的用户 ID",
    )
    student_id: Mapped[str] = mapped_column(String(30), index=True, nullable=False, comment="接收预警的学号")
    title: Mapped[str] = mapped_column(String(150), nullable=False, comment="预警标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="预警内容")
    shown_at: Mapped[datetime | None] = mapped_column(DateTime, index=True, comment="登录弹窗展示时间；为空表示待展示")
