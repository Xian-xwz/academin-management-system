from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.ai import ChatHistoryResponse, ErrorCaseCreate, ErrorCaseStatusUpdate, SendChatRequest, SendChatResponse
from app.services.ai import ai_chat_service
from app.services.error_case import error_case_service


router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat")
async def send_chat_message(
    payload: SendChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await ai_chat_service.send_message(db, payload, current_user)).model_dump())


@router.post("/chat/stream")
async def stream_chat_message(
    payload: SendChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    return StreamingResponse(
        ai_chat_service.stream_message(db, payload, current_user),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations")
async def list_chat_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success([item.model_dump() for item in await ai_chat_service.list_conversations(db, current_user)])


@router.post("/files/upload")
async def upload_ai_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await ai_chat_service.upload_file_to_dify(file, current_user)).model_dump())


@router.get("/conversations/{conversation_id}")
async def get_chat_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await ai_chat_service.get_history(db, conversation_id, current_user)).model_dump())


@router.delete("/conversations/{conversation_id}")
async def delete_chat_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await ai_chat_service.delete_conversation(db, conversation_id, current_user)
    return success({"deleted": True})


@router.post("/error-cases")
async def create_error_case(
    payload: ErrorCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await error_case_service.create_case(db, current_user, payload)).model_dump())


@router.get("/error-cases")
async def list_error_cases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success([item.model_dump() for item in await error_case_service.list_cases(db, current_user)])


@router.patch("/error-cases/{case_id}/status")
async def update_error_case_status(
    case_id: int,
    payload: ErrorCaseStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await error_case_service.update_status(db, current_user, case_id, payload)).model_dump())
