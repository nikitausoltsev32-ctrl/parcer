from types import SimpleNamespace

from app.services.llm.base import LLMClient, LLMMessage


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
