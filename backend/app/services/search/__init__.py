import asyncio
import logging

from app.services.search.firecrawl import enrich_website
from app.services.search.hunter import find_emails_by_domain
from app.services.search.serp import search_google, search_serp

logger = logging.getLogger(__name__)


async def search_companies(query: str, city: str | None = None, limit: int = 20) -> list[dict]:
    """Параллельный поиск: Google Maps + Google Search (SerpAPI), затем Firecrawl + Hunter."""
    logger.info("search_companies: start query=%r city=%r limit=%s", query, city, limit)

    fetch = max(limit, 20)
    maps_results, google_results = await asyncio.gather(
        _safe_serp(query, city, fetch),
        _safe_google(query, city, fetch),
    )
    logger.info("search_companies: maps=%s google=%s", len(maps_results), len(google_results))

    # Мёрджим: дедупликация по домену и имени
    seen_domains: set[str] = set()
    seen_names: set[str] = set()
    merged: list[dict] = []

    for item in maps_results + google_results:
        domain = _domain(item.get("website"))
        name = item.get("name", "").lower()
        if domain and domain in seen_domains:
            continue
        if name and name in seen_names:
            continue
        merged.append(item)
        if domain:
            seen_domains.add(domain)
        if name:
            seen_names.add(name)

    # Приоритет: у кого есть сайт — выше
    merged.sort(key=lambda r: (0 if r.get("website") else 1))
    results = merged[:limit]

    # Firecrawl: обогащаем первые 5 у кого есть сайт
    to_enrich = [r for r in results if r.get("website") and not r.get("website_summary")][:5]
    if to_enrich:
        try:
            summaries = await asyncio.gather(
                *[enrich_website(r["website"]) for r in to_enrich],
                return_exceptions=True,
            )
            for r, summary in zip(to_enrich, summaries):
                if isinstance(summary, str):
                    r["website_summary"] = summary
            logger.info("search_companies: firecrawl attempted for %s websites", len(to_enrich))
        except Exception as exc:
            logger.warning("search_companies: firecrawl gather failed: %r", exc)

    # Hunter: ищем email по домену для компаний без email
    to_hunt = [r for r in results if r.get("website") and not r.get("email")][:10]
    if to_hunt:
        hunter_results = await asyncio.gather(
            *[find_emails_by_domain(r["website"]) for r in to_hunt],
            return_exceptions=True,
        )
        for r, emails in zip(to_hunt, hunter_results):
            if isinstance(emails, list) and emails:
                r["email"] = emails[0]["email"]
        logger.info("search_companies: hunter attempted for %s domains", len(to_hunt))

    logger.info("search_companies: done total=%s", len(results))
    return results


async def _safe_serp(query: str, city: str | None, limit: int) -> list[dict]:
    try:
        return await search_serp(query, city, limit)
    except Exception as exc:
        logger.warning("search_companies: serp failed: %r", exc)
        return []


async def _safe_google(query: str, city: str | None, limit: int) -> list[dict]:
    try:
        return await search_google(query, city, limit)
    except Exception as exc:
        logger.warning("search_companies: google failed: %r", exc)
        return []


def _domain(url: str | None) -> str:
    if not url:
        return ""
    url = url.removeprefix("https://").removeprefix("http://").removeprefix("www.")
    return url.split("/")[0].lower()
