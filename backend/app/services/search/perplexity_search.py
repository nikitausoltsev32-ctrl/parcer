"""Direct lead discovery via Perplexity Sonar (live web + citations)."""
from __future__ import annotations

import json
import logging
import re

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat
from app.services.search.llm_search import _head_validate

logger = logging.getLogger(__name__)


def _parse_companies_json(text: str) -> list[dict] | None:
    """Parse Perplexity response, recovering partial JSON if truncated."""
    try:
        return json.loads(text).get("companies", [])
    except json.JSONDecodeError:
        pass
    matches = re.findall(r'\{[^{}]*"website"\s*:\s*"[^"]+"[^{}]*\}', text)
    recovered = []
    for match in matches:
        try:
            recovered.append(json.loads(match))
        except json.JSONDecodeError:
            continue
    return recovered if recovered else None


_PROMPT = """\
Find {count} real operating B2B companies in "{city}" for this search niche:
{niche}

ICP / query plan:
Buyer segments: {buyer_segments}
Positive keywords: {positive_keywords}
Excluded industries: {excluded_industries}
Negative keywords: {negative_keywords}

Search the live web. Return official company websites only.
The companies must be likely BUYERS or USERS of the seller's product.
Do not return suppliers of similar raw materials unless they are also a target buyer.
Do not return aggregators, directories, marketplaces, ratings, articles, media, job boards, or social-only pages.
If excluded/negative terms match, skip the company even if it looks semantically similar.

Return strict JSON without markdown:
{{"companies":[{{"name":"...","website":"https://...","city":"...","description":"..."}}]}}"""


async def perplexity_search_companies(
    niche: str,
    city: str | None,
    count: int = 15,
    log: LoggedLLMCall | None = None,
    query_plan: dict | None = None,
) -> list[dict]:
    """Return HEAD-validated company list from Perplexity Sonar web search."""
    client = get_llm_client("lead_discovery")
    plan = query_plan or {}
    prompt = _PROMPT.format(
        count=count,
        niche=niche,
        city=city or "Russia",
        buyer_segments=", ".join(_string_list(plan.get("buyer_segments"))) or "not specified",
        positive_keywords=", ".join(_string_list(plan.get("positive_keywords"))) or "not specified",
        excluded_industries=", ".join(_string_list(plan.get("excluded_industries"))) or "not specified",
        negative_keywords=", ".join(_string_list(plan.get("negative_keywords"))) or "not specified",
    )
    dummy_log = log or LoggedLLMCall()
    try:
        result = await logged_chat(
            client,
            [LLMMessage(role="user", content=prompt)],
            stage="lead_discovery",
            log=dummy_log,
            temperature=0.2,
            max_tokens=2048,
            timeout=30.0,
        )
    except Exception as exc:
        logger.warning("perplexity_search: LLM call failed: %r", exc)
        return []

    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()

    companies = _parse_companies_json(text)
    if companies is None:
        logger.warning("perplexity_search: bad JSON: %r", text[:200])
        return []

    candidates = []
    for company in companies:
        if not isinstance(company, dict):
            continue
        website = _normalize_website(company.get("website"))
        if website:
            candidates.append({**company, "website": website, "source": "perplexity"})
    if not candidates:
        return []
    return await _head_validate(candidates)


def _normalize_website(value: object) -> str | None:
    """Perplexity often returns bare domains ('dk96.ru') — add scheme instead of dropping them."""
    if not isinstance(value, str):
        return None
    site = value.strip().rstrip("/")
    if not site:
        return None
    if site.startswith(("http://", "https://")):
        return site
    if "." in site and " " not in site:
        return f"https://{site}"
    return None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [" ".join(str(item).split()) for item in value if " ".join(str(item).split())]
