import re
from urllib.parse import unquote, urlsplit

# Canonical aggregator/marketplace/directory blocklist for the whole lead pipeline.
# search/serp.py and search/yandex.py import this set — keep it the single source of truth
# so the two layers never drift (that drift was how medical aggregators leaked into results).
BLOCKED_DOMAINS = {
    # Marketplaces / classifieds / media
    'avito.ru', 'ozon.ru', 'wildberries.ru', 'market.yandex.ru', 'tiu.ru',
    'vc.ru', 'habr.com', 'kp.ru',
    # Search engines / social / aggregated maps
    'yandex.ru', 'yandex.com', 'google.com', 'maps.google.com',
    '2gis.ru', '0gis.ru', 'vk.com', 'ok.ru', 'turbopages.org',
    # Job boards / freelance
    'hh.ru', 'headhunter.ru', 'profi.ru',
    # Reviews / directories / business catalogs
    'zoon.ru', 'yell.ru', 'flamp.ru', 'otzovik.com', 'irecommend.ru',
    'tripadvisor.ru', 'tripadvisor.com', 'yelp.com',
    'rusprofile.ru', 'list-org.com', 'orgpage.ru', 'spr.ru',
    'blizko.ru', 'gorko.ru', 'cataloxy.ru', 'vbk.ru',
    # Medical aggregators / booking
    'prodoctorov.ru', 'napopravku.ru', 'docdoc.ru', 'sberhealth.ru',
    '32top.ru', 'doctu.ru', 'emex.ru', 'medbooking.com', 'infodoctor.ru',
}

BLOCKED_PATH_PARTS = (
    '/blog/',
    '/news/',
    '/novosti/',
    '/article/',
    '/articles/',
    '/stati/',
    '/statya/',
    '/journal/',
    '/media/',
    '/rating/',
    '/ratings/',
    '/review/',
    '/reviews/',
    '/top/',
    '/guide/',
    '/how-to/',
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
    'подборка',
    'сравнение',
    'обзор',
    'статья',
    'article',
    'review',
    'rating',
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
