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


def test_nemotron_override_uses_nvidia_reasoning_client(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "test-nvidia-key")

    client = get_llm_client("classify", model_override="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")

    assert client.model == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    assert client._extra_body() == {"chat_template_kwargs": {"enable_thinking": True, "reasoning_budget": 512}}
