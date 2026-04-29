"""Email sending and event tracking router."""
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Campaign, Email, EmailEvent, Lead, User, get_db
from routers.auth import get_current_user
from services.ai_personalization import AIPersonalizationService
from services.email_sender import EmailSenderService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["emails"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SendCampaignRequest(BaseModel):
    campaign_step_id: str | None = None


class EmailOut(BaseModel):
    id: str
    lead_id: str
    account_id: str | None
    campaign_step_id: str | None
    message_id: str
    status: str
    subject: str
    sent_at: datetime | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Background task: send all pending leads for a campaign
# ---------------------------------------------------------------------------


async def _send_campaign_background(
    campaign_id: str,
    campaign_step_id: str | None,
    user_id: str,
) -> None:
    """Background task: send emails to all 'new' leads in a campaign."""
    from models.database import AsyncSessionLocal

    from models import UserSettings

    async with AsyncSessionLocal() as db:
        try:
            # Check user settings for OpenAI API key
            from sqlalchemy import select
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            user_settings = result.scalar_one_or_none()
            openai_key = (user_settings.openai_api_key if user_settings else None) or None

            sender = EmailSenderService(db)
            ai_service = AIPersonalizationService(api_key=openai_key)
            await sender.send_campaign_emails(
                campaign_id=campaign_id,
                campaign_step_id=campaign_step_id,
                user_id=user_id,
                ai_service=ai_service,
            )
        except Exception:
            logger.exception("Background send failed for campaign %s", campaign_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/emails/send/{campaign_id}", status_code=202)
async def trigger_send_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    body: SendCampaignRequest = SendCampaignRequest(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger async email sending for a campaign. Returns 202 immediately."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
            Campaign.status == "active",
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found or not in active status",
        )

    background_tasks.add_task(
        _send_campaign_background,
        campaign_id=campaign_id,
        campaign_step_id=body.campaign_step_id,
        user_id=current_user.id,
    )
    return {"message": "Send job started", "campaign_id": campaign_id}


@router.get("/emails", response_model=list[EmailOut])
async def list_emails(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    campaign_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Email]:
    """List sent emails, optionally filtered by campaign."""
    query = (
        select(Email)
        .join(Lead, Lead.id == Email.lead_id)
        .join(Campaign, Campaign.id == Lead.campaign_id)
        .where(Campaign.user_id == current_user.id)
    )
    if campaign_id:
        query = query.where(Campaign.id == campaign_id)
    query = query.offset(skip).limit(limit).order_by(Email.sent_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Tracking endpoints (public — no auth)
# ---------------------------------------------------------------------------


@router.get("/track/open/{email_id}", response_class=Response)
async def track_open(
    email_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    1x1 pixel tracking for email opens.
    Records an 'open' event and returns a transparent GIF.
    """
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if email:
        event = EmailEvent(
            email_id=email_id,
            event_type="open",
            metadata_={
                "user_agent": request.headers.get("user-agent", ""),
                "ip": request.client.host if request.client else "",
            },
        )
        db.add(event)
        # Update lead status to 'contacted' if still 'new'
        lead_result = await db.execute(select(Lead).where(Lead.id == email.lead_id))
        lead = lead_result.scalar_one_or_none()
        if lead and lead.status == "new":
            lead.status = "contacted"
        try:
            await db.commit()
        except Exception:
            await db.rollback()

    # Return transparent 1x1 GIF
    pixel = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
        b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
        b"\x00\x00\x02\x02D\x01\x00;"
    )
    return Response(content=pixel, media_type="image/gif")


@router.get("/track/click/{email_id}")
async def track_click(
    email_id: str,
    url: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Record a click event and redirect to the target URL."""
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if email:
        event = EmailEvent(
            email_id=email_id,
            event_type="click",
            metadata_={
                "url": url,
                "user_agent": request.headers.get("user-agent", ""),
                "ip": request.client.host if request.client else "",
            },
        )
        db.add(event)
        try:
            await db.commit()
        except Exception:
            await db.rollback()

    return RedirectResponse(url=url, status_code=302)


@router.post("/track/reply/{email_id}", status_code=204)
async def track_reply(
    email_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Record a reply event (called by email provider webhook)."""
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        return

    event = EmailEvent(email_id=email_id, event_type="reply", metadata_={})
    db.add(event)

    # Update lead status to 'replied'
    lead_result = await db.execute(select(Lead).where(Lead.id == email.lead_id))
    lead = lead_result.scalar_one_or_none()
    if lead:
        lead.status = "replied"

    try:
        await db.commit()
    except Exception:
        await db.rollback()
