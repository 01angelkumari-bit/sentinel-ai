"""Local-only workspace provisioning for the Windows upload-first launcher."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.users.models import Organization, User

LOCAL_WORKSPACE_EMAIL = "local-workspace@sentinel.example.com"
_LEGACY_LOCAL_WORKSPACE_EMAIL = "local-workspace@sentinel.local"


def get_or_create_local_workspace_user(db: Session) -> User:
    """Return the single owner used only when LOCAL_DEMO_MODE is enabled."""
    user = db.scalar(
        select(User)
        .options(joinedload(User.organization))
        .where(User.email.in_((LOCAL_WORKSPACE_EMAIL, _LEGACY_LOCAL_WORKSPACE_EMAIL)))
    )
    if user:
        if user.email != LOCAL_WORKSPACE_EMAIL:
            user.email = LOCAL_WORKSPACE_EMAIL
            db.commit()
            db.refresh(user, attribute_names=["organization"])
        return user

    organization = Organization(name="Local Sentinel Workspace")
    db.add(organization)
    db.flush()
    user = User(
        organization_id=organization.id,
        email=LOCAL_WORKSPACE_EMAIL,
        full_name="Local Workspace",
        # This account never authenticates with a password. It exists only so
        # the existing organization-isolated import path remains unchanged.
        password_hash="local-workspace-not-for-authentication",
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user, attribute_names=["organization"])
    return user
