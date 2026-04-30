from __future__ import annotations

from pydantic import BaseModel


class ScheduleCourseItem(BaseModel):
    id: int
    name: str
    teacher: str | None = None
    location: str | None = None
    day: int
    sections: list[int]
    weeks: str | None = None
    note: str | None = None


class ScheduleResponse(BaseModel):
    term: str
    week: int
    courses: list[ScheduleCourseItem]


class UpdateCourseNoteRequest(BaseModel):
    note: str | None = None
