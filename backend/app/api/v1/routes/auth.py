from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import current_user
from app.api.v1.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.application.auth.service import AuthenticationError, EmailAlreadyRegistered, authenticate, create_access_token, register_user
from app.domain.users.models import User
from app.infrastructure.database import get_db
router = APIRouter(prefix="/auth", tags=["authentication"])
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    try: return register_user(db, email=str(payload.email), full_name=payload.full_name, password=payload.password)
    except EmailAlreadyRegistered: raise HTTPException(status_code=409, detail="An account with this email already exists")
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try: user = authenticate(db, email=str(payload.email), password=payload.password)
    except AuthenticationError: raise HTTPException(status_code=401, detail="Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    return TokenResponse(access_token=create_access_token(user.id))
@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)) -> User: return user

