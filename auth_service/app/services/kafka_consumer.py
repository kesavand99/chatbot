import json
import logging
import asyncio
import os
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from dotenv import load_dotenv
from sqlalchemy import text
from datetime import datetime
from dateutil.parser import isoparse  # For parsing ISO 8601 strings
from app.config.database import SessionLocal as async_session
from app.services.kafka_topics import (
    KAFKA_TOPIC_PREFIX,
    BASE_TOPICS,
    FULL_TOPICS,
    USER_CREATED,
    USER_STATUS_UPDATED,
    USER_PHONE_UPDATED,
    USER_PASSWORD_UPDATED,
    USER_UPDATED,
    USER_ADMIN_UPDATED,
)

logger = logging.getLogger(__name__)

# Load env first
load_dotenv()

# Use the same env var as producer for consistency
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "172.235.17.60:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "auth-service-group")
# Topics now come from kafka_topics module
# Subscribe to both prefixed and unprefixed topics if a prefix is set,
# to tolerate producers that might omit the prefix.
TOPICS = list(dict.fromkeys(FULL_TOPICS + (BASE_TOPICS if KAFKA_TOPIC_PREFIX else [])))

# -----------------------------
# Core Kafka consume loop
# -----------------------------
async def consume():
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        session_timeout_ms=30000,
        heartbeat_interval_ms=10000,
        request_timeout_ms=40000,
        max_poll_interval_ms=600000,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            topic = msg.topic
            base_topic = topic[len(KAFKA_TOPIC_PREFIX):] if KAFKA_TOPIC_PREFIX and topic.startswith(KAFKA_TOPIC_PREFIX) else topic
            payload = msg.value
            if payload is None or not isinstance(payload, dict):
                logger.warning(f"⚠️ Invalid message in {topic}: {payload}")
                continue

            # Accept both shapes: wrapped {success, data} and flat payloads
            if payload.get("data") is not None:
                data = payload["data"]
                if not payload.get("success"):
                    logger.warning(f"⚠️ Message marked unsuccessful in {topic}: {payload}")
                    continue
            else:
                data = payload

            # Flatten Sequelize-like shape: { dataValues: {...}, ... }
            if isinstance(data, dict) and isinstance(data.get("dataValues"), dict):
                data = data["dataValues"]

            user_id = data.get("userId")
            if not user_id:
                logger.error(f"Missing userId in {topic} event: {data}")
                continue

            logger.info(f"➡️ Processing '{base_topic}' for user {user_id} on topic '{topic}'")
            try:
                if base_topic == USER_CREATED:
                    await handle_user_created(data)
                elif base_topic == USER_STATUS_UPDATED:
                    await handle_user_status_updated(data)
                elif base_topic == USER_PHONE_UPDATED:
                    await handle_user_phone_updated(data)
                elif base_topic == USER_PASSWORD_UPDATED:
                    await handle_user_password_updated(data)
                elif base_topic == USER_UPDATED:
                    await handle_user_updated(data)
                elif base_topic == USER_ADMIN_UPDATED:
                    await handle_user_admin_updated(data)
            except Exception as e:
                logger.error(f"❌ Error handling {topic} for user {user_id}: {e}")
            finally:
                logger.info(f"🏁 Finished processing '{base_topic}' for user {user_id}")

    finally:
        await consumer.stop()

