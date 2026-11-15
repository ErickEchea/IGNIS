"""Assemble the Copilot from settings and on-disk artifacts (lazily, once per process)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ignis.ai.copilot import Copilot
from ignis.ai.providers.gemini import GeminiProvider
from ignis.ai.providers.ollama import OllamaProvider
from ignis.ai.router import Router
from ignis.evidence.rag.index import HybridIndex
from ignis.evidence.validator.nli import get_nli
from ignis.pipeline.build import build_sources
from ignis.settings import get_settings


@lru_cache(maxsize=1)
def get_router() -> Router:
    s = get_settings()
    return Router(GeminiProvider(s), OllamaProvider(s))


@lru_cache(maxsize=1)
def get_index() -> HybridIndex:
    idx = HybridIndex.load(get_settings().processed_dir / "index")
    idx.rerank_enabled = get_settings().rerank
    return idx


@lru_cache(maxsize=1)
def get_copilot() -> Copilot:
    s = get_settings()
    sources, _ = build_sources(s.processed_dir, s.raw_dir)
    return Copilot(
        index=get_index(),
        router=get_router(),
        registry={x.id for x in sources},
        registry_dois={x.id: x.doi for x in sources if x.doi},
        source_urls={x.id: x.url for x in sources},
        nli=get_nli(),
        timeout_s=s.llm_timeout_s,
    )


def status() -> dict[str, Any]:
    s = get_settings()
    r = get_router()
    idx_ok, n_chunks, dense = True, 0, False
    try:
        idx = get_index()
        n_chunks, dense = len(idx.chunks), idx.dense_available
    except FileNotFoundError:
        idx_ok = False
    return {
        "mode": s.llm_mode.value,
        "providers": [r.cloud.health() if r.cloud else None, r.local.health() if r.local else None],
        "rag": {
            "index_loaded": idx_ok,
            "n_chunks": n_chunks,
            "dense_embeddings": dense,
            "n_documents": len({c.source_id for c in get_index().chunks}) if idx_ok else 0,
        },
        "validator": {"nli_loaded": get_nli() is not None},
    }
