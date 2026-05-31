from app.core.config import settings
from app.services.llm.routing import STAGE_ROUTING, provider_has_key, resolve_stage


def test_resolve_uses_primary_when_its_key_present(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "or-key")
    monkeypatch.setattr(settings, "nvidia_api_key", "nv-key")
    assert resolve_stage("light_ai") == ("openrouter", "deepseek/deepseek-chat")


def test_resolve_falls_back_when_primary_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "nvidia_api_key", "nv-key")
    assert resolve_stage("light_ai") == ("nvidia", "z-ai/glm-5.1")


def test_resolve_returns_last_when_nothing_configured(monkeypatch):
    for attr in ("openrouter_api_key", "nvidia_api_key", "groq_api_key"):
        monkeypatch.setattr(settings, attr, "")
    provider, model = resolve_stage("url_classify")
    assert (provider, model) == STAGE_ROUTING["url_classify"][-1]


def test_provider_has_key_reads_settings(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "")
    assert provider_has_key("groq") is False
    monkeypatch.setattr(settings, "groq_api_key", "g")
    assert provider_has_key("groq") is True
