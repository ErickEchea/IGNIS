"""FastAPI application entry point."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ignis import __version__
from ignis.settings import LLMMode, get_settings


class CopilotRequest(BaseModel):
    question: str = Field(min_length=3, max_length=600)
    mode: LLMMode | None = None


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="IGNIS API",
        version=__version__,
        description="Space Fire Intelligence - evidence engine for partial-gravity fire safety.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        from ignis.ai.engine import status as engine_status

        return {"version": __version__, **engine_status()}

    @app.get("/api/search")
    def search(q: str, k: int = 8) -> dict[str, Any]:
        from ignis.ai.engine import get_index

        if not 2 <= len(q) <= 300:
            raise HTTPException(422, "query must be 2-300 characters")
        try:
            hits = get_index().search(q, k=min(max(k, 1), 20))
        except FileNotFoundError as exc:
            raise HTTPException(503, "retrieval index not built") from exc
        return {"query": q, "hits": [h.to_dict() for h in hits]}

    @app.post("/api/copilot")
    def copilot(req: CopilotRequest) -> dict[str, Any]:
        from ignis.ai.engine import get_copilot

        try:
            cp = get_copilot()
        except FileNotFoundError as exc:
            raise HTTPException(503, "retrieval index not built") from exc
        return cp.answer(req.question, req.mode or settings.llm_mode)

    return app


app = create_app()
