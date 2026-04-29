"""
Mailivery API client for email warmup integration.

API docs: https://mailivery.readme.io/reference/mailivery-api-introduction
Base URL: https://app.mailivery.io/api/v1
Auth: Bearer token
Rate limit: 240 req/min
"""
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

TIMEOUT = 30.0


class MailiveryError(Exception):
    """Raised when Mailivery API returns an error."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Mailivery error [{code}]: {message}")


class MailiveryClient:
    """HTTP client for Mailivery warmup API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.mailivery_api_key
        self.base_url = settings.mailivery_base_url
        self.enabled = bool(self.api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, path: str, data: dict | None = None
    ) -> dict:
        """Make an API request to Mailivery."""
        if not self.enabled:
            raise MailiveryError("NOT_CONFIGURED", "Mailivery API key not set")

        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.request(
                method, url, headers=self._headers(), json=data
            )

        if response.status_code == 429:
            raise MailiveryError("RATE_LIMITED", "Too many requests (240/min limit)")

        if response.status_code >= 400:
            try:
                body = response.json()
                raise MailiveryError(
                    body.get("code", "UNKNOWN"),
                    body.get("message", response.text),
                )
            except (ValueError, KeyError):
                raise MailiveryError("HTTP_ERROR", f"Status {response.status_code}")

        if response.status_code == 204:
            return {}
        return response.json()

    # ----- Mailbox Management -----

    async def connect_smtp_mailbox(
        self,
        email: str,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        imap_host: str | None = None,
        imap_port: int = 993,
    ) -> dict:
        """Connect a mailbox via SMTP credentials."""
        data = {
            "email": email,
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_username": smtp_user,
            "smtp_password": smtp_password,
        }
        if imap_host:
            data["imap_host"] = imap_host
            data["imap_port"] = imap_port

        result = await self._request("POST", "/connectsmtp", data)
        logger.info("Mailivery: connected mailbox %s → campaign_id=%s", email, result.get("id"))
        return result

    async def list_mailboxes(self) -> list[dict]:
        """List all connected mailboxes."""
        return await self._request("GET", "/allcampaigns")

    async def get_mailbox(self, campaign_id: str) -> dict:
        """Get mailbox details by campaign ID."""
        return await self._request("GET", f"/fetchcampaign?id={campaign_id}")

    async def delete_mailbox(self, campaign_id: str) -> dict:
        """Delete a connected mailbox."""
        return await self._request("DELETE", f"/campaign?id={campaign_id}")

    # ----- Warmup Controls -----

    async def start_warmup(self, campaign_id: str) -> dict:
        """Start warmup for a mailbox."""
        result = await self._request("PATCH", "/startwarmup", {"id": campaign_id})
        logger.info("Mailivery: warmup started for campaign %s", campaign_id)
        return result

    async def pause_warmup(self, campaign_id: str) -> dict:
        """Pause warmup."""
        result = await self._request("PATCH", "/pausewarmup", {"id": campaign_id})
        logger.info("Mailivery: warmup paused for campaign %s", campaign_id)
        return result

    async def resume_warmup(self, campaign_id: str) -> dict:
        """Resume paused warmup."""
        result = await self._request("PATCH", "/resumewarmup", {"id": campaign_id})
        logger.info("Mailivery: warmup resumed for campaign %s", campaign_id)
        return result

    async def set_emails_per_day(self, campaign_id: str, count: int) -> dict:
        """Update daily warmup email volume."""
        return await self._request(
            "PATCH", "/updateemailperday", {"id": campaign_id, "email_per_day": count}
        )

    async def enable_rampup(self, campaign_id: str) -> dict:
        """Enable progressive ramp-up."""
        return await self._request("PATCH", "/enablerampup", {"id": campaign_id})

    async def disable_rampup(self, campaign_id: str) -> dict:
        """Disable ramp-up (send at fixed volume)."""
        return await self._request("PATCH", "/disablerampup", {"id": campaign_id})

    # ----- Metrics -----

    async def get_metrics(self, campaign_id: str) -> dict:
        """Get warmup metrics (sent, received, spam, inbox rate)."""
        return await self._request("PATCH", "/getmetrics", {"id": campaign_id})

    async def get_health_score(self, campaign_id: str) -> dict:
        """Get mailbox health/warmup score."""
        return await self._request("PATCH", "/gethealthscore", {"id": campaign_id})

    async def get_activity_log(self, campaign_id: str) -> dict:
        """Get warmup activity log."""
        return await self._request("PATCH", "/getactivitylog", {"id": campaign_id})

    async def get_account_limits(self) -> dict:
        """Get account usage limits."""
        return await self._request("GET", "/getaccountlimits")
