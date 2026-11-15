"""Build the hybrid retrieval index from full-text-indexable sources and verified Finding Cards."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ignis.evidence.cards import load_cards
from ignis.evidence.documents import pdf_pages
from ignis.evidence.rag.index import EMBED_MODEL, Chunk, HybridIndex, chunk_pages
from ignis.pipeline.build import CARDS_DIR, build_sources
from ignis.settings import get_settings


def card_chunks() -> list[Chunk]:
    out = []
    for c in load_cards(CARDS_DIR):
        text = f'{c.claim} Source quote: "{c.provenance.quote}"'
        out.append(Chunk(f"CARD:{c.id}", c.provenance.source_id, c.provenance.page, text, "card"))
    return out


def build_index(out_dir: Path | None = None, *, embed: bool = True) -> Path:
    s = get_settings()
    out = out_dir or (s.processed_dir / "index")
    sources, _ = build_sources(s.processed_dir, s.raw_dir)
    chunks: list[Chunk] = card_chunks()
    for src in sources:
        if src.full_text_indexed and src.raw_path:
            chunks.extend(chunk_pages(src.id, pdf_pages(str(s.raw_dir / src.raw_path))))
    emb = None
    if embed:
        from fastembed import TextEmbedding

        t0 = time.time()
        model = TextEmbedding(EMBED_MODEL, cache_dir=str(s.models_dir))
        vecs = np.asarray(list(model.passage_embed([c.text for c in chunks], batch_size=64)), dtype=np.float32)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
        emb = vecs
        print(f"Embedded {len(chunks)} chunks in {time.time() - t0:.0f} s")
    HybridIndex.save(out, chunks, emb)
    print(f"Index: {len(chunks)} chunks ({sum(c.kind == 'card' for c in chunks)} card chunks) -> {out}")
    return out


if __name__ == "__main__":  # pragma: no cover
    build_index()
