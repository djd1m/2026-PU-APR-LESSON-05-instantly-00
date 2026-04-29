"""Analytics router: campaign stats and lead activity timeline."""
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Campaign, Email, EmailEvent, Lead, User, get_db
from routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CampaignStats(BaseModel):
    campaign_id: str
    campaign_name: str
    total_leads: int
    total_sent: int
    total_opens: int
    total_clicks: int
    total_replies: int
    total_bounces: int
    open_rate: float
    click_rate: float
    reply_rate: float


class LeadEvent(BaseModel):
    event_type: str
    occurred_at: datetime
    email_id: str
    metadata: dict

    model_config = {"from_attributes": True}


class LeadTimeline(BaseModel):
    lead_id: str
    lead_email: str
    events: list[LeadEvent]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/campaign/{campaign_id}", response_model=CampaignStats)
async def get_campaign_stats(
    campaign_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> CampaignStats:
    """Return aggregate stats for a campaign."""
    # Verify ownership
    camp_result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
        )
    )
    campaign = camp_result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Total leads
    leads_count = await db.scalar(
        select(func.count()).select_from(Lead).where(Lead.campaign_id == campaign_id)
    )

    # Total sent emails
    sent_count = await db.scalar(
        select(func.count())
        .select_from(Email)
        .join(Lead, Lead.id == Email.lead_id)
        .where(Lead.campaign_id == campaign_id, Email.status == "sent")
    )

    # Event counts
    def _event_count_query(event_type: str):
        return (
            select(func.count())
            .select_from(EmailEvent)
            .join(Email, Email.id == EmailEvent.email_id)
            .join(Lead, Lead.id == Email.lead_id)
            .where(Lead.campaign_id == campaign_id, EmailEvent.event_type == event_type)
        )

    opens = await db.scalar(_event_count_query("open")) or 0
    clicks = await db.scalar(_event_count_query("click")) or 0
    replies = await db.scalar(_event_count_query("reply")) or 0
    bounces = await db.scalar(_event_count_query("bounce")) or 0

    sent = sent_count or 0
    total_leads = leads_count or 0

    def _rate(numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round(numerator / denominator * 100, 2)

    return CampaignStats(
        campaign_id=campaign_id,
        campaign_name=campaign.name,
        total_leads=total_leads,
        total_sent=sent,
        total_opens=opens,
        total_clicks=clicks,
        total_replies=replies,
        total_bounces=bounces,
        open_rate=_rate(opens, sent),
        click_rate=_rate(clicks, sent),
        reply_rate=_rate(replies, sent),
    )


@router.get("/lead/{lead_id}/timeline", response_model=LeadTimeline)
async def get_lead_timeline(
    lead_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> LeadTimeline:
    """Return the full event timeline for a lead."""
    lead_result = await db.execute(
        select(Lead)
        .join(Campaign, Campaign.id == Lead.campaign_id)
        .where(Lead.id == lead_id, Campaign.user_id == current_user.id)
    )
    lead = lead_result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    events_result = await db.execute(
        select(EmailEvent)
        .join(Email, Email.id == EmailEvent.email_id)
        .where(Email.lead_id == lead_id)
        .order_by(EmailEvent.occurred_at.asc())
    )
    events = events_result.scalars().all()

    return LeadTimeline(
        lead_id=lead_id,
        lead_email=lead.email,
        events=[
            LeadEvent(
                event_type=ev.event_type,
                occurred_at=ev.occurred_at,
                email_id=ev.email_id,
                metadata=ev.metadata_,
            )
            for ev in events
        ],
    )


@router.get("/account/{account_id}")
async def get_account_performance(
    account_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return sending performance for an email account."""
    from models import EmailAccount

    acc_result = await db.execute(
        select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == current_user.id,
        )
    )
    account = acc_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    sent = await db.scalar(
        select(func.count())
        .select_from(Email)
        .where(Email.account_id == account_id, Email.status == "sent")
    ) or 0

    replies = await db.scalar(
        select(func.count())
        .select_from(EmailEvent)
        .join(Email, Email.id == EmailEvent.email_id)
        .where(Email.account_id == account_id, EmailEvent.event_type == "reply")
    ) or 0

    return {
        "account_id": account_id,
        "smtp_user": account.smtp_user,
        "sent_today": account.sent_today,
        "daily_limit": account.daily_limit,
        "warmup_score": account.warmup_score,
        "total_sent": sent,
        "total_replies": replies,
        "reply_rate": round(replies / sent * 100, 2) if sent > 0 else 0.0,
    }
