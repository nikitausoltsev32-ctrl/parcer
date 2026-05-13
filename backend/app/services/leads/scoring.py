from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MAPS_FEW_REVIEWS = 20
_MAPS_SOME_REVIEWS = 50
_MAPS_LOW_RATING = 4.0
_SERP_WEAK_POSITION = 7

# Contact bonus on top of AI score
_EMAIL_BONUS = 8
_PHONE_BONUS = 5


@dataclass(frozen=True)
class CandidateScore:
    score: int
    priority: str
    confidence: str
    reason: str


def score_candidate(candidate: dict[str, Any]) -> CandidateScore:
    reasons: list[str] = []

    ai_score = candidate.get("ai_score")  # light_result.relevance_score or deep lead_fit.score
    ai_reason = candidate.get("ai_reason")  # deep lead_fit.reason or None

    if ai_score is not None:
        score = int(ai_score)
        if ai_reason:
            reasons.append(ai_reason)
        # Contact presence on top of AI score
        if candidate.get("email"):
            score += _EMAIL_BONUS
            reasons.append("есть email")
        if candidate.get("phone"):
            score += _PHONE_BONUS
            reasons.append("есть телефон")
    else:
        # Mechanical fallback (no AI ran)
        score = 0
        if candidate.get("name"):
            score += 10
            reasons.append("есть название")
        if candidate.get("website"):
            score += 25
            reasons.append("есть сайт")
        if candidate.get("email"):
            score += 20
            reasons.append("есть email")
        if candidate.get("phone"):
            score += 15
            reasons.append("есть телефон")
        if candidate.get("website_summary"):
            score += 20
            reasons.append("есть описание")

    # Maps weakness bonuses (weak online presence = good prospect)
    reviews = candidate.get("maps_reviews_count")
    rating = candidate.get("maps_rating")
    position = candidate.get("serp_position")

    if isinstance(reviews, int | float):
        if reviews < _MAPS_FEW_REVIEWS:
            score += 8
            reasons.append("мало отзывов")
        elif reviews < _MAPS_SOME_REVIEWS:
            score += 4
            reasons.append("немного отзывов")

    if isinstance(rating, int | float) and rating < _MAPS_LOW_RATING:
        score += 7
        reasons.append("низкий рейтинг")

    if isinstance(position, int | float) and position >= _SERP_WEAK_POSITION:
        score += 5
        reasons.append("слабая позиция")

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

    return CandidateScore(
        score=score,
        priority=priority,
        confidence=confidence,
        reason=", ".join(reasons),
    )
