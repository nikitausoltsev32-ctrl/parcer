import asyncio
import logging
from inspect import signature

from app.services.llm.routing import provider_has_key
from app.services.search.firecrawl import enrich_website
from app.services.search.llm_search import llm_search_companies
from app.services.search.perplexity_search import perplexity_search_companies
from app.services.search.serp import search_google, search_serp

logger = logging.getLogger(__name__)


async def search_companies(
    query: str,
    city: str | None = None,
    limit: int = 20,
    *,
    enrich: bool = True,
    niche: str | None = None,
    query_plan: dict | None = None,
) -> list[dict]:
    """Параллельный поиск: Google Maps + Google Search (SerpAPI) + LLM, затем Firecrawl."""
    logger.info("search_companies: start query=%r city=%r limit=%s", query, city, limit)

    capped_limit = max(1, min(limit, 50))
    fetch = min(max(capped_limit * 2, 8), 50)
    discovery = (
        _safe_perplexity(niche or query, city, min(fetch, 20), query_plan=query_plan)
        if provider_has_key("openrouter")
        else _safe_llm_search(niche or query, city, min(fetch, 20))
    )
    maps_results, google_results, llm_results = await asyncio.gather(
        _safe_serp(query, city, fetch),
        _safe_google(query, city, fetch),
        discovery,
    )
    logger.info(
        "search_companies: maps=%s google=%s llm=%s",
        len(maps_results), len(google_results), len(llm_results),
    )

    # Мёрджим: дедупликация по домену и имени
    seen_domains: set[str] = set()
    seen_names: set[str] = set()
    merged: list[dict] = []

    for item in maps_results + google_results + llm_results:
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
    results = merged[:capped_limit]

    # Firecrawl: обогащаем первые 5 у кого есть сайт
    to_enrich = [r for r in results if r.get("website") and not r.get("website_summary")][:5] if enrich else []
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


async def _safe_llm_search(niche: str, city: str | None, count: int) -> list[dict]:
    try:
        return await llm_search_companies(niche, city, count)
    except Exception as exc:
        logger.warning("search_companies: llm_search failed: %r", exc)
        return []


async def _safe_perplexity(niche: str, city: str | None, count: int, *, query_plan: dict | None = None) -> list[dict]:
    try:
        if "query_plan" not in signature(perplexity_search_companies).parameters:
            return await perplexity_search_companies(niche, city, count)
        return await perplexity_search_companies(niche, city, count, query_plan=query_plan)
    except Exception as exc:
        logger.warning("search_companies: perplexity failed: %r", exc)
        return []


def _domain(url: str | None) -> str:
    if not url:
        return ""
    url = url.removeprefix("https://").removeprefix("http://").removeprefix("www.")
    return url.split("/")[0].lower()
