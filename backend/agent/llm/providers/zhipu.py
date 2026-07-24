from __future__ import annotations

from agent.llm.providers.openai_compatible import OpenAICompatibleLLM
from config.settings import settings


class ZhipuLLM(OpenAICompatibleLLM):
    """Zhipu GLM provider using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4.6v-flash",
        temperature: float = 0.7,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url or settings.ZHIPU_BASE_URL,
            model=model,
            temperature=temperature,
        )
