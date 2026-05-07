import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LeadList(Base):
    __tablename__ = 'lead_lists'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default='search')
    source_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lead(Base):
    __tablename__ = 'leads'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    list_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('lead_lists.id', ondelete='CASCADE'), nullable=True, index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True)
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    company_name: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    region: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    services: Mapped[list | None] = mapped_column(JSON, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    telegram: Mapped[str | None] = mapped_column(String, nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String, nullable=True)
    vk: Mapped[str | None] = mapped_column(String, nullable=True)
    instagram: Mapped[str | None] = mapped_column(String, nullable=True)
    has_contact_form: Mapped[bool] = mapped_column(Boolean, default=False)
    decision_maker: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    website_quality: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lead_fit: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pain_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reason_to_contact: Mapped[str | None] = mapped_column(Text, nullable=True)
    personalized_outreach: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processing: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cache_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_leads_domain', 'domain', postgresql_where='domain IS NOT NULL'),
        Index('uq_leads_user_domain', 'user_id', 'domain', unique=True, postgresql_where='domain IS NOT NULL'),
    )
