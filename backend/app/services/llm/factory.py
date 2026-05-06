from app.core.config import settings
from app.services.llm.base import LLMClient
from app.services.llm.glm import GLMClient
from app.services.llm.groq import GroqClient
from app.services.llm.minimax import MiniMaxClient
from app.services.llm.qwen import QwenClient

_OPENAI_PROVIDERS = {
    "groq": GroqClient,
    "qwen": QwenClient,
    "glm": GLMClient,
    "minimax": MiniMaxClient,
    "openrouter": MiniMaxClient,
}

CHAT_MODEL_OPTIONS = [
    {
        "id": "groq/llama-3.3-70b-versatile",
        "label": "Llama 3.3",
        "sub": "Groq",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "api_key_setting": "groq_api_key",
    },
    {
        "id": "openrouter/minimax/minimax-m2.5:free",
        "label": "MiniMax M2",
        "sub": "OpenRouter",
        "provider": "openrouter",
        "model": "minimax/minimax-m2.5:free",
        "api_key_setting": "openrouter_api_key",
    },
]

_CHAT_MODEL_BY_ID = {option["id"]: option for option in CHAT_MODEL_OPTIONS}


def get_available_chat_models() -> list[dict[str, str]]:
    return [
        {"id": option["id"], "label": option["label"], "sub": option["sub"]}
        for option in CHAT_MODEL_OPTIONS
        if getattr(settings, option["api_key_setting"], "")
    ]


def get_llm_client(task: str, *, model_override: str | None = None) -> LLMClient:
    """task: 'chat' | 'letters' | 'classify' | 'enrich'"""
    provider = getattr(settings, f"llm_{task}_provider")
    model = getattr(settings, f"llm_{task}_model")

    if model_override:
        option = _CHAT_MODEL_BY_ID.get(model_override)
        if not option:
            raise ValueError(f"Unsupported LLM model override: {model_override}")
        provider = option["provider"]
        model = option["model"]

    if provider == "claude":
        from app.services.llm.claude import ClaudeClient
        return ClaudeClient(model=model)

    cls = _OPENAI_PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Unknown LLM provider: {provider}")
    return cls(model=model)
