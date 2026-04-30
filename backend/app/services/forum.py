from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from fastapi import HTTPException, status
from sqlalchemy import String, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import ForumComment, ForumFile, ForumTopic, ForumTopicLike, Major, User
from app.schemas.forum import ForumCommentCreate, ForumCommentItem, ForumFileItem, ForumLikeResponse, ForumTopicCreate, ForumTopicItem, ForumTopicUpdate


class ForumService:
    async def list_majors(self, db: AsyncSession) -> list[dict[str, str]]:
        result = await db.execute(select(Major).order_by(Major.major_name))
        return [
            {
                "code": major.major_code,
                "name": major.major_name,
            }
            for major in result.scalars().all()
        ]

    async def list_topics(self, db: AsyncSession, current_user: User, q: str | None, major: str | None, sort: str) -> list[ForumTopicItem]:
        stmt = (
            select(ForumTopic)
            .options(
                selectinload(ForumTopic.comments).selectinload(ForumComment.files),
                selectinload(ForumTopic.files),
            )
            .where(ForumTopic.status == "normal")
        )
        if q:
            stmt = stmt.where(or_(ForumTopic.title.contains(q), ForumTopic.content.contains(q), cast(ForumTopic.tags_json, String).contains(q)))
        if major:
            major_result = await db.execute(select(Major).where(or_(Major.major_code == major, Major.major_name == major)))
            major_obj = major_result.scalar_one_or_none()
            if major_obj:
                stmt = stmt.where(ForumTopic.major_id == major_obj.id)
        stmt = stmt.order_by(ForumTopic.like_count.desc() if sort == "hot" else ForumTopic.created_at.desc())
        result = await db.execute(stmt)
        return [await self._to_topic_item(db, topic, current_user, include_comments=True) for topic in result.scalars().unique().all()]

    async def create_topic(self, db: AsyncSession, current_user: User, payload: ForumTopicCreate) -> ForumTopicItem:
        major_id = await self._resolve_major_id(db, payload.major, current_user.major_id)
        topic = ForumTopic(
            user_id=current_user.id,
            major_id=major_id,
            title=payload.title,
            summary=payload.summary or payload.content[:120],
            content=payload.content,
            tags_json=payload.tags,
        )
        db.add(topic)
        await db.commit()
        loaded_topic = await self._get_topic(db, topic.id)
        return await self._to_topic_item(db, loaded_topic, current_user, include_comments=True)

    async def get_topic(self, db: AsyncSession, current_user: User, topic_id: int) -> ForumTopicItem:
        topic = await self._get_topic(db, topic_id)
        topic.view_count += 1
        await db.commit()
        return await self._to_topic_item(db, topic, current_user, include_comments=True)

    async def update_topic(self, db: AsyncSession, current_user: User, topic_id: int, payload: ForumTopicUpdate) -> ForumTopicItem:
        topic = await self._get_topic(db, topic_id)
        self._ensure_topic_owner(current_user, topic)
        if payload.major is not None:
            topic.major_id = await self._resolve_major_id(db, payload.major, current_user.major_id)
        if payload.title is not None:
            topic.title = payload.title
        if payload.content is not None:
            topic.content = payload.content
        if payload.summary is not None:
            topic.summary = payload.summary
        elif payload.content is not None:
            topic.summary = payload.content[:120]
        if payload.tags is not None:
            topic.tags_json = payload.tags
        await db.commit()
        loaded_topic = await self._get_topic(db, topic.id)
        return await self._to_topic_item(db, loaded_topic, current_user, include_comments=True)

    async def delete_topic(self, db: AsyncSession, current_user: User, topic_id: int) -> None:
        topic = await self._get_topic(db, topic_id)
        self._ensure_topic_owner(current_user, topic)
        topic.status = "deleted"
        await db.commit()

    async def add_comment(self, db: AsyncSession, current_user: User, topic_id: int, payload: ForumCommentCreate) -> ForumCommentItem:
        topic = await self._get_topic(db, topic_id)
        comment = ForumComment(topic_id=topic.id, user_id=current_user.id, parent_id=payload.parent_id, content=payload.content)
        db.add(comment)
        topic.comment_count += 1
        await db.commit()
        await db.refresh(comment)
        author_name, author_avatar = await self._author_profile(db, comment.user_id)
        return ForumCommentItem(
            id=comment.id,
            author=author_name,
            authorAvatar=author_avatar,
            content=comment.content,
            createTime=comment.created_at,
            attachments=[],
            replies=[],
        )

    async def like_topic(self, db: AsyncSession, current_user: User, topic_id: int) -> ForumLikeResponse:
        topic = await self._get_topic(db, topic_id)
        result = await db.execute(select(ForumTopicLike).where(ForumTopicLike.topic_id == topic_id, ForumTopicLike.user_id == current_user.id))
        like = result.scalar_one_or_none()
        if like is None:
            db.add(ForumTopicLike(topic_id=topic_id, user_id=current_user.id))
            topic.like_count += 1
            await db.commit()
        return ForumLikeResponse(liked=True, likes=topic.like_count)

    async def unlike_topic(self, db: AsyncSession, current_user: User, topic_id: int) -> ForumLikeResponse:
        topic = await self._get_topic(db, topic_id)
        result = await db.execute(select(ForumTopicLike).where(ForumTopicLike.topic_id == topic_id, ForumTopicLike.user_id == current_user.id))
        like = result.scalar_one_or_none()
        if like is not None:
            await db.delete(like)
            topic.like_count = max(topic.like_count - 1, 0)
            await db.commit()
        return ForumLikeResponse(liked=False, likes=topic.like_count)

    async def upload_file(self, db: AsyncSession, current_user: User, topic_id: int, upload: UploadFile) -> ForumFileItem:
        topic = await self._get_topic(db, topic_id)
        return await self._save_upload(db, current_user, topic, upload)

    async def upload_comment_file(self, db: AsyncSession, current_user: User, topic_id: int, comment_id: int, upload: UploadFile) -> ForumFileItem:
        topic = await self._get_topic(db, topic_id)
        comment = await self._get_comment(db, topic_id, comment_id)
        return await self._save_upload(db, current_user, topic, upload, comment)

    async def _save_upload(
        self,
        db: AsyncSession,
        current_user: User,
        topic: ForumTopic,
        upload: UploadFile,
        comment: ForumComment | None = None,
    ) -> ForumFileItem:
        original_name = Path(upload.filename or "attachment").name
        topic_dir = settings.upload_dir / "forum" / str(topic.id)
        if comment is not None:
            topic_dir = topic_dir / "comments" / str(comment.id)
        topic_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}_{original_name}"
        storage_path = topic_dir / stored_name

        size = 0
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        with storage_path.open("wb") as file_obj:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    file_obj.close()
                    storage_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="上传文件超过大小限制")
                file_obj.write(chunk)

        relative_path = storage_path.relative_to(settings.upload_dir).as_posix()
        file_record = ForumFile(
            topic_id=topic.id,
            comment_id=comment.id if comment else None,
            uploader_id=current_user.id,
            original_name=original_name,
            storage_path=relative_path,
            file_size=size,
            mime_type=upload.content_type,
        )
        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)
        return self._to_file_item(file_record)

    async def get_download_file(self, db: AsyncSession, file_id: int) -> tuple[ForumFile, Path]:
        file_record = await db.get(ForumFile, file_id)
        if file_record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到附件")
        file_path = settings.upload_dir / file_record.storage_path
        if not file_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="附件文件不存在")
        file_record.download_count += 1
        await db.commit()
        return file_record, file_path

    async def _get_topic(self, db: AsyncSession, topic_id: int) -> ForumTopic:
        result = await db.execute(
            select(ForumTopic)
            .options(
                selectinload(ForumTopic.comments).selectinload(ForumComment.files),
                selectinload(ForumTopic.files),
            )
            .where(ForumTopic.id == topic_id, ForumTopic.status == "normal")
        )
        topic = result.scalar_one_or_none()
        if topic is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到论坛话题")
        return topic

    async def _get_comment(self, db: AsyncSession, topic_id: int, comment_id: int) -> ForumComment:
        result = await db.execute(
            select(ForumComment)
            .options(selectinload(ForumComment.files))
            .where(ForumComment.id == comment_id, ForumComment.topic_id == topic_id, ForumComment.status == "normal")
        )
        comment = result.scalar_one_or_none()
        if comment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到评论")
        return comment

    async def _resolve_major_id(self, db: AsyncSession, major_value: str | None, fallback_major_id: int | None) -> int | None:
        if not major_value:
            return fallback_major_id
        major_result = await db.execute(select(Major).where(or_(Major.major_code == major_value, Major.major_name == major_value)))
        major = major_result.scalar_one_or_none()
        return major.id if major else fallback_major_id

    def _ensure_topic_owner(self, current_user: User, topic: ForumTopic) -> None:
        if current_user.role == "admin" or topic.user_id == current_user.id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能编辑或删除自己发布的话题")

    async def _to_topic_item(self, db: AsyncSession, topic: ForumTopic, current_user: User, include_comments: bool) -> ForumTopicItem:
        author, author_avatar = await self._author_profile(db, topic.user_id)
        major_name = None
        if topic.major_id:
            major = await db.get(Major, topic.major_id)
            major_name = major.major_name if major else None
        like_result = await db.execute(select(ForumTopicLike).where(ForumTopicLike.topic_id == topic.id, ForumTopicLike.user_id == current_user.id))
        comments: list[ForumCommentItem] = []
        if include_comments:
            replies_by_parent: dict[int | None, list[ForumComment]] = {}
            for comment in sorted(topic.comments, key=lambda item: item.created_at):
                replies_by_parent.setdefault(comment.parent_id, []).append(comment)
            comments = [await self._to_comment_item(db, comment, replies_by_parent) for comment in replies_by_parent.get(None, [])]
        return ForumTopicItem(
            id=topic.id,
            title=topic.title,
            summary=topic.summary,
            content=topic.content,
            author=author,
            authorAvatar=author_avatar,
            major=major_name,
            tags=topic.tags_json or [],
            views=topic.view_count,
            likes=topic.like_count,
            replies=topic.comment_count,
            createTime=topic.created_at,
            attachments=[self._to_file_item(file) for file in topic.files if file.comment_id is None],
            comments=comments,
            liked=like_result.scalar_one_or_none() is not None,
            canEdit=current_user.role == "admin" or topic.user_id == current_user.id,
        )

    async def _to_comment_item(
        self,
        db: AsyncSession,
        comment: ForumComment,
        replies_by_parent: dict[int | None, list[ForumComment]] | None = None,
    ) -> ForumCommentItem:
        replies = replies_by_parent.get(comment.id, []) if replies_by_parent is not None else []
        author_name, author_avatar = await self._author_profile(db, comment.user_id)
        return ForumCommentItem(
            id=comment.id,
            author=author_name,
            authorAvatar=author_avatar,
            content=comment.content,
            createTime=comment.created_at,
            attachments=[self._to_file_item(file) for file in comment.files],
            replies=[await self._to_comment_item(db, reply, replies_by_parent) for reply in replies],
        )

    async def _author_name(self, db: AsyncSession, user_id: int) -> str:
        name, _ = await self._author_profile(db, user_id)
        return name

    async def _author_profile(self, db: AsyncSession, user_id: int) -> tuple[str, str | None]:
        user = await db.get(User, user_id)
        if not user:
            return "未知用户", None
        return user.real_name or user.username, user.avatar_url

    def _to_file_item(self, file: ForumFile) -> ForumFileItem:
        return ForumFileItem(
            id=file.id,
            originalName=file.original_name,
            storagePath=file.storage_path,
            fileSize=file.file_size,
            mimeType=file.mime_type,
        )


forum_service = ForumService()
