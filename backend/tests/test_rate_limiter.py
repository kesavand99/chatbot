"""Tests for the rate limiter middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from starlette.responses import Response

from app.core.rate_limiter import RateLimiter


def _make_request(path: str = "/chat", ip: str = "127.0.0.1", headers: dict = None):
    """Create a mock Starlette Request."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [(k.encode(), v.encode()) for k, v in (headers or {}).items()],
        "query_string": b"",
        "root_path": "",
    }
    request = Request(scope)
    request._client = MagicMock()
    request._client.host = ip
    # Override the client property
    scope["client"] = (ip, 0)
    return Request(scope)


@pytest.mark.asyncio
async def test_allows_requests_under_limit():
    app = AsyncMock()
    limiter = RateLimiter(app, max_requests=5, window_seconds=60)
    
    request = _make_request()
    call_next = AsyncMock(return_value=Response("OK"))

    response = await limiter.dispatch(request, call_next)
    assert response.status_code == 200
    assert response.headers.get("X-RateLimit-Remaining") == "4"


@pytest.mark.asyncio
async def test_blocks_after_limit():
    app = AsyncMock()
    limiter = RateLimiter(app, max_requests=3, window_seconds=60)
    
    call_next = AsyncMock(return_value=Response("OK"))

    # Make 3 requests to exhaust the limit
    for _ in range(3):
        request = _make_request(ip="10.0.0.1")
        await limiter.dispatch(request, call_next)

    # 4th request should be blocked
    request = _make_request(ip="10.0.0.1")
    response = await limiter.dispatch(request, call_next)
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_health_bypasses_rate_limit():
    app = AsyncMock()
    limiter = RateLimiter(app, max_requests=1, window_seconds=60)
    
    call_next = AsyncMock(return_value=Response("OK"))

    # Health checks should never be rate-limited
    for _ in range(5):
        request = _make_request(path="/health")
        response = await limiter.dispatch(request, call_next)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_different_ips_have_separate_limits():
    app = AsyncMock()
    limiter = RateLimiter(app, max_requests=2, window_seconds=60)
    
    call_next = AsyncMock(return_value=Response("OK"))

    # Exhaust IP 1
    for _ in range(2):
        await limiter.dispatch(_make_request(ip="1.1.1.1"), call_next)

    # IP 2 should still be fine
    response = await limiter.dispatch(_make_request(ip="2.2.2.2"), call_next)
    assert response.status_code == 200
    assert response.headers.get("X-RateLimit-Remaining") == "1"
