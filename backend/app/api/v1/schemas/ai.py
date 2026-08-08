from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None


class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: ChatMessageResponse
    follow_up_questions: list[str]
    model: str
    grounded: bool = True


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = []


class ForecastPoint(BaseModel):
    date: str
    value: float


class ForecastResponse(BaseModel):
    method: str
    horizon_days: int
    points: list[ForecastPoint]
    warning: str | None = None


class AnomalyItem(BaseModel):
    date: str
    revenue: float
    z_score: float
    direction: str


class AnomalyResponse(BaseModel):
    method: str
    items: list[AnomalyItem]
    count: int
