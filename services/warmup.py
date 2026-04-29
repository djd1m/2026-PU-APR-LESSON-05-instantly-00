"""
Email warmup service — progressive volume ramp-up.

Three modes:
1. Mailivery API (production) — if MAILIVERY_API_KEY is set
2. Self-hosted pool (budget) — cron + own seed accounts
3. Demo mode (no real sending) — local state machine only

Based on ColdMail.ru warmup architecture:
- 14-21 day progressive ramp: 5 → 50 emails/day
- State machine: new → warming → ready (score >= 85) | paused
- Auto-pause on high bounce rate (>5%)
- Score calculation based on inbox placement rate
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import EmailAccount, WarmupLog

logger = logging.getLogger(__name__)

# Warmup ramp schedule: day → target emails/day
RAMP_SCHEDULE = {
    1: 5, 2: 5, 3: 8, 4: 8,
    5: 12, 6: 12, 7: 18, 8: 18,
    9: 25, 10: 25, 11: 33, 12: 33,
    13: 42, 14: 50,
}

WARMUP_READY_SCORE = 85
MAX_BOUNCE_RATE = 5.0  # percent — auto-pause threshold


def _get_warmup_mode() -> str:
    """Determine warmup mode based on configuration."""
    if settings.mailivery_api_key:
        return "mailivery"
    return "demo"


class WarmupService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.mode = _get_warmup_mode()

    async def start_warmup(self, account: EmailAccount) -> EmailAccount:
        """Start or resume warmup for an account."""
        if account.warmup_status == "ready":
            logger.info("Account %s already warmed up (score=%d)", account.id, account.warmup_score)
            return account

        # Mailivery mode: connect + start via API
        if self.mode == "mailivery":
            await self._mailivery_start(account)

        account.warmup_enabled = True
        account.warmup_status = "warming"
        if account.warmup_day == 0:
            account.warmup_day = 1
        account.warmup_daily_target = self._get_daily_target(account.warmup_day)
        account.warmup_sent_today = 0

        await self.db.flush()
        await self.db.refresh(account)
        logger.info(
            "Warmup started [%s]: account=%s day=%d target=%d",
            self.mode, account.id, account.warmup_day, account.warmup_daily_target,
        )
        return account

    async def pause_warmup(self, account: EmailAccount) -> EmailAccount:
        """Pause warmup."""
        if self.mode == "mailivery" and account.mailivery_campaign_id:
            await self._mailivery_pause(account)

        account.warmup_enabled = False
        account.warmup_status = "paused"
        await self.db.flush()
        await self.db.refresh(account)
        logger.info("Warmup paused [%s]: account=%s", self.mode, account.id)
        return account

    async def sync_metrics(self, account: EmailAccount) -> dict | None:
        """Sync warmup metrics from Mailivery (production mode only)."""
        if self.mode != "mailivery" or not account.mailivery_campaign_id:
            return None

        from services.mailivery_client import MailiveryClient, MailiveryError
        client = MailiveryClient()
        try:
            metrics = await client.get_metrics(account.mailivery_campaign_id)
            health = await client.get_health_score(account.mailivery_campaign_id)

            # Update account from Mailivery data
            if "health_score" in health:
                account.warmup_score = min(100, max(0, int(health["health_score"])))
            if account.warmup_score >= WARMUP_READY_SCORE and account.warmup_day > 7:
                account.warmup_status = "ready"

            await self.db.flush()
            logger.info(
                "Mailivery sync: account=%s score=%d",
                account.id, account.warmup_score,
            )
            return {"metrics": metrics, "health": health}
        except MailiveryError as e:
            logger.warning("Mailivery sync failed: %s", e)
            return None

    async def advance_day(self, account: EmailAccount) -> WarmupLog:
        """
        Complete current warmup day and advance to the next.
        Called at end of each warmup cycle (e.g., by a daily cron/worker).
        """
        sent = account.warmup_sent_today
        bounces = 0
        inbox_rate = 100 if sent > 0 else 0

        # In mailivery mode, try to get real metrics
        if self.mode == "mailivery" and account.mailivery_campaign_id:
            real_metrics = await self.sync_metrics(account)
            if real_metrics and "metrics" in real_metrics:
                m = real_metrics["metrics"]
                sent = m.get("total_sent", sent)
                bounces = m.get("total_bounced", 0)
                inbox_pct = m.get("inbox_rate", inbox_rate)
                if isinstance(inbox_pct, (int, float)):
                    inbox_rate = int(inbox_pct)

        if sent > 0 and bounces > 0:
            bounce_rate = (bounces / sent) * 100
            inbox_rate = max(0, int(100 - bounce_rate))

            if bounce_rate > MAX_BOUNCE_RATE:
                logger.warning(
                    "Warmup auto-paused: account=%s bounce_rate=%.1f%%",
                    account.id, bounce_rate,
                )
                account.warmup_status = "paused"
                account.warmup_enabled = False

        # Update warmup score (weighted moving average)
        old_score = account.warmup_score
        if account.warmup_day <= 1:
            new_score = inbox_rate
        else:
            new_score = int(inbox_rate * 0.7 + old_score * 0.3)
        account.warmup_score = min(100, max(0, new_score))

        # Log this day
        log = WarmupLog(
            account_id=account.id,
            day_number=account.warmup_day,
            emails_sent=sent,
            emails_received=0,
            bounces=bounces,
            inbox_rate=inbox_rate,
            score_after=account.warmup_score,
            status="completed",
        )
        self.db.add(log)

        # Advance to next day
        account.warmup_day += 1
        account.warmup_daily_target = self._get_daily_target(account.warmup_day)
        account.warmup_sent_today = 0

        if account.warmup_score >= WARMUP_READY_SCORE and account.warmup_day > 7:
            account.warmup_status = "ready"
            logger.info(
                "Warmup complete: account=%s score=%d days=%d",
                account.id, account.warmup_score, account.warmup_day,
            )

        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_warmup_history(self, account_id: str) -> list[WarmupLog]:
        """Get warmup log history for an account."""
        result = await self.db.execute(
            select(WarmupLog)
            .where(WarmupLog.account_id == account_id)
            .order_by(WarmupLog.day_number.asc())
        )
        return list(result.scalars().all())

    async def get_status(self, account: EmailAccount) -> dict:
        """Get current warmup status summary."""
        logs = await self.get_warmup_history(account.id)
        total_sent = sum(log.emails_sent for log in logs)
        total_bounces = sum(log.bounces for log in logs)

        return {
            "account_id": account.id,
            "mode": self.mode,
            "status": account.warmup_status,
            "enabled": account.warmup_enabled,
            "current_day": account.warmup_day,
            "total_days": max(14, account.warmup_day),
            "daily_target": account.warmup_daily_target,
            "sent_today": account.warmup_sent_today,
            "score": account.warmup_score,
            "ready_threshold": WARMUP_READY_SCORE,
            "total_emails_sent": total_sent,
            "total_bounces": total_bounces,
            "mailivery_connected": bool(account.mailivery_campaign_id),
            "history": [
                {
                    "day": log.day_number,
                    "sent": log.emails_sent,
                    "bounces": log.bounces,
                    "inbox_rate": log.inbox_rate,
                    "score": log.score_after,
                }
                for log in logs
            ],
        }

    # ----- Mailivery Integration -----

    async def _mailivery_start(self, account: EmailAccount) -> None:
        """Connect mailbox to Mailivery and start warmup."""
        from services.mailivery_client import MailiveryClient, MailiveryError
        client = MailiveryClient()

        try:
            # Connect if not already connected
            if not account.mailivery_campaign_id:
                if account.provider != "smtp" or not account.smtp_host:
                    logger.warning("Mailivery requires SMTP — account %s is %s", account.id, account.provider)
                    return
                result = await client.connect_smtp_mailbox(
                    email=account.from_email,
                    smtp_host=account.smtp_host,
                    smtp_port=account.smtp_port,
                    smtp_user=account.smtp_user,
                    smtp_password=account.smtp_password,
                )
                account.mailivery_campaign_id = result.get("id") or result.get("campaign_id")
                await self.db.flush()

            # Start warmup + enable ramp-up
            if account.mailivery_campaign_id:
                await client.start_warmup(account.mailivery_campaign_id)
                await client.enable_rampup(account.mailivery_campaign_id)
        except MailiveryError as e:
            logger.error("Mailivery start failed: %s", e)

    async def _mailivery_pause(self, account: EmailAccount) -> None:
        """Pause warmup in Mailivery."""
        from services.mailivery_client import MailiveryClient, MailiveryError
        client = MailiveryClient()
        try:
            await client.pause_warmup(account.mailivery_campaign_id)
        except MailiveryError as e:
            logger.error("Mailivery pause failed: %s", e)

    @staticmethod
    def _get_daily_target(day: int) -> int:
        """Get target email count for a given warmup day."""
        if day in RAMP_SCHEDULE:
            return RAMP_SCHEDULE[day]
        return 50
