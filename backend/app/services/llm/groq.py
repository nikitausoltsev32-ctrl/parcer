from app.core.config import settings
from app.services.llm.base import LLMClient


class GroqClient(LLMClient):
    base_url = "https://api.groq.com/openai/v1"

    def __init__(self, model: str):
        self.api_key = settings.groq_api_key
        self.model = model
