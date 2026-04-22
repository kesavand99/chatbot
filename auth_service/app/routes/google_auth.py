# app/routes/google_auth.py
import os
import re
import secrets
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import database
from app.models import models
from app.schemas.schemas import APIResponse, GoogleSignInRequest
from app.services import kafka_producer
from app.services.kafka_topics import FULL_USER_REGISTERED, FULL_USER_LOGGEDIN
from app.utils.jwt_utils import create_token

# Google token verification
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

router = APIRouter()

@router.get("/auth/google/config")
async def get_google_config():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="Server missing GOOGLE_CLIENT_ID configuration")
    return {"client_id": client_id}

EMAIL_REGEX = r"^[^@]+@[^@]+\.[^@]+$"
MOBILE_REGEX = r"^(?:\+91)?[6-9]\d{9}$"


def _normalize_phone(phone: str) -> str:
    phone = phone.strip()
    if phone.startswith("+91"):
        phone = phone[3:]
    return phone


async def _get_role_by_id(db: AsyncSession, role_id: int) -> tuple[str, bool] | None:
    result = await db.execute(
        select(models.UserRole.role_name, models.UserRole.status).where(models.UserRole.role_id == role_id)
    )
    # Ensure we return a plain tuple instead of a SQLAlchemy Row for correct typing
    return result.tuples().first()


def _verify_google_id_token(id_token: str, audience: str) -> dict:
    try:
        request_adapter = google_requests.Request()
        claims = google_id_token.verify_oauth2_token(id_token, request_adapter, audience)
        return claims
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

@router.post("/auth/googleauthentication", response_model=APIResponse)
async def google_signup(
    body: GoogleSignInRequest,
    db: AsyncSession = Depends(database.get_db),
):
    audience = os.getenv("GOOGLE_CLIENT_ID")
    if not audience:
        raise HTTPException(status_code=500, detail="Server missing GOOGLE_CLIENT_ID configuration")

    claims = _verify_google_id_token(body.id_token, audience)

    # Extract verified email and names
    email = claims.get("email")
    email_verified = claims.get("email_verified")
    name = (claims.get("name") or "").strip()
    parts = name.split() if name else []
    given_name = claims.get("given_name") or (parts[0] if len(parts) > 0 else "")
    family_name = claims.get("family_name") or (parts[1] if len(parts) > 1 else "")

    if not email or not re.match(EMAIL_REGEX, email):
        raise HTTPException(status_code=400, detail="Google account email is missing or invalid")
    if email_verified is False:
        raise HTTPException(status_code=400, detail="Google email is not verified")

    # Try login path
    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalar_one_or_none()

    if user:
        if not getattr(user, "status", False):
            raise HTTPException(status_code=403, detail="User account is inactive")

        # Handle role arrays for existing user login
        user_roles = user.role if isinstance(user.role, list) else [user.role] if user.role is not None else []
        user_role_ids = user.role_id if isinstance(user.role_id, list) else [user.role_id] if user.role_id is not None else []
        
        token = create_token({
            "userId": str(user.userId),
            "role": user_roles,
            "role_id": user_role_ids,
            "email": str(user.email),
        })

        try:
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
        except Exception:
            pass

        return {
            "success": True,
            "message": "User logged in successfully with Google",
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
            },
        }

    # Registration path (first-time Google sign-in)
    # For Google registration, always assign role_id [2] regardless of request (same as normal registration)

    # Accept phone as optional; if missing, use email as unique placeholder to satisfy non-null + unique constraints
    phone = _normalize_phone(body.phone) if body.phone else email

    # Skip format validation for phone

    # Ensure phone uniqueness
    existing_phone = await db.execute(select(models.User).where(models.User.phone == phone))
    if existing_phone.scalar_one_or_none():
        # If collision occurs, append a short suffix to keep it unique
        phone = f"{phone}-g{secrets.token_hex(2)}"

    # Validate default role (always assign role_id 2 for Google registration)
    role_row = await _get_role_by_id(db, 2)
    if not role_row:
        raise HTTPException(status_code=500, detail="Default user role (ID 2) not found in system")
    role_name, role_status = role_row
    if not role_status:
        raise HTTPException(status_code=500, detail="Default user role (ID 2) is inactive")

    placeholder_password = secrets.token_urlsafe(32)
    new_user = models.User(
        first_name=given_name or "",
        last_name=family_name or "",
        email=email,
        phone=None,
        password=placeholder_password,
        role=[role_name],  # Store as array
        role_id=[2],  # Always assign role_id [2] for Google registration
        created_by=email,
        modified_by=None,
        modified_at=None,
        status=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    try:
        await kafka_producer.send_event(
            FULL_USER_REGISTERED,
            {
                "action": "registered",
                "success": True,
                "userId": str(new_user.userId),
                "first_name": new_user.first_name,
                "last_name": new_user.last_name,
                "email": new_user.email,
                "password": placeholder_password,
                "phone": new_user.phone,
                "role": new_user.role,  # Already an array
                "role_id": new_user.role_id,  # Already an array
                "created_by": new_user.email,
                "created_at": new_user.created_at.isoformat(),
                "authenticator": False
            }
        )
    except Exception:
        pass

    token = create_token({
        "userId": str(new_user.userId),
        "role": new_user.role,  # Already an array
        "role_id": new_user.role_id,  # Already an array
        "email": str(new_user.email),
    })

    # Also emit a logged-in event so clients can treat registration as an immediate login
    try:
        await kafka_producer.send_event(
            "user.loggedin",
            {
                "action": "login",
                "success": True,
                "userId": str(new_user.userId),
                "email": new_user.email,
                "phone": new_user.phone,
                "role": new_user.role,  # Already an array
                "role_id": new_user.role_id,  # Already an array
                "time": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        pass

    return {
        "success": True,
        "message": "User registered and logged in successfully with Google",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "userId": str(new_user.userId),
            "role": new_user.role,  # Already an array
            "role_id": new_user.role_id,  # Already an array
            "email": new_user.email,
            "phone": new_user.phone,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
        },
    }