import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.hunter.io/v2"


async def find_emails_by_domain(domain: str) -> list[dict]:
    """Возвращает список email-адресов для домена через Hunter.io.

    Каждый элемент: {"email": str, "type": "personal"|"generic", "confidence": int, "first_name": str, "last_name": str}
    """
    if not settings.hunter_api_key:
        return []

    domain = _clean_domain(domain)
    if not domain:
        return []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{_BASE}/domain-search",
                params={"domain": domain, "api_key": settings.hunter_api_key, "limit": 10},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("hunter: domain-search failed for %s: %s", domain, exc)
        return []

    emails = []
    for entry in data.get("data", {}).get("emails", []):
        if entry.get("value"):
            emails.append({
                "email": entry["value"],
                "type": entry.get("type", "generic"),
                "confidence": entry.get("confidence", 0),
                "first_name": entry.get("first_name") or "",
                "last_name": entry.get("last_name") or "",
            })

    # Сортируем: personal выше generic, потом по уверенности
    emails.sort(key=lambda e: (0 if e["type"] == "personal" else 1, -e["confidence"]))
    logger.info("hunter: found %s emails for %s", len(emails), domain)
    return emails


async def verify_email(email: str) -> dict:
    """Проверяет конкретный email. Возвращает {"result": "deliverable"|"undeliverable"|"risky", "score": int}."""
    if not settings.hunter_api_key:
        return {}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{_BASE}/email-verifier",
                params={"email": email, "api_key": settings.hunter_api_key},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("hunter: verify failed for %s: %s", email, exc)
        return {}

    d = data.get("data", {})
    return {"result": d.get("result", ""), "score": d.get("score", 0)}


def _clean_domain(url: str) -> str:
    url = url.removeprefix("https://").removeprefix("http://").removeprefix("www.")
    return url.split("/")[0].lower()
