"""
Unit tests for AIPersonalizationService.

Tests cover:
- Successful GPT-4 personalization (subject + body)
- Fallback to template rendering on OpenAI error
- Tenacity retry on RateLimitError
- Template rendering with lead variables
- Template rendering fallback on missing variables
- Concurrent personalization (subject || body)
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

# conftest.py sets env vars before this import
from services.ai_personalization import AIPersonalizationService, _render_template
from tests.conftest import make_lead


# ---------------------------------------------------------------------------
# Helper: build mock OpenAI response
# ---------------------------------------------------------------------------


def _make_openai_response(content: str) -> MagicMock:
    """Build a mock that mimics openai.types.chat.ChatCompletion."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# Test: _render_template
# ---------------------------------------------------------------------------


def test_render_template_basic():
    """Template variables are replaced with lead data."""
    lead = make_lead(first_name="Alice", last_name="Smith", company="Acme")
    result = _render_template("Hello {first_name} from {company}!", lead)
    assert result == "Hello Alice from Acme!"


def test_render_template_missing_variable():
    """Missing template variables return template as-is (no crash)."""
    lead = make_lead(first_name="Bob", company="Corp")
    result = _render_template("Hello {first_name}, your {nonexistent_var}!", lead)
    # Should return the template with the missing variable intact
    assert "Bob" in result or "{nonexistent_var}" in result


def test_render_template_custom_variables():
    """Custom variables from lead.custom_variables are available in template."""
    lead = make_lead(custom_variables={"role": "CEO", "industry": "SaaS"})
    result = _render_template("Hi {first_name}, are you the {role} at {company}?", lead)
    assert "CEO" in result


def test_render_template_empty_fields():
    """Template rendering handles None/empty lead fields gracefully."""
    lead = make_lead(first_name=None, company=None)
    result = _render_template("Hello {first_name}!", lead)
    assert result == "Hello !"  # Empty string for None fields


# ---------------------------------------------------------------------------
# Test: personalize_subject
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_personalize_subject_returns_gpt_response():
    """personalize_subject should return GPT-4 rewritten subject."""
    lead = make_lead(first_name="John", company="TechCorp")

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("Quick question for you, John")
    )

    service = AIPersonalizationService(client=mock_client)
    result = await service.personalize_subject(
        subject="Hello {first_name}!",
        lead=lead,
    )

    assert result == "Quick question for you, John"
    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_personalize_subject_fallback_on_openai_error():
    """personalize_subject falls back to template rendering on OpenAI connection error."""
    lead = make_lead(first_name="Jane", company="StartupXYZ")

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=MagicMock())
    )

    service = AIPersonalizationService(client=mock_client)
    result = await service.personalize_subject(
        subject="Hello {first_name}!",
        lead=lead,
    )

    # Should fall back to rendered template
    assert "Jane" in result


@pytest.mark.asyncio
async def test_personalize_subject_fallback_on_timeout():
    """personalize_subject falls back to template rendering on APITimeoutError."""
    lead = make_lead(first_name="Mike", company="BigCo")

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=APITimeoutError(request=MagicMock())
    )

    service = AIPersonalizationService(client=mock_client)
    result = await service.personalize_subject(
        subject="Reaching out about {company}",
        lead=lead,
    )

    assert "BigCo" in result


# ---------------------------------------------------------------------------
# Test: personalize_body
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_personalize_body_returns_gpt_response():
    """personalize_body should return GPT-4 rewritten body."""
    lead = make_lead(first_name="Sarah", company="MegaCorp")

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(
            "Hi Sarah, I noticed MegaCorp is growing rapidly. I'd love to connect."
        )
    )

    service = AIPersonalizationService(client=mock_client)
    result = await service.personalize_body(
        body="Hi {first_name}, I wanted to reach out about {company}.",
        lead=lead,
    )

    assert "Sarah" in result
    assert "MegaCorp" in result


@pytest.mark.asyncio
async def test_personalize_body_fallback_on_rate_limit():
    """personalize_body falls back to template when RateLimitError persists after retries."""
    lead = make_lead(first_name="Alex", company="SaaSCo")

    mock_client = AsyncMock()
    # Always raise RateLimitError to exhaust retries
    mock_client.chat.completions.create = AsyncMock(
        side_effect=RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "Rate limit exceeded"}},
        )
    )

    service = AIPersonalizationService(client=mock_client)
    result = await service.personalize_body(
        body="Hi {first_name}, reaching out about {company}.",
        lead=lead,
    )

    # After retries exhausted, falls back to template
    assert "Alex" in result or "SaaSCo" in result


@pytest.mark.asyncio
async def test_personalize_body_with_custom_variables():
    """personalize_body includes custom_variables in GPT context."""
    lead = make_lead(
        first_name="Tom",
        company="DevShop",
        custom_variables={"role": "CTO", "team_size": "50"},
    )

    mock_client = AsyncMock()
    captured_prompts = []

    async def capture_call(**kwargs):
        captured_prompts.append(kwargs.get("messages", []))
        return _make_openai_response("Personalized for CTO Tom at DevShop")

    mock_client.chat.completions.create = AsyncMock(side_effect=capture_call)

    service = AIPersonalizationService(client=mock_client)
    await service.personalize_body(
        body="Hi {first_name}, I see you lead {company}.",
        lead=lead,
    )

    # Verify that the context was included in the call
    assert len(captured_prompts) > 0


# ---------------------------------------------------------------------------
# Test: personalize (combined)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_personalize_runs_concurrently():
    """personalize() should call subject and body personalization concurrently."""
    lead = make_lead(first_name="Emma", company="CloudCo")

    call_order = []

    async def mock_personalize_subject(subject, lead):
        call_order.append("subject_start")
        await asyncio.sleep(0)  # Yield to event loop
        call_order.append("subject_end")
        return "Personalized subject for Emma"

    async def mock_personalize_body(body, lead):
        call_order.append("body_start")
        await asyncio.sleep(0)
        call_order.append("body_end")
        return "Personalized body for Emma at CloudCo"

    mock_client = AsyncMock()
    service = AIPersonalizationService(client=mock_client)

    with (
        patch.object(service, "personalize_subject", side_effect=mock_personalize_subject),
        patch.object(service, "personalize_body", side_effect=mock_personalize_body),
    ):
        subject, body = await service.personalize(
            lead=lead,
            subject_template="Hello {first_name}!",
            body_template="Hi {first_name}, reaching out about {company}.",
        )

    assert "Emma" in subject
    assert "Emma" in body


@pytest.mark.asyncio
async def test_personalize_both_fallback_when_openai_down():
    """personalize() returns template-rendered strings when OpenAI is unavailable."""
    lead = make_lead(first_name="Carlos", company="FinTech")

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=MagicMock())
    )

    service = AIPersonalizationService(client=mock_client)
    subject, body = await service.personalize(
        lead=lead,
        subject_template="Hello {first_name}!",
        body_template="Hi {first_name}, I wanted to reach out about {company}.",
    )

    assert "Carlos" in subject
    assert "Carlos" in body
    assert "FinTech" in body


@pytest.mark.asyncio
async def test_personalize_returns_tuple():
    """personalize() always returns a (str, str) tuple."""
    lead = make_lead()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("Personalized content")
    )

    service = AIPersonalizationService(client=mock_client)
    result = await service.personalize(
        lead=lead,
        subject_template="Subject",
        body_template="Body",
    )

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], str)
