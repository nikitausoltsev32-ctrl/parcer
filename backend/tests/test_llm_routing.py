from app.core.config import settings
from app.services.llm.routing import STAGE_ROUTING, provider_has_key, resolve_stage


def _clear_yandex(monkeypatch):
    # Yandex is first in every stage chain; clear it to exercise the foreign fallback order.
    monkeypatch.setattr(settings, "yandex_api_key", "")
    monkeypatch.setattr(settings, "yandex_folder_id", "")


def test_resolve_uses_primary_when_its_key_present(monkeypatch):
    _clear_yandex(monkeypatch)
    monkeypatch.setattr(settings, "openrouter_api_key", "or-key")
    monkeypatch.setattr(settings, "nvidia_api_key", "nv-key")
    assert resolve_stage("light_ai") == ("openrouter", "openai/gpt-4o-mini")


def test_resolve_falls_back_when_primary_key_missing(monkeypatch):
    _clear_yandex(monkeypatch)
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "nvidia_api_key", "nv-key")
    assert resolve_stage("light_ai") == ("nvidia", "z-ai/glm-5.1")


def test_resolve_returns_last_when_nothing_configured(monkeypatch):
    _clear_yandex(monkeypatch)
    for attr in ("openrouter_api_key", "nvidia_api_key", "groq_api_key"):
        monkeypatch.setattr(settings, attr, "")
    provider, model = resolve_stage("url_classify")
    assert (provider, model) == STAGE_ROUTING["url_classify"][-1]


def test_resolve_prefers_yandex_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "yandex_api_key", "ya-key")
    monkeypatch.setattr(settings, "yandex_folder_id", "folder")
    monkeypatch.setattr(settings, "openrouter_api_key", "or-key")
    provider, _ = resolve_stage("light_ai")
    assert provider == "yandex"


def test_provider_has_key_reads_settings(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "")
    assert provider_has_key("groq") is False
    monkeypatch.setattr(settings, "groq_api_key", "g")
    assert provider_has_key("groq") is True
