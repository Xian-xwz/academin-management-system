from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.academic import AcademicInfoResponse, GraduationProgressResponse
from app.services.academic import graduation_progress_service


router = APIRouter(prefix="/student", tags=["student"])


def _ensure_self_or_admin(current_user: User, student_id: str) -> None:
    if current_user.role == "admin" or current_user.student_id == student_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能查询本人学业信息")


@router.get("/{student_id}/academic-info")
async def get_academic_info(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _ensure_self_or_admin(current_user, student_id)
    return success((await graduation_progress_service.get_academic_info(db, student_id)).model_dump())


@router.get("/{student_id}/graduation-progress")
async def get_graduation_progress(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _ensure_self_or_admin(current_user, student_id)
    return success((await graduation_progress_service.calculate(db, student_id)).model_dump())
