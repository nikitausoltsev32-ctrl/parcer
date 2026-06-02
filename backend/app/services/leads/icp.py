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


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(term in folded for term in terms)


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


_MARBLE_MARKERS = (
    "мрамор",
    "marble",
    "крошк",
    "amp-minerals",
    "карбонат кальция",
    "кальцит",
    "минеральн",
)

_MARBLE_PRODUCTS = [
    "мраморная крошка",
    "минеральные наполнители",
    "карбонат кальция",
    "декоративные минеральные материалы",
]

_MARBLE_BUYERS = [
    "производители ЖБИ",
    "производители тротуарной плитки",
    "производители декоративного бетона",
    "производители сухих строительных смесей",
    "производители штукатурок и фасадных материалов",
    "производители искусственного камня и терраццо",
    "ландшафтные и благоустроительные компании",
]

_MARBLE_USE_CASES = [
    "заполнитель для бетона",
    "декоративная отделка бетона",
    "тротуарная плитка",
    "фасадные штукатурки",
    "сухие строительные смеси",
    "ландшафтное благоустройство",
]

_MARBLE_POSITIVE = [
    "жби",
    "бетон",
    "тротуарная плитка",
    "декоративный бетон",
    "сухие смеси",
    "штукатурка",
    "фасад",
    "терраццо",
    "искусственный камень",
    "благоустройство",
    "ландшафт",
    "строительные смеси",
    "производство плитки",
]

_MARBLE_NEGATIVE = [
    "удобр",
    "агрохим",
    "npk",
    "сульфат калия",
    "аммиачная селитра",
    "почвосмесь",
    "грунт для растений",
    "семена",
    "пестиц",
    "фунгиц",
    "гербиц",
    "урожай",
    "кормовая добавка",
]

_MARBLE_EXCLUDED = [
    "минеральные удобрения",
    "агрохимия",
    "садовые и сельскохозяйственные товары",
    "семена и почвенные смеси",
    "корма и ветеринарные добавки",
]


def build_icp_profile(
    business_profile: dict[str, Any] | None,
    *,
    query: str,
    city: str | None = None,
) -> ICPProfile:
    bp = dict(business_profile or {})
    stored = bp.get("icp") if isinstance(bp.get("icp"), dict) else {}
    text = " ".join(
        _clean(part)
        for part in [
            bp.get("business"),
            bp.get("offer"),
            bp.get("website"),
            bp.get("website_url"),
            query,
            city,
            stored.get("seller_summary"),
            " ".join(_clean_list(stored.get("products"))),
        ]
        if part
    )

    products = _clean_list(stored.get("products"))
    buyer_segments = _clean_list(stored.get("buyer_segments"))
    use_cases = _clean_list(stored.get("use_cases"))
    positive_keywords = _clean_list(stored.get("positive_keywords"))
    negative_keywords = _clean_list(stored.get("negative_keywords"))
    excluded_industries = _clean_list(stored.get("excluded_industries"))

    if _contains_any(text, _MARBLE_MARKERS):
        products = _merge(products, _MARBLE_PRODUCTS)
        buyer_segments = _merge(buyer_segments, _MARBLE_BUYERS)
        use_cases = _merge(use_cases, _MARBLE_USE_CASES)
        positive_keywords = _merge(positive_keywords, _MARBLE_POSITIVE)
        negative_keywords = _merge(negative_keywords, _MARBLE_NEGATIVE)
        excluded_industries = _merge(excluded_industries, _MARBLE_EXCLUDED)

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


def _merge(left: list[str], right: list[str]) -> list[str]:
    return _dedupe([*left, *right])


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

