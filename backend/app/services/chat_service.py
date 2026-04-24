"""Orchestration layer for chat interactions.

This service coordinates between intent detection, LLM communication,
and database persistence. Each concern lives in its own module.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime as dt, timezone

from fastapi import status

from app.models.chat import ChatMessage
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatListResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSummary,
)
from app.services.chat_repository import ChatRepository, ChatRepositoryError
from app.services.intent_service import check_intent
from app.services.llm_service import LLMService


@dataclass
class ChatServiceError(Exception):
    message: str
    status_code: int


class ChatService:
    """High-level chat orchestrator."""

    def __init__(self):
        self.repo = ChatRepository()
        self.llm = LLMService()

    # ── HTTP endpoint handler ────────────────────────────────────────

    async def process_chat(self, payload: ChatRequest) -> ChatResponse:
        try:
            user_message = ChatMessage(role="user", content=payload.message)

            # Fast-path intent detection
            fast_reply = await check_intent(payload.message)
            if fast_reply:
                return await self._handle_fast_reply(
                    payload.session_id, user_message, fast_reply
                )

            # Full LLM path
            existing = await self.repo.find_recent_history(payload.session_id)
            history = existing.get("messages", []) if existing else []
            is_new = not existing

            history_for_model = history + [user_message.model_dump(mode="json")]
            assistant_text = await self.llm.generate_reply(history_for_model)
            assistant_message = ChatMessage(role="assistant", content=assistant_text)

            # Generate metadata (title & suggestions) in parallel
            tasks = []
            if is_new:
                tasks.append(self.llm.generate_title(payload.message))
            else:
                tasks.append(asyncio.sleep(0, result=None))
            
            tasks.append(self.llm.generate_suggested_replies(assistant_text))
            
            ai_title, suggested_replies = await asyncio.gather(*tasks)

            # Check if admin is needed based on certain keywords or if LLM failed
            admin_needed = any(kw in assistant_text.lower() for kw in ["error", "sorry", "don't know", "unable to"])
            
            await self.repo.upsert_exchange(
                session_id=payload.session_id,
                user_msg=user_message.model_dump(mode="json"),
                assistant_msg=assistant_message.model_dump(mode="json"),
                is_new=is_new,
                title=ai_title or self._build_title(payload.message),
                suggested_replies=suggested_replies,
                is_admin_needed=admin_needed
            )

            return ChatResponse(
                session_id=payload.session_id,
                user_message=ChatMessageResponse(**user_message.model_dump()),
                assistant_message=ChatMessageResponse(**assistant_message.model_dump()),
                suggested_replies=suggested_replies,
                is_admin_needed=admin_needed
            )
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    # ── WebSocket streaming handler ──────────────────────────────────

    async def stream_chat(self, payload: ChatRequest):
        try:
            user_message = ChatMessage(role="user", content=payload.message)

            # Fast-path
            fast_reply = await check_intent(payload.message)
            if fast_reply:
                assistant_message = ChatMessage(role="assistant", content=fast_reply)
                existing = await self.repo.find_recent_history(payload.session_id)
                is_new = not existing
                
                admin_needed = any(kw in fast_reply.lower() for kw in ["error", "sorry", "don't know", "unable to"])

                await self.repo.upsert_exchange(
                    session_id=payload.session_id,
                    user_msg=user_message.model_dump(mode="json"),
                    assistant_msg=assistant_message.model_dump(mode="json"),
                    is_new=is_new,
                    title=self._build_title(payload.message),
                    is_admin_needed=admin_needed
                )

                yield {"type": "chunk", "content": fast_reply}
                yield self._build_final_response(
                    payload.session_id, user_message, assistant_message, [], admin_needed
                )
                return

            # LLM streaming path
            existing = await self.repo.find_recent_history(payload.session_id)
            history = existing.get("messages", []) if existing else []
            is_new = not existing

            history_for_model = history + [user_message.model_dump(mode="json")]
            assistant_content = ""

            # Optimization: Don't start metadata generation until the main response starts streaming
            # This avoids resource competition on local Ollama instances
            async for chunk_text in self.llm.stream_reply(history_for_model):
                assistant_content += chunk_text
                yield {"type": "chunk", "content": chunk_text}

            # Persist & generate metadata *after* streaming completes
            assistant_message = ChatMessage(role="assistant", content=assistant_content)
            
            # Start title generation (if new) and suggested replies in parallel after the main reply is done
            # This ensures the stream is fast and the metadata is generated only when resources are free
            tasks = []
            if is_new:
                tasks.append(self.llm.generate_title(payload.message))
            else:
                tasks.append(asyncio.sleep(0, result=None))
            
            tasks.append(self.llm.generate_suggested_replies(assistant_content))
            
            ai_title, suggested_replies = await asyncio.gather(*tasks)
            
            admin_needed = any(kw in assistant_content.lower() for kw in ["error", "sorry", "don't know", "unable to"])

            await self.repo.upsert_exchange(
                session_id=payload.session_id,
                user_msg=user_message.model_dump(mode="json"),
                assistant_msg=assistant_message.model_dump(mode="json"),
                is_new=is_new,
                title=ai_title or self._build_title(payload.message),
                suggested_replies=suggested_replies,
                is_admin_needed=admin_needed
            )

            yield self._build_final_response(
                payload.session_id, user_message, assistant_message, suggested_replies, admin_needed
            )

        except Exception as exc:
            yield {"type": "error", "detail": str(exc)}

    # ── Read-only operations ─────────────────────────────────────────

    async def get_history(self, session_id: str) -> ChatHistoryResponse:
        try:
            chat = await self.repo.get_full_history(session_id)
            if not chat:
                return ChatHistoryResponse(session_id=session_id, messages=[])
            return ChatHistoryResponse(
                session_id=session_id,
                messages=[ChatMessageResponse(**m) for m in chat.get("messages", [])],
                suggested_replies=chat.get("suggested_replies", []),
            )
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    async def list_chats(self) -> ChatListResponse:
        try:
            chats = await self.repo.list_all()
            return ChatListResponse(
                chats=[
                    ChatSummary(
                        session_id=c["session_id"],
                        title=c.get("title") or "New conversation",
                        created_at=c.get("created_at") or dt.now(timezone.utc),
                        updated_at=c.get("updated_at") or c.get("created_at") or dt.now(timezone.utc),
                    )
                    for c in chats
                ]
            )
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    async def delete_chat(self, session_id: str) -> None:
        try:
            found = await self.repo.delete(session_id)
            if not found:
                raise ChatServiceError(
                    message="Chat session not found.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    async def rename_chat(self, session_id: str, title: str) -> None:
        try:
            found = await self.repo.rename(session_id, title)
            if not found:
                raise ChatServiceError(
                    message="Chat session not found.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    async def list_pending_admin(self) -> ChatListResponse:
        try:
            chats = await self.repo.list_pending_admin()
            return ChatListResponse(
                chats=[
                    ChatSummary(
                        session_id=c["session_id"],
                        title=c.get("title") or "Pending Admin",
                        created_at=c.get("updated_at") or dt.now(timezone.utc),
                        updated_at=c.get("updated_at") or dt.now(timezone.utc),
                    )
                    for c in chats
                ]
            )
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    async def list_resolved_admin(self) -> ChatListResponse:
        try:
            chats = await self.repo.list_resolved_admin()
            return ChatListResponse(
                chats=[
                    ChatSummary(
                        session_id=c["session_id"],
                        title=c.get("title") or "Resolved Support",
                        created_at=c.get("updated_at") or dt.now(timezone.utc),
                        updated_at=c.get("updated_at") or dt.now(timezone.utc),
                    )
                    for c in chats
                ]
            )
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    async def answer_as_admin(self, session_id: str, content: str) -> None:
        try:
            found = await self.repo.add_support_message(session_id, "admin", content)
            if not found:
                raise ChatServiceError(
                    message="Chat session not found.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    async def add_support_message(self, session_id: str, content: str, user_name: str | None = None) -> None:
        try:
            await self.repo.add_support_message(session_id, "user", content, user_name)
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    async def get_support_messages(self, session_id: str) -> list[dict]:
        try:
            return await self.repo.get_support_thread(session_id)
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    async def close_ticket(self, session_id: str) -> None:
        try:
            found = await self.repo.close_support_ticket(session_id)
            if not found:
                raise ChatServiceError(
                    message="Chat session not found.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
        except ChatRepositoryError as exc:
            raise ChatServiceError(message=exc.message, status_code=exc.status_code) from exc

    # ── Helpers ──────────────────────────────────────────────────────

    async def _handle_fast_reply(
        self, session_id: str, user_message: ChatMessage, reply: str
    ) -> ChatResponse:
        assistant_message = ChatMessage(role="assistant", content=reply)
        existing = await self.repo.find_recent_history(session_id)
        is_new = not existing

        await self.repo.upsert_exchange(
            session_id=session_id,
            user_msg=user_message.model_dump(mode="json"),
            assistant_msg=assistant_message.model_dump(mode="json"),
            is_new=is_new,
            title=self._build_title(user_message.content),
        )

        return ChatResponse(
            session_id=session_id,
            user_message=ChatMessageResponse(**user_message.model_dump()),
            assistant_message=ChatMessageResponse(**assistant_message.model_dump()),
            suggested_replies=[],
        )

    @staticmethod
    def _build_title(message: str) -> str:
        clean = " ".join(message.split())
        return clean[:40] if len(clean) <= 40 else f"{clean[:37]}..."

    @staticmethod
    def _build_final_response(
        session_id: str,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
        suggested_replies: list[str],
        is_admin_needed: bool = False,
    ) -> dict:
        return {
            "type": "chat_response",
            "session_id": session_id,
            "user_message": user_message.model_dump(mode="json"),
            "assistant_message": assistant_message.model_dump(mode="json"),
            "suggested_replies": suggested_replies,
            "is_admin_needed": is_admin_needed,
        }
