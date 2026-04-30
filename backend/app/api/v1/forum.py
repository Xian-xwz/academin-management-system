from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.forum import ForumCommentCreate, ForumTopicCreate, ForumTopicUpdate
from app.services.forum import forum_service


router = APIRouter(prefix="/forum", tags=["forum"])


@router.get("/majors")
async def list_majors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success(await forum_service.list_majors(db))


@router.get("/topics")
async def list_topics(
    q: str | None = None,
    major: str | None = None,
    sort: str = Query("latest", pattern="^(latest|hot)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success([item.model_dump() for item in await forum_service.list_topics(db, current_user, q, major, sort)])


@router.post("/topics")
async def create_topic(
    payload: ForumTopicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await forum_service.create_topic(db, current_user, payload)).model_dump())


@router.get("/topics/{topic_id}")
async def get_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await forum_service.get_topic(db, current_user, topic_id)).model_dump())


@router.put("/topics/{topic_id}")
async def update_topic(
    topic_id: int,
    payload: ForumTopicUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await forum_service.update_topic(db, current_user, topic_id, payload)).model_dump())


@router.delete("/topics/{topic_id}")
async def delete_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await forum_service.delete_topic(db, current_user, topic_id)
    return success({"deleted": True})


@router.post("/topics/{topic_id}/comments")
async def add_comment(
    topic_id: int,
    payload: ForumCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await forum_service.add_comment(db, current_user, topic_id, payload)).model_dump())


@router.post("/topics/{topic_id}/like")
async def like_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await forum_service.like_topic(db, current_user, topic_id)).model_dump())


@router.delete("/topics/{topic_id}/like")
async def unlike_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await forum_service.unlike_topic(db, current_user, topic_id)).model_dump())


@router.post("/topics/{topic_id}/files")
async def upload_topic_file(
    topic_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await forum_service.upload_file(db, current_user, topic_id, file)).model_dump())


@router.post("/topics/{topic_id}/comments/{comment_id}/files")
async def upload_comment_file(
    topic_id: int,
    comment_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return success((await forum_service.upload_comment_file(db, current_user, topic_id, comment_id, file)).model_dump())


@router.get("/files/{file_id}/download")
async def download_topic_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    file_record, file_path = await forum_service.get_download_file(db, file_id)
    return FileResponse(path=file_path, filename=file_record.original_name, media_type=file_record.mime_type)
