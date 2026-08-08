import json
from uuid import UUID
from sqlalchemy.orm import Session
from app.domain.users.models import AuditLog


def record_audit(db: Session, organization_id: UUID, actor_id: UUID | None, action: str, resource_type: str, resource_id: object | None = None, detail: dict | None = None) -> None:
    db.add(AuditLog(organization_id=organization_id, actor_id=actor_id, action=action, resource_type=resource_type, resource_id=str(resource_id) if resource_id is not None else None, detail=json.dumps(detail, separators=(",", ":"), default=str) if detail else None))
