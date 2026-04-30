from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.core.security import require_admin
from app.db.session import get_db
from app.models import User
from app.schemas.admin import AdminAcademicWarningCreate, AdminForumTopicStatusUpdate
from app.services.academic import graduation_progress_service
from app.services.admin import admin_service


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> dict:
    return success((await admin_service.dashboard_summary(db)).model_dump())


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
    q: str | None = None,
    major_code: str | None = Query(None, alias="majorCode"),
    role: str | None = None,
    is_active: bool | None = Query(None, alias="isActive"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> dict:
    result = await admin_service.list_users(
        db,
        page=page,
        page_size=page_size,
        q=q,
        major_code=major_code,
        role=role,
        is_active=is_active,
    )
    return success(result.model_dump())


@router.get("/users/{student_id}")
async def get_user_detail(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> dict:
    return success((await admin_service.get_user_detail(db, student_id)).model_dump())


@router.get("/users/{student_id}/academic-info")
async def get_user_academic_info(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> dict:
    return success((await graduation_progress_service.get_academic_info(db, student_id)).model_dump())


@router.get("/users/{student_id}/graduation-progress")
async def get_user_graduation_progress(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> dict:
    return success((await graduation_progress_service.calculate(db, student_id)).model_dump())


@router.post("/users/{student_id}/warnings")
async def send_academic_warning(
    student_id: str,
    payload: AdminAcademicWarningCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> dict:
    return success((await admin_service.send_academic_warning(db, student_id, payload)).model_dump())


@router.get("/forum/topics")
async def list_forum_topics(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
    q: str | None = None,
    status_value: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> dict:
    result = await admin_service.list_forum_topics(db, page=page, page_size=page_size, q=q, status_value=status_value)
    return success(result.model_dump())


@router.delete("/forum/topics/{topic_id}")
async def hide_forum_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> dict:
    return success(await admin_service.hide_forum_topic(db, topic_id))


@router.patch("/forum/topics/{topic_id}")
async def update_forum_topic_status(
    topic_id: int,
    payload: AdminForumTopicStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> dict:
    try:
        status_value = payload.normalized_status()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return success(await admin_service.set_forum_topic_status(db, topic_id, status_value))
