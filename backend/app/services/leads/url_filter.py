import re
from urllib.parse import unquote, urlsplit

BLOCKED_DOMAINS = {
    'avito.ru',
    'hh.ru',
    'vc.ru',
    'habr.com',
    '2gis.ru',
    'wildberries.ru',
    'zoon.ru',
    'otzovik.com',
    'prodoctorov.ru',
    'yell.ru',
    'flamp.ru',
    'ozon.ru',
    'market.yandex.ru',
    'irecommend.ru',
}

BLOCKED_PATH_PARTS = (
    '/blog/',
    '/news/',
    '/tag/',
    '/category/',
    '/vakansii/',
    '/jobs/',
    '/privacy/',
    '/terms/',
)

BLOCKED_SEGMENT_PATTERNS = (
    'топ-',
    'рейтинг',
    'лучшие',
    'список',
    'как-выбрать',
)


def _split_url(url: str):
    parsed = urlsplit(url)
    if parsed.netloc:
        return parsed
    return urlsplit(f'https://{url}')


def _normalized_domain(url: str) -> str:
    parsed = _split_url(url)
    host = parsed.netloc.lower()
    if '@' in host:
        host = host.rsplit('@', 1)[-1]
    if ':' in host:
        host = host.split(':', 1)[0]
    return host.removeprefix('www.')


def is_blocked_domain(url: str) -> bool:
    domain = _normalized_domain(url)
    if not domain:
        return True
    return any(domain == blocked or domain.endswith(f'.{blocked}') for blocked in BLOCKED_DOMAINS)


def is_blocked_path(url: str) -> bool:
    parsed = _split_url(url)
    path = unquote(parsed.path or '').lower()
    query = (parsed.query or '').lower()

    if any(part in path for part in BLOCKED_PATH_PARTS):
        return True
    if any(path == part.removesuffix('/') for part in BLOCKED_PATH_PARTS):
        return True
    if 'utm_' in query:
        return True
    if re.search(r'/page/\d+(?:/|$)', path):
        return True
    if path.endswith('.pdf'):
        return True

    segments = [segment for segment in path.split('/') if segment]
    return any(pattern in segment for segment in segments for pattern in BLOCKED_SEGMENT_PATTERNS)


def filter_urls(urls: list[str]) -> list[str]:
    seen_domains: set[str] = set()
    filtered: list[str] = []

    for url in urls:
        if is_blocked_domain(url) or is_blocked_path(url):
            continue

        domain = _normalized_domain(url)
        if not domain or domain in seen_domains:
            continue

        seen_domains.add(domain)
        filtered.append(url)

    return filtered
