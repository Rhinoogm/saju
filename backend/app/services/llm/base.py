from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class LLMProviderError(RuntimeError):
    pass


class LLMTimeoutError(LLMProviderError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    provider: str
    raw_metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        schema_name: str,
    ) -> LLMResponse:
        ...
