"""Google Gemini provider (cloud). The API key lives only in the backend environment."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from ignis.ai.providers.base import ErrorKind, LLMResponse, ProviderError
from ignis.settings import Settings

_EXCLUDE = ("image", "tts", "audio", "live", "embedding", "aqa", "vision", "learnlm", "native")


class GeminiProvider:
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self._key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
        self._model = settings.gemini_model.strip()
        self._client: Any = None
        self._resolved: str | None = None
        self._candidates: list[str] | None = None
        self.skipped: list[str] = []
        self.last_error: str | None = None
        self.last_latency_s: float | None = None

    def configured(self) -> bool:
        return bool(self._key)

    def _get_client(self) -> Any:
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._key)
        return self._client

    @property
    def model(self) -> str:
        return self._resolved or self._model or "(auto)"

    def candidates(self) -> list[str]:
        """IGNIS_GEMINI_MODEL if set; otherwise text 'flash' models enabled on this key, best first."""
        if self._candidates is not None:
            return self._candidates
        if self._model:
            self._candidates = [self._model]
            return self._candidates
        names: list[str] = []
        for m in self._get_client().models.list():
            name = str(getattr(m, "name", "")).removeprefix("models/")
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" in actions and "flash" in name and not any(x in name for x in _EXCLUDE):
                names.append(name)
        if not names:
            raise ProviderError("unavailable", "no text 'flash' model is enabled for this API key")

        def version(n: str) -> tuple[float, int, int]:
            m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
            stable = 0 if ("preview" in n or "exp" in n) else 1
            full = 0 if "lite" in n else 1  # prefer the full flash model over flash-lite
            return (float(m.group(1)) if m else 0.0, stable, full)

        self._candidates = sorted(names, key=version, reverse=True)
        return self._candidates

    def resolve_model(self) -> str:
        return self._resolved or self.candidates()[0]

    def generate_json(self, system: str, user: str, schema: dict[str, Any], timeout_s: float) -> LLMResponse:
        """Try the sticky model first, then other enabled flash models on 404/5xx (all attempts recorded)."""
        if not self.configured():
            raise ProviderError("auth", "GEMINI_API_KEY is not set")
        from google.genai import errors, types

        order = self.candidates()
        if self._resolved in order:
            order = [self._resolved] + [m for m in order if m != self._resolved]
        self.skipped = []
        last: ProviderError | None = None
        for model in order[:4]:
            t0 = time.time()
            try:
                resp = self._get_client().models.generate_content(
                    model=model,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        temperature=0.1,
                        http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
                    ),
                )
            except errors.APIError as exc:
                code = getattr(exc, "code", None)
                if code in (401, 403):
                    self.last_error = f"auth: HTTP {code}"
                    raise ProviderError("auth", f"Gemini API error {code}") from exc
                kind: ErrorKind = "rate_limit" if code == 429 else "unavailable"
                self.skipped.append(f"{model}: HTTP {code}")
                last = ProviderError(kind, f"Gemini API error {code} ({model})")
                continue
            except Exception as exc:
                timed_out = "timeout" in type(exc).__name__.lower() or "timed out" in str(exc).lower()
                kind2: ErrorKind = "timeout" if timed_out else "unavailable"
                self.skipped.append(f"{model}: {type(exc).__name__}")
                last = ProviderError(kind2, f"Gemini request failed: {type(exc).__name__} ({model})")
                continue
            self.last_latency_s = round(time.time() - t0, 2)
            try:
                data = json.loads(resp.text or "")
            except (json.JSONDecodeError, TypeError) as exc:
                self.last_error = "invalid_output"
                raise ProviderError("invalid_output", "Gemini returned non-JSON output") from exc
            if not isinstance(data, dict):
                raise ProviderError("invalid_output", "Gemini returned a non-object JSON value")
            self._resolved = model
            self.last_error = None
            return LLMResponse(data, self.name, model, self.last_latency_s)
        self.last_error = "; ".join(self.skipped)
        raise last or ProviderError("unavailable", "no Gemini model responded")

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": self.configured(),
            "model": self.model,
            "candidates": self._candidates,
            "skipped_last_call": self.skipped,
            "last_latency_s": self.last_latency_s,
            "last_error": self.last_error,
        }
