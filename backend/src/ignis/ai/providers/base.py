"""Provider-agnostic interface for language models. The rest of IGNIS depends only on this."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

ErrorKind = Literal["rate_limit", "timeout", "unavailable", "invalid_output", "auth", "other"]


class ProviderError(Exception):
    def __init__(self, kind: ErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class LLMResponse:
    data: dict[str, Any]
    provider: str
    model: str
    latency_s: float


class LLMProvider(Protocol):
    name: str

    @property
    def model(self) -> str: ...

    def configured(self) -> bool: ...

    def generate_json(self, system: str, user: str, schema: dict[str, Any], timeout_s: float) -> LLMResponse:
        """Return a JSON object conforming to ``schema`` or raise :class:`ProviderError`."""
        ...

    def health(self) -> dict[str, Any]: ...