# -----------------------------
# Event Handlers
# -----------------------------
async def handle_user_created(data):
    async with async_session() as session:
        # Validate required fields
        required_fields = ["userId", "first_name", "last_name", "email", "phone", "role", "role_id", "created_at", "created_by"]
        if not all(field in data for field in required_fields):
            missing = [field for field in required_fields if field not in data]
            logger.error(f"Missing required fields in user.created event: {missing}, data: {data}")
            return

        # Handle password (accept 'pass' as fallback, warn about incorrect field name)
        password = data.get("password") or data.get("pass")
        if not password:
            logger.error(f"Missing password in user.created event: {data}")
            return
        if "pass" in data and "password" not in data:
            logger.warning(f"Deprecated field 'pass' used in user.created event for user {data['userId']}; use 'password' instead")

        
        # Parse created_at to datetime and make naive
        try:
            created_at = isoparse(data["created_at"]).replace(tzinfo=None)    
        except ValueError as e:
            logger.error(f"Invalid created_at format in user.created event: {data['created_at']}")
            return
        #print(f"{data}")
        
        # Handle role and role_id as arrays
        role_array = data["role"] if isinstance(data["role"], list) else [data["role"]]
        role_id_array = data["role_id"] if isinstance(data["role_id"], list) else [int(data["role_id"]) if data["role_id"] else None]
        # Accept authenticator flag if provided (defaults to False)
        authenticator_val = bool(data.get("authenticator", False))
        
        query = text("""
            INSERT INTO public.users
            ("userId", first_name, last_name, email, phone, password, role, role_id, created_at, created_by, status, authenticator)
            VALUES (:userId, :first_name, :last_name, :email, :phone, :password, :role, :role_id, :created_at, :created_by, :status, :authenticator)
            ON CONFLICT ("userId") DO NOTHING
        """)
        try:
            await session.execute(query, {
                "userId": data["userId"],
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "email": data["email"],
                "phone": data["phone"],
                "password": password,
                "role": role_array,
                "role_id": role_id_array,
                "created_at": created_at,
                "created_by": data["created_by"],
                "status": True,
                "authenticator": authenticator_val
            })
            await session.commit()
            logger.info(f"✅ Processed event user.created for user {data['userId']} (authenticator={authenticator_val})")
        except Exception as e:
            logger.error(f"Database error in user.created: {e}")
            await session.rollback()
            
async def handle_user_status_updated(data):
    async with async_session() as session:
        # Validate required fields
        required_fields = ["userId", "newStatus", "modifiedBy", "modifiedDate"]
        if not all(field in data for field in required_fields):
            logger.error(f"Missing required fields in user.status.updated event: {data}")
            return

        # Parse modifiedDate to datetime and make naive
        try:
            modified_at = isoparse(data["modifiedDate"]).replace(tzinfo=None)
        except ValueError as e:
            logger.error(f"Invalid modifiedDate format in user.status.updated event: {data['modifiedDate']}")
            return

        query = text("""
            UPDATE public.users
            SET status = :status,
                modified_by = :modified_by,
                modified_at = :modified_at
            WHERE "userId" = :userId
        """)
        try:
            await session.execute(query, {
                "status": data["newStatus"],
                "modified_by": data["modifiedBy"],
                "modified_at": modified_at,
                "userId": data["userId"],
            })
            await session.commit()
            logger.info(f"✅ Processed event user.status.updated for user {data['userId']}")
        except Exception as e:
            logger.error(f"Database error in user.status.updated: {e}")
            await session.rollback()

async def handle_user_phone_updated(data):
    async with async_session() as session:
        # Validate required fields
        required_fields = ["userId", "newPhone", "modifiedBy", "modifiedDate"]
        if not all(field in data for field in required_fields):
            logger.error(f"Missing required fields in user.phone.updated event: {data}")
            return

        # Parse modifiedDate to datetime and make naive
        try:
            modified_at = isoparse(data["modifiedDate"]).replace(tzinfo=None)
        except ValueError as e:
            logger.error(f"Invalid modifiedDate format in user.phone.updated event: {data['modifiedDate']}")
            return

        query = text("""
            UPDATE public.users
            SET phone = :phone,
                modified_by = :modified_by,
                modified_at = :modified_at
            WHERE "userId" = :userId
        """)
        try:
            await session.execute(query, {
                "phone": data["newPhone"],
                "modified_by": data["modifiedBy"],
                "modified_at": modified_at,
                "userId": data["userId"],
            })
            await session.commit()
            logger.info(f"✅ Processed event user.phone.updated for user {data['userId']}")
        except Exception as e:
            logger.error(f"Database error in user.phone.updated: {e}")
            await session.rollback()

