import asyncio
import logging

from app.services.search.firecrawl import enrich_website
from app.services.search.serp import search_serp
from app.services.search.twogis import search_twogis

logger = logging.getLogger(__name__)


async def search_companies(query: str, city: str | None = None, limit: int = 20) -> list[dict]:
    """Параллельный поиск: 2ГИС + SerpAPI, затем Firecrawl для сайтов."""
    logger.info("search_companies: start query=%r city=%r limit=%s", query, city, limit)

    # Запрашиваем оба источника с запасом, потом мёрджим
    fetch = max(limit, 20)
    twogis_results, serp_results = await asyncio.gather(
        _safe_twogis(query, city, fetch),
        _safe_serp(query, city, fetch),
    )
    logger.info("search_companies: 2gis=%s serp=%s", len(twogis_results), len(serp_results))

    # Мёрджим: дедупликация по домену и имени
    seen_domains: set[str] = set()
    seen_names: set[str] = set()
    merged: list[dict] = []

    for item in twogis_results + serp_results:
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

    logger.info("search_companies: done total=%s", len(results))
    return results


async def _safe_twogis(query: str, city: str | None, limit: int) -> list[dict]:
    try:
        return await search_twogis(query, city, limit)
    except Exception as exc:
        logger.warning("search_companies: 2gis failed: %r", exc)
        return []


async def _safe_serp(query: str, city: str | None, limit: int) -> list[dict]:
    try:
        return await search_serp(query, city, limit)
    except Exception as exc:
        logger.warning("search_companies: serp failed: %r", exc)
        return []


def _domain(url: str | None) -> str:
    if not url:
        return ""
    url = url.removeprefix("https://").removeprefix("http://").removeprefix("www.")
    return url.split("/")[0].lower()
