from __future__ import annotations

from pydantic import BaseModel


class BaseInfo(BaseModel):
    name: str
    studentId: str
    major: str | None = None
    grade: str | None = None


class GraduationRequirementInfo(BaseModel):
    total: float
    earned: float
    compulsory: float
    elective: float
    practice: float


class CourseInfo(BaseModel):
    name: str
    category: str | None = None
    credit: float
    score: float | None = None
    term: str | None = None


class CategoryStatistic(BaseModel):
    category: str
    earned: float
    total: float


class Suggestion(BaseModel):
    category: str
    gap: float
    desc: str


class AcademicInfoResponse(BaseModel):
    baseInfo: BaseInfo
    graduationReq: GraduationRequirementInfo
    courses: list[CourseInfo]
    statistics: list[CategoryStatistic]
    suggestions: list[Suggestion]


class GraduationProgressResponse(BaseModel):
    studentId: str
    majorCode: str | None = None
    majorName: str | None = None
    totalRequired: float
    totalEarned: float
    totalGap: float
    categoryBreakdown: list[CategoryStatistic]
    missingItems: list[Suggestion]
