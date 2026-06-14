"""Step 1 - prompt understanding. LLM-based ICP parser feeding the Query Generator."""
from __future__ import annotations

import json
from typing import Any

from app.services.leads.icp import ICPProfile, _clean_list, build_icp_profile
from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat

_PROMPT = """\
Ты разбираешь запрос для B2B-лидогенерации и строишь профиль идеального клиента (ICP).

Запрос пользователя: {query}
Город/регион: {city}
Бизнес продавца: {business}
Оффер продавца: {offer}

Определи, кого реально надо искать. Ключевой случай: пользователь часто продаёт
продукт/материал и хочет найти ПОКУПАТЕЛЕЙ/ПОТРЕБИТЕЛЕЙ этого продукта (компании,
которые его ПРИМЕНЯЮТ или в нём НУЖДАЮТСЯ), а не других продавцов того же сырья.
Поэтому buyer_segments — это конкретные отрасли и типы компаний, которые используют
или нуждаются в продукте. Если же пользователь ищет компании В нише — перечисли эти
компании как buyer_segments.

Отвечай строго JSON без markdown:
{{
  "intent": "buyers|niche",
  "seller_summary": "1-2 предложения о продавце и что он продаёт",
  "products": ["..."],
  "buyer_segments": ["конкретные отрасли/типы компаний, которые ПРИМЕНЯЮТ продукт"],
  "use_cases": ["..."],
  "positive_keywords": ["слова, по которым видно релевантную компанию"],
  "negative_keywords": ["слова, исключающие нерелевантные результаты"],
  "excluded_industries": ["отрасли, которые точно не подходят"]
}}"""


def _loads_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _merge(left: list[str], right: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in [*left, *right]:
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


async def parse_icp(
    query: str,
    business_profile: dict[str, Any] | None,
    city: str | None,
    *,
    log: LoggedLLMCall,
    model_override: str | None = None,
) -> ICPProfile:
    bp = dict(business_profile or {})
    fallback = build_icp_profile(bp, query=query, city=city)
    try:
        client = get_llm_client("query_gen", model_override=model_override)
        prompt = _PROMPT.format(
            query=query,
            city=city or "любой",
            business=bp.get("business") or "",
            offer=bp.get("offer") or "",
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
        data = _loads_json_object(text)
    except Exception:
        return fallback

    products = _merge(fallback.products, _clean_list(data.get("products")))
    buyer_segments = _merge(fallback.buyer_segments, _clean_list(data.get("buyer_segments")))
    use_cases = _merge(fallback.use_cases, _clean_list(data.get("use_cases")))
    positive_keywords = _merge(fallback.positive_keywords, _clean_list(data.get("positive_keywords")))
    negative_keywords = _merge(fallback.negative_keywords, _clean_list(data.get("negative_keywords")))
    excluded_industries = _merge(fallback.excluded_industries, _clean_list(data.get("excluded_industries")))

    summary = " ".join(str(data.get("seller_summary") or "").split()) or fallback.seller_summary

    if not buyer_segments:
        return fallback

    return ICPProfile(
        seller_summary=summary,
        products=products[:12],
        buyer_segments=buyer_segments[:12],
        use_cases=use_cases[:12],
        positive_keywords=positive_keywords[:24],
        negative_keywords=negative_keywords[:24],
        excluded_industries=excluded_industries[:12],
        source="parsed",
    )
