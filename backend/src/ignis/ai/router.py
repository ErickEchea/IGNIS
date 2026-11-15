"""AUTO / CLOUD / LOCAL / NONE routing between providers. Every switch is recorded and shown."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ignis.ai.providers.base import LLMProvider, LLMResponse, ProviderError
from ignis.settings import LLMMode


@dataclass
class Attempt:
    provider: str
    model: str
    ok: bool
    error_kind: str | None = None
    message: str | None = None


@dataclass
class RouteResult:
    response: LLMResponse | None
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def fallback_used(self) -> bool:
        return self.response is not None and len(self.attempts) > 1


class Router:
    def __init__(self, cloud: LLMProvider | None, local: LLMProvider | None) -> None:
        self.cloud = cloud
        self.local = local

    def chain(self, mode: LLMMode) -> list[LLMProvider]:
        if mode == LLMMode.NONE:
            return []
        if mode == LLMMode.CLOUD:
            return [p for p in (self.cloud,) if p is not None]
        if mode == LLMMode.LOCAL:
            return [p for p in (self.local,) if p is not None]
        return [p for p in (self.cloud, self.local) if p is not None]

    def generate_json(
        self, mode: LLMMode, system: str, user: str, schema: dict[str, Any], timeout_s: float
    ) -> RouteResult:
        result = RouteResult(None)
        for p in self.chain(mode):
            if not p.configured():
                result.attempts.append(Attempt(p.name, p.model, False, "auth", "not configured"))
                continue
            try:
                result.response = p.generate_json(system, user, schema, timeout_s)
                result.attempts.append(Attempt(p.name, result.response.model, True))
                return result
            except ProviderError as exc:
                result.attempts.append(Attempt(p.name, p.model, False, exc.kind, str(exc)))
        return result
