"""Tests for the ChatRepository module.

Uses a mock MongoDB collection to verify database operations
without a real MongoDB instance.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.services.chat_repository import ChatRepository, ChatRepositoryError


@pytest.fixture
def mock_collection():
    """Create a mock MongoDB collection."""
    col = AsyncMock()
    return col


@pytest.fixture
def repo(mock_collection):
    """Create a ChatRepository with a mocked database."""
    r = ChatRepository()
    with patch.object(r, "_col", return_value=mock_collection):
        yield r, mock_collection


@pytest.mark.asyncio
async def test_find_recent_history(repo):
    repository, col = repo
    expected = {"session_id": "s1", "messages": [{"role": "user", "content": "hi"}], "title": "Test"}
    col.find_one.return_value = expected

    result = await repository.find_recent_history("s1")
    assert result == expected
    col.find_one.assert_called_once()


@pytest.mark.asyncio
async def test_find_recent_history_not_found(repo):
    repository, col = repo
    col.find_one.return_value = None

    result = await repository.find_recent_history("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_upsert_exchange(repo):
    repository, col = repo
    col.update_one.return_value = AsyncMock()

    await repository.upsert_exchange(
        session_id="s1",
        user_msg={"role": "user", "content": "hello", "timestamp": "2026-01-01T00:00:00Z"},
        assistant_msg={"role": "assistant", "content": "hi", "timestamp": "2026-01-01T00:00:01Z"},
        is_new=True,
        title="Test Chat",
        suggested_replies=["follow up 1"],
    )
    col.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_delete_found(repo):
    repository, col = repo
    col.delete_one.return_value = MagicMock(deleted_count=1)

    result = await repository.delete("s1")
    assert result is True


@pytest.mark.asyncio
async def test_delete_not_found(repo):
    repository, col = repo
    col.delete_one.return_value = MagicMock(deleted_count=0)

    result = await repository.delete("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_get_full_history(repo):
    repository, col = repo
    expected = {
        "session_id": "s1",
        "messages": [
            {"role": "user", "content": "hello", "timestamp": "2026-01-01T00:00:00Z"},
            {"role": "assistant", "content": "hi", "timestamp": "2026-01-01T00:00:01Z"},
        ],
    }
    col.find_one.return_value = expected

    result = await repository.get_full_history("s1")
    assert result == expected
    assert len(result["messages"]) == 2
