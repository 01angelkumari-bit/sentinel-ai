from __future__ import annotations

import hashlib
import hmac
import secrets
import string
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.application.auth.email_service import SmtpEmailService, validate_mx_domain
from app.application.auth.service import EmailAlreadyRegistered, create_access_token, password_hasher
from app.core.config import get_settings
from app.domain.users.models import OtpChallenge, Organization, PendingRegistration, User

ALPHABET = string.ascii_uppercase + string.digits


def _now() -> datetime: return datetime.now(UTC)
def _aware(value: datetime) -> datetime: return value.replace(tzinfo=UTC) if value.tzinfo is None else value
def _otp_hash(email: str, purpose: str, code: str) -> str:
    key = get_settings().jwt_secret_key.encode()
    return hmac.new(key, f"{email.lower()}:{purpose}:{code.upper()}".encode(), hashlib.sha256).hexdigest()
def _code() -> str:
    while True:
        value = "".join(secrets.choice(ALPHABET) for _ in range(6))
        if any(char.isalpha() for char in value) and any(char.isdigit() for char in value): return value
def _generic() -> dict[str, str]: return {"message": "If an account exists for this email, a verification code has been sent."}


class OtpService:
    def __init__(self, db: Session) -> None: self.db, self.settings, self.email = db, get_settings(), SmtpEmailService()

    def _hourly_limit(self, email: str, purpose: str) -> None:
        since = _now() - timedelta(hours=1)
        count = self.db.scalar(select(func.count()).select_from(OtpChallenge).where(OtpChallenge.email == email, OtpChallenge.purpose == purpose, OtpChallenge.created_at >= since)) or 0
        if count >= self.settings.otp_hourly_limit: raise HTTPException(status_code=429, detail="Too many verification requests. Try again later.")

    def request_registration(self, *, email: str, full_name: str, organization_name: str, password: str) -> dict[str, str]:
        normalized = email.lower(); validate_mx_domain(normalized)
        if self.db.scalar(select(User.id).where(User.email == normalized)): raise EmailAlreadyRegistered()
        existing = self.db.scalar(select(PendingRegistration).where(PendingRegistration.email == normalized))
        now = _now()
        if existing and (now - _aware(existing.last_sent_at)).total_seconds() < self.settings.otp_resend_cooldown_seconds: raise HTTPException(status_code=429, detail="Wait before requesting another verification code.")
        code = _code(); expires = now + timedelta(minutes=self.settings.otp_expire_minutes)
        self.email.send_otp(normalized, code, "registration")
        if existing:
            existing.full_name=full_name.strip();existing.organization_name=organization_name.strip();existing.password_hash=password_hasher.hash(password);existing.otp_hash=_otp_hash(normalized,"registration",code);existing.expires_at=expires;existing.attempts=0;existing.last_sent_at=now
        else:self.db.add(PendingRegistration(email=normalized,full_name=full_name.strip(),organization_name=organization_name.strip(),password_hash=password_hasher.hash(password),otp_hash=_otp_hash(normalized,"registration",code),expires_at=expires,attempts=0,last_sent_at=now))
        self.db.commit();return {"message":"A verification code was sent to your email address."}

    def verify_registration(self, email: str, code: str) -> User:
        normalized=email.lower();pending=self.db.scalar(select(PendingRegistration).where(PendingRegistration.email==normalized))
        if not pending or _aware(pending.expires_at)<=_now(): raise HTTPException(status_code=400,detail="The verification code is invalid or expired.")
        if pending.attempts>=self.settings.otp_max_attempts: raise HTTPException(status_code=429,detail="Too many verification attempts. Request a new code.")
        pending.attempts+=1
        if not hmac.compare_digest(pending.otp_hash,_otp_hash(normalized,"registration",code)):
            self.db.commit();raise HTTPException(status_code=400,detail="The verification code is invalid or expired.")
        if self.db.scalar(select(User.id).where(User.email==normalized)): self.db.delete(pending);self.db.commit();raise EmailAlreadyRegistered()
        organization=Organization(name=pending.organization_name);self.db.add(organization);self.db.flush();user=User(organization_id=organization.id,email=normalized,full_name=pending.full_name,password_hash=pending.password_hash,role="owner");self.db.add(user);self.db.delete(pending);self.db.commit();self.db.refresh(user);self.db.refresh(user,attribute_names=["organization"]);return user

    def request_user_otp(self, email: str, purpose: str) -> dict[str, str]:
        normalized=email.lower();user=self.db.scalar(select(User).where(User.email==normalized))
        if not user:return _generic()
        self._hourly_limit(normalized,purpose);latest=self.db.scalar(select(OtpChallenge).where(OtpChallenge.email==normalized,OtpChallenge.purpose==purpose).order_by(OtpChallenge.created_at.desc()))
        if latest and (_now()-_aware(latest.created_at)).total_seconds()<self.settings.otp_resend_cooldown_seconds: raise HTTPException(status_code=429,detail="Wait before requesting another verification code.")
        self.db.execute(update(OtpChallenge).where(OtpChallenge.email==normalized,OtpChallenge.purpose==purpose,OtpChallenge.consumed_at.is_(None)).values(consumed_at=_now()))
        code=_code();challenge=OtpChallenge(user_id=user.id,organization_id=user.organization_id,email=normalized,purpose=purpose,otp_hash=_otp_hash(normalized,purpose,code),expires_at=_now()+timedelta(minutes=self.settings.otp_expire_minutes),attempts=0)
        self.email.send_otp(normalized,code,purpose);self.db.add(challenge);self.db.commit();return _generic()

    def _verify(self,email:str,purpose:str,code:str)->OtpChallenge:
        normalized=email.lower();challenge=self.db.scalar(select(OtpChallenge).where(OtpChallenge.email==normalized,OtpChallenge.purpose==purpose,OtpChallenge.consumed_at.is_(None)).order_by(OtpChallenge.created_at.desc()))
        if not challenge or _aware(challenge.expires_at)<=_now():raise HTTPException(status_code=400,detail="The verification code is invalid or expired.")
        if challenge.attempts>=self.settings.otp_max_attempts:raise HTTPException(status_code=429,detail="Too many verification attempts. Request a new code.")
        challenge.attempts+=1
        if not hmac.compare_digest(challenge.otp_hash,_otp_hash(normalized,purpose,code)):
            self.db.commit();raise HTTPException(status_code=400,detail="The verification code is invalid or expired.")
        challenge.consumed_at=_now();return challenge

    def verify_login(self,email:str,code:str,remember:bool)->str:
        challenge=self._verify(email,"login",code);user=self.db.get(User,challenge.user_id);token=create_access_token(self.db,user,remember=remember,reset_workspace=True);self.db.commit();return token

    def verify_password_reset(self,email:str,code:str)->str:
        challenge=self._verify(email,"password_reset",code);raw=secrets.token_urlsafe(48);challenge.reset_token_hash=hashlib.sha256(raw.encode()).hexdigest();challenge.reset_token_expires_at=_now()+timedelta(minutes=10);self.db.commit();return raw

    def reset_password(self,reset_token:str,new_password:str)->None:
        digest=hashlib.sha256(reset_token.encode()).hexdigest();challenge=self.db.scalar(select(OtpChallenge).where(OtpChallenge.reset_token_hash==digest))
        if not challenge or not challenge.reset_token_expires_at or _aware(challenge.reset_token_expires_at)<=_now():raise HTTPException(status_code=400,detail="The password reset authorization is invalid or expired.")
        user=self.db.get(User,challenge.user_id);user.password_hash=password_hasher.hash(new_password);challenge.reset_token_hash=None;challenge.reset_token_expires_at=None;self.db.commit()
