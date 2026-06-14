from urllib.parse import unquote, urlsplit

import httpx

from app.core.config import settings
from app.services.leads.url_filter import BLOCKED_DOMAINS as _AGGREGATOR_DOMAINS

_BASE = "https://serpapi.com/search"

_AGGREGATOR_WORDS = {
    "рейтинг", "топ", "лучшие", "лучших", "обзор", "каталог", "список",
    "подборка", "сравнение", "отзывы", "как выбрать", "статья",
    "rating", "top", "best", "review", "reviews", "directory", "catalog", "list",
    "guide", "article", "comparison",
}

_BLOCKED_ORGANIC_PATH_PARTS = (
    "/blog",
    "/news",
    "/novosti",
    "/article",
    "/articles",
    "/stati",
    "/statya",
    "/journal",
    "/media",
    "/rating",
    "/ratings",
    "/reviews",
    "/review",
    "/top",
    "/guide",
    "/how-to",
)


def _domain_from_url(url: str | None) -> str:
    if not url:
        return ""
    url = url.removeprefix("https://").removeprefix("http://").removeprefix("www.")
    return url.split("/")[0].lower()


def _is_aggregator_domain(domain: str) -> bool:
    """Match the domain itself or any subdomain (e.g. ``ekb.docdoc.ru``)."""
    if not domain:
        return False
    return any(domain == agg or domain.endswith("." + agg) for agg in _AGGREGATOR_DOMAINS)


def _summary_from_item(item: dict) -> str | None:
    for key in ("description", "snippet"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    return None


def _is_blocked_organic_result(link: str, title: str, snippet: str | None) -> bool:
    parsed = urlsplit(link)
    path = unquote(parsed.path or "").lower()
    if any(part in path for part in _BLOCKED_ORGANIC_PATH_PARTS):
        return True

    text = " ".join(part for part in [title, snippet or ""] if part).lower()
    return any(word in text for word in _AGGREGATOR_WORDS)


async def search_serp(query: str, city: str | None = None, limit: int = 20) -> list[dict]:
    if not settings.serpapi_key:
        return []

    q = f"{query} {city}".strip() if city else query
    params = {
        "q": q,
        "api_key": settings.serpapi_key,
        "engine": "google_maps",
        "type": "search",
        "hl": "ru",
        "gl": "ru",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for i, item in enumerate(data.get("local_results", [])[:limit]):
        phone = None
        if isinstance(item.get("phone"), str):
            phone = item["phone"]
        result = {
            "name": item.get("title", ""),
            "website": item.get("website"),
            "email": None,
            "phone": phone,
            "city": city,
            "industry": item.get("type"),
            "address": item.get("address"),
            "source": "serp_maps",
            "maps_rating": item.get("rating"),
            "maps_reviews_count": item.get("reviews"),
            "serp_position": item.get("position", i + 1),
        }
        summary = _summary_from_item(item)
        if summary:
            result["website_summary"] = summary
        results.append(result)

    return results


async def search_google(query: str, city: str | None = None, limit: int = 20) -> list[dict]:
    """Google Search (engine=google): knowledge_graph + local pack + filtered organic."""
    if not settings.serpapi_key:
        return []

    q = f"{query} {city}".strip() if city else query
    location = f"{city}, Russia" if city else "Russia"
    params = {
        "q": q,
        "api_key": settings.serpapi_key,
        "engine": "google",
        "gl": "ru",
        "hl": "ru",
        "location": location,
        "num": min(max(limit, 20), 30),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []

    # knowledge_graph — карточка конкретной компании
    kg = data.get("knowledge_graph", {})
    if kg.get("title") and (kg.get("phone") or kg.get("website")):
        result = {
            "name": kg.get("title", ""),
            "website": kg.get("website"),
            "email": None,
            "phone": kg.get("phone"),
            "city": city,
            "industry": kg.get("type"),
            "address": kg.get("address"),
            "source": "serp_google",
        }
        summary = _summary_from_item(kg)
        if summary:
            result["website_summary"] = summary
        results.append(result)

    # local_results — встроенный локальный блок (обычно 3 компании)
    for i, item in enumerate(data.get("local_results", {}).get("places", [])[:limit]):
        result = {
            "name": item.get("title", ""),
            "website": item.get("links", {}).get("website"),
            "email": None,
            "phone": item.get("phone"),
            "city": city,
            "industry": item.get("type"),
            "address": item.get("address"),
            "source": "serp_google",
            "maps_rating": item.get("rating"),
            "maps_reviews_count": item.get("reviews"),
            "serp_position": item.get("position", i + 1),
        }
        summary = _summary_from_item(item)
        if summary:
            result["website_summary"] = summary
        results.append(result)

    # organic_results — только реальные сайты компаний
    for item in data.get("organic_results", [])[:limit]:
        link = item.get("link", "")
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        domain = _domain_from_url(link)
        if _is_aggregator_domain(domain):
            continue
        if _is_blocked_organic_result(link, title, snippet):
            continue
        result = {
            "name": title,
            "website": link if link.startswith("http") else None,
            "email": None,
            "phone": None,
            "city": city,
            "industry": None,
            "address": None,
            "source": "serp_google",
        }
        summary = _summary_from_item(item)
        if summary:
            result["website_summary"] = summary
        results.append(result)

    return results[:limit]
