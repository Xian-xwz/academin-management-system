from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TimePlanEventBase(BaseModel):
    title: str
    type: str
    startTime: datetime
    endTime: datetime | None = None
    location: str | None = None
    desc: str | None = None
    status: str = "待开始"


class TimePlanEventCreate(TimePlanEventBase):
    pass


class TimePlanEventUpdate(BaseModel):
    title: str | None = None
    type: str | None = None
    startTime: datetime | None = None
    endTime: datetime | None = None
    location: str | None = None
    desc: str | None = None
    status: str | None = None


class TimePlanEventItem(TimePlanEventBase):
    id: int
    sourceType: str | None = None
    sourceId: int | None = None


class SyncFromScheduleResponse(BaseModel):
    synced: int
