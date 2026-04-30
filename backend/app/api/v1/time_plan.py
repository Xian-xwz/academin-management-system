from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.time_plan import TimePlanEventCreate, TimePlanEventUpdate
from app.services.time_plan import time_plan_service


router = APIRouter(prefix="/time-plan", tags=["time-plan"])


@router.get("/events")
async def list_events(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success([item.model_dump() for item in await time_plan_service.list_events(db, current_user)])


@router.post("/events")
async def create_event(
    payload: TimePlanEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await time_plan_service.create_event(db, current_user, payload)).model_dump())


@router.put("/events/{event_id}")
async def update_event(
    event_id: int,
    payload: TimePlanEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await time_plan_service.update_event(db, current_user, event_id, payload)).model_dump())


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success(await time_plan_service.delete_event(db, current_user, event_id))


@router.post("/sync-from-schedule")
async def sync_from_schedule(
    term: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success(await time_plan_service.sync_from_schedule(db, current_user, term))
