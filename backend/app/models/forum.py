from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ForumTopic(TimestampMixin, Base):
    """论坛话题，支持列表、详情、搜索和排序。"""

    __tablename__ = "forum_topics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        index=True,
        nullable=False,
        comment="发布者用户 ID",
    )
    major_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("majors.id"),
        index=True,
        comment="所属专业 ID",
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="话题标题")
    summary: Mapped[str | None] = mapped_column(String(300), comment="摘要")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="正文")
    tags_json: Mapped[list | None] = mapped_column(JSON, comment="标签数组")
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="浏览数")
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="点赞数")
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="评论数")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="normal", comment="状态")

    comments: Mapped[list["ForumComment"]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
    )
    files: Mapped[list["ForumFile"]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
    )
    likes: Mapped[list["ForumTopicLike"]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
    )


class ForumComment(TimestampMixin, Base):
    """论坛评论，parent_id 为空时为一级评论，否则为二级回复。"""

    __tablename__ = "forum_comments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("forum_topics.id"),
        index=True,
        nullable=False,
        comment="话题 ID",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        index=True,
        nullable=False,
        comment="评论用户 ID",
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("forum_comments.id"),
        index=True,
        comment="父评论 ID",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评论内容")
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="点赞数")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="normal", comment="状态")

    topic: Mapped[ForumTopic] = relationship(back_populates="comments")
    parent: Mapped[ForumComment | None] = relationship(
        remote_side=[id],
        back_populates="replies",
    )
    replies: Mapped[list["ForumComment"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    files: Mapped[list["ForumFile"]] = relationship(back_populates="comment")


class ForumFile(TimestampMixin, Base):
    """论坛附件文件记录。"""

    __tablename__ = "forum_files"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("forum_topics.id"),
        index=True,
        nullable=False,
        comment="话题 ID",
    )
    comment_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("forum_comments.id"),
        index=True,
        comment="评论 ID；为空表示话题附件",
    )
    uploader_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="上传者 ID",
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="存储路径")
    file_size: Mapped[int | None] = mapped_column(BigInteger, comment="文件大小")
    mime_type: Mapped[str | None] = mapped_column(String(100), comment="MIME 类型")
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="下载次数")

    topic: Mapped[ForumTopic] = relationship(back_populates="files")
    comment: Mapped[ForumComment | None] = relationship(back_populates="files")


class ForumTopicLike(TimestampMixin, Base):
    """论坛话题点赞记录，用唯一约束保证每个用户只能点赞一次。"""

    __tablename__ = "forum_topic_likes"
    __table_args__ = (
        UniqueConstraint("topic_id", "user_id", name="uk_forum_topic_user_like"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("forum_topics.id"),
        index=True,
        nullable=False,
        comment="话题 ID",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        index=True,
        nullable=False,
        comment="点赞用户 ID",
    )

    topic: Mapped[ForumTopic] = relationship(back_populates="likes")
