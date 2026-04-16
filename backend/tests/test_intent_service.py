"""Tests for the intent detection service.

These tests verify fast-path intent matching without needing
Ollama or MongoDB running.
"""

import pytest

from app.services.intent_service import check_intent


@pytest.mark.asyncio
async def test_time_intent():
    result = await check_intent("What time is it?")
    assert result is not None
    assert "current time" in result.lower()


@pytest.mark.asyncio
async def test_date_intent():
    result = await check_intent("What is the date today?")
    assert result is not None
    assert "date" in result.lower()


@pytest.mark.asyncio
async def test_open_google():
    result = await check_intent("open google")
    assert result is not None
    assert "google.com" in result


@pytest.mark.asyncio
async def test_open_youtube():
    result = await check_intent("open youtube")
    assert result is not None
    assert "youtube.com" in result


@pytest.mark.asyncio
async def test_play_song():
    result = await check_intent("play bohemian rhapsody")
    assert result is not None
    assert "youtube.com" in result
    assert "bohemian" in result.lower()


@pytest.mark.asyncio
async def test_email_placeholder():
    result = await check_intent("send email to someone")
    assert result is not None
    assert "email" in result.lower()


@pytest.mark.asyncio
async def test_no_match_returns_none():
    result = await check_intent("Tell me a joke about cats")
    assert result is None


@pytest.mark.asyncio
async def test_no_match_general_conversation():
    result = await check_intent("How do neural networks work?")
    assert result is None


@pytest.mark.asyncio
async def test_open_unknown_site_returns_none():
    result = await check_intent("open myobscuresite")
    assert result is None


@pytest.mark.asyncio
async def test_case_insensitivity():
    result = await check_intent("OPEN GOOGLE")
    assert result is not None
    assert "google.com" in result


@pytest.mark.asyncio
async def test_time_variant():
    result = await check_intent("tell me the time please")
    assert result is not None
    assert "current time" in result.lower()


@pytest.mark.asyncio
async def test_date_variant():
    result = await check_intent("what's the date?")
    assert result is not None
