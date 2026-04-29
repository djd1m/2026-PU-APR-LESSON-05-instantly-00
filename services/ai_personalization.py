"""
AI email personalization service using OpenAI GPT-4.

Key design:
- Async OpenAI client with per-request timeout
- Tenacity retry on rate limits and transient errors
- Graceful fallback: if OpenAI fails, return rendered template
- Template rendering supports {first_name}, {last_name}, {company} variables
"""
import logging
from string import Template

from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIConnectionError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from models import Lead

logger = logging.getLogger(__name__)


def _render_template(template: str, lead: Lead) -> str:
    """
    Render a template string with lead variables.
    Supports: {first_name}, {last_name}, {company}, {email}
    Plus any key from lead.custom_variables.
    Falls back gracefully if variable not present.
    """
    variables = {
        "first_name": lead.first_name or "",
        "last_name": lead.last_name or "",
        "company": lead.company or "",
        "email": lead.email,
    }
    # Merge custom variables (lower priority than standard fields)
    if lead.custom_variables:
        for key, value in lead.custom_variables.items():
            variables.setdefault(key, str(value))

    try:
        return template.format_map(variables)
    except KeyError as e:
        logger.warning("Template variable %s not found for lead %s", e, lead.email)
        # Return template with unfilled variables as-is
        return template


class AIPersonalizationService:
    """Wraps OpenAI GPT-4 for email personalization with fallback."""

    def __init__(self, client: AsyncOpenAI | None = None, api_key: str | None = None) -> None:
        self._client = client or AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            timeout=settings.openai_timeout,
            max_retries=0,  # We handle retries ourselves via tenacity
        )

    @retry(
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=False,  # Don't reraise — we catch in personalize()
    )
    async def _call_openai(self, prompt: str, context: str) -> str:
        """
        Call GPT-4 to rewrite an email.
        Returns the personalized email text or raises on unrecoverable error.
        """
        response = await self._client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert cold email copywriter. "
                        "Rewrite the provided email to be more personalized and compelling "
                        "for the specific recipient. Keep it concise and professional. "
                        "Return ONLY the rewritten email text, no explanation."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Recipient info:\n{context}\n\nEmail to personalize:\n{prompt}",
                },
            ],
            temperature=0.7,
            max_tokens=500,
        )
        return response.choices[0].message.content or prompt

    async def personalize_subject(self, subject: str, lead: Lead) -> str:
        """Personalize the email subject line for a lead."""
        context = (
            f"Name: {lead.first_name or 'Unknown'} {lead.last_name or ''}\n"
            f"Company: {lead.company or 'Unknown'}\n"
            f"Email: {lead.email}"
        )
        try:
            result = await self._call_openai(
                prompt=f"Subject line: {subject}",
                context=context,
            )
            # Strip any "Subject:" prefix GPT might add
            result = result.strip().removeprefix("Subject:").strip()
            return result if result else _render_template(subject, lead)
        except Exception as exc:
            logger.warning(
                "GPT-4 subject personalization failed for %s: %s. Using template.",
                lead.email, exc
            )
            return _render_template(subject, lead)

    async def personalize_body(self, body: str, lead: Lead) -> str:
        """Personalize the email body for a lead."""
        context = (
            f"Name: {lead.first_name or 'Unknown'} {lead.last_name or ''}\n"
            f"Company: {lead.company or 'Unknown'}\n"
            f"Email: {lead.email}"
        )
        if lead.custom_variables:
            context += f"\nAdditional info: {lead.custom_variables}"

        try:
            result = await self._call_openai(prompt=body, context=context)
            return result if result else _render_template(body, lead)
        except Exception as exc:
            logger.warning(
                "GPT-4 body personalization failed for %s: %s. Using template.",
                lead.email, exc
            )
            return _render_template(body, lead)

    async def personalize(
        self,
        lead: Lead,
        subject_template: str,
        body_template: str,
    ) -> tuple[str, str]:
        """
        Personalize both subject and body for a lead.

        Returns (subject, body) — always succeeds.
        Falls back to template rendering if OpenAI fails.
        """
        subject, body = await _concurrent_personalize(self, lead, subject_template, body_template)
        return subject, body


async def _concurrent_personalize(
    service: AIPersonalizationService,
    lead: Lead,
    subject_template: str,
    body_template: str,
) -> tuple[str, str]:
    """Run subject and body personalization concurrently."""
    import asyncio
    subject, body = await asyncio.gather(
        service.personalize_subject(subject_template, lead),
        service.personalize_body(body_template, lead),
    )
    return subject, body
