from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list | tuple | set):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean(value)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


@dataclass(frozen=True)
class ICPProfile:
    seller_summary: str
    products: list[str] = field(default_factory=list)
    buyer_segments: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    positive_keywords: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)
    excluded_industries: list[str] = field(default_factory=list)
    source: str = "generated"

    def to_dict(self) -> dict[str, Any]:
        return {
            "seller_summary": self.seller_summary,
            "products": self.products,
            "buyer_segments": self.buyer_segments,
            "use_cases": self.use_cases,
            "positive_keywords": self.positive_keywords,
            "negative_keywords": self.negative_keywords,
            "excluded_industries": self.excluded_industries,
            "source": self.source,
        }

    def compact(self) -> str:
        parts = [self.seller_summary]
        if self.products:
            parts.append("Products: " + ", ".join(self.products[:8]))
        if self.buyer_segments:
            parts.append("Buyer segments: " + ", ".join(self.buyer_segments[:10]))
        if self.use_cases:
            parts.append("Use cases: " + ", ".join(self.use_cases[:10]))
        if self.excluded_industries:
            parts.append("Exclude: " + ", ".join(self.excluded_industries[:10]))
        return "\n".join(part for part in parts if part)


@dataclass(frozen=True)
class QueryPlan:
    queries: list[str]
    negative_keywords: list[str] = field(default_factory=list)
    buyer_segments: list[str] = field(default_factory=list)
    excluded_industries: list[str] = field(default_factory=list)
    positive_keywords: list[str] = field(default_factory=list)
    rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "queries": self.queries,
            "negative_keywords": self.negative_keywords,
            "buyer_segments": self.buyer_segments,
            "excluded_industries": self.excluded_industries,
            "positive_keywords": self.positive_keywords,
            "rationale": self.rationale,
        }


class QueryList(list[str]):
    def __init__(self, values: list[str], query_plan: QueryPlan):
        super().__init__(values)
        self.query_plan = query_plan


def build_icp_profile(
    business_profile: dict[str, Any] | None,
    *,
    query: str,
    city: str | None = None,
) -> ICPProfile:
    bp = dict(business_profile or {})
    stored = bp.get("icp") if isinstance(bp.get("icp"), dict) else {}

    products = _clean_list(stored.get("products"))
    buyer_segments = _clean_list(stored.get("buyer_segments"))
    use_cases = _clean_list(stored.get("use_cases"))
    positive_keywords = _clean_list(stored.get("positive_keywords"))
    negative_keywords = _clean_list(stored.get("negative_keywords"))
    excluded_industries = _clean_list(stored.get("excluded_industries"))

    summary = _clean(stored.get("seller_summary")) or _clean(
        f"{bp.get('business', '')}. {bp.get('offer', '')}. Query: {query}."
    )
    if not summary:
        summary = query

    if not products:
        products = [_clean(bp.get("offer")) or query]
    if not buyer_segments:
        buyer_segments = [query]
    if not positive_keywords:
        positive_keywords = [query]

    return ICPProfile(
        seller_summary=summary,
        products=products[:12],
        buyer_segments=buyer_segments[:12],
        use_cases=use_cases[:12],
        positive_keywords=positive_keywords[:24],
        negative_keywords=negative_keywords[:24],
        excluded_industries=excluded_industries[:12],
        source="stored" if stored else "generated",
    )


def build_query_plan_from_queries(queries: list[str], icp: ICPProfile, rationale: str | None = None) -> QueryPlan:
    cleaned_queries = _dedupe([_clean(query) for query in queries if _clean(query)]) or icp.buyer_segments[:3]
    return QueryPlan(
        queries=cleaned_queries[:10],
        negative_keywords=icp.negative_keywords,
        buyer_segments=icp.buyer_segments,
        excluded_industries=icp.excluded_industries,
        positive_keywords=icp.positive_keywords,
        rationale=rationale,
    )


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean(value)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result

