import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Topic prefix for environment separation, e.g., "dev." or "prod."
KAFKA_TOPIC_PREFIX = os.getenv("KAFKA_TOPIC_PREFIX", "")

# Base topic names (should NOT include the prefix). Override via env if needed.
USER_CREATED = os.getenv("KAFKA_TOPIC_USER_CREATED", "user.created")
USER_REGISTERED = os.getenv("KAFKA_TOPIC_USER_REGISTERED", "user.registered")
USER_LOGGEDIN = os.getenv("KAFKA_TOPIC_USER_LOGGEDIN", "user.loggedin")
USER_STATUS_UPDATED = os.getenv("KAFKA_TOPIC_USER_STATUS_UPDATED", "user.status.updated")
USER_PHONE_UPDATED = os.getenv("KAFKA_TOPIC_USER_PHONE_UPDATED", "user.phone.updated")
USER_PASSWORD_UPDATED = os.getenv("KAFKA_TOPIC_USER_PASSWORD_UPDATED", "user.password.updated")
USER_UPDATED = os.getenv("KAFKA_TOPIC_USER_UPDATED", "user.updated")
USER_ADMIN_UPDATED = os.getenv("KAFKA_TOPIC_USER_ADMIN_UPDATED", "user.admin.updated")
# Additional topics used only for producing (not consumer subscription)
ADMIN_LOGGEDIN = os.getenv("KAFKA_TOPIC_ADMIN_LOGGEDIN", "admin.loggedin")
PASSWORD_RESET_OTP = os.getenv("KAFKA_TOPIC_PASSWORD_RESET_OTP", "auth.password.reset.otp")
PASSWORD_RESET_COMPLETED = os.getenv("KAFKA_TOPIC_PASSWORD_RESET_COMPLETED", "auth.password.reset.complete")
AUTH_PASSWORD_UPDATED = os.getenv("KAFKA_TOPIC_AUTH_PASSWORD_UPDATED", "auth.password.updated")

BASE_TOPICS = [
    USER_CREATED,
    USER_REGISTERED,
    USER_LOGGEDIN,
    USER_STATUS_UPDATED,
    USER_PHONE_UPDATED,
    USER_PASSWORD_UPDATED,
    USER_UPDATED,
    USER_ADMIN_UPDATED,
]

def _full_topic(name: str) -> str:
    """Apply prefix if not already present."""
    if KAFKA_TOPIC_PREFIX and not name.startswith(KAFKA_TOPIC_PREFIX):
        return f"{KAFKA_TOPIC_PREFIX}{name}"
    return name

FULL_USER_CREATED = _full_topic(USER_CREATED)
FULL_USER_REGISTERED = _full_topic(USER_REGISTERED)
FULL_USER_LOGGEDIN = _full_topic(USER_LOGGEDIN)
FULL_USER_STATUS_UPDATED = _full_topic(USER_STATUS_UPDATED)
FULL_USER_PHONE_UPDATED = _full_topic(USER_PHONE_UPDATED)
FULL_USER_PASSWORD_UPDATED = _full_topic(USER_PASSWORD_UPDATED)
FULL_USER_UPDATED = _full_topic(USER_UPDATED)
FULL_USER_ADMIN_UPDATED = _full_topic(USER_ADMIN_UPDATED)
FULL_ADMIN_LOGGEDIN = _full_topic(ADMIN_LOGGEDIN)
FULL_PASSWORD_RESET_OTP = _full_topic(PASSWORD_RESET_OTP)
FULL_PASSWORD_RESET_COMPLETED = _full_topic(PASSWORD_RESET_COMPLETED)
FULL_AUTH_PASSWORD_UPDATED = _full_topic(AUTH_PASSWORD_UPDATED)


FULL_TOPICS = [
    FULL_USER_CREATED,
    FULL_USER_REGISTERED,
    FULL_USER_LOGGEDIN,
    FULL_USER_STATUS_UPDATED,
    FULL_USER_PHONE_UPDATED,
    FULL_USER_PASSWORD_UPDATED,
    FULL_USER_UPDATED,
    FULL_USER_ADMIN_UPDATED,
]