import json
import logging
from time import perf_counter
import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_role, security
from app.api.v1.schemas.auth import EmailRequest, LoginRequest, MemberCreateRequest, MessageResponse, OtpVerifyRequest, PasswordOtpResponse, PasswordResetRequest, RegisterRequest, TokenResponse, UserResponse
from app.application.auth.email_service import EmailConfigurationError, EmailDeliveryError, EmailDomainError
from app.application.auth.otp_service import OtpService
from app.application.auth.service import AuthenticationError, EmailAlreadyRegistered, authenticate, create_access_token, create_organization_member
from app.application.auth.workspace import revoke_session
from app.core.config import get_settings
from app.domain.users.models import User
from app.infrastructure.database import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger("sentinel.auth")


def _token_response(token: str, user: User) -> TokenResponse:
    return TokenResponse(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "name": user.full_name},
        organization={"id": str(user.organization_id), "name": user.organization.name},
        role=user.role,
    )


def _record_timing(response: Response, event: str, started: float, timings: dict[str, float]) -> None:
    timings["total_ms"] = (perf_counter() - started) * 1000
    response.headers["Server-Timing"] = ", ".join(f"{name.removesuffix('_ms')};dur={duration:.1f}" for name, duration in timings.items())
    level = logging.WARNING if timings["total_ms"] >= get_settings().auth_slow_request_ms else logging.INFO
    logger.log(level, "%s %s", event, json.dumps({key: round(value, 2) for key, value in timings.items()}))


def _email_failure(exc: Exception) -> HTTPException:
    if isinstance(exc, EmailDomainError): return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=503, detail="Verification email could not be delivered. Check the email service configuration and try again.")


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED, summary="Queue a real registration OTP")
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    started=perf_counter();timings:dict[str,float]={}
    try: result=OtpService(db).request_registration(email=str(payload.email), full_name=payload.full_name, organization_name=payload.organization_name or f"{payload.full_name}'s Organization", password=payload.password,timings=timings)
    except EmailAlreadyRegistered: raise HTTPException(status_code=409, detail="An account with this email already exists")
    except (EmailConfigurationError, EmailDeliveryError, EmailDomainError) as exc: raise _email_failure(exc)
    _record_timing(response,"REGISTER_REQUEST_END",started,timings)
    return result


@router.post("/register/verify-otp", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def verify_registration(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try: user = OtpService(db).verify_registration(str(payload.email), payload.otp)
    except EmailAlreadyRegistered: raise HTTPException(status_code=409, detail="An account with this email already exists")
    token=create_access_token(db,user);db.commit();return _token_response(token,user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    started=perf_counter();timings:dict[str,float]={}
    logger.info("AUTH_REQUEST_START")
    try: user=authenticate(db,email=str(payload.email),password=payload.password,timings=timings)
    except AuthenticationError: raise HTTPException(status_code=401,detail="Invalid email or password",headers={"WWW-Authenticate":"Bearer"})
    token=create_access_token(db,user,remember=payload.remember,timings=timings)
    commit_started=perf_counter();db.commit();timings["commit_ms"]=(perf_counter()-commit_started)*1000
    _record_timing(response,"AUTH_REQUEST_END",started,timings)
    return _token_response(token,user)


@router.post("/otp-login/request", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def request_otp_login(payload: EmailRequest, db: Session = Depends(get_db)) -> dict:
    try: return OtpService(db).request_user_otp(str(payload.email),"login")
    except (EmailConfigurationError, EmailDeliveryError) as exc: raise _email_failure(exc)


@router.post("/otp-login/verify", response_model=TokenResponse)
def verify_otp_login(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token,user=OtpService(db).verify_login(str(payload.email),payload.otp,payload.remember)
    return _token_response(token,user)


@router.post("/password/request-otp", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def request_password_otp(payload: EmailRequest, db: Session = Depends(get_db)) -> dict:
    try: return OtpService(db).request_user_otp(str(payload.email),"password_reset")
    except (EmailConfigurationError, EmailDeliveryError) as exc: raise _email_failure(exc)


@router.post("/password/verify-otp", response_model=PasswordOtpResponse)
def verify_password_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> dict:
    token=OtpService(db).verify_password_reset(str(payload.email),payload.otp)
    return {"message":"Verification succeeded. Set a new password.","reset_token":token}


@router.post("/password/reset", response_model=MessageResponse)
def reset_password(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> dict:
    OtpService(db).reset_password(payload.reset_token,payload.new_password);return {"message":"Password reset completed. Sign in with your new password."}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(credentials: HTTPAuthorizationCredentials = Depends(security), user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    claims=jwt.decode(credentials.credentials,get_settings().jwt_secret_key,algorithms=[get_settings().jwt_algorithm])
    revoke_session(db, str(claims["jti"]))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)) -> UserResponse:
    return UserResponse(id=user.id,email=user.email,full_name=user.full_name,organization_id=user.organization_id,organization_name=user.organization.name,role=user.role)


@router.post("/members", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_member(payload: MemberCreateRequest,actor:User=Depends(require_role("admin")),db:Session=Depends(get_db))->UserResponse:
    try: member=create_organization_member(db,organization_id=actor.organization_id,email=str(payload.email),full_name=payload.full_name,password=payload.password,role=payload.role)
    except EmailAlreadyRegistered: raise HTTPException(status_code=409,detail="An account with this email already exists")
    return UserResponse(id=member.id,email=member.email,full_name=member.full_name,organization_id=member.organization_id,organization_name=member.organization.name,role=member.role)
