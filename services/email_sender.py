"""
Email sending service with account rotation and retry logic.

Key design:
- Uses SELECT FOR UPDATE SKIP LOCKED to safely rotate accounts across concurrent tasks
- Retries SMTP failures with exponential backoff (tenacity)
- Graceful fallback: if no accounts available, logs error and skips lead
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

import aiosmtplib
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from models import Campaign, CampaignStep, Email, EmailAccount, Lead

if TYPE_CHECKING:
    from services.ai_personalization import AIPersonalizationService

logger = logging.getLogger(__name__)


class NoAccountAvailableError(Exception):
    """Raised when no email account has remaining capacity."""


class EmailSenderService:
    """Handles email sending with account rotation and retry logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_available_account(self, user_id: str) -> EmailAccount:
        """
        Select the email account with the most remaining capacity.
        Uses FOR UPDATE SKIP LOCKED to prevent concurrent selection conflicts.

        Raises:
            NoAccountAvailableError: if no accounts have remaining capacity.
        """
        result = await self.db.execute(
            select(EmailAccount)
            .where(
                EmailAccount.user_id == user_id,
                EmailAccount.is_active.is_(True),
                EmailAccount.sent_today < EmailAccount.daily_limit,
            )
            .order_by(EmailAccount.sent_today.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        account = result.scalar_one_or_none()
        if account is None:
            raise NoAccountAvailableError(
                f"No email accounts with remaining capacity for user {user_id}"
            )
        return account

    async def _send_smtp(
        self,
        account: EmailAccount,
        to_email: str,
        subject: str,
        body: str,
        message_id: str,
    ) -> None:
        """
        Send an email via SMTP with retry on transient errors.
        Uses tenacity for exponential backoff.
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{account.smtp_user} <{account.from_email}>"
        msg["To"] = to_email
        msg["Message-ID"] = message_id

        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(f"<html><body>{body}</body></html>", "html"))

        await self._send_with_retry(account, msg)

    @retry(
        retry=retry_if_exception_type((aiosmtplib.SMTPException, OSError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _send_with_retry(
        self,
        account: EmailAccount,
        msg: MIMEMultipart,
    ) -> None:
        """Retry-wrapped SMTP send."""
        async with aiosmtplib.SMTP(
            hostname=account.smtp_host,
            port=account.smtp_port,
            use_tls=account.smtp_port == 465,
            start_tls=account.smtp_port == 587,
            timeout=30,
        ) as smtp:
            await smtp.login(account.smtp_user, account.smtp_password)
            await smtp.send_message(msg)

    async def send_single_email(
        self,
        lead: Lead,
        account: EmailAccount,
        subject: str,
        body: str,
        campaign_step_id: str | None = None,
    ) -> Email:
        """
        Send one email to a lead using the given account.
        Creates an Email record and increments account.sent_today.

        Returns the created Email record.
        """
        message_id = f"<{uuid.uuid4()}@{account.smtp_host}>"
        email_record = Email(
            lead_id=lead.id,
            account_id=account.id,
            campaign_step_id=campaign_step_id,
            message_id=message_id,
            status="pending",
            subject=subject,
            body=body,
            metadata_={"ai_personalized": False},
        )
        self.db.add(email_record)
        await self.db.flush()  # Get the ID

        try:
            await self._send_smtp(
                account=account,
                to_email=lead.email,
                subject=subject,
                body=body,
                message_id=message_id,
            )
            email_record.status = "sent"
            email_record.sent_at = datetime.now(timezone.utc)
            # Increment account counter
            account.sent_today += 1
            logger.info(
                "Email sent: email_id=%s lead=%s account=%s",
                email_record.id,
                lead.email,
                account.id,
            )
        except Exception as exc:
            email_record.status = "failed"
            email_record.metadata_["error"] = str(exc)
            logger.error(
                "Email send failed: lead=%s account=%s error=%s",
                lead.email,
                account.id,
                exc,
            )
        finally:
            await self.db.flush()

        return email_record

    async def send_campaign_emails(
        self,
        campaign_id: str,
        user_id: str,
        ai_service: "AIPersonalizationService",
        campaign_step_id: str | None = None,
    ) -> dict:
        """
        Send emails to all 'new' leads in a campaign.
        Uses account rotation for each lead.

        Returns summary: {sent, failed, skipped}
        """
        # Fetch campaign
        camp_result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = camp_result.scalar_one_or_none()
        if not campaign:
            logger.error("Campaign not found: %s", campaign_id)
            return {"sent": 0, "failed": 0, "skipped": 0}

        # Determine subject/body templates (from step if provided)
        subject_template = campaign.subject_template
        body_template = campaign.body_template

        if campaign_step_id:
            step_result = await self.db.execute(
                select(CampaignStep).where(CampaignStep.id == campaign_step_id)
            )
            step = step_result.scalar_one_or_none()
            if step:
                subject_template = step.subject_override or subject_template
                body_template = step.body_override or body_template

        # Fetch new leads
        leads_result = await self.db.execute(
            select(Lead).where(
                Lead.campaign_id == campaign_id,
                Lead.status == "new",
            )
        )
        leads = list(leads_result.scalars().all())

        sent = failed = skipped = 0

        for lead in leads:
            try:
                account = await self.get_available_account(user_id)
            except NoAccountAvailableError:
                logger.warning(
                    "No accounts available for campaign %s, stopping send", campaign_id
                )
                skipped += len(leads) - sent - failed - skipped
                break

            # Personalize if enabled
            subject, body = subject_template, body_template
            if campaign.ai_personalization_enabled:
                subject, body = await ai_service.personalize(
                    lead=lead,
                    subject_template=subject_template,
                    body_template=body_template,
                )

            if account.provider == "resend":
                from services.resend_sender import ResendEmailService
                resend_service = ResendEmailService(self.db)
                email = await resend_service.send_single_email(
                    lead=lead,
                    account=account,
                    subject=subject,
                    body=body,
                    campaign_step_id=campaign_step_id,
                )
            else:
                email = await self.send_single_email(
                    lead=lead,
                    account=account,
                    subject=subject,
                    body=body,
                    campaign_step_id=campaign_step_id,
                )

            if email.status == "sent":
                lead.status = "contacted"
                sent += 1
            else:
                failed += 1

        await self.db.commit()
        logger.info(
            "Campaign send complete: campaign=%s sent=%d failed=%d skipped=%d",
            campaign_id, sent, failed, skipped
        )
        return {"sent": sent, "failed": failed, "skipped": skipped}
