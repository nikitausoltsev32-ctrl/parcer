from app.core.config import settings
from app.services.llm.base import LLMClient


class QwenClient(LLMClient):
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, model: str):
        self.api_key = settings.qwen_api_key
        self.model = model
