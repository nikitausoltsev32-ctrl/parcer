import httpx

from app.core.config import settings

_BASE = "https://serpapi.com/search"

_AGGREGATOR_DOMAINS = {
    "2gis.ru", "zoon.ru", "avito.ru", "yell.ru", "flamp.ru",
    "yandex.ru", "yandex.com", "vk.com", "ok.ru", "headhunter.ru",
    "hh.ru", "profi.ru", "tiu.ru", "tripadvisor.ru", "tripadvisor.com",
    "otzovik.com", "irecommend.ru", "turbopages.org", "yelp.com",
    "google.com", "maps.google.com",
}

_AGGREGATOR_WORDS = {"рейтинг", "топ", "лучшие", "лучших", "обзор", "каталог", "список"}


def _domain_from_url(url: str | None) -> str:
    if not url:
        return ""
    url = url.removeprefix("https://").removeprefix("http://").removeprefix("www.")
    return url.split("/")[0].lower()


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
    for item in data.get("local_results", [])[:limit]:
        phone = None
        if isinstance(item.get("phone"), str):
            phone = item["phone"]
        results.append({
            "name": item.get("title", ""),
            "website": item.get("website"),
            "email": None,
            "phone": phone,
            "city": city,
            "industry": item.get("type"),
            "address": item.get("address"),
            "source": "serp_maps",
        })

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
        "num": min(limit, 20),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []

    # knowledge_graph — карточка конкретной компании
    kg = data.get("knowledge_graph", {})
    if kg.get("title") and (kg.get("phone") or kg.get("website")):
        results.append({
            "name": kg.get("title", ""),
            "website": kg.get("website"),
            "email": None,
            "phone": kg.get("phone"),
            "city": city,
            "industry": kg.get("type"),
            "address": kg.get("address"),
            "source": "serp_google",
        })

    # local_results — встроенный локальный блок (обычно 3 компании)
    for item in data.get("local_results", {}).get("places", [])[:limit]:
        results.append({
            "name": item.get("title", ""),
            "website": item.get("links", {}).get("website"),
            "email": None,
            "phone": item.get("phone"),
            "city": city,
            "industry": item.get("type"),
            "address": item.get("address"),
            "source": "serp_google",
        })

    # organic_results — только реальные сайты компаний
    for item in data.get("organic_results", [])[:limit]:
        link = item.get("link", "")
        title = item.get("title", "")
        domain = _domain_from_url(link)
        if domain in _AGGREGATOR_DOMAINS:
            continue
        if any(w in title.lower() for w in _AGGREGATOR_WORDS):
            continue
        results.append({
            "name": title,
            "website": link if link.startswith("http") else None,
            "email": None,
            "phone": None,
            "city": city,
            "industry": None,
            "address": None,
            "source": "serp_google",
        })

    return results[:limit]
