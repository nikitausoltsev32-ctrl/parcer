"""Step 1 — Query Generator. Turns user input into 5-15 search queries."""
from __future__ import annotations

import json

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat

_PROMPT = """\
Ты генератор поисковых запросов для B2B лидогенерации.
Ниша: {niche} | Город: {city} | Услуга продавца: {service_offered}

Сгенерируй 5–10 запросов для Google/Yandex.
Каждый запрос должен находить ОФИЦИАЛЬНЫЕ САЙТЫ компаний, не агрегаторы и статьи.
Добавь negative keywords.

Отвечай строго JSON без markdown:
{{"queries":[{{"query":"...","intent":"company_homepage|contacts_page|services_page|price_page","priority":"high|medium|low"}}],"negative_keywords":["..."],"expected_results_per_query":20}}"""


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
            return json.loads(text[start:end + 1])
        raise


async def generate_queries(
    niche: str,
    city: str | None,
    service_offered: str,
    log: LoggedLLMCall,
    model_override: str | None = None,
) -> list[str]:
    client = get_llm_client("query_gen", model_override=model_override)
    prompt = _PROMPT.format(
        niche=niche,
        city=city or "любой город",
        service_offered=service_offered,
    )
    result = await logged_chat(
        client,
        [LLMMessage(role="user", content=prompt)],
        stage="query_gen",
        log=log,
        temperature=0.2,
        max_tokens=512,
        timeout=90.0,
        response_format={"type": "json_object"},
    )
    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        data = _loads_json_object(text)
        return _normalize_queries(data, niche, city)
    except Exception:
        return [_fallback_query(niche, city)]
