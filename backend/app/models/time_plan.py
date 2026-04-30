from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TimePlanEvent(TimestampMixin, Base):
    """时间规划事件，覆盖课程、考试、作业和个人事项。"""

    __tablename__ = "time_plan_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        index=True,
        comment="用户 ID",
    )
    student_id: Mapped[str] = mapped_column(String(30), index=True, nullable=False, comment="学号")
    title: Mapped[str] = mapped_column(String(150), nullable=False, comment="事件标题")
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="事件类型：课程/考试/作业/个人")
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False, comment="开始时间")
    end_time: Mapped[datetime | None] = mapped_column(DateTime, comment="结束时间")
    location: Mapped[str | None] = mapped_column(String(120), comment="地点")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    reminder_time: Mapped[datetime | None] = mapped_column(DateTime, comment="提醒时间")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="待开始", comment="状态")
    source_type: Mapped[str | None] = mapped_column(String(30), comment="来源：manual/schedule_sync")
    source_id: Mapped[int | None] = mapped_column(BigInteger, comment="来源记录 ID")
