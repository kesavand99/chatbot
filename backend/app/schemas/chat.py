from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ChatResponse(BaseModel):
    session_id: str
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    suggested_replies: list[str] = Field(default_factory=list)
    is_admin_needed: bool = False


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageResponse]
    suggested_replies: list[str] = Field(default_factory=list)


class ChatSummary(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ChatListResponse(BaseModel):
    chats: list[ChatSummary]


class RenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
