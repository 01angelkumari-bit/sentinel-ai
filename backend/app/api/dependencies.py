from datetime import UTC, datetime
from uuid import UUID
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from app.core.config import get_settings
from app.domain.users.models import AuthSession, User
from app.infrastructure.database import get_db
security = HTTPBearer(auto_error=False)
def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject, token_org, jti = claims["sub"], claims["org"], claims["jti"]
    except (jwt.PyJWTError, KeyError): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    session = db.scalar(select(AuthSession).where(AuthSession.jti == jti, AuthSession.revoked_at.is_(None)))
    expires = session.expires_at.replace(tzinfo=UTC) if session and session.expires_at.tzinfo is None else session.expires_at if session else datetime.min.replace(tzinfo=UTC)
    if not session or expires <= datetime.now(UTC): raise HTTPException(status_code=401, detail="Session expired or revoked")
    user = db.get(User, UUID(subject))
    if not user or str(user.organization_id) != token_org or session.user_id != user.id or str(session.organization_id) != token_org: raise HTTPException(status_code=401, detail="Account or organization not found")
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT set_config('app.current_organization', :organization_id, true)"), {"organization_id": token_org})
    return user

ROLE_LEVEL = {"viewer": 0, "employee": 1, "manager": 2, "admin": 3, "owner": 4}
def require_role(minimum_role: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if ROLE_LEVEL.get(user.role, -1) < ROLE_LEVEL[minimum_role]:
            raise HTTPException(status_code=403, detail=f"{minimum_role.title()} role or higher is required")
        return user
    return dependency
