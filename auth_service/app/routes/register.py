# app/register.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from dotenv import load_dotenv
from app.services import kafka_producer

from app.config import database
from app.models import models
from app.schemas.schemas import RegisterRequest, APIResponse
from app.utils.jwt_utils import create_token

load_dotenv()
router = APIRouter()


@router.post("/auth/register", response_model=APIResponse)
async def register_user(request: RegisterRequest, db: AsyncSession = Depends(database.get_db)):
    try:
        # Validate password
        if not request.password.strip():
            raise HTTPException(status_code=400, detail="Password cannot be empty")

        # Check existing email
        existing_email = await db.execute(select(models.User).where(models.User.email == request.email))
        email_user = existing_email.scalar_one_or_none()

        # Check existing phone
        existing_phone = await db.execute(select(models.User).where(models.User.phone == request.phone))
        phone_user = existing_phone.scalar_one_or_none()

        if email_user and phone_user:
            raise HTTPException(status_code=400, detail="Email and phone number already registered")
        elif email_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        elif phone_user:
            raise HTTPException(status_code=400, detail="Phone number already registered")

        # For registration, always assign role_id [2] regardless of request
        # Validate that role_id 2 exists and is active
        role_query = await db.execute(select(models.UserRole.role_name, models.UserRole.status)
                                      .where(models.UserRole.role_id == 2))
        role_row = role_query.first()
        if not role_row:
            raise HTTPException(status_code=500, detail="Default user role (ID 2) not found in system")

        role_name, role_status = role_row
        if not role_status:
            raise HTTPException(status_code=500, detail="Default user role (ID 2) is inactive")

        # Create user with role arrays (always assign role [2] for registration)
        new_user = models.User(
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            phone=request.phone,
            password=request.password,  # Store plain password for now, consider hashing later
            role=[role_name],  # Store as array
            role_id=[2],  # Always assign role_id [2] for new registrations
            created_by=request.email,
            modified_by=None,
            modified_at=None,
            status=True
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)



        # Decide MFA requirement on signup via env flag OR client opt-in (request.mfa_required)
        import os
        env_mfa = os.getenv("AUTH_MFA_REQUIRED_ON_SIGNUP", "false").lower() == "true"
        client_mfa = bool(getattr(request, "mfa_required", False))
        mfa_on_signup = env_mfa or client_mfa
        if mfa_on_signup:
            # Client should call /auth/mfa/start next with identifier (email/phone)
            return {
                "success": True,
                "message": "MFA required",
                "data": {
                    "mfa_required": True,
                    "method": "totp",
                    "identifier": new_user.email,
                    "purpose": "register",
                },
            }

        # Generate JWT token and return immediately (no MFA required on signup)
        token = create_token({
            "userId": str(new_user.userId),
            "role": new_user.role,  # Already an array
            "role_id": new_user.role_id,  # Already an array  
            "email": str(new_user.email)
        })

        # Publish Kafka event ONLY when MFA is not required (i.e., token is being issued)
        try:
            from app.services.kafka_topics import FULL_USER_REGISTERED
            from app.utils.logger import logger
            payload = {
                "action": "registered",
                "success": True,
                "userId": str(new_user.userId),
                "first_name": new_user.first_name,
                "last_name": new_user.last_name,
                "email": new_user.email,
                "password": new_user.password,
                "phone": new_user.phone,
                "role": new_user.role,  # Already an array
                "role_id": new_user.role_id,  # Already an array
                "created_by": new_user.email,
                "created_at": new_user.created_at.isoformat(),
                "authenticator": False
            }
            logger.info(f"➡️ Sending register Kafka event for {new_user.email} to topic '{FULL_USER_REGISTERED}'")
            await kafka_producer.send_event(FULL_USER_REGISTERED, payload)
        except Exception as e:
            from app.utils.logger import logger
            logger.error(f"Kafka Error during register event: {e}")

        return {
            "success": True,
            "message": "User registered successfully",
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
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        try:
            await db.close()
        except Exception:
            pass
