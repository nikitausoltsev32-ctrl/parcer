import anthropic

from app.core.config import settings
from app.services.llm.base import LLMMessage, LLMResult


class ClaudeClient:
    """Anthropic Claude client. Uses anthropic SDK, not OpenAI-compatible endpoint."""

    def __init__(self, model: str):
        self.model = model

    def _require_key(self) -> str:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        return settings.anthropic_api_key

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
        api_key = self._require_key()
        client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)

        system = next((m.content for m in messages if m.role == "system"), None)
        user_messages = [
            {"role": m.role, "content": m.content or ""}
            for m in messages
            if m.role != "system"
        ]

        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system

        resp = await client.messages.create(**kwargs)
        text = resp.content[0].text if resp.content else None
        return LLMResult(content=text, tool_calls=[], raw=resp)
