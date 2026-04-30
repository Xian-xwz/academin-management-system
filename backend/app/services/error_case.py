from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ErrorCase, User
from app.schemas.ai import ErrorCaseCreate, ErrorCaseItem, ErrorCaseStatusUpdate


VALID_STATUSES = {"pending", "reviewed", "fixed", "ignored"}


class ErrorCaseService:
    async def create_case(self, db: AsyncSession, current_user: User, payload: ErrorCaseCreate) -> ErrorCaseItem:
        case = ErrorCase(
            user_id=current_user.id,
            question=payload.question,
            wrong_answer=payload.wrong_answer,
            expected_answer=payload.expected_answer,
            reason=payload.reason,
            status="pending",
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)
        return self._to_item(case)

    async def list_cases(self, db: AsyncSession, current_user: User) -> list[ErrorCaseItem]:
        stmt = select(ErrorCase).order_by(ErrorCase.created_at.desc())
        if current_user.role != "admin":
            stmt = stmt.where(ErrorCase.user_id == current_user.id)
        result = await db.execute(stmt)
        return [self._to_item(item) for item in result.scalars().all()]

    async def update_status(self, db: AsyncSession, current_user: User, case_id: int, payload: ErrorCaseStatusUpdate) -> ErrorCaseItem:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="错误案例状态不合法")
        case = await db.get(ErrorCase, case_id)
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到错误案例")
        if current_user.role != "admin" and case.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该错误案例")
        case.status = payload.status
        await db.commit()
        return self._to_item(case)

    def _to_item(self, case: ErrorCase) -> ErrorCaseItem:
        return ErrorCaseItem(
            id=case.id,
            question=case.question,
            wrong_answer=case.wrong_answer,
            expected_answer=case.expected_answer,
            reason=case.reason,
            status=case.status,
        )


error_case_service = ErrorCaseService()
