"""Step 9 — Deep AI Extraction. Fills full Lead JSON Schema. Cost: 5 credits."""
from __future__ import annotations

import json

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat

_PROMPT = """\
Ты анализируешь сайт компании как B2B-специалист.
Пользователь продаёт: {service_offered}

{pages_text}

Контакты из парсера: email={email}, phone={phone}, telegram={telegram}

Заполни JSON строго по схеме. Данные ТОЛЬКО из текста выше. Если нет — null. НЕ ВЫДУМЫВАЙ.
Отвечай строго JSON без текста вне JSON:

{{
  "company_name": null,
  "city": null,
  "region": null,
  "address": null,
  "industry": null,
  "description": null,
  "services": [],
  "email": null,
  "phone": null,
  "telegram": null,
  "whatsapp": null,
  "vk": null,
  "instagram": null,
  "has_contact_form": false,
  "decision_maker": {{"name": null, "role": null, "source_url": null}},
  "website_quality": {{
    "has_modern_design": null,
    "has_mobile_adaptation": null,
    "has_clear_cta": null,
    "has_online_booking": null,
    "has_outdated_content": null,
    "seo_visible": null,
    "comments": null
  }},
  "pain_points": [],
  "reason_to_contact": null,
  "confidence": 0.5
}}"""


async def run_deep_ai(
    *,
    pages: list[dict],
    service_offered: str,
    extracted_email: str | None,
    extracted_phone: str | None,
    extracted_telegram: str | None,
    log: LoggedLLMCall,
) -> dict:
    pages_text = "\n\n---\n\n".join(
        f"URL: {p['url']}\n{p.get('html', '')[:3000]}" for p in pages[:5]
    )
    client = get_llm_client("letters")
    prompt = _PROMPT.format(
        service_offered=service_offered[:200],
        pages_text=pages_text[:8000],
        email=extracted_email or "нет",
        phone=extracted_phone or "нет",
        telegram=extracted_telegram or "нет",
    )
    result = await logged_chat(
        client,
        [LLMMessage(role="user", content=prompt)],
        stage="deep_ai",
        log=log,
        temperature=0.2,
        max_tokens=1024,
        timeout=60.0,
    )
    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(text)
    except Exception:
        return {}
