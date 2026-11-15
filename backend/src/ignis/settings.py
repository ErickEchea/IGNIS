"""Runtime configuration. Secrets live only in backend environment variables."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class LLMMode(StrEnum):
    AUTO = "AUTO"  # Gemini first, visible fallback to Ollama, then no-LLM
    CLOUD = "CLOUD"  # Gemini only
    LOCAL = "LOCAL"  # Ollama only
    NONE = "NONE"  # no language model at all (retrieval + validator + Core only)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IGNIS_",
        env_file=(REPO_ROOT / "backend" / ".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_mode: LLMMode = LLMMode.AUTO
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = ""  # empty = auto-select a text "flash" model enabled on the key
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"
    llm_timeout_s: float = 60.0

    data_dir: Path = REPO_ROOT / "data"
    models_dir: Path = REPO_ROOT / "models_cache"  # ONNX models (embeddings, reranker, NLI)
    rerank: bool = True
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
