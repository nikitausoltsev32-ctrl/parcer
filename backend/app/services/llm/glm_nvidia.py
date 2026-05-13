from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.llm.base import LLMClient, LLMMessage, LLMResult

_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
_NEMOTRON_REASONING_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
_REASONING_MODELS = {_NEMOTRON_REASONING_MODEL}


class GLMNvidiaClient(LLMClient):
    """OpenAI-compatible NVIDIA API client for GLM and NVIDIA models.

    thinking=False (default): standard non-streaming, fastest.
    thinking=True: streams internally and returns content + reasoning_content via raw.
    """

    base_url = _NVIDIA_BASE_URL

    def __init__(self, model: str = "z-ai/glm-5.1", *, thinking: bool | None = None):
        self.api_key = settings.nvidia_api_key
        self.model = model
        self._thinking = model in _REASONING_MODELS if thinking is None else thinking

    def _extra_body(self) -> dict | None:
        if self.model == _NEMOTRON_REASONING_MODEL:
            return {"chat_template_kwargs": {"enable_thinking": True, "reasoning_budget": 512}}
        if not self._thinking:
            return {"chat_template_kwargs": {"enable_thinking": False}}
        return {"chat_template_kwargs": {"enable_thinking": True, "clear_thinking": False}}

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict | None = None,
        timeout: float = 60.0,
    ) -> LLMResult:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=timeout,
            max_retries=0,
        )
        effective_max_tokens = max(max_tokens, 256) if self.model in _REASONING_MODELS else max_tokens
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [self._to_openai(m) for m in messages],
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
            "extra_body": self._extra_body(),
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format

        if self._thinking and not tools:
            return await self._stream_with_thinking(client, payload)

        resp = await client.chat.completions.create(**payload)
        choice = resp.choices[0]
        msg = choice.message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments})
        return LLMResult(content=msg.content, tool_calls=tool_calls, raw=resp)

    async def _stream_with_thinking(self, client: Any, payload: dict) -> LLMResult:
        """Stream internally to capture content when thinking mode is on."""
        stream_payload = {**payload, "stream": True}
        stream = await client.chat.completions.create(**stream_payload)
        reasoning_parts: list[str] = []
        content_parts: list[str] = []
        async for chunk in stream:
            if not getattr(chunk, "choices", None) or not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            r = getattr(delta, "reasoning_content", None)
            c = getattr(delta, "content", None)
            if r:
                reasoning_parts.append(r)
            if c:
                content_parts.append(c)
        content = "".join(content_parts) or None
        reasoning = "".join(reasoning_parts) or None
        return LLMResult(content=content, raw={"reasoning": reasoning})
