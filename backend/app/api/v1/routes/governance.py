from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_role
from app.application.analytics.service import BusinessAnalyticsService
from app.application.audit import record_audit
from app.application.auth.service import EmailAlreadyRegistered, create_organization_member
from app.application.files.service import FileService
from app.domain.users.models import AuditLog, OrganizationInvitation, ReportSchedule, User
from app.infrastructure.database import get_db
from app.repositories.business_analytics import BusinessAnalyticsRepository

router = APIRouter(prefix="/governance", tags=["governance"])


class InvitationCreate(BaseModel):
    email: EmailStr
    role: Literal["admin", "manager", "employee", "viewer"]


class InvitationAccept(BaseModel):
    token: str = Field(min_length=32, max_length=300)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    frequency: Literal["daily", "weekly", "monthly"]


@router.get("/members")
def members(actor: User = Depends(require_role("manager")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(User).where(User.organization_id == actor.organization_id).order_by(User.created_at)).all()
    return [{"id": row.id, "email": row.email, "full_name": row.full_name, "role": row.role, "created_at": row.created_at} for row in rows]


@router.post("/invitations", status_code=status.HTTP_201_CREATED)
def invite(payload: InvitationCreate, actor: User = Depends(require_role("admin")), db: Session = Depends(get_db)) -> dict:
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    raw_token = token_urlsafe(48); now = datetime.now(timezone.utc)
    invitation = OrganizationInvitation(organization_id=actor.organization_id, invited_by_id=actor.id, email=email, role=payload.role, token_hash=sha256(raw_token.encode()).hexdigest(), expires_at=now + timedelta(days=7))
    db.add(invitation); db.flush(); record_audit(db, actor.organization_id, actor.id, "invitation.created", "organization_invitation", invitation.id, {"email": email, "role": payload.role}); db.commit()
    return {"id": invitation.id, "email": email, "role": payload.role, "token": raw_token, "expires_at": invitation.expires_at}


@router.post("/invitations/accept", status_code=status.HTTP_201_CREATED)
def accept_invitation(payload: InvitationAccept, db: Session = Depends(get_db)) -> dict:
    token_hash = sha256(payload.token.encode()).hexdigest(); now = datetime.now(timezone.utc)
    invitation = db.scalar(select(OrganizationInvitation).where(OrganizationInvitation.token_hash == token_hash))
    expires = invitation.expires_at.replace(tzinfo=timezone.utc) if invitation and invitation.expires_at.tzinfo is None else invitation.expires_at if invitation else now
    if not invitation or invitation.accepted_at or expires <= now:
        raise HTTPException(status_code=400, detail="Invitation is invalid, expired, or already accepted")
    try:
        member = create_organization_member(db, organization_id=invitation.organization_id, email=invitation.email, full_name=payload.full_name, password=payload.password, role=invitation.role)
    except EmailAlreadyRegistered:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    invitation = db.scalar(select(OrganizationInvitation).where(OrganizationInvitation.id == invitation.id)); invitation.accepted_at = now
    record_audit(db, member.organization_id, member.id, "invitation.accepted", "organization_invitation", invitation.id); db.commit()
    return {"id": member.id, "email": member.email, "organization_id": member.organization_id, "role": member.role}


@router.get("/audit-logs")
def audit_logs(limit: int = 100, actor: User = Depends(require_role("admin")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(AuditLog).where(AuditLog.organization_id == actor.organization_id).order_by(AuditLog.created_at.desc()).limit(min(max(limit, 1), 500))).all()
    return [{"id": row.id, "actor_id": row.actor_id, "action": row.action, "resource_type": row.resource_type, "resource_id": row.resource_id, "detail": row.detail, "created_at": row.created_at} for row in rows]


@router.post("/report-schedules", status_code=status.HTTP_201_CREATED)
def create_schedule(payload: ScheduleCreate, actor: User = Depends(require_role("manager")), db: Session = Depends(get_db)) -> dict:
    delta = {"daily": timedelta(days=1), "weekly": timedelta(days=7), "monthly": timedelta(days=30)}[payload.frequency]
    schedule = ReportSchedule(organization_id=actor.organization_id, created_by_id=actor.id, name=payload.name.strip(), frequency=payload.frequency, next_run_at=datetime.now(timezone.utc) + delta)
    db.add(schedule); db.flush(); record_audit(db, actor.organization_id, actor.id, "report_schedule.created", "report_schedule", schedule.id); db.commit(); db.refresh(schedule)
    return {"id": schedule.id, "name": schedule.name, "frequency": schedule.frequency, "next_run_at": schedule.next_run_at, "is_active": schedule.is_active}


@router.get("/report-schedules")
def schedules(actor: User = Depends(require_role("manager")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(ReportSchedule).where(ReportSchedule.organization_id == actor.organization_id).order_by(ReportSchedule.created_at.desc())).all()
    return [{"id": row.id, "name": row.name, "frequency": row.frequency, "next_run_at": row.next_run_at, "last_run_at": row.last_run_at, "is_active": row.is_active} for row in rows]


@router.post("/report-schedules/{schedule_id}/run")
def run_schedule(schedule_id: UUID, actor: User = Depends(require_role("manager")), db: Session = Depends(get_db)) -> dict:
    schedule = db.scalar(select(ReportSchedule).where(ReportSchedule.id == schedule_id, ReportSchedule.organization_id == actor.organization_id))
    if not schedule or not schedule.is_active:
        raise HTTPException(status_code=404, detail="Active report schedule not found")
    analytics = BusinessAnalyticsService(BusinessAnalyticsRepository(db, actor.organization_id))
    report = {"overview": analytics.overview(None, None), "products": analytics.products(None, None, 10), "regions": analytics.regions(None, None), "customers": analytics.customer_ltv(10), "generated_at": datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC"), "search": ""}
    asset = FileService(db).save_report(actor.id, actor.organization_id, report)
    schedule = db.scalar(select(ReportSchedule).where(ReportSchedule.id == schedule_id)); schedule.last_run_at = datetime.now(timezone.utc)
    record_audit(db, actor.organization_id, actor.id, "report_schedule.run", "file_asset", asset.id, {"schedule_id": str(schedule_id)}); db.commit()
    return {"file_id": asset.id, "view_url": f"/api/v1/files/{asset.id}/view", "download_url": f"/api/v1/files/{asset.id}/download"}
