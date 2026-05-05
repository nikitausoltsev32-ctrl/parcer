from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CandidateScore:
    score: int
    priority: str
    confidence: str
    reason: str


def score_candidate(candidate: dict[str, Any]) -> CandidateScore:
    score = 0
    reasons: list[str] = []

    if candidate.get("name"):
        score += 15
        reasons.append("есть название")
    if candidate.get("website"):
        score += 30
        reasons.append("есть сайт")
    if candidate.get("email"):
        score += 25
        reasons.append("есть email")
    if candidate.get("phone"):
        score += 20
        reasons.append("есть телефон")
    if candidate.get("website_summary"):
        score += 10
        reasons.append("есть краткое описание сайта")

    score = min(score, 100)
    if score >= 75:
        priority = "high"
    elif score >= 50:
        priority = "medium"
    else:
        priority = "low"

    if candidate.get("email") or candidate.get("phone"):
        confidence = "verified"
    elif candidate.get("website"):
        confidence = "inferred"
    else:
        confidence = "missing"

    return CandidateScore(score=score, priority=priority, confidence=confidence, reason=", ".join(reasons))
