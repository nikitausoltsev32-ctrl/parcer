from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from app.services.leads.extraction import normalize_domain

_LEGAL_PREFIX_RE = re.compile(r"^(?:ооо|ип|ао)\s+", re.IGNORECASE)
_NAME_NOISE_RE = re.compile(r"[\"'«»“”.,;:()]+")


def deduplicate_candidates(candidates: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    domain_index: dict[str, int] = {}
    name_index: dict[str, int] = {}

    for candidate in candidates:
        domain = normalize_domain(candidate.get("website"))
        normalized_name = _normalize_name(candidate.get("name"))

        duplicate_index: int | None = None
        if domain:
            duplicate_index = domain_index.get(domain)
        elif normalized_name:
            duplicate_index = name_index.get(normalized_name)
            if duplicate_index is None:
                duplicate_index = _find_fuzzy_duplicate(deduped, normalized_name)

        if duplicate_index is None:
            deduped.append(candidate)
            index = len(deduped) - 1
            if domain:
                domain_index[domain] = index
            elif normalized_name:
                name_index[normalized_name] = index
            continue

        if _score(candidate) > _score(deduped[duplicate_index]):
            deduped[duplicate_index] = candidate
            if domain:
                domain_index[domain] = duplicate_index
            elif normalized_name:
                name_index[normalized_name] = duplicate_index

    return deduped


def _normalize_name(value: Any) -> str:
    name = str(value or "").casefold().strip()
    name = _NAME_NOISE_RE.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = _LEGAL_PREFIX_RE.sub("", name).strip()
    return name


def _find_fuzzy_duplicate(candidates: list[dict], normalized_name: str) -> int | None:
    for index, candidate in enumerate(candidates):
        if normalize_domain(candidate.get("website")):
            continue
        existing_name = _normalize_name(candidate.get("name"))
        if existing_name and SequenceMatcher(None, normalized_name, existing_name).ratio() >= 0.85:
            return index
    return None


def _score(candidate: dict) -> int:
    value = candidate.get("score") or 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
