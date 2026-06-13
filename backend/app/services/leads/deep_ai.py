"""Step 9 - Deep AI Extraction. Fills full Lead JSON Schema. Cost: 5 credits."""
from __future__ import annotations

import json

from app.services.llm.base import LLMMessage
from app.services.llm.factory import get_llm_client
from app.services.llm.logged import LoggedLLMCall, logged_chat

_PROMPT = """\
You analyze a candidate company website for B2B lead qualification.

Seller ICP:
{service_offered}

Candidate website pages:
{pages_text}

Extracted public contacts: email={email}, phone={phone}, telegram={telegram}

Return strict JSON only. Use only facts from the provided text. If data is missing, return null/empty arrays.

Lead fit rules:
- Score 70+: clear evidence this company is a likely buyer/user in one of the ICP buyer segments.
- Score 45-69: possible fit, but evidence is partial.
- Score below 45: weak/generic fit.
- Score <=25 if the company belongs to an excluded industry or negative keyword group from ICP.
- Do not infer needs from generic industry labels alone.
- Score measures ICP fit only, not company size or quality. If the company is NOT a likely buyer, score <=30.
- priority must match score: high if score>=75, medium if 50-74, low if <50.
- Never combine a high score with priority "low".
- company_name: the official short company name from the site, not a page title or SEO phrase.

JSON shape:
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
  "lead_fit": {{
    "score": 0,
    "priority": "low",
    "reason": null
  }},
  "positive_evidence": [],
  "negative_evidence": [],
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
    pages_text = "\n\n---\n\n".join(f"URL: {p['url']}\n{p.get('html', '')[:3000]}" for p in pages[:5])
    client = get_llm_client("deep_ai")
    prompt = _PROMPT.format(
        service_offered=service_offered[:1200],
        pages_text=pages_text[:8000],
        email=extracted_email or "none",
        phone=extracted_phone or "none",
        telegram=extracted_telegram or "none",
    )
    result = await logged_chat(
        client,
        [LLMMessage(role="user", content=prompt)],
        stage="deep_ai",
        log=log,
        temperature=0.2,
        max_tokens=1200,
        timeout=120.0,
        response_format={"type": "json_object"},
    )
    text = (result.content or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return _coerce_scalar_strings(data)


_SCALAR_STRING_FIELDS = (
    "company_name", "city", "region", "address", "industry", "description",
    "reason_to_contact", "email", "phone", "telegram", "whatsapp", "vk", "instagram",
)


def _coerce_scalar_strings(data: dict) -> dict:
    if not isinstance(data, dict):
        return {}
    for field in _SCALAR_STRING_FIELDS:
        value = data.get(field)
        if isinstance(value, list):
            parts = [str(item).strip() for item in value if item not in (None, "")]
            data[field] = ", ".join(parts) or None
    return data
