import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    list_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contact_lists.id"))
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id"))
    smtp_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("smtp_accounts.id"))
    llm_provider: Mapped[str] = mapped_column(String, default="groq")
    llm_model: Mapped[str] = mapped_column(String, default="llama-3.3-70b-versatile")
    send_rate_per_hour: Mapped[int] = mapped_column(Integer, default=30)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft")
    stats: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {"generated": 0, "sent": 0, "delivered": 0, "opened": 0, "clicked": 0, "replied": 0, "failed": 0, "unsub": 0},
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CampaignMessage(Base):
    __tablename__ = "campaign_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contacts.id"))
    subject: Mapped[str] = mapped_column(String, default="")
    body: Mapped[str] = mapped_column(String, default="")
    body_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    tracking_id: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_campaign_messages_campaign_status", "campaign_id", "status"),
    )
