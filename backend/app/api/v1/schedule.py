from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.schedule import UpdateCourseNoteRequest
from app.services.schedule import schedule_service


router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("")
async def get_schedule(
    term: str = Query(...),
    week: int = Query(1, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await schedule_service.get_schedule(db, current_user, term, week)).model_dump())


@router.patch("/{schedule_id}/note")
async def update_course_note(
    schedule_id: int,
    payload: UpdateCourseNoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await schedule_service.update_note(db, current_user, schedule_id, payload.note)).model_dump())
