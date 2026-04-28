import logging

import httpx

from app.core.config import settings

_BASE = "https://api.firecrawl.dev/v1"
logger = logging.getLogger(__name__)


def _scrape_payload(url: str) -> dict:
    return {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }


async def enrich_website(url: str) -> str | None:
    """Скрапит сайт и возвращает краткое текстовое описание (до 500 символов)."""
    if not url:
        logger.info("firecrawl: skipped empty url")
        return None
    if not settings.firecrawl_api_key:
        logger.info("firecrawl: skipped %s because FIRECRAWL_API_KEY is empty", url)
        return None

    headers = {"Authorization": f"Bearer {settings.firecrawl_api_key}"}
    payload = _scrape_payload(url)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{_BASE}/scrape", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        text = data.get("data", {}).get("markdown", "")
        logger.info("firecrawl: scraped %s chars from %s", len(text), url)
        return text[:500].strip() if text else None
    except Exception as exc:
        logger.warning("firecrawl: failed for %s: %s", url, exc)
        return None
