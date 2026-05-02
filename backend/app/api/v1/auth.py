from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.core.responses import success
from app.db.session import get_db
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest
from app.services.auth import auth_service, build_user_info


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return success((await auth_service.register(db, payload)).model_dump())


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return success((await auth_service.login(db, payload)).model_dump())


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> dict:
    return success(build_user_info(current_user).model_dump())


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await auth_service.change_password(db, current_user, payload)
    return success({"changed": True})


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持上传图片作为头像")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        suffix = ".jpg"

    avatar_dir = settings.upload_dir / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{current_user.id}_{uuid4().hex}{suffix}"
    storage_path = avatar_dir / stored_name

    size = 0
    max_bytes = min(settings.max_upload_size_mb, 5) * 1024 * 1024
    with storage_path.open("wb") as file_obj:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                file_obj.close()
                storage_path.unlink(missing_ok=True)
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="头像图片不能超过 5MB")
            file_obj.write(chunk)

    old_avatar = current_user.avatar_url
    if old_avatar and old_avatar.startswith("/api/auth/avatars/"):
        old_name = old_avatar.rsplit("/", 1)[-1]
        if old_name.startswith(f"{current_user.id}_"):
            (avatar_dir / old_name).unlink(missing_ok=True)

    current_user.avatar_url = f"/api/auth/avatars/{stored_name}"
    await db.commit()
    return success(build_user_info(current_user).model_dump())


@router.get("/avatars/{file_name}")
async def get_avatar(file_name: str) -> FileResponse:
    safe_name = Path(file_name).name
    file_path = settings.upload_dir / "avatars" / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="头像不存在")
    return FileResponse(file_path)
