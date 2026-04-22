# app/login.py
import logging
import re
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from app.config import database
from app.models import models
from app.schemas.schemas import LoginRequest
from app.services import kafka_producer
from app.utils.jwt_utils import create_token

router = APIRouter()
logger = logging.getLogger("auth")

EMAIL_REGEX = r"^[^@]+@[^@]+\.[^@]+$"
MOBILE_REGEX = r"^(?:\+91)?[6-9]\d{9}$"


@router.post("/auth/login")
async def login_user(request: LoginRequest, db: AsyncSession = Depends(database.get_db)):
    try:
        identifier = request.identifier.strip()
        is_email = bool(re.match(EMAIL_REGEX, identifier))
        is_mobile = bool(re.match(MOBILE_REGEX, identifier))

        if not (is_email or is_mobile):
            detail_msg = "Invalid email format" if "@" in identifier else "Invalid mobile number format"
            logger.warning(f"❌ {detail_msg}: {identifier}")
            raise HTTPException(status_code=400, detail=detail_msg)

        # Normalize mobile
        if is_mobile and identifier.startswith("+91"):
            identifier = identifier[3:]

        # Fetch user
        result = await db.execute(
            select(models.User).where(
                (models.User.email == identifier) | (models.User.phone == identifier)
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            detail_msg = "Invalid Email credentials" if is_email else "Invalid Mobile credentials"
            logger.warning(f"❌ Login failed: {detail_msg} for {identifier}")
            raise HTTPException(status_code=404, detail=detail_msg)

        if not getattr(user, "status", False):
            logger.warning(f"❌ User inactive: {identifier}")
            raise HTTPException(status_code=403, detail="User account is inactive")

        # Plain-text password check
        if request.password != str(user.password):
            logger.warning(f"❌ Incorrect password for: {identifier}")
            raise HTTPException(status_code=401, detail="Incorrect password")

        # Role check: Normal login allows if role_id array contains 2
        user_role_ids = getattr(user, 'role_id', [])
        if not isinstance(user_role_ids, list):
            user_role_ids = [user_role_ids] if user_role_ids is not None else []
            
        if 2 not in user_role_ids:
            logger.warning(f"❌ Unauthorized role login attempt: {identifier} (role_id: {user.role_id})")
            raise HTTPException(status_code=403, detail="Invalid User")

        # If user has authenticator enabled, check for TOTP code; if missing, require MFA
        if getattr(user, "authenticator", False):
            code = getattr(request, "code", None)
            if not code:
                logger.info(f"🔐 MFA required for user: {identifier}")
                return {
                    "success": True,
                    "message": "MFA required",
                    "data": {
                        "mfa_required": True,
                        "method": "totp",
                        "identifier": identifier,
                        "purpose": "login",
                    }
                }
            # Validate code against active secret
            from app.models.models import MfaTotpSecret
            totp_q = await db.execute(
                select(MfaTotpSecret).where(MfaTotpSecret.user_id == user.userId, MfaTotpSecret.active == True)
            )
            totp_rec = totp_q.scalar_one_or_none()
            if not totp_rec:
                raise HTTPException(status_code=400, detail="TOTP not set up for this user")
            import pyotp
            totp = pyotp.TOTP(str(totp_rec.secret))
            if not totp.verify(code):
                raise HTTPException(status_code=401, detail="Invalid TOTP code")
            # proceed to token issuance below

        # Generate JWT token (no MFA path or code verified)
        user_roles = user.role if isinstance(user.role, list) else [user.role] if user.role is not None else []
        token = create_token({
            "userId": str(user.userId),
            "role": user_roles,
            "role_id": user_role_ids,
            "email": str(user.email)
        })

        logger.info(f"✅ User logged in successfully: {identifier}")

        # Kafka event
        try:
            from app.services.kafka_topics import FULL_USER_LOGGEDIN
            await kafka_producer.send_event(
                FULL_USER_LOGGEDIN,
                {
                    "action": "login",
                    "success": True,
                    "userId": str(user.userId),
                    "email": user.email,
                    "phone": user.phone,
                    "role": user_roles,
                    "role_id": user_role_ids,
                    "time": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"⚠️ Kafka login event error for {user.email}: {e}")

        # Return response (cast types to satisfy Pydantic/typing)
        return {
            "success": True,
            "message": "User logged in successfully",
            "data": {
                "access_token": token,
                "token_type": "bearer",
                "userId": str(user.userId),
                "role": user_roles,
                "role_id": user_role_ids,
                "email": user.email,
                "phone": user.phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        }

    except HTTPException:
        # Pass through known HTTP errors
        raise
    except Exception as e:
        # Catch-all for unexpected errors; DB session is auto-released by dependency
        logger.exception(f"Unexpected error in login route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
