from app.core.config import settings
from app.services.llm.base import LLMClient
from app.services.llm.glm import GLMClient
from app.services.llm.glm_nvidia import GLMNvidiaClient
from app.services.llm.groq import GroqClient
from app.services.llm.openrouter import OpenRouterClient
from app.services.llm.qwen import QwenClient
from app.services.llm.routing import STAGE_ROUTING, resolve_stage

_OPENAI_PROVIDERS = {
    "groq": GroqClient,
    "qwen": QwenClient,
    "glm": GLMClient,
    "nvidia": GLMNvidiaClient,
    "openrouter": OpenRouterClient,
}

CHAT_MODEL_OPTIONS = [
    {
        "id": "openrouter/openai/gpt-4o-mini",
        "label": "GPT-4o mini",
        "sub": "OpenRouter · основной",
        "provider": "openrouter",
        "model": "openai/gpt-4o-mini",
        "api_key_setting": "openrouter_api_key",
    },
    {
        "id": "openrouter/google/gemini-2.5-flash-lite",
        "label": "Gemini 2.5 Flash Lite",
        "sub": "OpenRouter · быстрый",
        "provider": "openrouter",
        "model": "google/gemini-2.5-flash-lite",
        "api_key_setting": "openrouter_api_key",
    },
    {
        "id": "nvidia/z-ai/glm-5.1",
        "label": "GLM 5.1",
        "sub": "NVIDIA",
        "provider": "nvidia",
        "model": "z-ai/glm-5.1",
        "api_key_setting": "nvidia_api_key",
    },
    {
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "label": "Nemotron 3 Nano Omni 30B",
        "sub": "NVIDIA reasoning",
        "provider": "nvidia",
        "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "api_key_setting": "nvidia_api_key",
        "thinking": True,
    },
]

_CHAT_MODEL_BY_ID = {option["id"]: option for option in CHAT_MODEL_OPTIONS}


def get_available_chat_models() -> list[dict[str, str]]:
    return [
        {
            "id": option["id"],
            "label": option["label"],
            "sub": option["sub"],
            "provider": option["provider"],
        }
        for option in CHAT_MODEL_OPTIONS
        if getattr(settings, option["api_key_setting"], "")
    ]


def is_available_model_override(model_id: str | None) -> bool:
    if not model_id:
        return True
    option = _CHAT_MODEL_BY_ID.get(model_id)
    return bool(option and getattr(settings, option["api_key_setting"], ""))


def get_llm_client(task: str, *, model_override: str | None = None) -> LLMClient:
    """task: legacy 'chat'|'letters'|'classify'|'enrich' or a stage name from STAGE_ROUTING."""
    thinking = None

    if model_override:
        option = _CHAT_MODEL_BY_ID.get(model_override)
        if not option:
            raise ValueError(f"Unsupported LLM model override: {model_override}")
        if not getattr(settings, option["api_key_setting"], ""):
            raise ValueError(f"LLM model override is not configured: {model_override}")
        provider = option["provider"]
        model = option["model"]
        thinking = option.get("thinking")
    elif task in STAGE_ROUTING:
        provider, model = resolve_stage(task)
    else:
        provider = getattr(settings, f"llm_{task}_provider")
        model = getattr(settings, f"llm_{task}_model")

    if provider == "claude":
        from app.services.llm.claude import ClaudeClient
        return ClaudeClient(model=model)

    cls = _OPENAI_PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Unknown LLM provider: {provider}")
    kwargs = {}
    if provider == "nvidia" and thinking is not None:
        kwargs["thinking"] = thinking
    return cls(model=model, **kwargs)
