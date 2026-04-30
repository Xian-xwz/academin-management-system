from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, hash_password, verify_password
from app.models import AcademicWarning, Major, User
from app.schemas.auth import AcademicWarningPopup, AuthResponse, LoginRequest, RegisterRequest, UserInfo
from app.services.dashboard import dashboard_service


def build_user_info(user: User) -> UserInfo:
    return UserInfo(
        id=user.id,
        username=user.username,
        name=user.real_name or user.username,
        studentId=user.student_id,
        avatarUrl=user.avatar_url,
        majorCode=user.major.major_code if user.major else None,
        majorName=user.major.major_name if user.major else None,
        grade=user.grade,
        role=user.role,
    )


class AuthService:
    async def register(self, db: AsyncSession, payload: RegisterRequest) -> AuthResponse:
        student_id = payload.student_id.strip()
        result = await db.execute(select(User).where(User.student_id == student_id))
        if result.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该学号已注册")

        major: Major | None = None
        if payload.major_code:
            major_result = await db.execute(select(Major).where(Major.major_code == payload.major_code.strip()))
            major = major_result.scalar_one_or_none()
            if major is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="专业代码不存在")

        user = User(
            username=student_id,
            student_id=student_id,
            password_hash=hash_password(payload.password),
            real_name=payload.real_name,
            email=payload.email,
            major_id=major.id if major else None,
            grade=payload.grade,
        )
        db.add(user)
        await db.commit()

        refreshed = await db.execute(
            select(User)
            .options(selectinload(User.major))
            .where(User.id == user.id)
        )
        user_with_major = refreshed.scalar_one()
        return AuthResponse(token=create_access_token(str(user_with_major.id)), userInfo=build_user_info(user_with_major))

    async def login(self, db: AsyncSession, payload: LoginRequest) -> AuthResponse:
        result = await db.execute(
            select(User)
            .options(selectinload(User.major))
            .where(User.username == payload.username.strip(), User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="学号或密码错误")

        await dashboard_service.generate_login_mock_activity(db, user)
        pending_warnings = await self._pop_pending_academic_warnings(db, user)
        return AuthResponse(
            token=create_access_token(str(user.id)),
            userInfo=build_user_info(user),
            pendingAcademicWarnings=pending_warnings,
        )

    async def _pop_pending_academic_warnings(self, db: AsyncSession, user: User) -> list[AcademicWarningPopup]:
        if user.role != "student":
            return []
        result = await db.execute(
            select(AcademicWarning)
            .where(AcademicWarning.user_id == user.id, AcademicWarning.shown_at.is_(None))
            .order_by(AcademicWarning.created_at.asc())
        )
        warnings = list(result.scalars().all())
        if not warnings:
            return []

        now = datetime.now()
        for warning in warnings:
            warning.shown_at = now
        await db.commit()
        return [AcademicWarningPopup(id=warning.id, title=warning.title, content=warning.content) for warning in warnings]


auth_service = AuthService()
