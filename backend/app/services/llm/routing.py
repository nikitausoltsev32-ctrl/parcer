from app.core.config import settings

# provider -> settings attribute name for API key
_PROVIDER_KEY_ATTR = {
    "openrouter": "openrouter_api_key",
    "nvidia": "nvidia_api_key",
    "groq": "groq_api_key",
    "qwen": "qwen_api_key",
    "glm": "glm_api_key",
    "claude": "anthropic_api_key",
}

# Stage -> ordered list [(provider, model)].
# Resolver picks first entry whose key is set.
STAGE_ROUTING: dict[str, list[tuple[str, str]]] = {
    "query_gen":      [("openrouter", "google/gemini-2.0-flash-001"), ("nvidia", "z-ai/glm-5.1")],
    "lead_discovery": [("openrouter", "perplexity/sonar"), ("nvidia", "z-ai/glm-5.1")],
    "url_classify":   [
        ("openrouter", "google/gemini-2.0-flash-8b"),
        ("groq", "llama-3.3-70b-versatile"),
        ("nvidia", "z-ai/glm-5.1"),
    ],
    "light_ai":       [("openrouter", "deepseek/deepseek-chat"), ("nvidia", "z-ai/glm-5.1")],
    "deep_ai":        [("openrouter", "deepseek/deepseek-chat"), ("nvidia", "z-ai/glm-5.1")],
    "outreach":       [("openrouter", "deepseek/deepseek-chat"), ("nvidia", "z-ai/glm-5.1")],
    "inbox_classify": [("openrouter", "google/gemini-2.0-flash-8b"), ("nvidia", "z-ai/glm-5.1")],
}


def provider_has_key(provider: str) -> bool:
    attr = _PROVIDER_KEY_ATTR.get(provider)
    return bool(attr and getattr(settings, attr, ""))


def resolve_stage(stage: str) -> tuple[str, str]:
    chain = STAGE_ROUTING[stage]
    for provider, model in chain:
        if provider_has_key(provider):
            return provider, model
    return chain[-1]
