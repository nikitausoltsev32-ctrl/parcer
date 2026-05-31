"""Lead-search tariff policy derived from CLAUDE.md."""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_PLAN = "trial"


@dataclass(frozen=True)
class LeadPlanPolicy:
    page_limit: int
    deep_ai_enabled: bool


_PLAN_POLICIES: dict[str, LeadPlanPolicy] = {
    "free": LeadPlanPolicy(page_limit=2, deep_ai_enabled=False),
    "starter": LeadPlanPolicy(page_limit=3, deep_ai_enabled=False),
    "pro": LeadPlanPolicy(page_limit=5, deep_ai_enabled=True),
    "agency": LeadPlanPolicy(page_limit=7, deep_ai_enabled=True),
    "max": LeadPlanPolicy(page_limit=10, deep_ai_enabled=True),
    "trial": LeadPlanPolicy(page_limit=2, deep_ai_enabled=False),
    # Temporary dev plan — no restrictions, remove before production
    "dev": LeadPlanPolicy(page_limit=10, deep_ai_enabled=True),
}


def normalize_plan(plan: str | None) -> str:
    normalized = (plan or DEFAULT_PLAN).strip().lower()
    return normalized or DEFAULT_PLAN


def get_lead_plan_policy(plan: str | None) -> LeadPlanPolicy:
    return _PLAN_POLICIES.get(normalize_plan(plan), _PLAN_POLICIES[DEFAULT_PLAN])


def page_limit_for_plan(plan: str | None) -> int:
    return get_lead_plan_policy(plan).page_limit


def deep_ai_allowed_for_plan(plan: str | None) -> bool:
    return get_lead_plan_policy(plan).deep_ai_enabled


def effective_search_limit(*, requested_limit: int, fast_mode: bool, leads_quota: int | None) -> int:
    capped_requested = max(1, min(int(requested_limit), 50))
    capped = capped_requested
    if leads_quota is None:
        return capped
    return max(0, min(capped, int(leads_quota)))
