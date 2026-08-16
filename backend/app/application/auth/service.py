from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID, uuid4
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.core.config import get_settings
from app.domain.users.models import AuthSession, Organization, User
from app.application.auth.workspace import rotate_user_sessions

# OWASP's Argon2id minimum profile is secure while avoiding pwdlib's costly
# four-lane default on a constrained web worker. Existing hashes are upgraded
# transparently after a successful login.
password_hasher = PasswordHash((Argon2Hasher(time_cost=2, memory_cost=19_456, parallelism=1),))
_dummy_password_hash = password_hasher.hash("sentinel-constant-time-auth-check")
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
def authenticate(db: Session, *, email: str, password: str, timings: dict[str, float] | None = None) -> User:
    started = perf_counter()
    user = db.scalar(select(User).options(joinedload(User.organization)).where(User.email == email.lower()))
    if timings is not None: timings["db_query_ms"] = (perf_counter() - started) * 1000
    started = perf_counter()
    verified, updated_hash = password_hasher.verify_and_update(password, user.password_hash if user else _dummy_password_hash)
    if timings is not None: timings["password_verify_ms"] = (perf_counter() - started) * 1000
    if not user or not verified: raise AuthenticationError()
    if updated_hash:
        user.password_hash = updated_hash
    return user
def create_access_token(db: Session, user: User, *, remember: bool = False, rotate_sessions: bool = False, timings: dict[str, float] | None = None) -> str:
    started = perf_counter()
    if rotate_sessions:
        rotate_user_sessions(db, user.organization_id, user.id)
    settings = get_settings(); expires = datetime.now(UTC) + (timedelta(days=7) if remember else timedelta(minutes=settings.access_token_expire_minutes)); jti = uuid4().hex
    db.add(AuthSession(user_id=user.id, organization_id=user.organization_id, jti=jti, expires_at=expires))
    token = jwt.encode({"sub": str(user.id), "org": str(user.organization_id), "role": user.role, "jti": jti, "exp": expires, "iat": datetime.now(UTC)}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    if timings is not None: timings["session_jwt_ms"] = (perf_counter() - started) * 1000
    return token
