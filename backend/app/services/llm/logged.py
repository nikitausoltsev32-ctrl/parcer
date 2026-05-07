"""LLM wrapper that records each call into llm_calls[] for LeadProcessingLog."""
from __future__ import annotations

import time
import uuid
from typing import Any

from app.services.llm.base import LLMClient, LLMMessage, LLMResult


class LoggedLLMCall:
    """Accumulates llm_calls entries; attach to LeadProcessingLog.llm_calls."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.total_cost_usd: float = 0.0

    def add(self, entry: dict[str, Any]) -> None:
        self.entries.append(entry)
        self.total_cost_usd += entry.get("cost_usd", 0.0)


_COST_PER_TOKEN: dict[str, float] = {
    # provider/model → cost per 1k tokens (input, output)
    "groq/llama-3.1-8b-instant": (0.0, 0.0),
    "groq/llama-3.3-70b-versatile": (0.0, 0.0),
    "qwen/qwen2.5-72b-instruct": (0.0014, 0.0014),
    "glm/glm-4-flash": (0.0, 0.0),
    "anthropic/claude-sonnet-4-6": (0.003, 0.015),
    "anthropic/claude-haiku-4-5": (0.00025, 0.00125),
}


def _estimate_cost(model_key: str, input_tokens: int, output_tokens: int) -> float:
    rates = _COST_PER_TOKEN.get(model_key, (0.001, 0.002))
    return (input_tokens / 1000) * rates[0] + (output_tokens / 1000) * rates[1]


async def logged_chat(
    client: LLMClient,
    messages: list[LLMMessage],
    *,
    stage: str,
    log: LoggedLLMCall,
    temperature: float = 0.4,
    max_tokens: int = 1024,
    timeout: float = 30.0,
) -> LLMResult:
    call_id = str(uuid.uuid4())
    t0 = time.monotonic()
    entry: dict[str, Any] = {
        "call_id": call_id,
        "model": client.model,
        "stage": stage,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "cost_usd": 0.0,
        "duration_ms": 0,
        "success": False,
        "error": None,
    }
    try:
        result = await client.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        raw = result.raw
        if raw and hasattr(raw, "usage") and raw.usage:
            entry["input_tokens"] = raw.usage.prompt_tokens or 0
            entry["output_tokens"] = raw.usage.completion_tokens or 0
            provider = getattr(client, "_provider_key", "")
            entry["cost_usd"] = _estimate_cost(provider, entry["input_tokens"], entry["output_tokens"])
        entry["success"] = True
        return result
    except Exception as exc:
        entry["error"] = str(exc)[:300]
        raise
    finally:
        entry["duration_ms"] = int((time.monotonic() - t0) * 1000)
        log.add(entry)
