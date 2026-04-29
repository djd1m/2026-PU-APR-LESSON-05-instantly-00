"""
Test configuration and fixtures.

CRITICAL: Environment variables MUST be set before any app module imports.
This file is loaded by pytest before any test module, ensuring env vars
are present when pydantic-settings initializes in config.py.
"""
import os

# ---------------------------------------------------------------------------
# Set ALL required env vars BEFORE importing any app modules
# ---------------------------------------------------------------------------
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_instantly")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-minimum-x")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-placeholder-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-4")
os.environ.setdefault("OPENAI_TIMEOUT", "30.0")
os.environ.setdefault("OPENAI_MAX_RETRIES", "3")
os.environ.setdefault("EMAIL_MAX_RETRIES", "3")
os.environ.setdefault("EMAIL_RETRY_WAIT_SECONDS", "0.01")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")

# ---------------------------------------------------------------------------
# App imports (after env vars are set)
# ---------------------------------------------------------------------------
import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# pytest-asyncio configuration
# ---------------------------------------------------------------------------
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    """Register asyncio mode."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def make_user(
    id: str | None = None,
    email: str = "test@example.com",
    is_active: bool = True,
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock()
    user.id = id or str(uuid.uuid4())
    user.email = email
    user.is_active = is_active
    user.hashed_password = "hashed"
    user.created_at = datetime.now(timezone.utc)
    return user


def make_lead(
    id: str | None = None,
    campaign_id: str | None = None,
    email: str = "lead@example.com",
    first_name: str = "John",
    last_name: str = "Doe",
    company: str = "Acme Corp",
    status: str = "new",
    custom_variables: dict | None = None,
) -> MagicMock:
    """Create a mock Lead object."""
    lead = MagicMock()
    lead.id = id or str(uuid.uuid4())
    lead.campaign_id = campaign_id or str(uuid.uuid4())
    lead.email = email
    lead.first_name = first_name
    lead.last_name = last_name
    lead.company = company
    lead.status = status
    lead.custom_variables = custom_variables or {}
    lead.created_at = datetime.now(timezone.utc)
    return lead


def make_email_account(
    id: str | None = None,
    user_id: str | None = None,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    smtp_user: str = "sender@example.com",
    smtp_password: str = "password123",
    from_email: str = "sender@example.com",
    is_active: bool = True,
    sent_today: int = 0,
    daily_limit: int = 50,
    warmup_enabled: bool = False,
    warmup_score: int = 0,
) -> MagicMock:
    """Create a mock EmailAccount object."""
    account = MagicMock()
    account.id = id or str(uuid.uuid4())
    account.user_id = user_id or str(uuid.uuid4())
    account.smtp_host = smtp_host
    account.smtp_port = smtp_port
    account.smtp_user = smtp_user
    account.smtp_password = smtp_password
    account.from_email = from_email
    account.is_active = is_active
    account.sent_today = sent_today
    account.daily_limit = daily_limit
    account.warmup_enabled = warmup_enabled
    account.warmup_score = warmup_score
    account.created_at = datetime.now(timezone.utc)
    return account


def make_campaign(
    id: str | None = None,
    user_id: str | None = None,
    name: str = "Test Campaign",
    status: str = "active",
    from_name: str = "Test Sender",
    from_email: str = "sender@example.com",
    subject_template: str = "Hello {first_name}!",
    body_template: str = "Hi {first_name}, I wanted to reach out about {company}.",
    ai_personalization_enabled: bool = False,
) -> MagicMock:
    """Create a mock Campaign object."""
    campaign = MagicMock()
    campaign.id = id or str(uuid.uuid4())
    campaign.user_id = user_id or str(uuid.uuid4())
    campaign.name = name
    campaign.status = status
    campaign.from_name = from_name
    campaign.from_email = from_email
    campaign.subject_template = subject_template
    campaign.body_template = body_template
    campaign.ai_personalization_enabled = ai_personalization_enabled
    campaign.created_at = datetime.now(timezone.utc)
    campaign.updated_at = datetime.now(timezone.utc)
    return campaign


def make_async_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def make_scalar_result(value) -> AsyncMock:
    """Create a mock that returns value from scalar_one_or_none()."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    return result


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Reusable async DB session mock."""
    return make_async_session()


@pytest.fixture
def sample_user() -> MagicMock:
    return make_user()


@pytest.fixture
def sample_lead() -> MagicMock:
    return make_lead()


@pytest.fixture
def sample_account() -> MagicMock:
    return make_email_account()


@pytest.fixture
def sample_campaign() -> MagicMock:
    return make_campaign()
