import asyncio

from app.services.search.firecrawl import enrich_website
from app.services.search.serp import search_serp
from app.services.search.twogis import search_twogis


async def search_companies(query: str, city: str | None = None, limit: int = 20) -> list[dict]:
    """Ищет компании: сначала 2ГИС, дополняет SerpAPI до нужного количества."""
    results = await search_twogis(query, city, limit)

    if len(results) < limit:
        serp = await search_serp(query, city, limit - len(results))
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

    return results


def _domain(url: str | None) -> str:
    if not url:
        return ""
    url = url.removeprefix("https://").removeprefix("http://").removeprefix("www.")
    return url.split("/")[0].lower()
