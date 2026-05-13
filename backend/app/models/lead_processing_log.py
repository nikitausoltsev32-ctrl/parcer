import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LeadProcessingLog(Base):
    __tablename__ = "lead_processing_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    contact_list_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contact_lists.id", ondelete="SET NULL"),
        nullable=True,
    )
    search_query_original: Mapped[str] = mapped_column(String, default="")
    search_queries_generated: Mapped[list | None] = mapped_column(JSON, nullable=True)
    urls_found: Mapped[int] = mapped_column(Integer, default=0)
    urls_after_filter: Mapped[int] = mapped_column(Integer, default=0)
    urls_crawled: Mapped[int] = mapped_column(Integer, default=0)
    pages_crawled_total: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    total_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    ai_credits_used: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str] = mapped_column(String, default="success")
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
