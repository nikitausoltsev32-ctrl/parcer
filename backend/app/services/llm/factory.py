from app.core.config import settings
from app.services.llm.base import LLMClient
from app.services.llm.glm import GLMClient
from app.services.llm.groq import GroqClient
from app.services.llm.minimax import MiniMaxClient
from app.services.llm.qwen import QwenClient

_OPENAI_PROVIDERS = {"groq": GroqClient, "qwen": QwenClient, "glm": GLMClient, "minimax": MiniMaxClient}


def get_llm_client(task: str) -> LLMClient:
    """task: 'chat' | 'letters' | 'classify' | 'enrich'"""
    provider = getattr(settings, f"llm_{task}_provider")
    model = getattr(settings, f"llm_{task}_model")

    if provider == "claude":
        from app.services.llm.claude import ClaudeClient
        return ClaudeClient(model=model)

    cls = _OPENAI_PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Unknown LLM provider: {provider}")
    return cls(model=model)
