# app/routes/password_reset.py
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import cast
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from app.config.database import get_db
from app.models.models import User, PasswordResetOTP
from app.schemas.schemas import (
    ForgotPasswordRequest,
    ResendOtpRequest,
    ResetPasswordRequest,
    ValidateOtpRequest,
    SetNewPasswordRequest,
)
from app.services import kafka_producer
from app.services.kafka_topics import FULL_PASSWORD_RESET_OTP, FULL_PASSWORD_RESET_COMPLETED, FULL_AUTH_PASSWORD_UPDATED
from app.utils.jwt_utils import create_token, decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
logger = logging.getLogger("auth")

OTP_TTL_SECONDS = 180
bearer = HTTPBearer(auto_error=True)


def generate_6_digit_otp() -> str:
    # Always 6-digit numeric with leading zeros if needed
    return f"{random.randint(0, 999999):06d}"


@router.post("/auth/forgot_password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Find user by email
        result = await db.execute(select(User).where(User.email == payload.email))
        user: User | None = result.scalar_one_or_none()
        if not user:
            # Don't leak existence; keep generic message
            raise HTTPException(status_code=404, detail="Invalid email")

        # Handle both first-time and resend here with cooldown check
        now = datetime.utcnow()
        result_otp = await db.execute(
            select(PasswordResetOTP).where(PasswordResetOTP.email == payload.email)
        )
        existing: PasswordResetOTP | None = result_otp.scalar_one_or_none()

        # Enforce cooldown if an OTP exists
        if existing:
            created_at = cast(datetime, existing.created_at)
            elapsed = (now - created_at).total_seconds()
            if elapsed < 30:
                wait = int(30 - elapsed)
                raise HTTPException(status_code=429, detail=f"Please wait {wait} seconds before requesting OTP again")

            # Update existing OTP
            otp = generate_6_digit_otp()
            setattr(existing, "otp_code", otp)
            setattr(existing, "expires_at", now + timedelta(seconds=OTP_TTL_SECONDS))
            setattr(existing, "created_at", now)  # reset cooldown start
            await db.commit()
            otp_ref = str(existing.id)
        else:
            # Create new OTP
            otp = generate_6_digit_otp()
            expires_at = now + timedelta(seconds=OTP_TTL_SECONDS)

            otp_row = PasswordResetOTP(
                user_id=user.userId,
                email=payload.email,
                otp_code=otp,
                expires_at=expires_at,
            )
            db.add(otp_row)
            await db.commit()
            otp_ref = str(otp_row.id)

        # Send via Kafka for downstream email/SMS service
        try:
            await kafka_producer.send_event(
                FULL_PASSWORD_RESET_OTP,
                {
                    "action": "password_reset_otp",
                    "success": True,
                    "userId": str(user.userId),
                    "email": user.email,
                    "otp": otp,
                    "otp_ref": otp_ref,
                    "expires_in_sec": OTP_TTL_SECONDS,
                    "time": datetime.utcnow().isoformat() + "Z",
                },
            )
        except Exception as e:
            logger.error(f"Kafka OTP send failed for {payload.email}: {e}")

        return {"success": True, "message": "OTP sent to email if it exists", "data": {"otp_ref": otp_ref, "expires_in_sec": OTP_TTL_SECONDS, "resend_available_in_sec": 30}}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in forgot_password: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        try:
            await db.close()
        except Exception:
            pass





@router.post("/auth/validate_otp")
async def validate_otp(payload: ValidateOtpRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Find OTP by otp_ref (id) and code to disambiguate
        result_otp = await db.execute(
            select(PasswordResetOTP).where(
                (PasswordResetOTP.id == payload.otp_ref) & (PasswordResetOTP.otp_code == payload.otp)
            )
        )
        otp_row: PasswordResetOTP | None = result_otp.scalar_one_or_none()
        if not otp_row:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        # Use naive UTC
        now = datetime.utcnow()
        expires_at_val = cast(datetime, otp_row.expires_at)
        if expires_at_val < now:
            await db.execute(delete(PasswordResetOTP).where(PasswordResetOTP.id == otp_row.id))
            await db.commit()
            raise HTTPException(status_code=400, detail="OTP expired")

        # Issue short-lived reset token (5 minutes)
        reset_token = create_token({
            "sub": "password_reset",
            "email": otp_row.email,
            "userId": str(otp_row.user_id),
            "type": "reset"
        }, expires_delta=5)  # minutes

        return {"success": True, "message": "OTP validated", "data": {"reset_token": reset_token}}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in validate_otp: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        try:
            await db.close()
        except Exception:
            pass


@router.post("/auth/set_new_password")
async def set_new_password(payload: SetNewPasswordRequest, creds: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_db)):
    try:
        if payload.new_password != payload.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")

        # Decode and verify reset token
        try:
            token_payload = decode_access_token(creds.credentials)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        if token_payload.get("type") != "reset" or token_payload.get("sub") != "password_reset":
            raise HTTPException(status_code=401, detail="Invalid token type")

        email = token_payload.get("email")
        user_id = token_payload.get("userId")
        if not email or not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Find user by email
        result_user = await db.execute(select(User).where(User.email == email))
        user: User | None = result_user.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update password and audit fields
        old_password = getattr(user, "password")
        setattr(user, "password", payload.new_password)
        setattr(user, "modified_by", str(user.userId))  # self-modified via reset
        setattr(user, "modified_at", datetime.utcnow())

        # Delete any OTPs for this email (cleanup)
        await db.execute(delete(PasswordResetOTP).where(PasswordResetOTP.email == email))

        await db.commit()

        # Emit detailed password updated event for auth on separate topic
        try:
            await kafka_producer.send_event(
                FULL_AUTH_PASSWORD_UPDATED,
                {
                    "action": "auth.password.updated",
                    "userId": str(user.userId),
                    "email": user.email,
                    "old_password": old_password,
                    "new_password": payload.new_password,
                    "modified_by": str(user.email),
                    "modified_at": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"Kafka auth.password.updated failed for {email}: {e}")

        # Emit existing completion signal
        try:
            await kafka_producer.send_event(
                FULL_PASSWORD_RESET_COMPLETED,
                {
                    "action": "password_reset_completed",
                    "success": True,
                    "userId": str(user.userId),
                    "email": user.email,
                    "time": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"Kafka password update event failed for {email}: {e}")

        return {"success": True, "message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in set_new_password: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        try:
            await db.close()
        except Exception:
            pass