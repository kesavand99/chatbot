"""MongoDB persistence layer for chat conversations.

Encapsulates all database reads/writes so the ChatService
doesn't need to know about MongoDB internals.
"""

from datetime import datetime as dt, timezone

from pymongo.errors import PyMongoError
from fastapi import status

from app.db.mongo import get_database

COLLECTION = "chats"


class ChatRepositoryError(Exception):
    """Raised when a DB operation fails."""

    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _db_error(exc: PyMongoError) -> ChatRepositoryError:
    return ChatRepositoryError(
        message="Could not connect to MongoDB. Make sure MongoDB is running.",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class ChatRepository:
    """Async MongoDB repository for chat sessions."""

    def _col(self):
        return get_database()[COLLECTION]

    async def ensure_indexes(self) -> None:
        """Create a unique index on session_id and a TTL index on updated_at if needed."""
        try:
            await self._col().create_index("session_id", unique=True)
            await self._col().create_index([("updated_at", -1)])
        except PyMongoError:
            pass

    async def find_recent_history(self, session_id: str, limit: int = 10):
        """Return the last *limit* messages and title for a session, or ``None``."""
        try:
            return await self._col().find_one(
                {"session_id": session_id},
                {"messages": {"$slice": -limit}, "title": 1},
            )
        except PyMongoError as exc:
            raise _db_error(exc) from exc

    async def upsert_exchange(
        self,
        session_id: str,
        user_msg: dict,
        assistant_msg: dict,
        *,
        is_new: bool,
        title: str | None = None,
        suggested_replies: list[str] | None = None,
        is_admin_needed: bool = False,
    ) -> None:
        """Persist a user/assistant message pair, creating the doc if needed."""
        now = dt.now(timezone.utc)
        update: dict = {
            "$set": {
                "updated_at": now,
                "is_admin_needed": is_admin_needed
            },
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
        }

        if suggested_replies is not None:
            update["$set"]["suggested_replies"] = suggested_replies

        if is_new:
            update["$setOnInsert"] = {
                "session_id": session_id,
                "title": title or "New conversation",
                "created_at": now,
                "support_messages": []
            }

        try:
            await self._col().update_one(
                {"session_id": session_id}, update, upsert=True
            )
        except PyMongoError as exc:
            raise _db_error(exc) from exc

    async def add_support_message(self, session_id: str, role: str, content: str, user_name: str | None = None) -> bool:
        """Appends a message to the separate support_messages thread.

        Uses upsert so a brand-new session document is created automatically
        when the user opens Customer Support before starting an AI chat.
        """
        now = dt.now(timezone.utc)
        msg = {
            "role": role,
            "content": content,
            "timestamp": now.isoformat()
        }
        try:
            update: dict = {
                "$push": {"support_messages": msg},
                "$set": {
                    "updated_at": now,
                    "is_admin_needed": role != "admin",
                },
                "$setOnInsert": {
                    "session_id": session_id,
                    "title": user_name or "Support Chat",
                    "created_at": now,
                    "messages": [],
                }
            }

            await self._col().update_one({"session_id": session_id}, update, upsert=True)
            return True
        except PyMongoError as exc:
            raise _db_error(exc) from exc

    async def get_support_thread(self, session_id: str) -> list[dict]:
        """Fetch only the human-admin support thread."""
        try:
            doc = await self._col().find_one({"session_id": session_id}, {"support_messages": 1})
            return doc.get("support_messages", []) if doc else []
        except PyMongoError as exc:
            raise _db_error(exc) from exc

    async def list_pending_admin(self, limit: int = 50) -> list[dict]:
        """Return chat sessions where admin help is flagged."""
        try:
            cursor = self._col().find(
                {"is_admin_needed": True},
                {"_id": 0, "session_id": 1, "title": 1, "updated_at": 1}
            ).sort("updated_at", -1)
            return await cursor.to_list(length=limit)
        except PyMongoError as exc:
            raise _db_error(exc) from exc

    async def list_resolved_admin(self, limit: int = 50) -> list[dict]:
        """Return chat sessions where admin help was requested but is now resolved."""
        try:
            cursor = self._col().find(
                {
                    "support_messages.0": {"$exists": True},
                    "is_admin_needed": False
                },
                {"_id": 0, "session_id": 1, "title": 1, "updated_at": 1}
            ).sort("updated_at", -1)
            return await cursor.to_list(length=limit)
        except PyMongoError as exc:
            raise _db_error(exc) from exc

    async def close_support_ticket(self, session_id: str) -> bool:
        """Clears the admin flag and adds a closure message."""
        now = dt.now(timezone.utc)
        msg = {
            "role": "admin",
            "content": "This support ticket has been closed. Thank you!",
            "timestamp": now.isoformat()
        }
        try:
            result = await self._col().update_one(
                {"session_id": session_id},
                {
                    "$push": {"support_messages": msg},
                    "$set": {"is_admin_needed": False, "updated_at": now}
                }
            )
            return result.matched_count > 0
        except PyMongoError as exc:
            raise _db_error(exc) from exc

    async def get_full_history(self, session_id: str) -> dict | None:
        """Return the full chat document (without Mongo _id)."""
        try:
            return await self._col().find_one(
                {"session_id": session_id}, {"_id": 0}
            )
        except PyMongoError as exc:
            raise _db_error(exc) from exc

    async def list_all(self, limit: int = 200) -> list[dict]:
        """Return chat summaries sorted by most recently updated."""
        try:
            cursor = self._col().find(
                {},
                {"_id": 0, "session_id": 1, "title": 1, "created_at": 1, "updated_at": 1},
            ).sort("updated_at", -1)
            return await cursor.to_list(length=limit)
        except PyMongoError as exc:
            raise _db_error(exc) from exc

    async def delete(self, session_id: str) -> bool:
        """Delete a session. Returns ``True`` if found, ``False`` otherwise."""
        try:
            result = await self._col().delete_one({"session_id": session_id})
            return result.deleted_count > 0
        except PyMongoError as exc:
            raise _db_error(exc) from exc

    async def rename(self, session_id: str, title: str) -> bool:
        """Rename a chat session. Returns ``True`` if found, ``False`` otherwise."""
        try:
            result = await self._col().update_one(
                {"session_id": session_id},
                {"$set": {"title": title}},
            )
            return result.matched_count > 0
        except PyMongoError as exc:
            raise _db_error(exc) from exc
