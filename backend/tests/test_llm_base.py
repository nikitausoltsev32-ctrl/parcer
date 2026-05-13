from types import SimpleNamespace

from app.services.llm.base import LLMClient, LLMMessage, LLMResult
from app.services.llm.logged import LoggedLLMCall, logged_chat


async def test_llm_client_disables_openai_sdk_retries(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **payload):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="ok",
                            tool_calls=None,
                        )
                    )
                ]
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", FakeAsyncOpenAI)

    client = LLMClient()
    client.base_url = "https://example.com"
    client.api_key = "test-key"
    client.model = "test-model"

    await client.chat([LLMMessage(role="user", content="hello")])

    assert captured["max_retries"] == 0


async def test_logged_chat_passes_response_format_to_client():
    captured = {}

    class FakeClient:
        model = "test-model"

        async def chat(self, messages, **kwargs):
            captured["messages"] = messages
            captured["kwargs"] = kwargs
            return LLMResult(content='{"ok":true}', raw=None)

    log = LoggedLLMCall()
    result = await logged_chat(
        FakeClient(),
        [LLMMessage(role="user", content="Return JSON")],
        stage="test",
        log=log,
        response_format={"type": "json_object"},
    )

    assert result.content == '{"ok":true}'
    assert captured["kwargs"]["response_format"] == {"type": "json_object"}
    assert log.entries[0]["success"] is True
