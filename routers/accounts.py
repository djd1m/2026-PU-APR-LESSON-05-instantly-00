"""Email account management router: CRUD with SMTP and Resend support + warmup."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import EmailAccount, User, get_db
from routers.auth import get_current_user
from services.warmup import WarmupService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["accounts"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AccountCreate(BaseModel):
    provider: str = "smtp"  # "smtp" or "resend"
    from_email: str
    daily_limit: int = 50
    # SMTP fields (required when provider=smtp)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    # Resend fields (required when provider=resend)
    api_key: str | None = None


class AccountUpdate(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    from_email: str | None = None
    daily_limit: int | None = None
    is_active: bool | None = None
    warmup_enabled: bool | None = None
    api_key: str | None = None


class AccountOut(BaseModel):
    id: str
    provider: str
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    from_email: str
    sent_today: int
    daily_limit: int
    is_active: bool
    warmup_enabled: bool
    warmup_status: str
    warmup_score: int
    warmup_day: int
    warmup_daily_target: int
    warmup_sent_today: int
    warmup_max_per_day: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_account_owned(
    account_id: str, user: User, db: AsyncSession
) -> EmailAccount:
    result = await db.execute(
        select(EmailAccount).where(
            EmailAccount.id == account_id, EmailAccount.user_id == user.id
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> EmailAccount:
    """Add a new email sending account (SMTP or Resend)."""
    if body.provider == "smtp":
        if not all([body.smtp_host, body.smtp_user, body.smtp_password]):
            raise HTTPException(
                status_code=400,
                detail="SMTP provider requires smtp_host, smtp_user, smtp_password",
            )
    elif body.provider == "resend":
        if not body.api_key:
            raise HTTPException(
                status_code=400,
                detail="Resend provider requires api_key",
            )
    else:
        raise HTTPException(status_code=400, detail="Invalid provider. Use 'smtp' or 'resend'")

    account = EmailAccount(**body.model_dump(), user_id=current_user.id)
    db.add(account)
    await db.flush()
    await db.refresh(account)
    logger.info("Account created: %s provider=%s by user %s", account.id, body.provider, current_user.id)
    return account


@router.get("/", response_model=list[AccountOut])
async def list_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[EmailAccount]:
    """List all email accounts for the current user."""
    result = await db.execute(
        select(EmailAccount).where(EmailAccount.user_id == current_user.id)
    )
    return list(result.scalars().all())


@router.get("/{account_id}", response_model=AccountOut)
async def get_account(
    account_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> EmailAccount:
    """Get a specific email account."""
    return await _get_account_owned(account_id, current_user, db)


@router.put("/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: str,
    body: AccountUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> EmailAccount:
    """Update email account settings."""
    account = await _get_account_owned(account_id, current_user, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    await db.flush()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an email account."""
    account = await _get_account_owned(account_id, current_user, db)
    await db.delete(account)


# ---------------------------------------------------------------------------
# Warmup Endpoints
# ---------------------------------------------------------------------------


@router.post("/{account_id}/warmup/start")
async def start_warmup(
    account_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start or resume email warmup for an account."""
    account = await _get_account_owned(account_id, current_user, db)
    service = WarmupService(db, user_id=current_user.id)
    account = await service.start_warmup(account)
    return await service.get_status(account)


@router.post("/{account_id}/warmup/pause")
async def pause_warmup(
    account_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Pause email warmup."""
    account = await _get_account_owned(account_id, current_user, db)
    service = WarmupService(db, user_id=current_user.id)
    account = await service.pause_warmup(account)
    return await service.get_status(account)


@router.post("/{account_id}/warmup/advance")
async def advance_warmup_day(
    account_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Advance warmup to the next day (simulate daily cycle for demo)."""
    account = await _get_account_owned(account_id, current_user, db)
    if account.warmup_status != "warming":
        raise HTTPException(status_code=400, detail="Account is not currently warming up")
    service = WarmupService(db, user_id=current_user.id)
    # Simulate some sends for demo
    account.warmup_sent_today = account.warmup_daily_target
    await service.advance_day(account)
    return await service.get_status(account)


@router.get("/{account_id}/warmup/status")
async def get_warmup_status(
    account_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current warmup status and history."""
    account = await _get_account_owned(account_id, current_user, db)
    service = WarmupService(db, user_id=current_user.id)
    return await service.get_status(account)
