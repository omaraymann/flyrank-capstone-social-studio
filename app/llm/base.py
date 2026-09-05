from dataclasses import dataclass
from typing import Protocol


class LLMError(RuntimeError):
    """A safe, provider-independent generation failure."""


@dataclass(frozen=True)
class GenerationSettings:
    model: str
    temperature: float
    top_p: float
    top_k: int | None
    max_output_tokens: int


@dataclass(frozen=True)
class LLMResult:
    variants: dict[str, str]
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMProvider(Protocol):
    name: str

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        platforms: list[str],
        settings: GenerationSettings,
    ) -> LLMResult: ...
