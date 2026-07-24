from __future__ import annotations

from agent.llm.base import BaseLLM
from agent.llm.providers.dashscope_compat import DashScopeCompatLLM
from agent.llm.providers.zhipu import ZhipuLLM


class LLMFactory:
    """Factory for creating LLM provider instances."""

    _registry: dict[str, type[BaseLLM]] = {}

    @classmethod
    def register(cls, name: str, llm_cls: type[BaseLLM]) -> None:
        """Register an LLM provider class."""
        cls._registry[name] = llm_cls

    @classmethod
    def create(cls, provider_name: str, config: dict) -> BaseLLM:
        """Create an LLM instance by provider name."""
        if provider_name not in cls._registry:
            raise UnknownProviderError(f"Unknown LLM provider: {provider_name}")
        llm_cls = cls._registry[provider_name]
        return llm_cls(**config)

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._registry.keys())


class UnknownProviderError(Exception):
    """Raised when an unknown LLM provider is requested."""
    pass


# Register built-in text providers
LLMFactory.register("dashscope", DashScopeCompatLLM)
LLMFactory.register("zhipu", ZhipuLLM)

# Register realtime providers
try:
    from agent.llm.realtime.dashscope_realtime import DashScopeRealtimeLLM

    LLMFactory.register("dashscope_realtime", DashScopeRealtimeLLM)
except ImportError:
    pass
