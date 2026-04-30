from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AdminMajorStat(BaseModel):
    majorCode: str | None = None
    majorName: str | None = None
    count: int


class AdminDashboardSummary(BaseModel):
    totalUsers: int
    activeUsers: int
    studentUsers: int
    adminUsers: int
    majorDistribution: list[AdminMajorStat]


class AdminUserItem(BaseModel):
    id: int
    username: str
    studentId: str
    name: str
    avatarUrl: str | None = None
    majorCode: str | None = None
    majorName: str | None = None
    grade: str | None = None
    role: str
    isActive: bool
    createdAt: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserItem]
    total: int
    page: int
    pageSize: int


class AdminUserDetail(AdminUserItem):
    email: str | None = None
    updatedAt: datetime


class AdminAcademicWarningCreate(BaseModel):
    title: str = "学业预警提醒"
    content: str


class AdminAcademicWarningResponse(BaseModel):
    warningId: int
    studentId: str
    title: str
    content: str


class AdminForumTopicItem(BaseModel):
    id: int
    title: str
    author: str
    authorStudentId: str
    majorName: str | None = None
    status: str
    views: int
    likes: int
    comments: int
    createdAt: datetime


class AdminForumTopicListResponse(BaseModel):
    items: list[AdminForumTopicItem]
    total: int
    page: int
    pageSize: int


class AdminForumTopicStatusUpdate(BaseModel):
    """管理员调整帖子可见状态，当前仅支持 normal 与 deleted（软删除/隐藏）。"""

    status: str

    def normalized_status(self) -> str:
        value = self.status.strip()
        if value not in {"normal", "deleted"}:
            raise ValueError("status 仅允许为 normal 或 deleted")
        return value
