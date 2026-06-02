"""Step 1 - Query Generator. Turns user input into ICP-aware search queries."""
from __future__ import annotations

import json
from typing import Any

from app.services.leads.icp import ICPProfile, QueryList, build_query_plan_from_queries
from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat

_PROMPT = """\
You generate web search queries for B2B lead generation.

Search request: {niche}
City/region: {city}
Seller offer: {service_offered}

ICP profile:
{icp_profile}

Generate 5-10 Google/Yandex queries that find OFFICIAL COMPANY WEBSITES.
The target is BUYERS/USERS of the seller's product, not other sellers of similar raw materials.
Avoid aggregators, ratings, directories, articles, marketplaces, job boards, and media pages.

Return strict JSON without markdown:
{{
  "queries": [
    {{"query": "...", "intent": "company_homepage|contacts_page|services_page|price_page",
      "priority": "high|medium|low"}}
  ],
  "negative_keywords": ["..."],
  "buyer_segments": ["..."],
  "excluded_industries": ["..."],
  "positive_keywords": ["..."],
  "expected_results_per_query": 20,
  "rationale": "..."
}}"""


def _fallback_query(niche: str, city: str | None) -> str:
    return f"{niche} {city or ''}".strip()


def _normalize_queries(data: dict, niche: str, city: str | None) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    for item in data.get("queries", []):
        if not isinstance(item, dict):
            continue
        query = item.get("query")
        if not isinstance(query, str):
            continue
        cleaned = " ".join(query.split())
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        queries.append(cleaned)
        if len(queries) >= 10:
            break
    return queries or [_fallback_query(niche, city)]


def _loads_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


async def generate_queries(
    niche: str,
    city: str | None,
    service_offered: str,
    log: LoggedLLMCall,
    model_override: str | None = None,
    icp_profile: ICPProfile | dict | None = None,
) -> list[str]:
    client = get_llm_client("query_gen", model_override=model_override)
    icp = _coerce_icp(icp_profile, service_offered)
    prompt = _PROMPT.format(
        niche=niche,
        city=city or "any city",
        service_offered=service_offered,
        icp_profile=icp.compact(),
    )
    result = await logged_chat(
        client,
        [LLMMessage(role="user", content=prompt)],
        stage="query_gen",
        log=log,
        temperature=0.2,
        max_tokens=700,
        timeout=90.0,
        response_format={"type": "json_object"},
    )
    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        data = _loads_json_object(text)
        queries = _normalize_queries(data, niche, city)
        plan = build_query_plan_from_queries(queries, icp, rationale=_optional_str(data.get("rationale")))
        plan = type(plan)(
            queries=plan.queries,
            negative_keywords=_merge_terms(plan.negative_keywords, data.get("negative_keywords")),
            buyer_segments=_merge_terms(plan.buyer_segments, data.get("buyer_segments")),
            excluded_industries=_merge_terms(plan.excluded_industries, data.get("excluded_industries")),
            positive_keywords=_merge_terms(plan.positive_keywords, data.get("positive_keywords")),
            rationale=plan.rationale,
        )
        return QueryList(queries, plan)
    except Exception:
        queries = [_fallback_query(niche, city)]
        return QueryList(queries, build_query_plan_from_queries(queries, icp, rationale="fallback"))


def _coerce_icp(value: ICPProfile | dict | None, fallback: str) -> ICPProfile:
    if isinstance(value, ICPProfile):
        return value
    if isinstance(value, dict):
        return ICPProfile(
            seller_summary=str(value.get("seller_summary") or fallback),
            products=_list_of_str(value.get("products")),
            buyer_segments=_list_of_str(value.get("buyer_segments")),
            use_cases=_list_of_str(value.get("use_cases")),
            positive_keywords=_list_of_str(value.get("positive_keywords")),
            negative_keywords=_list_of_str(value.get("negative_keywords")),
            excluded_industries=_list_of_str(value.get("excluded_industries")),
            source=str(value.get("source") or "stored"),
        )
    return ICPProfile(seller_summary=fallback, products=[fallback], buyer_segments=[], positive_keywords=[fallback])


def _list_of_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [" ".join(str(item).split()) for item in value if " ".join(str(item).split())]


def _optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _merge_terms(base: list[str], extra: object) -> list[str]:
    values = list(base)
    if isinstance(extra, list):
        values.extend(str(item) for item in extra if item)
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(str(value).split())
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result[:24]
