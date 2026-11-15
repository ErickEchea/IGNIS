"""Hybrid scientific retrieval: BM25 + dense embeddings + Reciprocal Rank Fusion + cross-encoder rerank.

Works with no language model. Every hit carries document id, page and the exact chunk text, so the
Validator can check that an answer cites text that was really retrieved.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from ignis.settings import get_settings


def models_dir() -> Path:
    return get_settings().models_dir


EMBED_MODEL = "BAAI/bge-small-en-v1.5"
RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
CHUNK_CHARS = 1100
CHUNK_OVERLAP = 180
RRF_K = 60
_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
_STOP = frozenset(
    [
        "the",
        "a",
        "an",
        "of",
        "and",
        "or",
        "in",
        "on",
        "at",
        "to",
        "for",
        "by",
        "with",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "as",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "into",
        "than",
        "then",
        "there",
        "their",
        "which",
        "who",
        "what",
        "when",
        "where",
        "how",
        "why",
        "can",
        "could",
        "may",
        "might",
        "will",
        "would",
        "should",
        "do",
        "does",
        "did",
        "not",
        "no",
    ]
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


@dataclass(frozen=True)
class Chunk:
    id: str  # "<source_id>#p<page>:<n>" or "CARD:<card_id>"
    source_id: str
    page: int | None
    text: str
    kind: str  # "document" | "card"


def chunk_pages(source_id: str, pages: tuple[str, ...]) -> list[Chunk]:
    out: list[Chunk] = []
    for pno, raw in enumerate(pages, start=1):
        text = re.sub(r"\s+", " ", raw).strip()
        if len(text) < 80:
            continue
        start, n = 0, 0
        while start < len(text):
            end = min(len(text), start + CHUNK_CHARS)
            if end < len(text):  # cut at a sentence or word boundary when possible
                cut = text.rfind(". ", start + CHUNK_CHARS // 2, end)
                end = cut + 1 if cut != -1 else max(text.rfind(" ", start, end), start + CHUNK_CHARS // 2)
            piece = text[start:end].strip()
            if piece:
                out.append(Chunk(f"{source_id}#p{pno}:{n}", source_id, pno, piece, "document"))
                n += 1
            if end >= len(text):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
    return out


@dataclass
class Hit:
    chunk: Chunk
    bm25_rank: int | None
    dense_rank: int | None
    rrf: float
    rerank: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["chunk"] = asdict(self.chunk)
        return d


class HybridIndex:
    """In-memory hybrid index (corpus of ~10^4 chunks: exact cosine search is fast enough)."""

    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray | None) -> None:
        self.chunks = chunks
        self.by_id = {c.id: c for c in chunks}
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks])
        self.embeddings = embeddings  # (n, d) float32, L2-normalized, or None (BM25 only)
        self._embedder: Any = None
        self._reranker: Any = None
        self.rerank_enabled = True

    # ------------------------------------------------------------------ persistence
    @staticmethod
    def save(path: Path, chunks: list[Chunk], embeddings: np.ndarray | None) -> None:
        path.mkdir(parents=True, exist_ok=True)
        with (path / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for c in chunks:
                fh.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
        if embeddings is not None:
            np.save(path / "embeddings.npy", embeddings.astype(np.float16))
        (path / "meta.json").write_text(
            json.dumps(
                {
                    "embed_model": EMBED_MODEL,
                    "n_chunks": len(chunks),
                    "chunk_chars": CHUNK_CHARS,
                    "overlap": CHUNK_OVERLAP,
                },
                indent=1,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> HybridIndex:
        chunks = [Chunk(**json.loads(line)) for line in (path / "chunks.jsonl").open(encoding="utf-8")]
        emb_path = path / "embeddings.npy"
        emb = np.load(emb_path).astype(np.float32) if emb_path.exists() else None
        return cls(chunks, emb)

    # ------------------------------------------------------------------ models (lazy)
    def _embed_query(self, query: str) -> np.ndarray | None:
        if self.embeddings is None:
            return None
        try:
            if self._embedder is None:
                from fastembed import TextEmbedding

                self._embedder = TextEmbedding(EMBED_MODEL, cache_dir=str(models_dir()))
            vec = np.asarray(next(iter(self._embedder.query_embed([query]))), dtype=np.float32)
            return vec / (np.linalg.norm(vec) + 1e-12)
        except Exception:  # model unavailable -> BM25 only, reported in status
            self.embeddings = None
            return None

    def _rerank(self, query: str, hits: list[Hit]) -> None:
        try:
            if self._reranker is None:
                from fastembed.rerank.cross_encoder import TextCrossEncoder

                self._reranker = TextCrossEncoder(RERANK_MODEL, cache_dir=str(models_dir()))
            scores = list(self._reranker.rerank(query, [h.chunk.text for h in hits]))
            for h, s in zip(hits, scores, strict=True):
                h.rerank = float(s)
        except Exception:
            for h in hits:
                h.rerank = None

    # ------------------------------------------------------------------ search
    def search(self, query: str, k: int = 8, candidates: int = 40, rerank: bool = True) -> list[Hit]:
        toks = tokenize(query)
        ranks_bm: dict[int, int] = {}
        if toks:
            scores = self.bm25.get_scores(toks)
            top = np.argsort(-scores)[:candidates]
            ranks_bm = {int(i): r for r, i in enumerate(top) if scores[i] > 0}
        ranks_dense: dict[int, int] = {}
        qv = self._embed_query(query)
        if qv is not None and self.embeddings is not None:
            sims = self.embeddings @ qv
            top = np.argsort(-sims)[:candidates]
            ranks_dense = {int(i): r for r, i in enumerate(top)}
        fused: dict[int, float] = {}
        for ranks in (ranks_bm, ranks_dense):
            for i, r in ranks.items():
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + r + 1)
        order = sorted(fused, key=lambda i: -fused[i])[:candidates]
        hits = [Hit(self.chunks[i], ranks_bm.get(i), ranks_dense.get(i), round(fused[i], 6)) for i in order]
        if rerank and self.rerank_enabled and hits:
            pool = hits[: min(len(hits), 24)]
            self._rerank(query, pool)
            if all(h.rerank is not None for h in pool):
                pool.sort(key=lambda h: -(h.rerank or 0.0))
                hits = pool
        return hits[:k]

    @property
    def dense_available(self) -> bool:
        return self.embeddings is not None
