"""Simple in-memory rate limiter middleware.

Uses a sliding-window counter per client IP to prevent API abuse.
No external dependencies required — suitable for single-instance deployments.
For multi-instance (load-balanced) setups, swap for Redis-backed rate limiting.
"""

import time
from collections import defaultdict

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RateLimiter(BaseHTTPMiddleware):
    """Per-IP rate limiting with a sliding time window."""

    def __init__(
        self,
        app,
        *,
        max_requests: int = 30,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # { ip: [timestamp, ...] }
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_old_entries(self, ip: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for health checks and WebSocket upgrades
        if request.url.path == "/health":
            return await call_next(request)
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        ip = self._get_client_ip(request)
        now = time.time()

        self._clean_old_entries(ip, now)

        if len(self._requests[ip]) >= self.max_requests:
            return Response(
                content='{"detail":"Too many requests. Please slow down."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        self._requests[ip].append(now)
        remaining = self.max_requests - len(self._requests[ip])

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
