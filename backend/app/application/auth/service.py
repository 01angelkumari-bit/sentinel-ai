from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.domain.users.models import AuthSession, Organization, User
from app.application.auth.workspace import rotate_user_sessions

password_hasher = PasswordHash.recommended()
class AuthenticationError(Exception): pass
class EmailAlreadyRegistered(Exception): pass
def register_user(db: Session, *, email: str, full_name: str, password: str, organization_name: str | None = None) -> User:
    normalized_email = email.lower()
    if db.scalar(select(User).where(User.email == normalized_email)):
        raise EmailAlreadyRegistered()
    display_name = full_name.strip()
    organization = Organization(name=(organization_name or f"{display_name}'s Organization").strip())
    db.add(organization); db.flush()
    user = User(organization_id=organization.id, email=normalized_email, full_name=display_name, password_hash=password_hasher.hash(password), role="owner")
    db.add(user); db.commit(); db.refresh(user); db.refresh(user, attribute_names=["organization"])
    return user
def create_organization_member(db: Session, *, organization_id: UUID, email: str, full_name: str, password: str, role: str) -> User:
    normalized_email = email.lower()
    if db.scalar(select(User).where(User.email == normalized_email)):
        raise EmailAlreadyRegistered()
    user = User(organization_id=organization_id, email=normalized_email, full_name=full_name.strip(), password_hash=password_hasher.hash(password), role=role)
    db.add(user); db.commit(); db.refresh(user); db.refresh(user, attribute_names=["organization"])
    return user
def authenticate(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not password_hasher.verify(password, user.password_hash): raise AuthenticationError()
    return user
def create_access_token(db: Session, user: User, *, remember: bool = False, rotate_sessions: bool = False) -> str:
    if rotate_sessions:
        rotate_user_sessions(db, user.organization_id, user.id)
    settings = get_settings(); expires = datetime.now(UTC) + (timedelta(days=7) if remember else timedelta(minutes=settings.access_token_expire_minutes)); jti = uuid4().hex
    db.add(AuthSession(user_id=user.id, organization_id=user.organization_id, jti=jti, expires_at=expires))
    return jwt.encode({"sub": str(user.id), "org": str(user.organization_id), "role": user.role, "jti": jti, "exp": expires, "iat": datetime.now(UTC)}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
