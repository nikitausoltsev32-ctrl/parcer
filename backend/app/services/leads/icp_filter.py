from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.leads.icp import ICPProfile, QueryPlan

_GENERIC_WEB_NOISE_TERMS = {
    "article",
    "articles",
    "blog",
    "career",
    "careers",
    "job",
    "jobs",
    "news",
    "review",
    "reviews",
    "rating",
    "ratings",
    "top",
    "вакансии",
    "вакансия",
    "карьера",
    "новости",
    "новость",
    "статьи",
    "статья",
    "блог",
    "рейтинг",
    "топ",
    "отзывы",
    "отзыв",
}


@dataclass(frozen=True)
class ICPReject:
    reason: str
    matched_terms: list[str] = field(default_factory=list)
    evidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "matched_terms": self.matched_terms,
            "evidence": self.evidence,
        }


def candidate_text(raw: dict[str, Any], extracted: dict[str, Any] | None = None) -> str:
    fields = [
        raw.get("website"),
        raw.get("domain"),
        raw.get("name"),
        raw.get("title"),
        raw.get("industry"),
        raw.get("website_summary"),
        raw.get("description"),
        raw.get("snippet"),
    ]
    if extracted:
        fields.extend(
            [
                extracted.get("title"),
                extracted.get("h1"),
                extracted.get("meta_description"),
                extracted.get("og_description"),
                extracted.get("about_text"),
                extracted.get("visible_text_snippet"),
            ]
        )
        fields.extend(extracted.get("h2s") or [])
    return " ".join(str(value or "") for value in fields).casefold()


def reject_by_icp(
    raw: dict[str, Any],
    *,
    icp: ICPProfile,
    query_plan: QueryPlan,
    extracted: dict[str, Any] | None = None,
) -> ICPReject | None:
    text = candidate_text(raw, extracted)
    if not text.strip():
        return None

    negative_terms = _present_terms(
        text,
        [
            *icp.negative_keywords,
            *[term for term in query_plan.negative_keywords if _is_icp_negative(term)],
        ],
    )
    excluded_terms = _present_terms(text, [*icp.excluded_industries, *query_plan.excluded_industries])
    if negative_terms or excluded_terms:
        return ICPReject(
            reason="excluded_keyword" if negative_terms else "excluded_industry",
            matched_terms=_dedupe([*negative_terms, *excluded_terms]),
            evidence=_snippet(text, [*negative_terms, *excluded_terms]),
        )

    return None


def has_positive_icp_evidence(
    raw: dict[str, Any],
    *,
    icp: ICPProfile,
    query_plan: QueryPlan,
    extracted: dict[str, Any] | None = None,
) -> bool:
    text = candidate_text(raw, extracted)
    terms = [*icp.positive_keywords, *query_plan.positive_keywords, *icp.buyer_segments, *query_plan.buyer_segments]
    return bool(_present_terms(text, terms))


def _present_terms(text: str, terms: list[str]) -> list[str]:
    found: list[str] = []
    for term in terms:
        cleaned = " ".join(str(term or "").casefold().split())
        if not cleaned:
            continue
        if cleaned in text:
            found.append(cleaned)
    return _dedupe(found)


def _is_icp_negative(term: str) -> bool:
    cleaned = " ".join(str(term or "").casefold().split())
    return bool(cleaned and cleaned not in _GENERIC_WEB_NOISE_TERMS)


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _snippet(text: str, terms: list[str]) -> str | None:
    for term in terms:
        index = text.find(term.casefold())
        if index >= 0:
            start = max(0, index - 80)
            end = min(len(text), index + len(term) + 80)
            return " ".join(text[start:end].split())
    return None
