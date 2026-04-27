from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMMessage:
    role: str
    content: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class LLMResult:
    content: str | None
    tool_calls: list[dict] = field(default_factory=list)
    raw: Any = None


class LLMClient:
    """OpenAI-compatible client. Subclasses set base_url, api_key, model."""

    base_url: str = ""
    api_key: str = ""
    model: str = ""

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        response_format: dict | None = None,
        timeout: float = 30.0,
    ) -> LLMResult:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key, timeout=timeout)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [self._to_openai(m) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format
        resp = await client.chat.completions.create(**payload)
        choice = resp.choices[0]
        msg = choice.message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                )
        return LLMResult(content=msg.content, tool_calls=tool_calls, raw=resp)

    @staticmethod
    def _to_openai(m: LLMMessage) -> dict:
        d: dict[str, Any] = {"role": m.role}
        if m.content is not None:
            d["content"] = m.content
        if m.tool_calls:
            d["tool_calls"] = m.tool_calls
        if m.tool_call_id:
            d["tool_call_id"] = m.tool_call_id
        if m.name:
            d["name"] = m.name
        return d
