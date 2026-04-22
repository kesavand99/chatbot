import os
import ssl
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in .env")

Base = declarative_base()

# Configure SSL conditionally based on POSTGRES_SSLMODE
ssl_mode = os.getenv("POSTGRES_SSLMODE", "").lower()
connect_args = {}
if ssl_mode in {"require", "verify-ca", "verify-full", "prefer"}:
    ssl_context = ssl.create_default_context()
    if ssl_mode in {"require", "prefer"}:
        # permissive: do not verify hostname/cert (suitable for managed DBs without CA)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    # For verify-ca/verify-full, keep defaults; mount CA certs if needed
    connect_args["ssl"] = ssl_context

# Async engine with bounded pool to avoid exhausting Postgres connections
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # ensures dead connections are detected
    future=True,
    # Keep pool small to prevent TooManyConnections when multiple services run
    pool_size=int(os.getenv("DB_POOL_SIZE", "3")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "1")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),  # recycle connections periodically
    connect_args=connect_args,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_db():
    async with SessionLocal() as session:
        yield session