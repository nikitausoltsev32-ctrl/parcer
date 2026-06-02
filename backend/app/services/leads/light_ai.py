"""Step 8 - Light AI. Classify if lead is worth deep analysis. Cost: 1 credit."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat

_PROMPT = """\
You are a B2B lead-fit classifier. Return only strict JSON without markdown.

Candidate company:
Title: {title}
Description/snippet: {meta_description}
H1: {h1}
About section: {about_text}
Website text: {visible_text_snippet}
Contacts: email={email}, phone={phone}

Seller ICP:
{icp_description}

City/region: {city}

Tasks:
1. Decide if this company is a likely BUYER/USER of the seller's product.
2. If the company belongs to an excluded industry or negative keyword group from ICP, set is_relevant_to_icp=false, relevance_score<=25, pass_to_deep_ai=false.
3. Do not give a high score for generic "construction" unless the text shows a target use case or buyer segment from ICP.
4. description: 1-2 short factual sentences about what the company does.
5. hook: one concrete factual reason why this company may need the seller's product, or null.

Rules:
- Use only evidence from the provided text. Do not invent email, phone, people, pain, or needs.
- Запрещено писать общую зацепку without concrete evidence from the candidate text.
- If evidence is weak, keep score low and hook null.

JSON shape:
{{
  "industry": null,
  "city": null,
  "description": null,
  "hook": null,
  "is_commercial": true,
  "is_relevant_to_icp": false,
  "relevance_score": 0,
  "pass_to_deep_ai": false,
  "positive_evidence": [],
  "negative_evidence": []
}}

pass_to_deep_ai=true only when relevance_score>=60 AND is_commercial=true AND is_relevant_to_icp=true."""


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
            return json.loads(text[start : end + 1])
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
    client = get_llm_client("light_ai", model_override=model_override)
    prompt = _PROMPT.format(
        title=_clean_string(title)[:200],
        meta_description=_clean_string(meta_description)[:500],
        h1=_clean_string(h1)[:200],
        about_text=_clean_string(about_text)[:1400],
        visible_text_snippet=_clean_string(visible_text_snippet)[:1800],
        email=email or "none",
        phone=phone or "none",
        icp_description=_clean_string(icp_description)[:1200],
        city=city or "unknown",
    )
    result = await logged_chat(
        client,
        [LLMMessage(role="user", content=prompt)],
        stage="light_ai",
        log=log,
        temperature=0.1,
        max_tokens=420,
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

    score = _safe_int(data.get("relevance_score"), default=0)
    commercial = bool(data.get("is_commercial", False))
    relevant = bool(data.get("is_relevant_to_icp", False))
    return LightAIResult(
        industry=_clean_string(data.get("industry")),
        city=_clean_string(data.get("city") or city),
        description=_clean_optional_string(data.get("description")),
        hook=_clean_optional_string(data.get("hook")),
        is_commercial=commercial,
        is_relevant_to_icp=relevant,
        relevance_score=score,
        pass_to_deep_ai=score >= 60 and commercial and relevant,
        raw=data,
    )


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
