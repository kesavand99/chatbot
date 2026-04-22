from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime, timedelta
import uuid

from app.config.database import Base

class User(Base):
    __tablename__ = "users"

    userId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, unique=True)
    password = Column(String, nullable=False)
    role = Column(ARRAY(String), nullable=False)  # Changed to support array of roles
    role_id = Column(ARRAY(Integer), nullable=False)  # Changed to support array of role IDs
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=False)
    modified_by = Column(String, nullable=True)
    modified_at = Column(DateTime, nullable=True)
    status = Column(Boolean, default=True)
    authenticator = Column(Boolean, default=False)


class UserRole(Base):
    __tablename__ = "user_roles"

    role_id = Column(Integer, primary_key=True, nullable=False)
    role_name = Column(String, nullable=False)
    status = Column(Boolean, default=True)


class PasswordResetOTP(Base):
    """Stores a short-lived OTP for password reset (expires in 180 seconds)."""

    __tablename__ = "password_reset_otps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.userId"), nullable=False)
    email = Column(String, nullable=False, index=True)
    otp_code = Column(String, nullable=False)  # 6-digit numeric stored as string
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class MfaTotpSecret(Base):
    """TOTP secret for Google Authenticator (per user)."""

    __tablename__ = "mfa_totp_secrets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.userId"), nullable=False)
    email = Column(String, nullable=False, index=True)
    secret = Column(String, nullable=False)  # base32 secret for TOTP
    issuer = Column(String, nullable=False, default="Semiconspace")
    account_name = Column(String, nullable=False)  # typically user email
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)