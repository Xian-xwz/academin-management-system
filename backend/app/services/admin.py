from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AcademicWarning, ForumTopic, Major, User
from app.schemas.admin import (
    AdminAcademicWarningCreate,
    AdminAcademicWarningResponse,
    AdminDashboardSummary,
    AdminForumTopicItem,
    AdminForumTopicListResponse,
    AdminMajorStat,
    AdminUserDetail,
    AdminUserItem,
    AdminUserListResponse,
)


class AdminService:
    async def dashboard_summary(self, db: AsyncSession) -> AdminDashboardSummary:
        total_users = await self._count_users(db)
        active_users = await self._count_users(db, User.is_active.is_(True))
        student_users = await self._count_users(db, User.role == "student")
        admin_users = await self._count_users(db, User.role == "admin")

        major_result = await db.execute(
            select(Major.major_code, Major.major_name, func.count(User.id))
            .select_from(User)
            .join(Major, User.major_id == Major.id, isouter=True)
            .where(User.role == "student")
            .group_by(Major.major_code, Major.major_name)
            .order_by(func.count(User.id).desc())
        )
        major_distribution = [
            AdminMajorStat(majorCode=code, majorName=name or "未绑定专业", count=count)
            for code, name, count in major_result.all()
        ]

        return AdminDashboardSummary(
            totalUsers=total_users,
            activeUsers=active_users,
            studentUsers=student_users,
            adminUsers=admin_users,
            majorDistribution=major_distribution,
        )

    async def list_users(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        q: str | None = None,
        major_code: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> AdminUserListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        filters = self._user_filters(q=q, major_code=major_code, role=role, is_active=is_active)

        total_result = await db.execute(select(func.count()).select_from(User).where(*filters))
        total = int(total_result.scalar_one())

        result = await db.execute(
            select(User)
            .options(selectinload(User.major))
            .where(*filters)
            .order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        users = list(result.scalars().all())
        return AdminUserListResponse(
            items=[self._to_user_item(user) for user in users],
            total=total,
            page=page,
            pageSize=page_size,
        )

    async def get_user_detail(self, db: AsyncSession, student_id: str) -> AdminUserDetail:
        user = await self._get_user_by_student_id(db, student_id)
        item = self._to_user_item(user)
        return AdminUserDetail(**item.model_dump(), email=user.email, updatedAt=user.updated_at)

    async def send_academic_warning(
        self,
        db: AsyncSession,
        student_id: str,
        payload: AdminAcademicWarningCreate,
    ) -> AdminAcademicWarningResponse:
        user = await self._get_user_by_student_id(db, student_id)
        if user.role != "student":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能向学生账号发送学业预警")
        warning = AcademicWarning(
            user_id=user.id,
            student_id=user.student_id,
            title=payload.title.strip() or "学业预警提醒",
            content=payload.content.strip(),
        )
        db.add(warning)
        await db.commit()
        await db.refresh(warning)
        return AdminAcademicWarningResponse(
            warningId=warning.id,
            studentId=user.student_id,
            title=warning.title,
            content=warning.content,
        )

    async def list_forum_topics(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        q: str | None = None,
        status_value: str | None = None,
    ) -> AdminForumTopicListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        filters = []
        if q:
            keyword = q.strip()
            filters.append(or_(ForumTopic.title.contains(keyword), ForumTopic.content.contains(keyword)))
        if status_value:
            filters.append(ForumTopic.status == status_value.strip())

        total_result = await db.execute(select(func.count()).select_from(ForumTopic).where(*filters))
        total = int(total_result.scalar_one())
        result = await db.execute(
            select(ForumTopic)
            .where(*filters)
            .order_by(ForumTopic.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        topics = list(result.scalars().all())
        return AdminForumTopicListResponse(
            items=[await self._to_forum_topic_item(db, topic) for topic in topics],
            total=total,
            page=page,
            pageSize=page_size,
        )

    async def hide_forum_topic(self, db: AsyncSession, topic_id: int) -> dict[str, int | str]:
        topic = await db.get(ForumTopic, topic_id)
        if topic is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到论坛话题")
        topic.status = "deleted"
        await db.commit()
        return {"id": topic_id, "status": topic.status}

    async def set_forum_topic_status(self, db: AsyncSession, topic_id: int, status_value: str) -> dict[str, int | str]:
        """管理员设置帖子状态：normal 恢复显示，deleted 隐藏（软删除）。"""
        if status_value not in {"normal", "deleted"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="状态仅支持 normal 或 deleted")
        topic = await db.get(ForumTopic, topic_id)
        if topic is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到论坛话题")
        topic.status = status_value
        await db.commit()
        return {"id": topic_id, "status": topic.status}

    async def _count_users(self, db: AsyncSession, *filters) -> int:
        result = await db.execute(select(func.count()).select_from(User).where(*filters))
        return int(result.scalar_one())

    def _user_filters(
        self,
        *,
        q: str | None,
        major_code: str | None,
        role: str | None,
        is_active: bool | None,
    ) -> list:
        filters = []
        if q:
            keyword = q.strip()
            filters.append(or_(User.student_id.contains(keyword), User.username.contains(keyword), User.real_name.contains(keyword)))
        if major_code:
            filters.append(User.major.has(Major.major_code == major_code.strip()))
        if role:
            filters.append(User.role == role.strip())
        if is_active is not None:
            filters.append(User.is_active.is_(is_active))
        return filters

    async def _get_user_by_student_id(self, db: AsyncSession, student_id: str) -> User:
        result = await db.execute(
            select(User)
            .options(selectinload(User.major))
            .where(User.student_id == student_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该用户")
        return user

    def _to_user_item(self, user: User) -> AdminUserItem:
        return AdminUserItem(
            id=user.id,
            username=user.username,
            studentId=user.student_id,
            name=user.real_name or user.username,
            avatarUrl=user.avatar_url,
            majorCode=user.major.major_code if user.major else None,
            majorName=user.major.major_name if user.major else None,
            grade=user.grade,
            role=user.role,
            isActive=user.is_active,
            createdAt=user.created_at,
        )

    async def _to_forum_topic_item(self, db: AsyncSession, topic: ForumTopic) -> AdminForumTopicItem:
        author = await db.get(User, topic.user_id)
        major = await db.get(Major, topic.major_id) if topic.major_id else None
        return AdminForumTopicItem(
            id=topic.id,
            title=topic.title,
            author=author.real_name or author.username if author else "未知用户",
            authorStudentId=author.student_id if author else "-",
            majorName=major.major_name if major else None,
            status=topic.status,
            views=topic.view_count,
            likes=topic.like_count,
            comments=topic.comment_count,
            createdAt=topic.created_at,
        )


admin_service = AdminService()
