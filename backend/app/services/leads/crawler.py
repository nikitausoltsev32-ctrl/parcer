"""Step 6 — Crawler. Fetch HTML pages for a domain. httpx primary, Firecrawl fallback."""
from __future__ import annotations

import asyncio
import random
from urllib.parse import unquote, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.leads.policy import page_limit_for_plan

_PRIORITY_PATHS = [
    "/", "/contacts", "/kontakty", "/contact", "/kontakt",
    "/about", "/o-kompanii", "/o-nas",
    "/services", "/uslugi",
    "/price", "/prices", "/stoimost", "/portfolio",
]

_SKIP_PATHS = [
    "/blog", "/news", "/novosti", "/privacy", "/politika",
    "/terms", "/cart", "/login", "/register", "/cabinet",
]

_CONTACT_LINK_TOKENS = (
    "contact", "contacts", "kontakt", "kontakty", "svyaz", "feedback",
    "контакт", "контакты", "связь",
)

# Pool of real Chrome/Firefox UAs across Windows, Mac, Linux
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/110.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def _page_limit(plan: str) -> int:
    return page_limit_for_plan(plan)


def _browser_headers() -> dict[str, str]:
    ua = random.choice(_USER_AGENTS)
    is_firefox = "Firefox" in ua
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        if is_firefox
        else "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }


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


def _extract_contact_links(html: str, base_url: str, limit: int = 3) -> list[str]:
    parts = urlsplit(base_url)
    root_host = parts.netloc.lower()
    links: list[str] = []
    seen: set[str] = set()
    soup = BeautifulSoup(html or "", "html.parser")

    for anchor in soup.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        absolute = urljoin(base_url, href)
        parsed = urlsplit(absolute)
        if parsed.netloc.lower() != root_host:
            continue

        path = unquote(parsed.path or "").lower()
        text = (anchor.get_text(" ", strip=True) or "").lower()
        haystack = f"{path} {text}"
        if not any(token in haystack for token in _CONTACT_LINK_TOKENS):
            continue
        if any(skip in path for skip in _SKIP_PATHS):
            continue

        normalized = absolute.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        links.append(normalized)
        if len(links) >= limit:
            break

    return links


async def _fetch_one(client: httpx.AsyncClient, url: str, timeout: float = 15.0) -> str | None:
    try:
        resp = await client.get(url, timeout=timeout, follow_redirects=True)
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            return resp.text
    except Exception:
        pass
    return None


async def crawl_website(website: str, plan: str = "trial", *, fast_mode: bool = False) -> list[dict]:
    """Returns list of {url, html} dicts for successfully fetched pages."""
    limit = min(_page_limit(plan), 2) if fast_mode else _page_limit(plan)
    timeout = 8.0 if fast_mode else 15.0
    delay_range = (0.2, 0.5) if fast_mode else (0.8, 2.0)
    urls = _candidate_urls(website, limit)
    pages: list[dict] = []

    async with httpx.AsyncClient(headers=_browser_headers(), max_redirects=3) as client:
        index = 0
        while index < len(urls):
            url = urls[index]
            index += 1
            if len(pages) >= limit:
                break
            html = await _fetch_one(client, url, timeout=timeout)
            if html:
                pages.append({"url": url, "html": html})
                for discovered in reversed(_extract_contact_links(html, url)):
                    if discovered not in urls:
                        urls.insert(index, discovered)
            await asyncio.sleep(random.uniform(*delay_range))

    # Firecrawl fallback: full-content scrape when httpx got nothing
    if not pages and settings.firecrawl_api_key:
        from app.services.search.firecrawl import crawl_pages_full
        pages = await crawl_pages_full(website, limit)

    return pages
