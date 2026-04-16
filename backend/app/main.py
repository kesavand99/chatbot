from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_allowed_origins
from app.core.rate_limiter import RateLimiter
from app.db.mongo import close_mongo_connection, connect_to_mongo
from app.services.chat_repository import ChatRepository


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_to_mongo()
    # Create indexes on startup
    repo = ChatRepository()
    await repo.ensure_indexes()
    yield
    await close_mongo_connection()


app = FastAPI(title="AI Chatbot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting: 300 requests per minute per client IP (to allow for polling multiple tabs)
app.add_middleware(RateLimiter, max_requests=300, window_seconds=60)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

