"""Step 6 — Crawler. Fetch HTML pages for a domain. httpx primary, Firecrawl fallback."""
from __future__ import annotations

import asyncio
import random
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.config import settings

_PRIORITY_PATHS = [
    "/", "/about", "/o-kompanii", "/o-nas",
    "/services", "/uslugi", "/contacts", "/kontakty",
    "/price", "/prices", "/stoimost", "/portfolio",
]

_SKIP_PATHS = [
    "/blog", "/news", "/novosti", "/privacy", "/politika",
    "/terms", "/cart", "/login", "/register", "/cabinet",
]

_HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

_PLAN_PAGE_LIMITS = {"free": 2, "starter": 3, "pro": 5, "agency": 7, "max": 10, "trial": 2}


def _page_limit(plan: str) -> int:
    return _PLAN_PAGE_LIMITS.get(plan, 2)


def _candidate_urls(base: str, limit: int) -> list[str]:
    parts = urlsplit(base)
    root = f"{parts.scheme}://{parts.netloc}"
    urls = []
    seen = set()
    for path in _PRIORITY_PATHS:
        url = urljoin(root, path)
        if url not in seen:
            seen.add(url)
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls


async def _fetch_one(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        resp = await client.get(url, timeout=15, follow_redirects=True)
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            return resp.text
    except Exception:
        pass
    return None


async def crawl_website(website: str, plan: str = "trial") -> list[dict]:
    """Returns list of {url, html} dicts for successfully fetched pages."""
    limit = _page_limit(plan)
    urls = _candidate_urls(website, limit)
    pages: list[dict] = []

    async with httpx.AsyncClient(headers=_HEADERS, max_redirects=3) as client:
        for url in urls:
            if len(pages) >= limit:
                break
            html = await _fetch_one(client, url)
            if html:
                pages.append({"url": url, "html": html})
            delay = random.uniform(1.0, 3.0)
            await asyncio.sleep(delay)

    # Firecrawl fallback if we got nothing
    if not pages and settings.firecrawl_api_key:
        from app.services.search.firecrawl import enrich_website
        summary = await enrich_website(website)
        if summary:
            pages.append({"url": website, "html": f"<p>{summary}</p>", "from_firecrawl": True})

    return pages
