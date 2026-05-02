from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class KnowledgeCardItem(BaseModel):
    id: int
    title: str | None = None
    inputType: str
    templateId: str | None = None
    imageNumber: str | None = None
    routeReason: str | None = None
    status: str
    outputImageUrl: str | None = None
    errorMessage: str | None = None
    createdAt: datetime
    updatedAt: datetime


class KnowledgeCardDetail(KnowledgeCardItem):
    inputText: str | None = None
    inputImageUrl: str | None = None
    prompt: str | None = None
    extraPrompt: str | None = None
    difyWorkflowRunId: str | None = None
    difyTaskId: str | None = None
    rawResponse: dict | None = None


class KnowledgeCardListResponse(BaseModel):
    items: list[KnowledgeCardItem]
    total: int
    page: int
    pageSize: int
