"""Step 4 — URL Classifier. LLM for border cases that deterministic filter can't resolve."""
from __future__ import annotations

import json

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat

_LABELS = ("company_homepage", "contacts", "services", "garbage")

_PROMPT = """\
Определи тип URL. Ответ строго JSON без markdown:
{{"label":"company_homepage|contacts|services|garbage"}}

URL: {url}
Заголовок страницы: {title}
Описание: {description}

Только JSON."""


def _loads_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


async def classify_url(
    url: str,
    title: str,
    description: str,
    log: LoggedLLMCall,
    model_override: str | None = None,
) -> str:
    client = get_llm_client("url_classify", model_override=model_override)
    prompt = _PROMPT.format(url=url, title=title[:200], description=description[:300])
    result = await logged_chat(
        client,
        [LLMMessage(role="user", content=prompt)],
        stage="url_classify",
        log=log,
        temperature=0.1,
        max_tokens=32,
        timeout=90.0,
        response_format={"type": "json_object"},
    )
    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        label = _loads_json_object(text).get("label", "garbage")
        return label if label in _LABELS else "garbage"
    except Exception:
        return "garbage"
