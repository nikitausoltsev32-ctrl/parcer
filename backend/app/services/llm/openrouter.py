from app.core.config import settings
from app.services.llm.base import LLMClient


class OpenRouterClient(LLMClient):
    base_url = "https://openrouter.ai/api/v1"

    def __init__(self, model: str):
        self.api_key = settings.openrouter_api_key
        self.model = model
