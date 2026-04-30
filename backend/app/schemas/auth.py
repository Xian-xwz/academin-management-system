from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    student_id: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=6, max_length=128)
    real_name: str | None = None
    email: str | None = None
    major_code: str | None = None
    grade: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserInfo(BaseModel):
    id: int
    username: str
    name: str
    studentId: str
    avatarUrl: str | None = None
    majorCode: str | None = None
    majorName: str | None = None
    grade: str | None = None
    role: str


class AcademicWarningPopup(BaseModel):
    id: int
    title: str
    content: str


class AuthResponse(BaseModel):
    token: str
    userInfo: UserInfo
    pendingAcademicWarnings: list[AcademicWarningPopup] = Field(default_factory=list)
