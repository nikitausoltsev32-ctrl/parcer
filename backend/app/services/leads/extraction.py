from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

_EMAIL_RE = re.compile(r"(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w.+-])", re.IGNORECASE)
_PHONE_RE = re.compile(r"(\+?7|8)?[\s(.-]*\d{3}[\s). -]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}")
_INN_RE = re.compile(r"\b(\d{10}|\d{12})\b")
_TG_RE = re.compile(r"https?://t\.me/[A-Za-z0-9_]{4,}", re.IGNORECASE)
_WA_RE = re.compile(r"https?://(?:wa\.me|api\.whatsapp\.com/send\?phone=)[^\s)]+", re.IGNORECASE)
_VK_RE = re.compile(r"https?://vk\.com/[A-Za-z0-9_.-]+", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractedPublicContacts:
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None
    whatsapp: str | None = None
    vk: str | None = None


def normalize_website(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlsplit(raw)
    if not parsed.netloc:
        return None
    path = parsed.path.rstrip("/") or ""
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), path, "", ""))


def normalize_domain(value: str | None) -> str:
    website = normalize_website(value)
    if not website:
        return ""
    host = urlsplit(website).netloc.lower()
    return host.removeprefix("www.")


def normalize_phone_e164(raw: str | None) -> str | None:
    if not raw:
        return None

    cleaned = re.sub(r"[\s().-]+", "", raw.strip())
    if not cleaned:
        return None

    digits = re.sub(r"\D", "", cleaned)
    if len(digits) < 11:
        return None
    if cleaned.startswith("+7") and len(digits) == 11:
        return f"+{digits}"
    if digits.startswith("8") and len(digits) == 11:
        return f"+7{digits[1:]}"
    if digits.startswith("7") and len(digits) == 11:
        return f"+{digits}"
    return None


def extract_inn(text: str | None) -> str | None:
    source = text or ""
    for match in _INN_RE.finditer(source):
        context = source[max(0, match.start() - 24) : match.end() + 24].casefold()
        if "инн" in context or "inn" in context:
            return match.group(1)
    return None


def extract_all_emails(text: str | None) -> list[str]:
    source = text or ""
    emails: list[str] = []
    seen: set[str] = set()
    for match in _EMAIL_RE.finditer(source):
        email = match.group(1).lower()
        if email in seen:
            continue
        seen.add(email)
        emails.append(email)
    return emails


def extract_public_contacts(text: str | None) -> ExtractedPublicContacts:
    source = text or ""
    return ExtractedPublicContacts(
        email=_first(_EMAIL_RE, source),
        phone=_first(_PHONE_RE, source),
        telegram=_first(_TG_RE, source),
        whatsapp=_first(_WA_RE, source),
        vk=_first(_VK_RE, source),
    )


def _first(pattern: re.Pattern[str], value: str) -> str | None:
    match = pattern.search(value)
    return match.group(0).strip(".,; ") if match else None
