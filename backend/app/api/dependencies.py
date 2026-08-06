from uuid import UUID
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.domain.users.models import User
from app.infrastructure.database import get_db
security = HTTPBearer()
def current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    try: subject = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])["sub"]
    except (jwt.PyJWTError, KeyError): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, UUID(subject))
    if not user: raise HTTPException(status_code=401, detail="Account not found")
    return user

