from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Schedule, TimePlanEvent, User
from app.schemas.time_plan import TimePlanEventCreate, TimePlanEventItem, TimePlanEventUpdate


class TimePlanService:
    async def list_events(self, db: AsyncSession, current_user: User) -> list[TimePlanEventItem]:
        result = await db.execute(
            select(TimePlanEvent)
            .where(TimePlanEvent.student_id == current_user.student_id)
            .order_by(TimePlanEvent.start_time)
        )
        return [self._to_item(item) for item in result.scalars().all()]

    async def create_event(self, db: AsyncSession, current_user: User, payload: TimePlanEventCreate) -> TimePlanEventItem:
        event = TimePlanEvent(
            user_id=current_user.id,
            student_id=current_user.student_id,
            title=payload.title,
            event_type=payload.type,
            start_time=payload.startTime,
            end_time=payload.endTime,
            location=payload.location,
            description=payload.desc,
            status=payload.status,
            source_type="manual",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return self._to_item(event)

    async def update_event(self, db: AsyncSession, current_user: User, event_id: int, payload: TimePlanEventUpdate) -> TimePlanEventItem:
        event = await self._get_owned_event(db, current_user, event_id)
        update_data = payload.model_dump(exclude_unset=True)
        mapping = {"type": "event_type", "startTime": "start_time", "endTime": "end_time", "desc": "description"}
        for key, value in update_data.items():
            setattr(event, mapping.get(key, key), value)
        await db.commit()
        return self._to_item(event)

    async def delete_event(self, db: AsyncSession, current_user: User, event_id: int) -> dict[str, int]:
        event = await self._get_owned_event(db, current_user, event_id)
        await db.delete(event)
        await db.commit()
        return {"id": event_id}

    async def sync_from_schedule(self, db: AsyncSession, current_user: User, term: str) -> dict[str, int]:
        result = await db.execute(
            select(Schedule).where(Schedule.student_id == current_user.student_id, Schedule.semester == term)
        )
        synced = 0
        for schedule in result.scalars().all():
            exists = await db.execute(
                select(TimePlanEvent).where(
                    TimePlanEvent.student_id == current_user.student_id,
                    TimePlanEvent.source_type == "schedule_sync",
                    TimePlanEvent.source_id == schedule.id,
                )
            )
            if exists.scalar_one_or_none() is not None:
                continue
            start_time = datetime(2026, 3, min(schedule.day_of_week, 7), 8, 0)
            event = TimePlanEvent(
                user_id=current_user.id,
                student_id=current_user.student_id,
                title=schedule.course_name,
                event_type="课程",
                start_time=start_time,
                end_time=start_time + timedelta(minutes=100),
                location=schedule.location,
                description=schedule.weeks_text,
                status="待开始",
                source_type="schedule_sync",
                source_id=schedule.id,
            )
            db.add(event)
            synced += 1
        await db.commit()
        return {"synced": synced}

    async def _get_owned_event(self, db: AsyncSession, current_user: User, event_id: int) -> TimePlanEvent:
        event = await db.get(TimePlanEvent, event_id)
        if event is None or event.student_id != current_user.student_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到时间规划事件")
        return event

    def _to_item(self, event: TimePlanEvent) -> TimePlanEventItem:
        return TimePlanEventItem(
            id=event.id,
            title=event.title,
            type=event.event_type,
            startTime=event.start_time,
            endTime=event.end_time,
            location=event.location,
            desc=event.description,
            status=event.status,
            sourceType=event.source_type,
            sourceId=event.source_id,
        )


time_plan_service = TimePlanService()
