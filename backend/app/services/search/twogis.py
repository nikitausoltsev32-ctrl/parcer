import httpx

from app.core.config import settings

_BASE = "https://catalog.api.2gis.com/3.0"


async def search_twogis(query: str, city: str | None = None, limit: int = 20) -> list[dict]:
    if not settings.twogis_api_key:
        return []

    q = f"{query} {city}".strip() if city else query
    params = {
        "q": q,
        "key": settings.twogis_api_key,
        "page_size": min(limit, 50),
        "fields": "items.point,items.address,items.contact_groups,items.rubrics,items.org",
        "locale": "ru_RU",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_BASE}/items", params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("result", {}).get("items", []):
        contacts = item.get("contact_groups", [{}])[0] if item.get("contact_groups") else {}
        emails = [c["value"] for c in contacts.get("contacts", []) if c.get("type") == "email"]
        phones = [c["value"] for c in contacts.get("contacts", []) if c.get("type") == "phone"]
        rubrics = [r.get("name", "") for r in item.get("rubrics", [])]

        results.append({
            "name": item.get("name", ""),
            "website": next(
                (c["value"] for c in contacts.get("contacts", []) if c.get("type") == "website"), None
            ),
            "email": emails[0] if emails else None,
            "phone": phones[0] if phones else None,
            "city": city,
            "industry": rubrics[0] if rubrics else None,
            "address": item.get("address_name"),
            "source": "2gis",
        })

    return results
