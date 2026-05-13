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


async def crawl_pages_full(url: str, limit: int = 3) -> list[dict]:
    """Scrape up to `limit` pages via Firecrawl, return [{url, html}] compatible with crawler pipeline."""
    if not url or not settings.firecrawl_api_key:
        return []

    headers = {"Authorization": f"Bearer {settings.firecrawl_api_key}"}
    pages: list[dict] = []

    # Always scrape root page
    urls_to_scrape = [url]
    # Add a couple of priority paths to get contacts/about
    from urllib.parse import urljoin, urlsplit
    parts = urlsplit(url if "://" in url else f"https://{url}")
    root = f"{parts.scheme}://{parts.netloc}"
    for path in ("/contacts", "/kontakty", "/about", "/o-kompanii", "/o-nas"):
        if len(urls_to_scrape) >= limit:
            break
        urls_to_scrape.append(urljoin(root, path))

    async with httpx.AsyncClient(timeout=30) as client:
        for page_url in urls_to_scrape[:limit]:
            try:
                resp = await client.post(
                    f"{_BASE}/scrape",
                    json={"url": page_url, "formats": ["markdown"], "onlyMainContent": True},
                    headers=headers,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                markdown = data.get("data", {}).get("markdown", "") or ""
                if markdown.strip():
                    # Wrap markdown as pseudo-HTML so html_extraction pipeline can process it
                    html = f"<body><pre>{markdown}</pre></body>"
                    pages.append({"url": page_url, "html": html, "from_firecrawl": True})
            except Exception as exc:
                logger.warning("firecrawl crawl_pages_full: failed for %s: %s", page_url, exc)

    logger.info("firecrawl: got %d pages for %s", len(pages), url)
    return pages


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
