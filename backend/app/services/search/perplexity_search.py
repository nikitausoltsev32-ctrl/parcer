"""Direct lead discovery via Perplexity Sonar (live web + citations).

Unlike llm_search (model recalls companies from training memory), Sonar
queries the live web. URLs are still HEAD-validated before crawling.
"""
from __future__ import annotations

import json
import logging

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat
from app.services.search.llm_search import _head_validate

logger = logging.getLogger(__name__)

_PROMPT = """\
Найди {count} реальных действующих компаний из ниши "{niche}" в городе "{city}".
Ищи по актуальному вебу. Только официальные сайты компаний — не агрегаторы,
не каталоги, не статьи. Для каждой компании укажи рабочий домен.

Отвечай строго JSON без markdown:
{{"companies":[{{"name":"...","website":"https://...","city":"...","description":"..."}}]}}"""


async def perplexity_search_companies(
    niche: str,
    city: str | None,
    count: int = 15,
    log: LoggedLLMCall | None = None,
) -> list[dict]:
    """Return HEAD-validated company list from Perplexity Sonar web search."""
    client = get_llm_client("lead_discovery")
    prompt = _PROMPT.format(count=count, niche=niche, city=city or "России")
    dummy_log = log or LoggedLLMCall()
    try:
        result = await logged_chat(
            client,
            [LLMMessage(role="user", content=prompt)],
            stage="lead_discovery",
            log=dummy_log,
            temperature=0.2,
            max_tokens=1024,
            timeout=30.0,
        )
    except Exception as exc:
        logger.warning("perplexity_search: LLM call failed: %r", exc)
        return []

    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        companies = json.loads(text).get("companies", [])
        if not isinstance(companies, list):
            return []
    except Exception:
        logger.warning("perplexity_search: bad JSON: %r", text[:200])
        return []

    candidates = [
        {**c, "source": "perplexity"}
        for c in companies
        if isinstance(c, dict) and isinstance(c.get("website"), str) and c["website"].startswith("http")
    ]
    if not candidates:
        return []
    return await _head_validate(candidates)
