# app/routes/mfa_totp.py
import re


import pyotp
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config.database import get_db
from app.models.models import User, MfaTotpSecret
from app.schemas.schemas import (
    TotpSetupStartRequest,
    TotpSetupStartResponse,
    TotpVerifyRequest,
    SetAuthenticatorRequest,
)


router = APIRouter()

EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
MOBILE_REGEX = re.compile(r"^(?:\+91)?[6-9]\d{9}$")


def _normalize_identifier(identifier: str) -> tuple[str, bool, bool]:
    identifier = identifier.strip()
    is_email = bool(EMAIL_REGEX.match(identifier))
    is_mobile = bool(MOBILE_REGEX.match(identifier))
    if is_mobile and identifier.startswith("+91"):
        identifier = identifier[3:]
    return identifier, is_email, is_mobile


@router.post("/auth/mfa/start", response_model=TotpSetupStartResponse)
async def totp_setup_start(payload: TotpSetupStartRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate a TOTP secret and return otpauth URL + raw secret.
    If an active secret already exists for this user, reuse it (idempotent).
    """
    identifier, is_email, is_mobile = _normalize_identifier(payload.identifier)
    if not (is_email or is_mobile):
        raise HTTPException(status_code=400, detail="Invalid identifier format")

    result = await db.execute(
        select(User).where((User.email == identifier) | (User.phone == identifier))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not getattr(user, "status", False):
        raise HTTPException(status_code=403, detail="User account is inactive")

    # Check for existing active secret
    existing_q = await db.execute(
        select(MfaTotpSecret).where(MfaTotpSecret.user_id == user.userId, MfaTotpSecret.active == True)
    )
    existing = existing_q.scalar_one_or_none()
    if existing:
        secret = str(existing.secret)
    else:
        secret = pyotp.random_base32()
        record = MfaTotpSecret(
            user_id=user.userId,
            email=str(user.email),
            secret=secret,
            issuer="Semiconspace",
            account_name=str(user.email),
            active=True,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

    # Build otpauth URL
    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(name=str(user.email), issuer_name="Semiconspace")

    return TotpSetupStartResponse(otpauth_url=otpauth_url, secret=secret)


@router.post("/auth/mfa/toggle")
async def toggle_authenticator(payload: SetAuthenticatorRequest, db: AsyncSession = Depends(get_db)):
    """
    Enable/disable authenticator for a user by email/phone.
    If enabling, ensure a TOTP secret exists (create if missing).
    """
    identifier, is_email, is_mobile = _normalize_identifier(payload.identifier)
    if not (is_email or is_mobile):
        raise HTTPException(status_code=400, detail="Invalid identifier format")

    # Load user
    result = await db.execute(
        select(User).where((User.email == identifier) | (User.phone == identifier))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update flag (use setattr to satisfy type checker if model columns are untyped)
    setattr(user, 'authenticator', bool(payload.enabled))  # type: ignore[assignment]
    await db.commit()
    await db.refresh(user)

    # If enabling and no active secret, create one (idempotent)
    if bool(getattr(user, 'authenticator', False)):
        existing_q = await db.execute(
            select(MfaTotpSecret).where(MfaTotpSecret.user_id == user.userId, MfaTotpSecret.active == True)
        )
        existing = existing_q.scalar_one_or_none()
        if not existing:
            secret = pyotp.random_base32()
            record = MfaTotpSecret(
                user_id=user.userId,
                email=str(user.email),
                secret=secret,
                issuer="Semiconspace",
                account_name=str(user.email),
                active=True,
            )
            db.add(record)
            await db.commit()

    return {"success": True, "message": "Authenticator updated", "data": {"authenticator": user.authenticator}}


@router.post("/auth/mfa/verify")
async def totp_verify(payload: TotpVerifyRequest, db: AsyncSession = Depends(get_db)):
    """
    Verify a 6-digit TOTP code for a user with an active secret.
    After success:
    - If purpose == "register": issue JWT + produce Kafka FULL_USER_REGISTERED
    - Else (login/default): issue JWT + produce Kafka FULL_USER_LOGGEDIN
    """
    identifier, is_email, is_mobile = _normalize_identifier(payload.identifier)
    if not (is_email or is_mobile):
        raise HTTPException(status_code=400, detail="Invalid identifier format")

    # Load user
    result = await db.execute(
        select(User).where((User.email == identifier) | (User.phone == identifier))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not getattr(user, "status", False):
        raise HTTPException(status_code=403, detail="User account is inactive")

    # Load active secret
    secret_q = await db.execute(
        select(MfaTotpSecret).where(MfaTotpSecret.user_id == user.userId, MfaTotpSecret.active == True)
    )
    secret_rec = secret_q.scalar_one_or_none()
    if not secret_rec:
        raise HTTPException(status_code=400, detail="TOTP not set up for this user")

    totp = pyotp.TOTP(str(secret_rec.secret))
    # Verify within default window; adjust 'valid_window' if needed to tolerate small drift
    is_valid = totp.verify(payload.code)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    # Issue JWT token
    from app.utils.jwt_utils import create_token
    
    # Determine purpose for token and events
    purpose = (payload.purpose or "login").lower()
    
    # For admin login, include type in token
    token_payload = {
        "userId": str(user.userId),
        "role": str(user.role),
        "role_id": user.role_id,
        "email": str(user.email),
    }
    if purpose == "admin_login":
        token_payload["type"] = "admin"
    
    token = create_token(token_payload)

    # Ensure DB reflects authenticator enabled when this verify completes for registration
    if purpose == "register":
        try:
            setattr(user, 'authenticator', True)
            await db.commit()
            await db.refresh(user)
        except Exception:
            # If DB update fails, continue but report generic success
            pass

    # Produce Kafka event depending on purpose
    try:
        from datetime import datetime, timezone
        from app.services import kafka_producer
        from app.services.kafka_topics import FULL_USER_REGISTERED, FULL_USER_LOGGEDIN

        if purpose == "register":
            await kafka_producer.send_event(
                FULL_USER_REGISTERED,
                {
                    "action": "registered",
                    "success": True,
                    "userId": str(user.userId),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "password": user.password,
                    "role": user.role,
                    "role_id": user.role_id,
                    "created_by": user.email,
                    "created_at": getattr(user, "created_at", datetime.now(timezone.utc)).isoformat(),
                    "authenticator": True,
                },
            )
            success_message = "User registered successfully"
        else:
            await kafka_producer.send_event(
                FULL_USER_LOGGEDIN,
                {
                    "action": "login",
                    "success": True,
                    "userId": str(user.userId),
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                    "role_id": user.role_id,
                    "time": datetime.now(timezone.utc).isoformat(),
                },
            )
            success_message = "User logged in successfully"
    except Exception:
        # Do not fail the request due to Kafka publishing errors
        success_message = "MFA verified"

    # Return token + user info (aligned with login/register success payloads)
    return {
        "success": True,
        "message": success_message,
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "userId": str(user.userId),
            "role": user.role,
            "role_id": user.role_id,
            "email": user.email,
            "phone": user.phone,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
    }