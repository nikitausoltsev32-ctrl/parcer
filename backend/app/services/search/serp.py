import httpx

from app.core.config import settings

_BASE = "https://serpapi.com/search"


async def search_serp(query: str, city: str | None = None, limit: int = 20) -> list[dict]:
    if not settings.serpapi_key:
        return []

    q = f"{query} {city}".strip() if city else query
    params = {
        "q": q,
        "api_key": settings.serpapi_key,
        "engine": "google",
        "num": min(limit, 20),
        "hl": "ru",
        "gl": "ru",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("organic_results", [])[:limit]:
        results.append({
            "name": item.get("title", ""),
            "website": item.get("link"),
            "email": None,
            "phone": None,
            "city": city,
            "industry": None,
            "address": None,
            "source": "serp",
        })

    return results
