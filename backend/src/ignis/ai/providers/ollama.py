"""Ollama provider (local only; not available in the cloud deployment)."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ignis.ai.providers.base import LLMResponse, ProviderError
from ignis.settings import Settings


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self.last_error: str | None = None
        self.last_latency_s: float | None = None

    @property
    def model(self) -> str:
        return self._model

    def configured(self) -> bool:
        return bool(self.base_url and self._model)

    def generate_json(self, system: str, user: str, schema: dict[str, Any], timeout_s: float) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "format": schema,  # Ollama structured outputs (JSON schema)
            "stream": False,
            "think": False,
            "options": {"temperature": 0.1, "num_ctx": 8192},
            "keep_alive": "10m",
        }
        t0 = time.time()
        try:
            r = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=timeout_s)
        except httpx.TimeoutException as exc:
            self.last_error = "timeout"
            raise ProviderError("timeout", "Ollama timed out") from exc
        except httpx.HTTPError as exc:
            self.last_error = "unavailable"
            raise ProviderError("unavailable", f"Ollama not reachable at {self.base_url}") from exc
        if r.status_code == 404:
            self.last_error = "model not found"
            raise ProviderError("unavailable", f"Ollama model {self._model} not found")
        if r.status_code >= 400:
            self.last_error = f"HTTP {r.status_code}"
            raise ProviderError("unavailable", f"Ollama error {r.status_code}")
        self.last_latency_s = round(time.time() - t0, 2)
        try:
            content = r.json()["message"]["content"]
            data = json.loads(content)
        except (KeyError, ValueError) as exc:
            self.last_error = "invalid_output"
            raise ProviderError("invalid_output", "Ollama returned non-JSON output") from exc
        if not isinstance(data, dict):
            raise ProviderError("invalid_output", "Ollama returned a non-object JSON value")
        self.last_error = None
        return LLMResponse(data, self.name, self._model, self.last_latency_s)

    def health(self) -> dict[str, Any]:
        reachable = False
        models: list[str] = []
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            reachable = r.status_code == 200
            models = [m["name"] for m in r.json().get("models", [])] if reachable else []
        except (httpx.HTTPError, ValueError):
            reachable = False
        return {
            "provider": self.name,
            "configured": self.configured(),
            "reachable": reachable,
            "model": self._model,
            "model_installed": self._model in models,
            "last_latency_s": self.last_latency_s,
            "last_error": self.last_error,
        }
