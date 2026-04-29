"""Lead management router: CRUD, bulk import, unsubscribe."""
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import Campaign, Lead, User, get_db
from routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leads", tags=["leads"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LeadCreate(BaseModel):
    campaign_id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    custom_variables: dict = {}


class LeadUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    status: str | None = None
    custom_variables: dict | None = None


class LeadOut(BaseModel):
    id: str
    campaign_id: str
    email: str
    first_name: str | None
    last_name: str | None
    company: str | None
    status: str
    custom_variables: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class BulkImportRequest(BaseModel):
    campaign_id: str
    leads: list[LeadCreate]


class BulkImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _verify_campaign_ownership(
    campaign_id: str, user: User, db: AsyncSession
) -> Campaign:
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    camp = result.scalar_one_or_none()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return camp


VALID_LEAD_STATUSES = {"new", "contacted", "replied", "bounced", "unsubscribed"}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=LeadOut, status_code=201)
async def create_lead(
    body: LeadCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Lead:
    """Add a single lead to a campaign."""
    await _verify_campaign_ownership(body.campaign_id, current_user, db)
    lead = Lead(**body.model_dump())
    db.add(lead)
    await db.flush()
    await db.refresh(lead)
    return lead


@router.post("/bulk", response_model=BulkImportResult)
async def bulk_import_leads(
    body: BulkImportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> BulkImportResult:
    """Bulk import leads into a campaign. Skips duplicates by email."""
    await _verify_campaign_ownership(body.campaign_id, current_user, db)

    # Fetch existing emails to skip duplicates
    existing_result = await db.execute(
        select(Lead.email).where(Lead.campaign_id == body.campaign_id)
    )
    existing_emails = {row[0] for row in existing_result.all()}

    imported = 0
    skipped = 0
    errors: list[str] = []

    for lead_data in body.leads:
        if lead_data.email in existing_emails:
            skipped += 1
            continue
        try:
            lead = Lead(
                campaign_id=body.campaign_id,
                email=lead_data.email,
                first_name=lead_data.first_name,
                last_name=lead_data.last_name,
                company=lead_data.company,
                custom_variables=lead_data.custom_variables,
            )
            db.add(lead)
            existing_emails.add(lead_data.email)
            imported += 1
        except Exception as e:
            errors.append(f"{lead_data.email}: {str(e)}")

    await db.flush()
    logger.info(
        "Bulk import campaign=%s: imported=%d skipped=%d errors=%d",
        body.campaign_id, imported, skipped, len(errors)
    )
    return BulkImportResult(imported=imported, skipped=skipped, errors=errors)


@router.get("/", response_model=list[LeadOut])
async def list_leads(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    campaign_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
) -> list[Lead]:
    """List leads, optionally filtered by campaign or status."""
    query = (
        select(Lead)
        .join(Campaign, Campaign.id == Lead.campaign_id)
        .where(Campaign.user_id == current_user.id)
    )
    if campaign_id:
        query = query.where(Lead.campaign_id == campaign_id)
    if status_filter:
        query = query.where(Lead.status == status_filter)
    query = query.offset(skip).limit(limit).order_by(Lead.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(
    lead_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Lead:
    """Get a specific lead."""
    result = await db.execute(
        select(Lead)
        .join(Campaign, Campaign.id == Lead.campaign_id)
        .where(Lead.id == lead_id, Campaign.user_id == current_user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: str,
    body: LeadUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Lead:
    """Update lead fields."""
    result = await db.execute(
        select(Lead)
        .join(Campaign, Campaign.id == Lead.campaign_id)
        .where(Lead.id == lead_id, Campaign.user_id == current_user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    updates = body.model_dump(exclude_none=True)
    if "status" in updates and updates["status"] not in VALID_LEAD_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {updates['status']}")

    for field, value in updates.items():
        setattr(lead, field, value)
    await db.flush()
    await db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a lead."""
    result = await db.execute(
        select(Lead)
        .join(Campaign, Campaign.id == Lead.campaign_id)
        .where(Lead.id == lead_id, Campaign.user_id == current_user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)


@router.get("/unsubscribe/{lead_id}", status_code=200)
async def unsubscribe(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Public unsubscribe endpoint (no auth required).
    Sets lead status to 'unsubscribed'.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        # Return success to avoid email enumeration
        return {"message": "Unsubscribed successfully"}

    lead.status = "unsubscribed"
    await db.flush()
    logger.info("Lead unsubscribed: %s", lead_id)
    return {"message": "You have been unsubscribed successfully"}
