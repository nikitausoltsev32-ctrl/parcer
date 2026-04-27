import httpx

from app.core.config import settings

_BASE = "https://api.firecrawl.dev/v1"


async def enrich_website(url: str) -> str | None:
    """Скрапит сайт и возвращает краткое текстовое описание (до 500 символов)."""
    if not settings.firecrawl_api_key or not url:
        return None

    headers = {"Authorization": f"Bearer {settings.firecrawl_api_key}"}
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
        "maxLength": 1000,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{_BASE}/scrape", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        text = data.get("data", {}).get("markdown", "")
        return text[:500].strip() if text else None
    except Exception:
        return None
