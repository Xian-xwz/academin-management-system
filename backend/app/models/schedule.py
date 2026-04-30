from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Schedule(TimestampMixin, Base):
    """学生课表记录，支持按学期、周次和节次查询，并保存课程备注。"""

    __tablename__ = "schedules"
    __table_args__ = (
        Index("idx_schedule_week_query", "student_id", "semester", "start_week", "end_week"),
        Index("idx_schedule_grid", "student_id", "semester", "day_of_week", "start_section"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        index=True,
        comment="用户 ID",
    )
    student_id: Mapped[str] = mapped_column(String(30), index=True, nullable=False, comment="学号")
    course_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("courses.id"), comment="课程 ID")
    course_name: Mapped[str] = mapped_column(String(150), nullable=False, comment="课程名称")
    teacher: Mapped[str | None] = mapped_column(String(80), comment="授课教师")
    location: Mapped[str | None] = mapped_column(String(120), comment="上课地点")
    semester: Mapped[str] = mapped_column(String(50), index=True, nullable=False, comment="学期")
    weeks_text: Mapped[str | None] = mapped_column(String(100), comment="周次文本，例如 1-16周")
    start_week: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="开始周")
    end_week: Mapped[int] = mapped_column(Integer, nullable=False, default=20, comment="结束周")
    week_pattern: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="all",
        server_default="all",
        comment="周次规则：all/odd/even/custom",
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False, comment="星期几：1-7")
    start_section: Mapped[int] = mapped_column(Integer, nullable=False, comment="开始节次")
    end_section: Mapped[int] = mapped_column(Integer, nullable=False, comment="结束节次")
    note: Mapped[str | None] = mapped_column(Text, comment="课程备注")

    course: Mapped["Course | None"] = relationship()
