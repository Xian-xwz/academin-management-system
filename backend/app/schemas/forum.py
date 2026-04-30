from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ForumTopicCreate(BaseModel):
    title: str
    content: str
    major: str | None = None
    tags: list[str] = []
    summary: str | None = None


class ForumTopicUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    major: str | None = None
    tags: list[str] | None = None
    summary: str | None = None


class ForumCommentCreate(BaseModel):
    content: str
    parent_id: int | None = None


class ForumCommentItem(BaseModel):
    id: int
    author: str
    authorAvatar: str | None = None
    content: str
    createTime: datetime
    attachments: list["ForumFileItem"] = []
    replies: list["ForumCommentItem"] = []


class ForumFileItem(BaseModel):
    id: int
    originalName: str
    storagePath: str
    fileSize: int | None = None
    mimeType: str | None = None


class ForumTopicItem(BaseModel):
    id: int
    title: str
    summary: str | None = None
    content: str
    author: str
    authorAvatar: str | None = None
    major: str | None = None
    tags: list[str] = []
    views: int
    likes: int
    replies: int
    createTime: datetime
    attachments: list[ForumFileItem] = []
    comments: list[ForumCommentItem] = []
    liked: bool = False
    canEdit: bool = False


class ForumLikeResponse(BaseModel):
    liked: bool
    likes: int
