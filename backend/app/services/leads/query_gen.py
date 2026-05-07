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


async def generate_queries(
    niche: str,
    city: str | None,
    service_offered: str,
    log: LoggedLLMCall,
) -> list[str]:
    client = get_llm_client("classify")
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
        temperature=0.5,
        max_tokens=512,
    )
    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        data = json.loads(text)
        queries = [q["query"] for q in data.get("queries", []) if q.get("query")]
        return queries or [f"{niche} {city or ''}".strip()]
    except Exception:
        return [f"{niche} {city or ''}".strip()]
