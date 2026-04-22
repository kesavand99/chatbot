"""Service for communicating with the Ollama LLM API.

Handles both streaming and non-streaming completions, title generation,
and suggested reply generation.
"""

import json
from typing import AsyncIterator

import httpx

from app.core.config import settings


class LLMService:
    """Singleton-style async HTTP client for Ollama interactions."""

    _client: httpx.AsyncClient | None = None

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(90.0, connect=10.0, read=80.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            )
        return cls._client

    async def generate_reply(self, history: list[dict]) -> str:
        """Send full history to Ollama and return the complete reply."""
        messages = [{"role": "system", "content": settings.system_prompt}]
        messages.extend([
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ])

        payload = {
            "model": settings.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": 1024,
                "temperature": 0.7,
            },
        }
        try:
            client = await self.get_client()
            response = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            return f"I'm sorry, I encountered an error: {str(e)}"

    async def stream_reply(self, history: list[dict]) -> AsyncIterator[str]:
        """Stream tokens from Ollama one chunk at a time."""
        messages = [{"role": "system", "content": settings.system_prompt}]
        messages.extend([
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ])

        payload = {
            "model": settings.ollama_model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_ctx": 1024, # Smaller context for faster local CPU processing
                "temperature": 0.7,
            },
        }
        try:
            client = await self.get_client()
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
                timeout=90.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk_data = json.loads(line)
                    chunk_text = chunk_data.get("message", {}).get("content", "")
                    if chunk_text:
                        yield chunk_text
                    if chunk_data.get("done"):
                        break
        except Exception as e:
            print(f"Error communicating with Ollama: {str(e)}")
            yield "I'm sorry, I encountered an error communicating with Ollama."

    async def generate_title(self, message: str) -> str | None:
        """Generate a short AI title for a new conversation."""
        prompt = (
            f"Generate a very short, concise title (max 5 words) for a chat that starts with: '{message}'. "
            "Respond ONLY with the title text, no quotes or explanations."
        )
        try:
            title = await self._simple_call(prompt)
            return title[:50] if title else None
        except Exception as e:
            print(f"Error in LLM service: {str(e)}")
            return None

    async def generate_suggested_replies(self, assistant_text: str) -> list[str]:
        """Generate up to 3 follow-up suggestions based on the last AI response."""
        prompt = (
            f"Based on this AI response: '{assistant_text}', suggest 3 very short follow-up questions or replies "
            "that a user might want to ask. Format: reply 1 | reply 2 | reply 3. "
            "Respond ONLY with the formatted replies, no other text."
        )
        try:
            raw = await self._simple_call(prompt)
            if not raw:
                return []
            replies = [r.strip() for r in raw.split("|") if r.strip()]
            return replies[:3]
        except Exception:
            return []

    async def _simple_call(self, prompt: str) -> str | None:
        """Short, constrained LLM call for metadata generation."""
        payload = {
            "model": settings.ollama_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "num_predict": 30,  # Even smaller for metadata
                "temperature": 0.3, # More deterministic
            },
        }
        try:
            client = await self.get_client()
            response = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
                timeout=8.0, # Fail fast
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"Error in LLM service: {str(e)}")
            return None
