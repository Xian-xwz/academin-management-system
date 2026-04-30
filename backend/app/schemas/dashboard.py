from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DashboardNotificationItem(BaseModel):
    id: str
    type: str
    title: str
    content: str
    time: datetime | None = None
    targetUrl: str | None = None
    read: bool = False
