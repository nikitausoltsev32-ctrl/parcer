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


@dataclass(frozen=True)
class FunnelStats:
    niche: str
    city: str | None
    urls_found: int
    urls_after_filter: int
    urls_crawled: int
    pages_crawled: int
    serp_prescreened_out: int
    icp_rejected_out: int
    history_skipped_out: int
    saved: int
    with_any_channel: int
    with_email: int
    with_personal_email: int
    score_70_plus: int
    source_counts: dict[str, int]


def compute_funnel(
    niche: str,
    city: str | None,
    *,
    urls_found: int,
    urls_after_filter: int,
    urls_crawled: int,
    pages_crawled: int,
    serp_prescreened_out: int,
    icp_rejected_out: int,
    history_skipped_out: int,
    leads: list[dict],
) -> FunnelStats:
    source_counts: dict[str, int] = {}
    with_any = with_email = with_personal = score_70 = 0
    for lead in leads:
        source = lead.get("source") or "unknown"
        source_counts[source] = source_counts.get(source, 0) + 1
        if has_any_channel(lead):
            with_any += 1
        email = lead.get("email")
        if email:
            with_email += 1
            if not is_generic_email(email):
                with_personal += 1
        score = lead.get("score")
        if isinstance(score, (int, float)) and score >= 70:
            score_70 += 1
    return FunnelStats(
        niche=niche,
        city=city,
        urls_found=urls_found,
        urls_after_filter=urls_after_filter,
        urls_crawled=urls_crawled,
        pages_crawled=pages_crawled,
        serp_prescreened_out=serp_prescreened_out,
        icp_rejected_out=icp_rejected_out,
        history_skipped_out=history_skipped_out,
        saved=len(leads),
        with_any_channel=with_any,
        with_email=with_email,
        with_personal_email=with_personal,
        score_70_plus=score_70,
        source_counts=source_counts,
    )
