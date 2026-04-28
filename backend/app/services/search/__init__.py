import asyncio
import logging

from app.services.search.firecrawl import enrich_website
from app.services.search.serp import search_serp
from app.services.search.twogis import search_twogis

logger = logging.getLogger(__name__)


async def search_companies(query: str, city: str | None = None, limit: int = 20) -> list[dict]:
    """Ищет компании: сначала 2ГИС, дополняет SerpAPI до нужного количества."""
    logger.info("search_companies: start query=%r city=%r limit=%s", query, city, limit)
    try:
        results = await search_twogis(query, city, limit)
    except Exception as exc:
        logger.warning("search_companies: 2gis failed query=%r city=%r: %r", query, city, exc)
        results = []
    logger.info("search_companies: 2gis returned %s results", len(results))

    if len(results) < limit:
        try:
            serp = await search_serp(query, city, limit - len(results))
        except Exception as exc:
            logger.warning("search_companies: serp failed query=%r city=%r: %r", query, city, exc)
            serp = []
        logger.info("search_companies: serp returned %s results", len(serp))
        # дедупликация по домену
        existing_domains = {_domain(r["website"]) for r in results if r.get("website")}
        for item in serp:
            if _domain(item.get("website")) not in existing_domains:
                results.append(item)
                existing_domains.add(_domain(item.get("website")))

    results = results[:limit]

    # Обогащение сайтов через Firecrawl (параллельно, не более 5)
    to_enrich = [r for r in results if r.get("website") and not r.get("email")][:5]
    if to_enrich:
        summaries = await asyncio.gather(*[enrich_website(r["website"]) for r in to_enrich])
        for r, summary in zip(to_enrich, summaries):
            r["website_summary"] = summary
        logger.info("search_companies: firecrawl attempted for %s websites", len(to_enrich))

    logger.info("search_companies: done total=%s", len(results))
    return results


def _domain(url: str | None) -> str:
    if not url:
        return ""
    url = url.removeprefix("https://").removeprefix("http://").removeprefix("www.")
    return url.split("/")[0].lower()
