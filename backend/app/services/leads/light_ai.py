"""Step 8 — Light AI. Classify if lead worth deep analysis. Cost: 1 credit."""
from __future__ import annotations

import json
from dataclasses import dataclass

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat

_PROMPT = """\
Ты классификатор B2B-лидов. Отвечай только JSON без markdown.

Title: {title}
Description: {meta_description}
H1: {h1}
Текст: {visible_text_snippet}
Контакты: email={email}, phone={phone}
ICP: {icp_description}
Город: {city}

Задача: стоит ли лид глубокого анализа?

{{"industry":"...","city":"...","is_commercial":true,"is_relevant_to_icp":true,"relevance_score":0,"pass_to_deep_ai":false}}

pass_to_deep_ai=true только если relevance_score>=60 AND is_commercial=true."""


@dataclass
class LightAIResult:
    industry: str
    city: str
    is_commercial: bool
    is_relevant_to_icp: bool
    relevance_score: int
    pass_to_deep_ai: bool
    raw: dict


async def run_light_ai(
    *,
    title: str,
    meta_description: str,
    h1: str,
    visible_text_snippet: str,
    email: str | None,
    phone: str | None,
    icp_description: str,
    city: str | None,
    log: LoggedLLMCall,
) -> LightAIResult:
    client = get_llm_client("classify")
    prompt = _PROMPT.format(
        title=title[:200],
        meta_description=meta_description[:300],
        h1=h1[:200],
        visible_text_snippet=visible_text_snippet[:1500],
        email=email or "нет",
        phone=phone or "нет",
        icp_description=icp_description[:300],
        city=city or "неизвестен",
    )
    result = await logged_chat(
        client,
        [LLMMessage(role="user", content=prompt)],
        stage="light_ai",
        log=log,
        temperature=0.1,
        max_tokens=128,
    )
    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        data = json.loads(text)
    except Exception:
        data = {}

    score = int(data.get("relevance_score", 0))
    commercial = bool(data.get("is_commercial", False))
    return LightAIResult(
        industry=data.get("industry", ""),
        city=data.get("city", city or ""),
        is_commercial=commercial,
        is_relevant_to_icp=bool(data.get("is_relevant_to_icp", False)),
        relevance_score=score,
        pass_to_deep_ai=score >= 60 and commercial,
        raw=data,
    )
