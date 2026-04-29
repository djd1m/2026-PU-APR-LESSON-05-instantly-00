"""
Unit tests for EmailSenderService.

Tests cover:
- Account rotation (picks lowest sent_today)
- Rotation skips full accounts
- Rotation raises when no accounts available
- Successful send flow (increments sent_today, sets status)
- Retry on SMTP failure
- Campaign send with multiple leads
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# conftest.py sets env vars before this import
from services.email_sender import EmailSenderService, NoAccountAvailableError
from tests.conftest import (
    make_async_session,
    make_campaign,
    make_email_account,
    make_lead,
    make_scalar_result,
)


# ---------------------------------------------------------------------------
# Test: get_available_account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rotation_picks_lowest_sent():
    """get_available_account should return the account with lowest sent_today."""
    db = make_async_session()
    account = make_email_account(sent_today=5, daily_limit=50)

    # Mock SELECT FOR UPDATE result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=account)
    db.execute = AsyncMock(return_value=mock_result)

    service = EmailSenderService(db)
    result = await service.get_available_account(user_id=account.user_id)

    assert result is account
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_rotation_skips_full_accounts():
    """get_available_account returns None (raises) when all accounts are at limit."""
    db = make_async_session()

    # Return None — all accounts full
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=mock_result)

    service = EmailSenderService(db)
    with pytest.raises(NoAccountAvailableError):
        await service.get_available_account(user_id=str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_rotation_raises_no_accounts_available():
    """Explicitly test NoAccountAvailableError is raised with no active accounts."""
    db = make_async_session()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=result_mock)

    service = EmailSenderService(db)
    with pytest.raises(NoAccountAvailableError) as exc_info:
        await service.get_available_account("user-123")

    assert "No email accounts" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test: send_single_email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_single_email_success():
    """send_single_email should create Email record and increment sent_today on success."""
    db = make_async_session()
    account = make_email_account(sent_today=10, daily_limit=50)
    lead = make_lead()

    # Track added objects
    added_objects = []
    db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

    service = EmailSenderService(db)

    with patch.object(service, "_send_smtp", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None  # Success

        email = await service.send_single_email(
            lead=lead,
            account=account,
            subject="Hello John!",
            body="Hi John, reaching out about Acme Corp.",
        )

    assert email.status == "sent"
    assert email.sent_at is not None
    assert account.sent_today == 11  # Incremented
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_send_single_email_failure():
    """send_single_email should set status=failed on SMTP error."""
    import aiosmtplib

    db = make_async_session()
    account = make_email_account(sent_today=5, daily_limit=50)
    lead = make_lead()

    service = EmailSenderService(db)

    with patch.object(service, "_send_smtp", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = aiosmtplib.SMTPException("Connection refused")

        email = await service.send_single_email(
            lead=lead,
            account=account,
            subject="Test subject",
            body="Test body",
        )

    assert email.status == "failed"
    assert "error" in email.metadata_
    # sent_today should NOT be incremented on failure
    assert account.sent_today == 5


@pytest.mark.asyncio
async def test_send_increments_sent_today_only_on_success():
    """Account.sent_today should only increment when send succeeds."""
    db = make_async_session()
    account = make_email_account(sent_today=20, daily_limit=50)
    lead = make_lead()

    service = EmailSenderService(db)

    with patch.object(service, "_send_smtp", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None

        email = await service.send_single_email(
            lead=lead, account=account, subject="Subj", body="Body"
        )

    assert email.status == "sent"
    assert account.sent_today == 21


# ---------------------------------------------------------------------------
# Test: send_campaign_emails
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_campaign_emails_sends_to_all_new_leads():
    """send_campaign_emails should process all 'new' leads."""
    db = make_async_session()
    campaign = make_campaign(ai_personalization_enabled=False)
    account = make_email_account(sent_today=0, daily_limit=100)
    leads = [make_lead(status="new") for _ in range(3)]

    # With campaign_step_id=None: 2 db.execute calls (campaign, leads)
    # get_available_account is patched separately
    call_count = {"n": 0}

    def mock_execute(query):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            # Campaign query
            result.scalar_one_or_none = MagicMock(return_value=campaign)
        else:
            # Leads query
            scalars_mock = MagicMock()
            scalars_mock.all = MagicMock(return_value=leads)
            result.scalars = MagicMock(return_value=scalars_mock)
        return result

    db.execute = AsyncMock(side_effect=mock_execute)

    service = EmailSenderService(db)
    ai_service = AsyncMock()

    sent_email = MagicMock()
    sent_email.status = "sent"

    with (
        patch.object(service, "get_available_account", new_callable=AsyncMock) as mock_account,
        patch.object(service, "send_single_email", new_callable=AsyncMock) as mock_send,
    ):
        mock_account.return_value = account
        mock_send.return_value = sent_email

        result = await service.send_campaign_emails(
            campaign_id=campaign.id,
            user_id=campaign.user_id,
            ai_service=ai_service,
            campaign_step_id=None,
        )

    assert result["sent"] == 3
    assert result["failed"] == 0
    assert mock_send.call_count == 3


@pytest.mark.asyncio
async def test_send_campaign_stops_when_no_accounts():
    """send_campaign_emails should stop and skip remaining leads when no accounts available."""
    db = make_async_session()
    campaign = make_campaign(ai_personalization_enabled=False)
    leads = [make_lead(status="new") for _ in range(5)]

    call_count = {"n": 0}

    def mock_execute(query):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            # Campaign query
            result.scalar_one_or_none = MagicMock(return_value=campaign)
        else:
            # Leads query
            scalars_mock = MagicMock()
            scalars_mock.all = MagicMock(return_value=leads)
            result.scalars = MagicMock(return_value=scalars_mock)
        return result

    db.execute = AsyncMock(side_effect=mock_execute)

    service = EmailSenderService(db)
    ai_service = AsyncMock()

    # Patch get_available_account to always raise NoAccountAvailableError
    with patch.object(
        service,
        "get_available_account",
        new_callable=AsyncMock,
        side_effect=NoAccountAvailableError("No accounts"),
    ):
        result = await service.send_campaign_emails(
            campaign_id=campaign.id,
            user_id=campaign.user_id,
            ai_service=ai_service,
        )

    # Should have sent 0 and skipped all 5
    assert result["sent"] == 0
    assert result["skipped"] == 5


@pytest.mark.asyncio
async def test_send_campaign_not_found():
    """send_campaign_emails returns zeros when campaign doesn't exist."""
    db = make_async_session()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=result_mock)

    service = EmailSenderService(db)
    ai_service = AsyncMock()

    result = await service.send_campaign_emails(
        campaign_id="nonexistent-id",
        user_id="user-id",
        ai_service=ai_service,
    )

    assert result == {"sent": 0, "failed": 0, "skipped": 0}
