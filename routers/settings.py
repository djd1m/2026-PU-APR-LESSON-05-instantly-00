"""User settings router: API keys and preferences managed via UI."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, UserSettings, get_db
from routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SettingsOut(BaseModel):
    mailivery_api_key: str | None = None
    openai_api_key: str | None = None

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    mailivery_api_key: str | None = None
    openai_api_key: str | None = None


class SettingsOutMasked(BaseModel):
    """Returns masked keys so the UI can show if a key is set without exposing it."""
    mailivery_api_key_set: bool = False
    mailivery_api_key_preview: str = ""
    openai_api_key_set: bool = False
    openai_api_key_preview: str = ""


def _mask_key(key: str | None) -> tuple[bool, str]:
    if not key:
        return False, ""
    if len(key) <= 8:
        return True, "****"
    return True, key[:4] + "..." + key[-4:]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/", response_model=SettingsOutMasked)
async def get_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> SettingsOutMasked:
    """Get current user settings (keys are masked)."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        return SettingsOutMasked()

    m_set, m_preview = _mask_key(settings.mailivery_api_key)
    o_set, o_preview = _mask_key(settings.openai_api_key)

    return SettingsOutMasked(
        mailivery_api_key_set=m_set,
        mailivery_api_key_preview=m_preview,
        openai_api_key_set=o_set,
        openai_api_key_preview=o_preview,
    )


@router.put("/", response_model=SettingsOutMasked)
async def update_settings(
    body: SettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> SettingsOutMasked:
    """Update user settings. Only non-null fields are updated."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    if body.mailivery_api_key is not None:
        settings.mailivery_api_key = body.mailivery_api_key or None
    if body.openai_api_key is not None:
        settings.openai_api_key = body.openai_api_key or None

    await db.flush()
    await db.refresh(settings)

    m_set, m_preview = _mask_key(settings.mailivery_api_key)
    o_set, o_preview = _mask_key(settings.openai_api_key)

    logger.info("Settings updated for user %s", current_user.id)
    return SettingsOutMasked(
        mailivery_api_key_set=m_set,
        mailivery_api_key_preview=m_preview,
        openai_api_key_set=o_set,
        openai_api_key_preview=o_preview,
    )
