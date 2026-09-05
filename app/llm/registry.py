from app.config import settings
from app.llm.base import LLMProvider
from app.llm.openrouter import OpenRouterProvider


provider: LLMProvider = OpenRouterProvider(
    settings.openrouter_api_key,
    settings.openrouter_base_url,
    settings.llm_timeout_seconds,
)


def get_llm_provider() -> LLMProvider:
    return provider
