from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact, ContactList
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.services.leads.extraction import extract_public_contacts, normalize_domain, normalize_website
from app.services.leads.scoring import score_candidate
from app.services.search import search_companies


@dataclass(frozen=True)
class LeadSearchResult:
    list_id: str
    list_name: str
    saved: int
    contacts: list[dict[str, Any]]
    log_id: str


async def run_lead_search(
    db: AsyncSession,
    *,
    user: User,
    query: str,
    city: str | None,
    limit: int,
    list_name: str | None = None,
) -> LeadSearchResult:
    clean_query = " ".join(query.split())
    clean_city = " ".join(city.split()) if city else None
    capped_limit = max(1, min(limit, 50))
    raw_results = await search_companies(clean_query, clean_city, capped_limit)

    seen_domains: set[str] = set()
    contacts_payload: list[dict[str, Any]] = []
    for raw in raw_results:
        website = normalize_website(raw.get("website"))
        domain = normalize_domain(website)
        dedupe_key = domain or (raw.get("name") or "").strip().lower()
        if not dedupe_key or dedupe_key in seen_domains:
            continue
        seen_domains.add(dedupe_key)

        text_blob = "\n".join(
            str(value)
            for value in [
                raw.get("name"),
                raw.get("website_summary"),
                raw.get("summary"),
                raw.get("description"),
                raw.get("email"),
                raw.get("phone"),
            ]
            if value
        )
        extracted = extract_public_contacts(text_blob)
        candidate = {
            **raw,
            "website": website,
            "domain": domain,
            "email": raw.get("email") or extracted.email,
            "phone": raw.get("phone") or extracted.phone,
            "telegram": extracted.telegram,
            "whatsapp": extracted.whatsapp,
            "vk": extracted.vk,
        }
        scored = score_candidate(candidate)
        candidate["score"] = scored.score
        candidate["priority"] = scored.priority
        candidate["confidence"] = scored.confidence
        candidate["score_reason"] = scored.reason
        contacts_payload.append(candidate)

    fallback_name = f"Поиск {datetime.now(UTC).date().isoformat()}"
    resolved_list_name = list_name or f"{clean_query} {clean_city or ''}".strip() or fallback_name
    contact_list = ContactList(
        id=uuid.uuid4(),
        user_id=user.id,
        name=resolved_list_name,
        source="search",
        source_meta={"query": clean_query, "city": clean_city},
        total_count=len(contacts_payload),
    )
    db.add(contact_list)
    await db.flush()

    response_contacts: list[dict[str, Any]] = []
    for item in contacts_payload:
        enrichment = {
            "website": item.get("website"),
            "website_summary": item.get("website_summary") or item.get("summary"),
            "lead_score": item["score"],
            "priority": item["priority"],
            "confidence": item["confidence"],
            "score_reason": item["score_reason"],
            "telegram": item.get("telegram"),
            "whatsapp": item.get("whatsapp"),
            "vk": item.get("vk"),
        }
        contact = Contact(
            id=uuid.uuid4(),
            user_id=user.id,
            list_id=contact_list.id,
            contact_name=item.get("name"),
            email=item.get("email"),
            phone=item.get("phone"),
            enrichment=enrichment,
            raw=item,
        )
        db.add(contact)
        response_contacts.append({"id": str(contact.id), **item})

    log = LeadProcessingLog(
        id=uuid.uuid4(),
        user_id=user.id,
        contact_list_id=contact_list.id,
        search_query_original=clean_query,
        search_queries_generated=[clean_query],
        urls_found=len(raw_results),
        urls_after_filter=len(contacts_payload),
        urls_crawled=sum(1 for result in raw_results if result.get("website_summary")),
        pages_crawled_total=sum(1 for result in raw_results if result.get("website_summary")),
        llm_calls=[],
        total_cost_usd=0,
        ai_credits_used=0,
        outcome="success",
        meta={"city": clean_city, "limit": capped_limit},
    )
    db.add(log)
    await db.commit()

    return LeadSearchResult(
        list_id=str(contact_list.id),
        list_name=contact_list.name,
        saved=len(response_contacts),
        contacts=response_contacts,
        log_id=str(log.id),
    )
