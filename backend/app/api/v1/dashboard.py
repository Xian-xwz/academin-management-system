from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.services.dashboard import dashboard_service


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/notifications")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success([item.model_dump() for item in await dashboard_service.list_notifications(db, current_user)])
