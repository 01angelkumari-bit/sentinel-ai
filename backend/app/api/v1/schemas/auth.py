from uuid import UUID
from typing import Literal
from pydantic import BaseModel, EmailStr, Field
class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    organization_name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    remember: bool = False
class EmailRequest(BaseModel):
    email: EmailStr
class OtpVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^[A-Za-z0-9]{6}$")
    remember: bool = False
class PasswordResetRequest(BaseModel):
    reset_token: str = Field(min_length=32, max_length=300)
    new_password: str = Field(min_length=8, max_length=128)
class MessageResponse(BaseModel):
    message: str
class PasswordOtpResponse(MessageResponse):
    reset_token: str | None = None
class MemberCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "manager", "employee", "viewer"]
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, str] | None = None
    organization: dict[str, str] | None = None
    role: str | None = None
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    organization_id: UUID
    organization_name: str
    role: str
    model_config = {"from_attributes": True}
