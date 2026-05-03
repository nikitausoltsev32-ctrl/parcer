"""Enrichment service: Hunter.io (email) + Firecrawl (website) → LLM → contact.enrichment."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.company import Company
from app.models.contact import Contact
from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client

logger = logging.getLogger(__name__)

_FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"
_FIRECRAWL_TIMEOUT = 20.0
_LLM_TIMEOUT = 30.0


async def _scrape_website(url: str) -> str | None:
    if not settings.firecrawl_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=_FIRECRAWL_TIMEOUT) as client:
            resp = await client.post(
                _FIRECRAWL_URL,
                headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
                json={"url": url, "formats": ["markdown"]},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("markdown") or None
    except Exception as exc:
        logger.warning("firecrawl failed for %s: %s", url, exc)
        return None


_SUMMARIZE_PROMPT = """\
Ты — аналитик B2B-продаж. Изучи информацию о компании и верни JSON строго по схеме:

{{
  "description": "1-2 предложения о чём компания",
  "services": "главный продукт/услуга (≤10 слов)",
  "target": "кто клиенты компании (≤10 слов)",
  "city": "город или null"
}}

Только JSON, без markdown-обёртки.

Данные о компании:
{context}
"""


async def _llm_summarize(context: str) -> str:
    client = get_llm_client("enrich")
    prompt = _SUMMARIZE_PROMPT.format(context=context)
    result = await client.chat(
        [LLMMessage(role="user", content=prompt)],
        max_tokens=512,
        temperature=0.3,
        timeout=_LLM_TIMEOUT,
    )
    return (result.content or "").strip()


def _parse_summary(text: str) -> dict:
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


async def enrich_contact(contact_id: str, db: AsyncSession) -> dict:
    if settings.llm_enrich_provider == "disabled":
        return {"enriched": False, "reason": "disabled"}

    import uuid as _uuid
    contact = await db.get(Contact, _uuid.UUID(contact_id))
    if contact is None:
        logger.warning("enrich_contact: contact %s not found", contact_id)
        return {"enriched": False, "reason": "not_found"}

    company: Company | None = None
    if contact.company_id:
        company = await db.get(Company, contact.company_id)

    website = (
        (company.website if company else None)
        or (contact.enrichment or {}).get("website")
        or (contact.raw or {}).get("website")
    )

    if not website:
        return {"enriched": False, "reason": "no_website"}

    from app.services.search.hunter import find_emails_by_domain

    scraped, hunter_emails = await asyncio.gather(
        _scrape_website(website),
        find_emails_by_domain(website),
    )

    # Сохраняем лучший email из Hunter если у контакта ещё нет
    if hunter_emails and not contact.email:
        contact.email = hunter_emails[0]["email"]
        logger.info("enrich_contact: set email from hunter: %s", contact.email)

    parts: list[str] = []
    if company:
        if company.name:
            parts.append(f"Название: {company.name}")
        if company.industry:
            parts.append(f"Отрасль: {company.industry}")
        if company.city:
            parts.append(f"Город: {company.city}")
        if company.notes:
            parts.append(f"Заметки: {company.notes}")
    if contact.contact_name:
        parts.append(f"Контакт: {contact.contact_name}")
    if contact.position:
        parts.append(f"Должность: {contact.position}")
    parts.append(f"Сайт: {website}")
    if scraped:
        parts.append(f"\nКонтент сайта (markdown):\n{scraped[:4000]}")

    context = "\n".join(parts)
    try:
        raw_summary = await _llm_summarize(context)
        enrichment = _parse_summary(raw_summary)
    except Exception as exc:
        logger.error("enrich_contact: llm failed for %s: %s", contact_id, exc)
        return {"enriched": False, "reason": "llm_error"}

    enrichment["enriched_at"] = datetime.now(UTC).isoformat()
    sources = []
    if scraped:
        sources.append("firecrawl")
    if hunter_emails:
        sources.append("hunter")
        enrichment["hunter_emails"] = hunter_emails[:3]
    sources.append("llm")
    enrichment["source"] = "+".join(sources)

    existing = contact.enrichment or {}
    existing.update(enrichment)
    contact.enrichment = existing

    await db.commit()
    logger.info("enrich_contact: enriched %s (%s)", contact_id, enrichment["source"])
    return {"enriched": True, "source": enrichment["source"]}
