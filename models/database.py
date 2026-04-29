"""SQLAlchemy 2.0 async models and database setup."""
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import settings


# ---------------------------------------------------------------------------
# Engine & Session factory
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=5,
    max_overflow=15,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    # Relationships (noload — must be explicitly loaded)
    email_accounts: Mapped[list["EmailAccount"]] = relationship(
        "EmailAccount", back_populates="user", lazy="noload"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="user", lazy="noload"
    )
    settings: Mapped["UserSettings | None"] = relationship(
        "UserSettings", back_populates="user", uselist=False, lazy="noload", cascade="all, delete-orphan"
    )


class UserSettings(Base):
    """Per-user platform settings (API keys, preferences)."""
    __tablename__ = "user_settings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    mailivery_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    openai_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="settings", lazy="noload")


class EmailAccount(Base):
    __tablename__ = "email_accounts"
    __table_args__ = (
        CheckConstraint("sent_today >= 0", name="ck_sent_today_non_negative"),
        CheckConstraint("daily_limit > 0", name="ck_daily_limit_positive"),
        CheckConstraint("warmup_score >= 0 AND warmup_score <= 100", name="ck_warmup_score_range"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(20), default="smtp", nullable=False)
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int] = mapped_column(Integer, default=587, nullable=False)
    smtp_user: Mapped[str] = mapped_column(String(255), nullable=True)
    smtp_password: Mapped[str] = mapped_column(String(500), nullable=True)
    api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sent_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    warmup_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warmup_status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    warmup_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warmup_day: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warmup_daily_target: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    warmup_max_per_day: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    warmup_sent_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mailivery_campaign_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="email_accounts", lazy="noload")
    emails: Mapped[list["Email"]] = relationship(
        "Email", back_populates="account", lazy="noload"
    )
    warmup_logs: Mapped[list["WarmupLog"]] = relationship(
        "WarmupLog", back_populates="account", lazy="noload", cascade="all, delete-orphan"
    )


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'completed')",
            name="ck_campaign_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    from_name: Mapped[str] = mapped_column(String(255), nullable=False)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    reply_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject_template: Mapped[str] = mapped_column(Text, nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    ai_personalization_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="campaigns", lazy="noload")
    steps: Mapped[list["CampaignStep"]] = relationship(
        "CampaignStep", back_populates="campaign", lazy="noload", cascade="all, delete-orphan"
    )
    leads: Mapped[list["Lead"]] = relationship(
        "Lead", back_populates="campaign", lazy="noload", cascade="all, delete-orphan"
    )


class CampaignStep(Base):
    __tablename__ = "campaign_steps"
    __table_args__ = (
        CheckConstraint("step_number >= 1", name="ck_step_number_positive"),
        CheckConstraint("delay_days >= 0", name="ck_delay_days_non_negative"),
        UniqueConstraint("campaign_id", "step_number", name="uq_campaign_step_number"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    campaign_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subject_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_override: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="steps", lazy="noload"
    )
    emails: Mapped[list["Email"]] = relationship(
        "Email", back_populates="campaign_step", lazy="noload"
    )


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'contacted', 'replied', 'bounced', 'unsubscribed')",
            name="ck_lead_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    campaign_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    custom_variables: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="leads", lazy="noload"
    )
    emails: Mapped[list["Email"]] = relationship(
        "Email", back_populates="lead", lazy="noload"
    )


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'bounced')",
            name="ck_email_status",
        ),
        UniqueConstraint("message_id", name="uq_email_message_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    lead_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("email_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_step_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("campaign_steps.id", ondelete="SET NULL"),
        nullable=True,
    )
    message_id: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="emails", lazy="noload")
    account: Mapped["EmailAccount"] = relationship(
        "EmailAccount", back_populates="emails", lazy="noload"
    )
    campaign_step: Mapped["CampaignStep"] = relationship(
        "CampaignStep", back_populates="emails", lazy="noload"
    )
    events: Mapped[list["EmailEvent"]] = relationship(
        "EmailEvent", back_populates="email", lazy="noload", cascade="all, delete-orphan"
    )


class EmailEvent(Base):
    __tablename__ = "email_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('open', 'click', 'reply', 'bounce', 'unsubscribe')",
            name="ck_event_type",
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    email_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)

    email: Mapped["Email"] = relationship("Email", back_populates="events", lazy="noload")


class WarmupLog(Base):
    """Tracks daily warmup cycle results per account."""
    __tablename__ = "warmup_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("email_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    emails_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bounces: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inbox_rate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_after: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    account: Mapped["EmailAccount"] = relationship(
        "EmailAccount", back_populates="warmup_logs", lazy="noload"
    )


# ---------------------------------------------------------------------------
# Dependency: async DB session per request
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
