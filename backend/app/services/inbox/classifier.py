"""Classify incoming email into one of {interested, rejected, autoreply, question, unsubscribe, other}."""

import json

from app.services.llm import get_llm_client
from app.services.llm.base import LLMMessage

SYSTEM_PROMPT = """Классифицируй входящее B2B-письмо на русском в одну из категорий:
- interested — заинтересован, хочет продолжить
- rejected — отказ, не нужно
- autoreply — автоответ (отпуск, out of office)
- question — уточняющий вопрос (цена, сроки)
- unsubscribe — просьба отписать
- other — ничего из вышеперечисленного

Ответь JSON: {"classification": "...", "confidence": 0.0-1.0}
"""


async def classify_inbox_message(body_text: str) -> dict:
    client = get_llm_client("inbox_classify")
    text = (body_text or "")[:1500]
    result = await client.chat(
        messages=[LLMMessage(role="system", content=SYSTEM_PROMPT), LLMMessage(role="user", content=text)],
        temperature=0.1,
        max_tokens=50,
        response_format={"type": "json_object"},
    )
    return json.loads(result.content)
