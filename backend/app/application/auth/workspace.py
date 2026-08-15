from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.application.files.sales_import import delete_tenant_business_data
from app.core.config import get_settings
from app.domain.users.models import AuthSession, ChatConversation, ChatMessage, DatasetImport, FileAsset, OtpChallenge


def _storage_root() -> Path:
    backend_root = Path(__file__).resolve().parents[3]
    configured = Path(get_settings().storage_root)
    return (configured if configured.is_absolute() else backend_root / configured).resolve()


def clear_temporary_workspace(db: Session, organization_id: UUID) -> list[Path]:
    """Remove session-only analytics data while preserving accounts and governance records."""
    root = _storage_root()
    assets = list(db.scalars(select(FileAsset).where(FileAsset.organization_id == organization_id)))
    paths: list[Path] = []
    for asset in assets:
        path = (root / asset.relative_path).resolve()
        if root in path.parents:
            paths.append(path)

    db.execute(delete(ChatMessage).where(ChatMessage.organization_id == organization_id))
    db.execute(delete(ChatConversation).where(ChatConversation.organization_id == organization_id))
    db.execute(delete(DatasetImport).where(DatasetImport.organization_id == organization_id))
    db.execute(delete(FileAsset).where(FileAsset.organization_id == organization_id))
    db.execute(delete(OtpChallenge).where(OtpChallenge.organization_id == organization_id))
    delete_tenant_business_data(db, organization_id)
    db.flush()
    return paths


def rotate_user_sessions(db: Session, organization_id: UUID, user_id: UUID) -> None:
    """Invalidate older login tokens without deleting organization-owned data."""
    db.execute(
        update(AuthSession)
        .where(AuthSession.organization_id == organization_id, AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    db.flush()


def revoke_session(db: Session, jti: str) -> None:
    """Revoke only the session being signed out; permanent tenant data is preserved."""
    db.execute(
        update(AuthSession)
        .where(AuthSession.jti == jti, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    db.commit()
