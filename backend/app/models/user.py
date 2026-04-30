from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    """统一登录用户表，当前以学生用户为主，预留管理员角色。"""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("username = student_id", name="ck_users_username_equals_student_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="登录用户名，与学号一致",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="密码哈希",
    )
    real_name: Mapped[str | None] = mapped_column(String(50), comment="真实姓名")
    student_id: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        nullable=False,
        comment="学号",
    )
    email: Mapped[str | None] = mapped_column(String(120), comment="邮箱")
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="student",
        comment="角色：student/admin",
    )
    major_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("majors.id"),
        index=True,
        comment="所属专业 ID",
    )
    grade: Mapped[str | None] = mapped_column(String(20), comment="年级，例如 2021级")
    avatar_url: Mapped[str | None] = mapped_column(String(255), comment="头像 URL")
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="账号是否启用",
    )

    major: Mapped[Major | None] = relationship(back_populates="users")
