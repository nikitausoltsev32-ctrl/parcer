"""Step 8 - Light AI. Classify if lead is worth deep analysis. Cost: 1 credit."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat

_PROMPT = """\
Ты B2B-классификатор лидов. Отвечай только JSON, без markdown.

Компания: {title}
Описание/сниппет: {meta_description}
H1: {h1}
About section: {about_text}
Текст сайта: {visible_text_snippet}
Контакты: email={email}, phone={phone}
Продаём: {icp_description}
Город: {city}

Задачи:
1. Оцени лид — стоит ли глубокий анализ для продавца услуги "{icp_description}".
2. description: 1-2 коротких фактических предложения о том, чем занимается компания.
3. hook: 1 предложение — конкретная зацепка, почему этой компании может быть нужна услуга "{icp_description}". Только факты из текста. Если зацепки нет — null.

Правила:
- Используй только факты из текста выше. Не выдумывай.
- description и hook пишут по-русски если текст на русском.
- Если текста недостаточно — description: null, hook: null.
- Запрещено писать общую зацепку без факта из текста: "можем улучшить сайт", "увеличить заявки", "привлечь клиентов", "повысить продажи".
- hook должен ссылаться на конкретный наблюдаемый факт: услуга, город, сегмент клиентов, слабое место сайта, форма, контакты или явно указанный оффер.
- Если конкретного факта для hook нет — hook: null, даже если лид релевантен.

{{"industry":null,"city":null,"description":null,"hook":null,"is_commercial":true,"is_relevant_to_icp":true,"relevance_score":0,"pass_to_deep_ai":false}}

pass_to_deep_ai=true только если relevance_score>=60 AND is_commercial=true."""


@dataclass
class LightAIResult:
    industry: str
    city: str
    description: str | None
    hook: str | None = None
    is_commercial: bool = False
    is_relevant_to_icp: bool = False
    relevance_score: int = 0
    pass_to_deep_ai: bool = False
    raw: dict = field(default_factory=dict)


def _clean_string(value: Any) -> str:
    return " ".join(str(value or "").split())


def _clean_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _loads_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


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
    about_text: str = "",
    model_override: str | None = None,
) -> LightAIResult:
    client = get_llm_client("classify", model_override=model_override)
    prompt = _PROMPT.format(
        title=_clean_string(title)[:200],
        meta_description=_clean_string(meta_description)[:300],
        h1=_clean_string(h1)[:200],
        about_text=_clean_string(about_text)[:1200],
        visible_text_snippet=_clean_string(visible_text_snippet)[:1500],
        email=email or "нет",
        phone=phone or "нет",
        icp_description=_clean_string(icp_description)[:300],
        city=city or "неизвестен",
    )
    result = await logged_chat(
        client,
        [LLMMessage(role="user", content=prompt)],
        stage="light_ai",
        log=log,
        temperature=0.1,
        max_tokens=300,
        timeout=90.0,
        response_format={"type": "json_object"},
    )
    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        data = _loads_json_object(text)
    except Exception:
        data = {}

    score = int(data.get("relevance_score", 0))
    commercial = bool(data.get("is_commercial", False))
    return LightAIResult(
        industry=_clean_string(data.get("industry")),
        city=_clean_string(data.get("city") or city),
        description=_clean_optional_string(data.get("description")),
        hook=_clean_optional_string(data.get("hook")),
        is_commercial=commercial,
        is_relevant_to_icp=bool(data.get("is_relevant_to_icp", False)),
        relevance_score=score,
        pass_to_deep_ai=score >= 60 and commercial,
        raw=data,
    )
