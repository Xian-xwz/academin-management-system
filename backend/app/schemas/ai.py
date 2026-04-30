from __future__ import annotations

from pydantic import BaseModel, Field


class ChatSource(BaseModel):
    documentName: str | None = None
    title: str | None = None
    content: str | None = None
    score: float | None = None


class DifyChatFile(BaseModel):
    type: str
    transfer_method: str = "local_file"
    upload_file_id: str


class DifyUploadedFile(BaseModel):
    id: str
    name: str | None = None
    size: int | None = None
    extension: str | None = None
    mime_type: str | None = None
    type: str = "image"


class SendChatRequest(BaseModel):
    query: str = Field(min_length=1)
    conversation_id: str | None = None
    student_id: str | None = None
    major_code: str | None = None
    major_name: str | None = None
    intent: str | None = None
    inputs: dict | None = None
    files: list[DifyChatFile] = Field(default_factory=list)


class SendChatResponse(BaseModel):
    answer: str
    conversation_id: str
    sources: list[ChatSource] = []
    intent: str | None = None
    need_personal_data: bool = False


class ChatMessageItem(BaseModel):
    role: str
    content: str
    intent: str | None = None
    sources: list[ChatSource] = []
    need_personal_data: bool = False


class ChatSessionItem(BaseModel):
    id: str
    title: str | None = None
    time: str | None = None


class ChatHistoryResponse(BaseModel):
    conversation_id: str
    title: str | None = None
    messages: list[ChatMessageItem]


class ErrorCaseCreate(BaseModel):
    question: str
    wrong_answer: str | None = None
    expected_answer: str | None = None
    reason: str | None = None


class ErrorCaseStatusUpdate(BaseModel):
    status: str


class ErrorCaseItem(BaseModel):
    id: int
    question: str
    wrong_answer: str | None = None
    expected_answer: str | None = None
    reason: str | None = None
    status: str
