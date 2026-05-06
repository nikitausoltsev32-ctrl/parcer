import logging
import re

import httpx

from app.core.config import settings

_BASE = "https://api.firecrawl.dev/v1"
logger = logging.getLogger(__name__)
_MARKDOWN_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]+\)")
_MARKDOWN_TOKEN_RE = re.compile(r"[*_`>#]+")
_NAV_LABELS = {
    "about",
    "blog",
    "contact",
    "contacts",
    "facebook",
    "home",
    "instagram",
    "menu",
    "portfolio",
    "privacy",
    "services",
    "telegram",
    "terms",
    "vk",
    "whatsapp",
}


def _scrape_payload(url: str) -> dict:
    return {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }


def _markdown_to_summary(markdown: str, limit: int = 500) -> str | None:
    if not markdown:
        return None

    parts: list[str] = []
    size = 0
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("```", "|")):
            continue

        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+]\s+", "", line)
        line = _MARKDOWN_LINK_RE.sub(r"\1", line)
        line = _MARKDOWN_TOKEN_RE.sub("", line)
        line = re.sub(r"\s+", " ", line).strip(" -:;")

        if not line:
            continue
        if line.lower() in _NAV_LABELS:
            continue
        if line.startswith(("http://", "https://", "mailto:", "tel:")):
            continue

        sentence = line.rstrip(".!?")
        parts.append(sentence)
        size += len(sentence) + 2
        if size >= limit:
            break

    text = ". ".join(parts).strip()
    if not text:
        return None
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(".,;:")
    if not text.endswith((".", "!", "?")):
        text += "."
    return text


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
        return _markdown_to_summary(text)
    except Exception as exc:
        logger.warning("firecrawl: failed for %s: %s", url, exc)
        return None
