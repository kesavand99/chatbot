from pydantic import BaseModel, EmailStr, Field
from typing import Annotated
from uuid import UUID
from datetime import datetime
from typing import Optional, Any


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    password: str
    role_id: int
    mfa_required: Optional[bool] = None  # Optional per-request override


class LoginRequest(BaseModel):
    identifier: str
    password: str
    role_id: Optional[int] = 2
    code: Optional[str] = None  # optional 6-digit TOTP code for MFA login


class SetAuthenticatorRequest(BaseModel):
    identifier: str  # email or phone
    enabled: bool





# Google auth requests
class GoogleRegisterRequest(BaseModel):
    id_token: str
    phone: Optional[str] = None
    role_id: int


class GoogleLoginRequest(BaseModel):
    id_token: str


class GoogleSignInRequest(BaseModel):
    id_token: str
    phone: Optional[str] = None
    role_id: Optional[int] = 2


class UserResponse(BaseModel):
    userId: UUID
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    role_id: int
    created_at: datetime
    created_by: str
    modified_by: Optional[str]
    modified_at: Optional[datetime]

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    userId: UUID
    role: str
    role_id: int
    email: EmailStr
    phone: Optional[str] = None
    first_name: str
    last_name: str

    class Config:
        from_attributes = True


# ✅ Flexible response wrapper
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None   # can be TokenResponse, UserResponse, [] etc.


# TOTP schemas
class TotpSetupStartRequest(BaseModel):
    identifier: str  # email or phone


class TotpSetupStartResponse(BaseModel):
    otpauth_url: str
    secret: str  # base32 secret (show raw key and QR code)


class TotpVerifyRequest(BaseModel):
    identifier: str  # email or phone
    code: Annotated[str, Field(pattern=r"^\d{6}$")]
    purpose: Optional[str] = "login"  # "register" or "login" to decide Kafka event


# Password reset
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResendOtpRequest(BaseModel):
    email: EmailStr
    otp_ref: UUID


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: Annotated[str, Field(pattern=r"^\d{6}$")]  # 6-digit numeric
    new_password: str
    confirm_password: str


class ValidateOtpRequest(BaseModel):
    otp: Annotated[str, Field(pattern=r"^\d{6}$")]  # 6-digit numeric
    otp_ref: UUID  # reference returned when requesting OTP


class SetNewPasswordRequest(BaseModel):
    new_password: str
    confirm_password: str
