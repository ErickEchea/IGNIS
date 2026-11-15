# IGNIS backend image (Google Cloud Run). Build context: repository root.
#   docker build -t ignis-api .
# The retrieval index and the ONNX models are baked into the image: no downloads at request time.
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    IGNIS_LLM_MODE=CLOUD

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /usr/local/bin/uv

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src ./src
RUN uv sync --frozen --no-dev

# Data the API needs: source registry, scenarios, processed metadata and the hybrid index.
WORKDIR /app
COPY pipeline/manifests ./pipeline/manifests
COPY pipeline/cards ./pipeline/cards
COPY data/processed/ntrs_records.json data/processed/psi_catalog.json ./data/processed/
COPY data/processed/index ./data/processed/index

# Pre-download the three ONNX models (embeddings, reranker, NLI) into the image.
RUN /app/backend/.venv/bin/python -c "from ignis.evidence.rag.index import HybridIndex; \
from fastembed import TextEmbedding; from fastembed.rerank.cross_encoder import TextCrossEncoder; \
from ignis.evidence.rag.index import EMBED_MODEL, RERANK_MODEL; from ignis.settings import get_settings; \
d=str(get_settings().models_dir); TextEmbedding(EMBED_MODEL, cache_dir=d); TextCrossEncoder(RERANK_MODEL, cache_dir=d); \
from ignis.evidence.validator.nli import NliModel; NliModel()"

RUN useradd --create-home ignis && chown -R ignis /app
USER ignis
EXPOSE 8080
CMD ["sh", "-c", "/app/backend/.venv/bin/uvicorn ignis.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
