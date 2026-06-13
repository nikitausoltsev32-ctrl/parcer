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


SERP_SOURCES = frozenset({"serp_maps", "serp_google"})
LLM_SOURCES = frozenset({"perplexity", "llm_search"})


def _serp_count(stats: FunnelStats) -> int:
    return sum(count for src, count in stats.source_counts.items() if src in SERP_SOURCES)


def _llm_count(stats: FunnelStats) -> int:
    return sum(count for src, count in stats.source_counts.items() if src in LLM_SOURCES)


def funnel_to_csv_rows(stats_list: list[FunnelStats]) -> list[dict]:
    rows: list[dict] = []
    for stats in stats_list:
        rows.append(
            {
                "niche": stats.niche,
                "city": stats.city or "",
                "urls_found": stats.urls_found,
                "urls_after_filter": stats.urls_after_filter,
                "urls_crawled": stats.urls_crawled,
                "pages_crawled": stats.pages_crawled,
                "serp_prescreened_out": stats.serp_prescreened_out,
                "icp_rejected_out": stats.icp_rejected_out,
                "history_skipped_out": stats.history_skipped_out,
                "saved": stats.saved,
                "with_any_channel": stats.with_any_channel,
                "with_email": stats.with_email,
                "with_personal_email": stats.with_personal_email,
                "score_70_plus": stats.score_70_plus,
                "serp_count": _serp_count(stats),
                "llm_count": _llm_count(stats),
                "source_counts": ", ".join(f"{k}={v}" for k, v in sorted(stats.source_counts.items())),
            }
        )
    return rows


def format_funnel_table(stats_list: list[FunnelStats]) -> str:
    header = (
        f"{'niche':<28} {'city':<16} {'found':>6} {'filter':>6} {'crawl':>6} "
        f"{'saved':>6} {'channel':>8} {'email':>6} {'personal':>9} {'score70':>8} "
        f"{'serp':>5} {'llm':>5}"
    )
    lines = [header, "-" * len(header)]
    for stats in stats_list:
        lines.append(
            f"{stats.niche[:27]:<28} {(stats.city or '')[:15]:<16} "
            f"{stats.urls_found:>6} {stats.urls_after_filter:>6} {stats.urls_crawled:>6} "
            f"{stats.saved:>6} {stats.with_any_channel:>8} {stats.with_email:>6} "
            f"{stats.with_personal_email:>9} {stats.score_70_plus:>8} "
            f"{_serp_count(stats):>5} {_llm_count(stats):>5}"
        )
    return "\n".join(lines)
