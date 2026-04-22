# app/login.py
import logging
import re
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from app.models import models
from app.schemas.schemas import LoginRequest
from app.config.database import get_db
from app.services import kafka_producer
from app.utils.jwt_utils import create_token


router = APIRouter()
logger = logging.getLogger("auth")

EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
MOBILE_REGEX = re.compile(r"^(?:\+91)?[6-9]\d{9}$")


def normalize_mobile(identifier: str) -> str:
    """Normalize mobile number to 10-digit format (strip +91 if present)"""
    if identifier.startswith("+91"):
        return identifier[3:]
    return identifier
@router.post("/auth/admin_login")
async def admin_login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Admin login endpoint for users with role_id in [1,3,4,5]
    """
    try:
        logger = logging.getLogger(__name__)
        
        identifier = request.identifier.strip()
        is_email = bool(EMAIL_REGEX.match(identifier))
        is_mobile = bool(MOBILE_REGEX.match(identifier))

        # Validate identifier
        if not (is_email or is_mobile):
            if "@" in identifier or "." in identifier or identifier.isalnum():
                detail_msg = "Invalid email format"
            elif identifier.isdigit() or identifier.startswith("+"):
                detail_msg = "Invalid mobile number format"
            else:
                detail_msg = "Invalid login identifier"
            logger.warning(f"❌ {detail_msg}: {identifier}")
            raise HTTPException(status_code=400, detail=detail_msg)

        # Normalize mobile
        if is_mobile:
            identifier = normalize_mobile(identifier)

        # Fetch admin user - for array role_ids, we need to check if only 2 is present or other combinations with 2
        result = await db.execute(
            select(models.User).where(
                (models.User.email == identifier) | (models.User.phone == identifier)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"❌ Admin login failed: Invalid credentials for identifier: {identifier}")
            raise HTTPException(status_code=404, detail="Invalid admin credentials")

        # Admin role logic: deny ONLY if user has role_id [2] alone
        user_role_ids = getattr(user, 'role_id', [])
        if not isinstance(user_role_ids, list):
            user_role_ids = [user_role_ids] if user_role_ids is not None else []
            
        # Admin login logic:
        # - If role_id array is exactly [2] (only role 2): DENY
        # - If role_id array has other roles like [6], [3], [1], [5]: ALLOW
        # - If role_id array has [2] with other roles like [2,3], [2,6]: ALLOW
        if user_role_ids == [2]:
            logger.warning(f"❌ Unauthorized admin login attempt: {identifier} (role_id: {user.role_id}) - user has only role 2")
            raise HTTPException(status_code=403, detail="Invalid admin credentials")
        
        if not getattr(user, "status", False):
            logger.warning(f"❌ User account is inactive: {identifier}")
            raise HTTPException(status_code=403, detail="User account is inactive")

        # Plain-text password check
        if request.password != str(user.password):
            logger.warning(f"❌ Incorrect password attempt for admin: {identifier}")
            raise HTTPException(status_code=401, detail="Incorrect password")

        # If user has authenticator enabled, check for TOTP code; if missing, require MFA
        if getattr(user, "authenticator", False):
            code = getattr(request, "code", None)
            if not code:
                logger.info(f"🔐 MFA required for admin: {identifier}")
                return {
                    "success": True,
                    "message": "MFA required",
                    "data": {
                        "mfa_required": True,
                        "method": "totp",
                        "identifier": identifier,
                        "purpose": "admin_login",
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

        # Create JWT token (no MFA path or code verified)
        user_roles = user.role if isinstance(user.role, list) else [user.role] if user.role is not None else []
        token = create_token({
            "userId": str(user.userId),
            "role": user_roles,
            "role_id": user_role_ids,
            "email": user.email,
            "type": "admin"
        })

        logger.info(f"✅ Admin logged in successfully: {identifier} (Role ID: {user.role_id})")

        # Kafka event
        try:
            from app.services.kafka_topics import FULL_ADMIN_LOGGEDIN
            await kafka_producer.send_event(
                FULL_ADMIN_LOGGEDIN,
                {
                    "action": "admin_login",
                    "success": True,
                    "userId": str(user.userId),
                    "email": user.email,
                    "phone": user.phone,
                    "role": user_roles,
                    "role_id": user_role_ids,
                    "type": "admin",
                    "time": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"⚠️ Kafka admin login event error for {user.email}: {e}")

        # Success response
        return {
            "success": True,
            "message": "Admin logged in successfully",
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
                "type": "admin"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in admin_login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        try:
            await db.close()
        except Exception:
            pass