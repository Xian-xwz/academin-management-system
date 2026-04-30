from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Schedule, User
from app.schemas.schedule import ScheduleCourseItem, ScheduleResponse


class ScheduleService:
    async def get_schedule(self, db: AsyncSession, current_user: User, term: str, week: int) -> ScheduleResponse:
        result = await db.execute(
            select(Schedule)
            .where(
                Schedule.student_id == current_user.student_id,
                Schedule.semester == term,
                Schedule.start_week <= week,
                Schedule.end_week >= week,
            )
            .order_by(Schedule.day_of_week, Schedule.start_section)
        )
        schedules = [
            item
            for item in result.scalars().all()
            if item.week_pattern == "all"
            or (item.week_pattern == "odd" and week % 2 == 1)
            or (item.week_pattern == "even" and week % 2 == 0)
            or item.week_pattern == "custom"
        ]
        return ScheduleResponse(
            term=term,
            week=week,
            courses=[self._to_item(item) for item in schedules],
        )

    async def update_note(self, db: AsyncSession, current_user: User, schedule_id: int, note: str | None) -> ScheduleCourseItem:
        schedule = await db.get(Schedule, schedule_id)
        if schedule is None or schedule.student_id != current_user.student_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到课表记录")
        schedule.note = note
        await db.commit()
        return self._to_item(schedule)

    def _to_item(self, item: Schedule) -> ScheduleCourseItem:
        return ScheduleCourseItem(
            id=item.id,
            name=item.course_name,
            teacher=item.teacher,
            location=item.location,
            day=item.day_of_week,
            sections=list(range(item.start_section, item.end_section + 1)),
            weeks=item.weeks_text,
            note=item.note,
        )


schedule_service = ScheduleService()
