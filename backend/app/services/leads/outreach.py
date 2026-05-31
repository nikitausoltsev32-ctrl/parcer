"""Step 12 — Outreach Generation. Personalized first message. Cost: 3 credits."""
from __future__ import annotations

import json

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat

_PROMPT = """\
Ты пишешь первое холодное сообщение от лица специалиста.

Специалист продаёт: {service_offered}
Компания: {company_name}
Ниша: {industry}
Описание: {description}
Слабые места: {pain_points}
Повод: {reason_to_contact}

Правила:
1. Только факты из данных выше — не выдумывать
2. Не писать "вы теряете клиентов" — только наблюдения
3. Email: тема + тело, не более 120 слов
4. Telegram: не более 60 слов

Ответ строго JSON без markdown:
{{"email_subject":"...","email_body":"...","telegram_message":"..."}}"""


async def generate_outreach(
    *,
    service_offered: str,
    company_name: str | None,
    industry: str | None,
    description: str | None,
    pain_points: list[str],
    reason_to_contact: str | None,
    log: LoggedLLMCall,
) -> dict:
    client = get_llm_client("outreach")
    prompt = _PROMPT.format(
        service_offered=service_offered[:200],
        company_name=company_name or "Компания",
        industry=industry or "неизвестная ниша",
        description=(description or "нет описания")[:500],
        pain_points=", ".join(pain_points[:5]) or "не определены",
        reason_to_contact=reason_to_contact or "общий интерес",
    )
    result = await logged_chat(
        client,
        [LLMMessage(role="user", content=prompt)],
        stage="outreach",
        log=log,
        temperature=0.6,
        max_tokens=512,
        timeout=120.0,
        response_format={"type": "json_object"},
    )
    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        data = json.loads(text)
        return {
            "email_subject": data.get("email_subject"),
            "email_body": data.get("email_body"),
            "telegram_message": data.get("telegram_message"),
            "regeneration_count": 0,
        }
    except Exception:
        return {"email_subject": None, "email_body": None, "telegram_message": None, "regeneration_count": 0}
