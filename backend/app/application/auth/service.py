from datetime import UTC, datetime, timedelta
from uuid import UUID
import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.domain.users.models import User

password_hasher = PasswordHash.recommended()
class AuthenticationError(Exception): pass
class EmailAlreadyRegistered(Exception): pass
def register_user(db: Session, *, email: str, full_name: str, password: str) -> User:
    normalized_email = email.lower()
    if db.scalar(select(User).where(User.email == normalized_email)):
        raise EmailAlreadyRegistered()
    user = User(email=normalized_email, full_name=full_name.strip(), password_hash=password_hasher.hash(password))
    db.add(user); db.commit(); db.refresh(user)
    return user
def authenticate(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not password_hasher.verify(password, user.password_hash): raise AuthenticationError()
    return user
def create_access_token(user_id: UUID) -> str:
    settings = get_settings(); expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expires, "iat": datetime.now(UTC)}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

