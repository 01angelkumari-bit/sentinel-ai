from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.api.v1.schemas.ai import AnomalyResponse, ChatRequest, ChatResponse, ConversationResponse, ForecastResponse
from app.application.ai.service import SentinelAIService
from app.core.config import get_settings
from app.domain.users.models import ChatConversation, ChatMessage, User
from app.infrastructure.database import get_db

router = APIRouter(prefix="/ai", tags=["Sentinel AI"])


def service(user: User, db: Session) -> SentinelAIService:
    return SentinelAIService(db, user.organization_id, user.id)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    conversation, message, followups = service(user, db).chat(payload.message, payload.conversation_id)
    return {"conversation_id": conversation.id, "message": message, "follow_up_questions": followups, "model": get_settings().ai_model_id, "grounded": True}


@router.get("/conversations", response_model=list[ConversationResponse])
def conversations(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = list(db.scalars(select(ChatConversation).where(ChatConversation.organization_id == user.organization_id, ChatConversation.user_id == user.id).order_by(ChatConversation.updated_at.desc()).limit(50)))
    return [{"id": row.id, "title": row.title, "created_at": row.created_at, "updated_at": row.updated_at, "messages": []} for row in rows]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def conversation(conversation_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(ChatConversation).where(ChatConversation.id == conversation_id, ChatConversation.organization_id == user.organization_id, ChatConversation.user_id == user.id))
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = list(db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == row.id, ChatMessage.organization_id == user.organization_id).order_by(ChatMessage.created_at)))
    return {"id": row.id, "title": row.title, "created_at": row.created_at, "updated_at": row.updated_at, "messages": messages}


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_conversation(conversation_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    row = db.scalar(select(ChatConversation).where(ChatConversation.id == conversation_id, ChatConversation.organization_id == user.organization_id, ChatConversation.user_id == user.id))
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(row); db.commit(); return Response(status_code=204)


@router.get("/forecast", response_model=ForecastResponse)
def forecast(horizon_days: int = Query(30, ge=1, le=365), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return service(user, db).forecast(horizon_days)


@router.get("/anomalies", response_model=AnomalyResponse)
def anomalies(threshold: float = Query(2.5, ge=1.5, le=5), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return service(user, db).anomalies(threshold)


@router.get("/dataset-intelligence", summary="Profile the active dataset and return evidence-backed sentiment and risks")
def dataset_intelligence(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return service(user, db).dataset_intelligence()
