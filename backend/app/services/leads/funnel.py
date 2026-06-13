from __future__ import annotations

from dataclasses import dataclass

# Role mailboxes — present on most sites, but not a person you can call by name.
GENERIC_EMAIL_LOCALPARTS = frozenset(
    {
        "info", "mail", "office", "sales", "support", "admin", "contact",
        "hello", "zakaz", "shop", "order", "client", "clients", "manager",
        "reception", "secretary", "post", "noreply", "no-reply", "help",
        "service", "team", "welcome",
    }
)


def is_generic_email(email: str | None) -> bool:
    if not email or "@" not in email:
        return False
    local = email.split("@", 1)[0].strip().lower()
    return local in GENERIC_EMAIL_LOCALPARTS


def has_any_channel(lead: dict) -> bool:
    return bool(
        lead.get("email")
        or lead.get("phone")
        or lead.get("telegram")
        or lead.get("whatsapp")
        or lead.get("has_contact_form")
    )
