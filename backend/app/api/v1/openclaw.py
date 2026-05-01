from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.responses import success
from app.core.security import OpenClawClient, require_openclaw_client
from app.db.session import get_db
from app.schemas.ai import SendChatRequest
from app.services.academic import graduation_progress_service
from app.services.ai import ai_chat_service
from app.services.openclaw import openclaw_tool_service
from app.services.schedule import schedule_service
from app.services.time_plan import time_plan_service


router = APIRouter(prefix="/openclaw", tags=["openclaw"])


class OpenClawChatRequest(BaseModel):
    studentId: str = Field(min_length=1)
    query: str = Field(min_length=1)
    conversationId: str | None = None
    intent: str | None = None


@router.get("/health")
async def health(
    db: AsyncSession = Depends(get_db),
    client: OpenClawClient = Depends(require_openclaw_client),
) -> dict:
    async def operation() -> dict:
        database_ok = await openclaw_tool_service.check_database(db)
        return {
            "backend": "ok",
            "database": "ok" if database_ok else "error",
            "difyConfigured": bool(settings.dify_app_api_key),
            "allowedStudentMode": "all" if "*" in settings.openclaw_allowed_student_ids else "allowlist",
        }

    return success(
        await openclaw_tool_service.run_with_audit(
            db=db,
            client=client,
            tool_name="health",
            student_id=None,
            request_summary={},
            operation=operation,
        )
    )


@router.get("/students/me/academic-info")
async def get_academic_info(
    studentId: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: OpenClawClient = Depends(require_openclaw_client),
) -> dict:
    async def operation() -> dict:
        await openclaw_tool_service.require_allowed_student(db, studentId)
        return (await graduation_progress_service.get_academic_info(db, studentId)).model_dump()

    return success(
        await openclaw_tool_service.run_with_audit(
            db=db,
            client=client,
            tool_name="students.me.academic_info",
            student_id=studentId,
            request_summary={"studentId": studentId},
            operation=operation,
        )
    )


@router.get("/students/me/graduation-progress")
async def get_graduation_progress(
    studentId: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: OpenClawClient = Depends(require_openclaw_client),
) -> dict:
    async def operation() -> dict:
        await openclaw_tool_service.require_allowed_student(db, studentId)
        return (await graduation_progress_service.calculate(db, studentId)).model_dump()

    return success(
        await openclaw_tool_service.run_with_audit(
            db=db,
            client=client,
            tool_name="students.me.graduation_progress",
            student_id=studentId,
            request_summary={"studentId": studentId},
            operation=operation,
        )
    )


@router.get("/students/me/schedule")
async def get_schedule(
    studentId: str = Query(..., min_length=1),
    term: str = Query(..., min_length=1),
    week: int = Query(1, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    client: OpenClawClient = Depends(require_openclaw_client),
) -> dict:
    async def operation() -> dict:
        user = await openclaw_tool_service.require_allowed_student(db, studentId)
        return (await schedule_service.get_schedule(db, user, term, week)).model_dump()

    return success(
        await openclaw_tool_service.run_with_audit(
            db=db,
            client=client,
            tool_name="students.me.schedule",
            student_id=studentId,
            request_summary={"studentId": studentId, "term": term, "week": week},
            operation=operation,
        )
    )


@router.get("/students/me/time-plan/events")
async def list_time_plan_events(
    studentId: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    client: OpenClawClient = Depends(require_openclaw_client),
) -> dict:
    async def operation() -> list[dict]:
        user = await openclaw_tool_service.require_allowed_student(db, studentId)
        return [item.model_dump() for item in await time_plan_service.list_events(db, user)]

    return success(
        await openclaw_tool_service.run_with_audit(
            db=db,
            client=client,
            tool_name="students.me.time_plan_events",
            student_id=studentId,
            request_summary={"studentId": studentId},
            operation=operation,
        )
    )


@router.post("/ai/chat")
async def send_chat_message(
    payload: OpenClawChatRequest,
    db: AsyncSession = Depends(get_db),
    client: OpenClawClient = Depends(require_openclaw_client),
) -> dict:
    async def operation() -> dict:
        user = await openclaw_tool_service.require_allowed_student(db, payload.studentId)
        request = SendChatRequest(
            student_id=payload.studentId,
            query=payload.query,
            conversation_id=payload.conversationId,
            intent=payload.intent,
        )
        return (await ai_chat_service.send_message(db, request, user)).model_dump()

    return success(
        await openclaw_tool_service.run_with_audit(
            db=db,
            client=client,
            tool_name="ai.chat",
            student_id=payload.studentId,
            request_summary={
                "studentId": payload.studentId,
                "queryLength": len(payload.query),
                "conversationId": payload.conversationId,
                "intent": payload.intent,
            },
            operation=operation,
        )
    )
