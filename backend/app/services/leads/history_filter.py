from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import CampaignMessage
from app.models.contact import Contact
from app.models.inbox_message import InboxMessage
from app.models.lead import Lead
from app.models.suppression import Suppression


@dataclass(frozen=True)
class HistoryDecision:
    skip: bool
    reason: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"skip": self.skip, "reason": self.reason, "meta": self.meta}


async def check_candidate_history(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    domain: str | None,
    email: str | None = None,
    phone: str | None = None,
    company_name: str | None = None,
) -> HistoryDecision:
    if email:
        suppressed = await db.execute(
            select(Suppression).where(Suppression.user_id == user_id, Suppression.email == email).limit(1)
        )
        suppression = suppressed.scalar_one_or_none()
        if suppression is not None:
            return HistoryDecision(
                skip=True,
                reason="suppressed",
                meta={"email": email, "suppression_reason": suppression.reason},
            )

    contact = await _find_contact(db, user_id=user_id, email=email, phone=phone, company_name=company_name)
    if contact is not None:
        message = await _latest_campaign_message(db, contact.id)
        inbox = await _latest_inbox_message(db, user_id=user_id, contact_id=contact.id)
        if message is not None and message.sent_at is not None:
            return HistoryDecision(
                skip=True,
                reason="already_contacted",
                meta={
                    "contact_id": str(contact.id),
                    "campaign_message_id": str(message.id),
                    "sent_at": message.sent_at.isoformat(),
                    "status": message.status,
                },
            )
        if inbox is not None and (inbox.classification in {"rejected", "unsubscribe"}):
            return HistoryDecision(
                skip=True,
                reason=f"already_{inbox.classification}",
                meta={
                    "contact_id": str(contact.id),
                    "inbox_message_id": str(inbox.id),
                    "classification": inbox.classification,
                },
            )
        return HistoryDecision(
            skip=True,
            reason="already_in_crm",
            meta={"contact_id": str(contact.id), "status": contact.status},
        )

    if domain:
        existing_lead = await db.execute(
            select(Lead).where(Lead.user_id == user_id, Lead.domain == domain).order_by(Lead.created_at.desc()).limit(1)
        )
        lead = existing_lead.scalar_one_or_none()
        if lead is not None:
            return HistoryDecision(
                skip=True,
                reason="already_found",
                meta={"lead_id": str(lead.id), "created_at": lead.created_at.isoformat() if lead.created_at else None},
            )

    return HistoryDecision(skip=False)


async def _find_contact(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    email: str | None,
    phone: str | None,
    company_name: str | None,
) -> Contact | None:
    if email:
        row = await db.execute(select(Contact).where(Contact.user_id == user_id, Contact.email == email).limit(1))
        contact = row.scalar_one_or_none()
        if contact is not None:
            return contact

    if phone:
        row = await db.execute(select(Contact).where(Contact.user_id == user_id, Contact.phone == phone).limit(1))
        contact = row.scalar_one_or_none()
        if contact is not None:
            return contact

    cleaned_name = " ".join(str(company_name or "").split())
    if cleaned_name:
        row = await db.execute(
            select(Contact)
            .where(Contact.user_id == user_id, Contact.contact_name.ilike(f"%{cleaned_name[:80]}%"))
            .limit(1)
        )
        return row.scalar_one_or_none()

    return None


async def _latest_campaign_message(db: AsyncSession, contact_id: uuid.UUID) -> CampaignMessage | None:
    row = await db.execute(
        select(CampaignMessage)
        .where(CampaignMessage.contact_id == contact_id)
        .order_by(CampaignMessage.sent_at.desc().nullslast())
        .limit(1)
    )
    return row.scalar_one_or_none()


async def _latest_inbox_message(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    contact_id: uuid.UUID,
) -> InboxMessage | None:
    row = await db.execute(
        select(InboxMessage)
        .where(InboxMessage.user_id == user_id, InboxMessage.contact_id == contact_id)
        .order_by(InboxMessage.received_at.desc().nullslast(), InboxMessage.created_at.desc())
        .limit(1)
    )
    return row.scalar_one_or_none()

