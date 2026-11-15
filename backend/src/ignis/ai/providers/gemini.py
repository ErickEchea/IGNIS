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

    def resolve_model(self) -> str:
        """Use IGNIS_GEMINI_MODEL; otherwise pick a text 'flash' model actually enabled on this key."""
        if self._resolved:
            return self._resolved
        if self._model:
            self._resolved = self._model
            return self._resolved
        names: list[str] = []
        for m in self._get_client().models.list():
            name = str(getattr(m, "name", "")).removeprefix("models/")
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" in actions and "flash" in name and not any(x in name for x in _EXCLUDE):
                names.append(name)
        if not names:
            raise ProviderError("unavailable", "no text 'flash' model is enabled for this API key")

        def version(n: str) -> tuple[float, int]:
            m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
            return (float(m.group(1)) if m else 0.0, 0 if ("preview" in n or "exp" in n) else 1)

        self._resolved = sorted(names, key=version, reverse=True)[0]
        return self._resolved

    def generate_json(self, system: str, user: str, schema: dict[str, Any], timeout_s: float) -> LLMResponse:
        if not self.configured():
            raise ProviderError("auth", "GEMINI_API_KEY is not set")
        from google.genai import errors, types

        t0 = time.time()
        try:
            model = self.resolve_model()
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
        except ProviderError:
            raise
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            kind: ErrorKind = "rate_limit" if code == 429 else "auth" if code in (401, 403) else "unavailable"
            self.last_error = f"{kind}: HTTP {code}"
            raise ProviderError(kind, f"Gemini API error {code}") from exc
        except Exception as exc:
            timed_out = "timeout" in type(exc).__name__.lower() or "timed out" in str(exc).lower()
            kind2: ErrorKind = "timeout" if timed_out else "unavailable"
            self.last_error = f"{kind2}: {type(exc).__name__}"
            raise ProviderError(kind2, f"Gemini request failed: {type(exc).__name__}") from exc
        self.last_latency_s = round(time.time() - t0, 2)
        try:
            data = json.loads(resp.text or "")
        except (json.JSONDecodeError, TypeError) as exc:
            self.last_error = "invalid_output"
            raise ProviderError("invalid_output", "Gemini returned non-JSON output") from exc
        if not isinstance(data, dict):
            raise ProviderError("invalid_output", "Gemini returned a non-object JSON value")
        self.last_error = None
        return LLMResponse(data, self.name, model, self.last_latency_s)

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": self.configured(),
            "model": self.model,
            "last_latency_s": self.last_latency_s,
            "last_error": self.last_error,
        }
