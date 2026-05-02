from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.services.knowledge_card import knowledge_card_service


router = APIRouter(prefix="/knowledge-cards", tags=["knowledge-cards"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


@router.get("")
async def list_knowledge_cards(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=50),
    status_value: str | None = Query(None, alias="status"),
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await knowledge_card_service.list_cards(
        db,
        current_user,
        page=page,
        page_size=page_size,
        status_value=status_value,
        q=q,
    )
    return success(result.model_dump())


@router.get("/{card_id}")
async def get_knowledge_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await knowledge_card_service.get_card(db, current_user, card_id)).model_dump())


@router.get("/{card_id}/files/{kind}")
async def get_knowledge_card_file(
    card_id: int,
    kind: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    file_path, mime_type = await knowledge_card_service.get_card_file(db, current_user, card_id, kind)
    return FileResponse(path=file_path, media_type=mime_type)


@router.post("/stream")
async def generate_knowledge_card_stream(
    input_text: str | None = Form(None, alias="inputText"),
    extra_prompt: str | None = Form(None, alias="extraPrompt"),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    async def iterator():
        async for event in knowledge_card_service.generate_stream(
            db,
            current_user,
            input_text=input_text,
            extra_prompt=extra_prompt,
            image=image,
        ):
            yield _sse(event)

    return StreamingResponse(iterator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
