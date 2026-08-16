from datetime import UTC, datetime
from uuid import UUID
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload
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
        user_id, organization_id = UUID(subject), UUID(token_org)
    except (jwt.PyJWTError, KeyError): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    except (TypeError, ValueError): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    user = db.scalar(
        select(User)
        .join(AuthSession, AuthSession.user_id == User.id)
        .options(joinedload(User.organization))
        .where(
            User.id == user_id,
            User.organization_id == organization_id,
            AuthSession.jti == jti,
            AuthSession.organization_id == organization_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
        )
    )
    if not user: raise HTTPException(status_code=401, detail="Session expired, revoked, or unavailable")
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
