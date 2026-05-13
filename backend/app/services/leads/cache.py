"""Step 5 — Cache Check. Look up existing lead by domain before crawling."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead

_LEAD_CACHE_TTL_DAYS = 14
_HTML_CACHE_TTL_DAYS = 30


def domain_content_hash(html: str) -> str:
    return hashlib.sha256(html.encode()).hexdigest()


async def get_cached_lead(db: AsyncSession, user_id: uuid.UUID, domain: str) -> Lead | None:
    cutoff = datetime.now(UTC) - timedelta(days=_LEAD_CACHE_TTL_DAYS)
    row = await db.execute(
        select(Lead).where(
            Lead.user_id == user_id,
            Lead.domain == domain,
            Lead.cache_valid.is_(True),
            Lead.created_at >= cutoff,
        )
    )
    return row.scalar_one_or_none()


async def invalidate_if_changed(db: AsyncSession, lead: Lead, new_html: str) -> bool:
    """Returns True if cache was invalidated (HTML changed)."""
    new_hash = domain_content_hash(new_html)
    if lead.content_hash and lead.content_hash == new_hash:
        return False
    lead.cache_valid = False
    lead.content_hash = new_hash
    lead.last_scraped_at = datetime.now(UTC)
    await db.flush()
    return True
