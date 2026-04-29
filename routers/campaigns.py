"""Campaign management router: CRUD + steps + status transitions."""
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Campaign, CampaignStep, User, get_db
from routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["campaigns"])

VALID_STATUS_TRANSITIONS = {
    "draft": {"active"},
    "active": {"paused", "completed"},
    "paused": {"active", "completed"},
    "completed": set(),
}

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CampaignCreate(BaseModel):
    name: str
    from_name: str
    from_email: str
    reply_to: str | None = None
    subject_template: str
    body_template: str
    ai_personalization_enabled: bool = False


class CampaignUpdate(BaseModel):
    name: str | None = None
    from_name: str | None = None
    from_email: str | None = None
    reply_to: str | None = None
    subject_template: str | None = None
    body_template: str | None = None
    ai_personalization_enabled: bool | None = None


class CampaignStatusUpdate(BaseModel):
    status: str


class CampaignOut(BaseModel):
    id: str
    name: str
    status: str
    from_name: str
    from_email: str
    reply_to: str | None
    subject_template: str
    body_template: str
    ai_personalization_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StepCreate(BaseModel):
    step_number: int
    delay_days: int = 0
    subject_override: str | None = None
    body_override: str | None = None


class StepOut(BaseModel):
    id: str
    campaign_id: str
    step_number: int
    delay_days: int
    subject_override: str | None
    body_override: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_campaign_owned(
    campaign_id: str, user: User, db: AsyncSession
) -> Campaign:
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    camp = result.scalar_one_or_none()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return camp


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    """Create a new campaign."""
    campaign = Campaign(**body.model_dump(), user_id=current_user.id)
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    logger.info("Campaign created: %s by user %s", campaign.id, current_user.id)
    return campaign


@router.get("/", response_model=list[CampaignOut])
async def list_campaigns(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
) -> list[Campaign]:
    """List all campaigns for the current user."""
    result = await db.execute(
        select(Campaign)
        .where(Campaign.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .order_by(Campaign.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    """Get a specific campaign."""
    return await _get_campaign_owned(campaign_id, current_user, db)


@router.put("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    """Update campaign fields."""
    campaign = await _get_campaign_owned(campaign_id, current_user, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(campaign, field, value)
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.patch("/{campaign_id}/status", response_model=CampaignOut)
async def update_campaign_status(
    campaign_id: str,
    body: CampaignStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    """Transition campaign status."""
    campaign = await _get_campaign_owned(campaign_id, current_user, db)
    allowed = VALID_STATUS_TRANSITIONS.get(campaign.status, set())
    if body.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{campaign.status}' to '{body.status}'",
        )
    campaign.status = body.status
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a campaign (cascade deletes steps and leads)."""
    campaign = await _get_campaign_owned(campaign_id, current_user, db)
    await db.delete(campaign)


# ---------------------------------------------------------------------------
# Campaign Steps
# ---------------------------------------------------------------------------


@router.post("/{campaign_id}/steps", response_model=StepOut, status_code=201)
async def add_step(
    campaign_id: str,
    body: StepCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> CampaignStep:
    """Add a step to a campaign."""
    await _get_campaign_owned(campaign_id, current_user, db)
    step = CampaignStep(**body.model_dump(), campaign_id=campaign_id)
    db.add(step)
    await db.flush()
    await db.refresh(step)
    return step


@router.get("/{campaign_id}/steps", response_model=list[StepOut])
async def list_steps(
    campaign_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[CampaignStep]:
    """List all steps for a campaign."""
    await _get_campaign_owned(campaign_id, current_user, db)
    result = await db.execute(
        select(CampaignStep)
        .where(CampaignStep.campaign_id == campaign_id)
        .order_by(CampaignStep.step_number)
    )
    return list(result.scalars().all())


@router.delete("/{campaign_id}/steps/{step_id}", status_code=204)
async def delete_step(
    campaign_id: str,
    step_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a specific campaign step."""
    await _get_campaign_owned(campaign_id, current_user, db)
    result = await db.execute(
        select(CampaignStep).where(
            CampaignStep.id == step_id,
            CampaignStep.campaign_id == campaign_id,
        )
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    await db.delete(step)
