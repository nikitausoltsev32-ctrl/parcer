from app.core.config import settings
from app.services.llm.base import LLMClient


class GLMClient(LLMClient):
    base_url = "https://open.bigmodel.cn/api/paas/v4"

    def __init__(self, model: str):
        self.api_key = settings.glm_api_key
        self.model = model