async def handle_user_updated(data):
    async with async_session() as session:
        # Accepts a flat profile or wrapped { success, data: {...} }
        # Required minimal fields
        required_fields = ["userId", "email", "first_name", "last_name", "role", "role_id", "modified_by", "status"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            logger.error(f"Missing fields in user.updated event: {missing}; data: {data}")
            return

        # Optional phone: treat empty string/whitespace/"null" as NULL to avoid unique violations on ''
        raw_phone = data.get("phone")
        phone_val = None
        if isinstance(raw_phone, str):
            p = raw_phone.strip()
            if p and p.lower() != "null":
                phone_val = p
        elif raw_phone is not None:
            phone_val = str(raw_phone)

        # Parse timestamps if present
        created_at = None
        if data.get("created_at"):
            try:
                created_at = isoparse(str(data["created_at"]).strip()).replace(tzinfo=None)
            except Exception:
                created_at = None
        modified_at = None
        if data.get("modified_date"):
            try:
                modified_at = isoparse(str(data["modified_date"]).strip()).replace(tzinfo=None)
            except Exception:
                modified_at = None

        # If password present, store as received (note: should be hashed upstream)
        password_val = data.get("password")

        # Handle role and role_id as arrays
        role_array = data.get("role")
        if role_array and not isinstance(role_array, list):
            role_array = [role_array]
            
        role_id_array = data.get("role_id")
        if role_id_array and not isinstance(role_id_array, list):
            role_id_array = [int(str(role_id_array).strip()) if str(role_id_array).strip() not in ("", "None", "null") else None]
        elif isinstance(role_id_array, list):
            role_id_array = [int(str(rid).strip()) if str(rid).strip() not in ("", "None", "null") else None for rid in role_id_array]

        # Upsert core user profile fields
        query = text("""
            INSERT INTO public.users ("userId", first_name, last_name, email, phone, password, role, role_id, created_at, created_by, modified_by, modified_at, status)
            VALUES (:userId, :first_name, :last_name, :email, :phone, :password, :role, :role_id, :created_at, :created_by, :modified_by, :modified_at, :status)
            ON CONFLICT ("userId") DO UPDATE SET
                first_name = EXCLUDED.first_name,
                last_name  = EXCLUDED.last_name,
                email      = EXCLUDED.email,
                phone      = EXCLUDED.phone,
                password   = COALESCE(EXCLUDED.password, public.users.password),
                role       = EXCLUDED.role,
                role_id    = EXCLUDED.role_id,
                created_at = COALESCE(EXCLUDED.created_at, public.users.created_at),
                created_by = COALESCE(EXCLUDED.created_by, public.users.created_by),
                modified_by= EXCLUDED.modified_by,
                modified_at= COALESCE(EXCLUDED.modified_at, NOW()),
                status     = EXCLUDED.status
        """)

        try:
            await session.execute(query, {
                "userId": data["userId"],
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "email": data.get("email"),
                "phone": phone_val,
                "password": password_val,
                "role": role_array,
                "role_id": role_id_array,
                "created_at": created_at,
                "created_by": data.get("created_by") or data.get("email"),
                "modified_by": data.get("modified_by") or data.get("email"),
                "modified_at": modified_at,
                "status": (str(data.get("status")).lower() in ("true", "1", "yes")) if data.get("status") is not None else True,
            })
            await session.commit()
            logger.info(f"✅ Processed event user.updated for user {data['userId']}")
        except Exception as e:
            logger.error(f"Database error in user.updated: {e}")
            await session.rollback()

# -----------------------------
# Start Consumer with Reconnect
# -----------------------------
async def start_consumer():
    """Runs Kafka consumer with auto-reconnect."""
    while True:
        try:
            logger.info("🚀 Starting Kafka consumer...")
            await consume()
        except KafkaConnectionError as e:
            logger.warning(f"⚠️ Kafka connection lost: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"❌ Unexpected Kafka consumer error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

async def handle_user_password_updated(data):
    async with async_session() as session:
        required_fields = ["userId", "email", "password", "modifiedBy", "modifiedDate"]
        if not all(field in data for field in required_fields):
            logger.error(f"Missing required fields in user.password.updated event: {data}")
            return

        # Parse modifiedDate to datetime (make naive)
        try:
            modified_at = isoparse(data["modifiedDate"]).replace(tzinfo=None)
        except ValueError:
            logger.error(f"Invalid modifiedDate format in user.password.updated event: {data['modifiedDate']}")
            return

        # ⚠️ Storing raw password is insecure — hashing should be done before insertion
        query = text("""
            UPDATE public.users
            SET password = :password,
                modified_by = :modified_by,
                modified_at = :modified_at
            WHERE "userId" = :userId AND email = :email
        """)
        try:
            await session.execute(query, {
                "password": data["password"],  # You should hash this
                "modified_by": data["modifiedBy"],
                "modified_at": modified_at,
                "userId": data["userId"],
                "email": data["email"]
            })
            await session.commit()
            logger.info(f"✅ Processed event user.password.updated for user {data['userId']}")
        except Exception as e:
            logger.error(f"Database error in user.password.updated: {e}")
            await session.rollback()

async def handle_user_admin_updated(data):
    """Handle user.admin.updated events accepting multiple field variants and saving all available fields"""
    async with async_session() as session:
        # Helper to pick first present non-empty key from variants
        def pick(*keys):
            for k in keys:
                if k in data and data[k] not in (None, ""):
                    return data[k]
            return None

        # Normalize incoming fields (support snake_case and camelCase)
        user_id = pick("userId", "user_id")
        email = pick("email")
        first_name = pick("first_name", "firstName")
        last_name = pick("last_name", "lastName")
        phone_raw = pick("phone", "phoneNumber", "mobile")
        password_val = pick("password", "pass")  # fallback to deprecated 'pass'
        role_val = pick("role", "roles")
        role_id_val = pick("role_id", "roleId", "roleIds")
        created_by = pick("created_by", "createdBy", "email")
        modified_by = pick("modified_by", "modifiedBy", "email")
        created_at_raw = pick("created_at", "createdAt")
        modified_at_raw = pick("modified_date", "modifiedDate")
        status_raw = pick("status", "is_active", "isActive")
        authenticator_val = bool(pick("authenticator", "mfa", "twoFactorEnabled") or False)

        # Validate required core fields
        required_pairs = {
            "userId": user_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": role_val,
            "role_id": role_id_val,
        }
        missing = [k for k, v in required_pairs.items() if v is None]
        if missing:
            logger.error(f"Missing fields in user.admin.updated event: {missing}; data: {data}")
            return

        # Phone normalization: treat empty string/whitespace/"null" as NULL
        phone_val = None
        if isinstance(phone_raw, str):
            p = phone_raw.strip()
            if p and p.lower() != "null":
                phone_val = p
        elif phone_raw is not None:
            phone_val = str(phone_raw)

        # Parse timestamps if present
        created_at = None
        if created_at_raw:
            try:
                created_at = isoparse(str(created_at_raw).strip()).replace(tzinfo=None)
            except Exception:
                created_at = None
        modified_at = None
        if modified_at_raw:
            try:
                modified_at = isoparse(str(modified_at_raw).strip()).replace(tzinfo=None)
            except Exception:
                modified_at = None

        # Roles to arrays
        role_array = role_val if isinstance(role_val, list) else [role_val]
        role_id_array = role_id_val
        if role_id_array and not isinstance(role_id_array, list):
            role_id_array = [int(str(role_id_array).strip()) if str(role_id_array).strip() not in ("", "None", "null") else None]
        elif isinstance(role_id_array, list):
            role_id_array = [int(str(rid).strip()) if str(rid).strip() not in ("", "None", "null") else None for rid in role_id_array]

        # Status normalization
        if isinstance(status_raw, bool):
            status_bool = status_raw
        elif status_raw is None:
            status_bool = True
        else:
            status_bool = str(status_raw).strip().lower() in ("true", "1", "yes")

        # Upsert user profile (now includes authenticator field)
        query = text("""
            INSERT INTO public.users ("userId", first_name, last_name, email, phone, password, role, role_id, created_at, created_by, modified_by, modified_at, status, authenticator)
            VALUES (:userId, :first_name, :last_name, :email, :phone, :password, :role, :role_id, :created_at, :created_by, :modified_by, :modified_at, :status, :authenticator)
            ON CONFLICT ("userId") DO UPDATE SET
                first_name = EXCLUDED.first_name,
                last_name  = EXCLUDED.last_name,
                email      = EXCLUDED.email,
                phone      = EXCLUDED.phone,
                password   = COALESCE(EXCLUDED.password, public.users.password),
                role       = EXCLUDED.role,
                role_id    = EXCLUDED.role_id,
                created_at = COALESCE(EXCLUDED.created_at, public.users.created_at),
                created_by = COALESCE(EXCLUDED.created_by, public.users.created_by),
                modified_by= EXCLUDED.modified_by,
                modified_at= COALESCE(EXCLUDED.modified_at, NOW()),
                status     = EXCLUDED.status,
                authenticator = COALESCE(EXCLUDED.authenticator, public.users.authenticator)
        """)

        try:
            await session.execute(query, {
                "userId": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone_val,
                "password": password_val,  # Consider hashing upstream or here
                "role": role_array,
                "role_id": role_id_array,
                "created_at": created_at,
                "created_by": created_by,
                "modified_by": modified_by,
                "modified_at": modified_at,
                "status": status_bool,
                "authenticator": authenticator_val,
            })
            await session.commit()
            logger.info(f"✅ Processed event user.admin.updated for user {user_id}")
        except Exception as e:
            logger.error(f"Database error in user.admin.updated: {e}")
            await session.rollback()



            