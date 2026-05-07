import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r'(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w.+-])', re.IGNORECASE)
PHONE_RE = re.compile(r'(?:(?:\+7|8)[\s\-()]*\d(?:[\s\-()]*\d){9,10})')


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = ' '.join(value.split())
    return normalized or None


def _first_match(pattern: re.Pattern[str], value: str) -> str | None:
    match = pattern.search(value)
    return _clean_text(match.group(1) if match.lastindex else match.group(0)) if match else None


def _extract_phone(value: str) -> str | None:
    match = PHONE_RE.search(value)
    if not match:
        return None
    candidate = match.group(0)
    digits = re.sub(r'\D', '', candidate)
    if not (digits.startswith('7') or digits.startswith('8')):
        return None
    if len(digits) not in (11,):
        return None
    return _clean_text(candidate)


def _extract_schema_org(soup: BeautifulSoup) -> dict | None:
    for script in soup.find_all('script', attrs={'type': re.compile(r'ld\+json', re.IGNORECASE)}):
        raw = script.string or script.get_text() or ''
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    return item
    return None


def _extract_address(soup: BeautifulSoup, schema_org: dict | None) -> str | None:
    if schema_org:
        address = schema_org.get('address')
        if isinstance(address, str):
            cleaned = _clean_text(address)
            if cleaned:
                return cleaned
        if isinstance(address, dict):
            parts = [
                address.get('streetAddress'),
                address.get('addressLocality'),
                address.get('addressRegion'),
                address.get('postalCode'),
                address.get('addressCountry'),
            ]
            joined = _clean_text(', '.join(str(part) for part in parts if part))
            if joined:
                return joined

    address_tag = soup.find('address')
    if address_tag:
        return _clean_text(address_tag.get_text(' ', strip=True))
    return None


def _has_contact_form(soup: BeautifulSoup) -> bool:
    for form in soup.find_all('form'):
        action_parts = [
            form.get('action') or '',
            form.get('id') or '',
            ' '.join(form.get('class', [])),
        ]
        action = ' '.join(action_parts).lower()
        if any(token in action for token in ('contact', 'form', 'zayavka')):
            return True

        for input_tag in form.find_all(['input', 'textarea', 'select']):
            field = ' '.join(
                [
                    input_tag.get('type') or '',
                    input_tag.get('name') or '',
                    input_tag.get('id') or '',
                    input_tag.get('placeholder') or '',
                ]
            ).lower()
            if any(token in field for token in ('email', 'mail', 'phone', 'tel', 'телефон')):
                return True
    return False


def _extract_social_links(soup: BeautifulSoup, base_url: str) -> dict[str, str | None]:
    links = {
        'vk': None,
        'telegram': None,
        'whatsapp': None,
        'instagram': None,
    }

    for anchor in soup.find_all('a', href=True):
        href = (anchor.get('href') or '').strip()
        if not href:
            continue
        absolute = urljoin(base_url, href)
        lower = absolute.lower()

        if links['vk'] is None and 'vk.com' in lower:
            links['vk'] = absolute
        if links['telegram'] is None and 't.me' in lower:
            links['telegram'] = absolute
        if links['whatsapp'] is None and ('wa.me' in lower or 'whatsapp.com' in lower):
            links['whatsapp'] = absolute
        if links['instagram'] is None and 'instagram.com' in lower:
            links['instagram'] = absolute

    return links


def _extract_meta_description(soup: BeautifulSoup) -> str | None:
    tag = soup.find('meta', attrs={'name': re.compile(r'^description$', re.IGNORECASE)})
    if tag and tag.get('content'):
        return _clean_text(tag.get('content'))
    return None


def extract_from_html(html: str, url: str) -> dict:
    soup = BeautifulSoup(html or '', 'html.parser')

    for tag in soup(['script', 'style', 'noscript']):
        tag.extract()

    visible_text = _clean_text(soup.get_text(' ', strip=True)) or ''
    schema_org = _extract_schema_org(BeautifulSoup(html or '', 'html.parser'))

    title_tag = BeautifulSoup(html or '', 'html.parser').title
    title = _clean_text(title_tag.get_text(strip=True)) if title_tag else None

    h1_tag = soup.find('h1')
    h1 = _clean_text(h1_tag.get_text(' ', strip=True)) if h1_tag else None
    h2s = [_clean_text(tag.get_text(' ', strip=True)) for tag in soup.find_all('h2')]
    h3s = [_clean_text(tag.get_text(' ', strip=True)) for tag in soup.find_all('h3')]

    all_text = ' '.join(
        part
        for part in [
            html or '',
            visible_text,
        ]
        if part
    )

    email = _first_match(EMAIL_RE, all_text)
    phone = _extract_phone(all_text)

    return {
        'title': title,
        'h1': h1,
        'h2s': [value for value in h2s if value],
        'h3s': [value for value in h3s if value],
        'meta_description': _extract_meta_description(BeautifulSoup(html or '', 'html.parser')),
        'email': email,
        'phone': phone,
        'address': _extract_address(BeautifulSoup(html or '', 'html.parser'), schema_org),
        'has_contact_form': _has_contact_form(BeautifulSoup(html or '', 'html.parser')),
        'social_links': _extract_social_links(BeautifulSoup(html or '', 'html.parser'), url),
        'schema_org': schema_org,
        'visible_text_snippet': visible_text[:2000],
    }
