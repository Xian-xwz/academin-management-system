from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import OpenClawClient
from app.models import OpenClawToolAudit, User

T = TypeVar("T")


class OpenClawToolService:
    async def require_allowed_student(self, db: AsyncSession, student_id: str) -> User:
        if not self._is_student_allowed(student_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该学生未授权给 OpenClaw 工具访问")

        result = await db.execute(
            select(User)
            .options(selectinload(User.major))
            .where(User.student_id == student_id, User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该学号对应的启用用户")
        return user

    async def check_database(self, db: AsyncSession) -> bool:
        await db.execute(text("SELECT 1"))
        return True

    async def run_with_audit(
        self,
        db: AsyncSession,
        client: OpenClawClient,
        tool_name: str,
        student_id: str | None,
        request_summary: dict | None,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        started_at = perf_counter()
        try:
            result = await operation()
        except HTTPException as exc:
            await self.record_audit(
                db=db,
                client=client,
                tool_name=tool_name,
                student_id=student_id,
                request_summary=request_summary,
                response_status=exc.status_code,
                duration_ms=self._duration_ms(started_at),
                error_message=str(exc.detail),
            )
            raise
        except Exception as exc:
            await self.record_audit(
                db=db,
                client=client,
                tool_name=tool_name,
                student_id=student_id,
                request_summary=request_summary,
                response_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                duration_ms=self._duration_ms(started_at),
                error_message=type(exc).__name__,
            )
            raise

        await self.record_audit(
            db=db,
            client=client,
            tool_name=tool_name,
            student_id=student_id,
            request_summary=request_summary,
            response_status=status.HTTP_200_OK,
            duration_ms=self._duration_ms(started_at),
            error_message=None,
        )
        return result

    async def record_audit(
        self,
        db: AsyncSession,
        client: OpenClawClient,
        tool_name: str,
        student_id: str | None,
        request_summary: dict | None,
        response_status: int,
        duration_ms: int,
        error_message: str | None,
    ) -> None:
        db.add(
            OpenClawToolAudit(
                caller=client.name,
                tool_name=tool_name,
                student_id=student_id,
                request_summary=request_summary,
                response_status=response_status,
                duration_ms=duration_ms,
                error_message=error_message,
            )
        )
        await db.commit()

    def _is_student_allowed(self, student_id: str) -> bool:
        allowed = settings.openclaw_allowed_student_ids
        return "*" in allowed or student_id in allowed

    def _duration_ms(self, started_at: float) -> int:
        return max(round((perf_counter() - started_at) * 1000), 0)


openclaw_tool_service = OpenClawToolService()
