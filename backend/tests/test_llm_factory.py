from app.core.config import Settings, settings
from app.services.llm.factory import get_available_chat_models, get_llm_client, is_available_model_override


def test_default_llm_routing_uses_glm_via_nvidia():
    assert Settings.model_fields["llm_chat_provider"].default == "nvidia"
    assert Settings.model_fields["llm_chat_model"].default == "z-ai/glm-5.1"
    assert Settings.model_fields["llm_letters_provider"].default == "nvidia"
    assert Settings.model_fields["llm_letters_model"].default == "z-ai/glm-5.1"
    assert Settings.model_fields["llm_classify_provider"].default == "nvidia"
    assert Settings.model_fields["llm_classify_model"].default == "z-ai/glm-5.1"
    assert Settings.model_fields["llm_enrich_provider"].default == "nvidia"
    assert Settings.model_fields["llm_enrich_model"].default == "z-ai/glm-5.1"


def test_available_chat_models_excludes_dead_minimax_option(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "test-nvidia-key")
    monkeypatch.setattr(settings, "openrouter_api_key", "old-openrouter-key")
    monkeypatch.setattr(settings, "groq_api_key", "old-groq-key")

    models = get_available_chat_models()

    assert models == [
        {"id": "nvidia/z-ai/glm-5.1", "label": "GLM 5.1", "sub": "NVIDIA"},
        {
            "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "label": "Nemotron 3 Nano Omni 30B",
            "sub": "NVIDIA reasoning",
        },
    ]
    assert is_available_model_override("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning") is True


def test_available_chat_models_returns_empty_list_without_nvidia_key(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "")

    assert get_available_chat_models() == []
    assert is_available_model_override("nvidia/z-ai/glm-5.1") is False
    assert is_available_model_override("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning") is False


def test_nemotron_override_uses_nvidia_reasoning_client(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "test-nvidia-key")

    client = get_llm_client("classify", model_override="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")

    assert client.model == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    assert client._extra_body() == {"chat_template_kwargs": {"enable_thinking": True, "reasoning_budget": 512}}


def test_openrouter_client_uses_openrouter_base_and_key(monkeypatch):
    from app.services.llm.openrouter import OpenRouterClient
    monkeypatch.setattr(settings, "openrouter_api_key", "or-test-key")
    client = OpenRouterClient(model="deepseek/deepseek-chat")
    assert client.base_url == "https://openrouter.ai/api/v1"
    assert client.api_key == "or-test-key"
    assert client.model == "deepseek/deepseek-chat"


def test_stage_routing_picks_openrouter_for_light_ai(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "or-key")
    monkeypatch.setattr(settings, "nvidia_api_key", "nv-key")
    client = get_llm_client("light_ai")
    assert client.base_url == "https://openrouter.ai/api/v1"
    assert client.model == "deepseek/deepseek-chat"


def test_stage_routing_falls_back_to_nvidia_without_openrouter(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "nvidia_api_key", "nv-key")
    client = get_llm_client("light_ai")
    assert client.model == "z-ai/glm-5.1"


def test_legacy_task_classify_unchanged(monkeypatch):
    # Legacy tasks not in STAGE_ROUTING read settings.llm_classify_*
    client = get_llm_client("classify")
    assert client.model == "z-ai/glm-5.1"
