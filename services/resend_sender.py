"""Resend email sending service."""
import logging
import uuid
from datetime import datetime, timezone

import resend
from sqlalchemy.ext.asyncio import AsyncSession

from models import Email, EmailAccount, Lead

logger = logging.getLogger(__name__)


class ResendEmailService:
    """Send emails via Resend API."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def send_single_email(
        self,
        lead: Lead,
        account: EmailAccount,
        subject: str,
        body: str,
        campaign_step_id: str | None = None,
    ) -> Email:
        """Send one email via Resend API."""
        message_id = f"<{uuid.uuid4()}@resend>"
        email_record = Email(
            lead_id=lead.id,
            account_id=account.id,
            campaign_step_id=campaign_step_id,
            message_id=message_id,
            status="pending",
            subject=subject,
            body=body,
            metadata_={"provider": "resend"},
        )
        self.db.add(email_record)
        await self.db.flush()

        try:
            resend.api_key = account.api_key
            params = {
                "from": account.from_email,
                "to": [lead.email],
                "subject": subject,
                "html": f"<html><body>{body}</body></html>",
                "text": body,
            }
            result = resend.Emails.send(params)
            email_record.status = "sent"
            email_record.sent_at = datetime.now(timezone.utc)
            email_record.message_id = result.get("id", message_id)
            account.sent_today += 1
            logger.info(
                "Email sent via Resend: email_id=%s lead=%s resend_id=%s",
                email_record.id,
                lead.email,
                result.get("id"),
            )
        except Exception as exc:
            email_record.status = "failed"
            email_record.metadata_["error"] = str(exc)
            logger.error(
                "Resend send failed: lead=%s error=%s",
                lead.email,
                exc,
            )
        finally:
            await self.db.flush()

        return email_record
