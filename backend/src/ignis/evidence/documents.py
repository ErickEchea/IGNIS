"""Page-level text access for locally downloaded source documents (PDF)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pypdfium2 as pdfium


@lru_cache(maxsize=256)
def pdf_pages(path: str) -> tuple[str, ...]:
    """Return the text of every page (1-based page i is element i-1)."""
    doc = pdfium.PdfDocument(path)
    try:
        pages: list[str] = []
        for i in range(len(doc)):
            page = doc[i]
            textpage = page.get_textpage()
            pages.append(textpage.get_text_range())
            textpage.close()
            page.close()
        return tuple(pages)
    finally:
        doc.close()


class DocumentStore:
    """Maps source ids to local PDF files and serves page text."""

    def __init__(self, raw_dir: Path, pdf_paths: dict[str, str]) -> None:
        self.raw_dir = raw_dir
        self.pdf_paths = pdf_paths  # source_id -> path relative to raw_dir

    def has_text(self, source_id: str) -> bool:
        rel = self.pdf_paths.get(source_id)
        return rel is not None and (self.raw_dir / rel).exists()

    def pages(self, source_id: str) -> tuple[str, ...] | None:
        rel = self.pdf_paths.get(source_id)
        if rel is None:
            return None
        path = self.raw_dir / rel
        if not path.exists():
            return None
        return pdf_pages(str(path))

    def page_text(self, source_id: str, page: int | None) -> str | None:
        pages = self.pages(source_id)
        if pages is None:
            return None
        if page is None:
            return "\n".join(pages)
        if not 1 <= page <= len(pages):
            return ""  # page out of range -> quote cannot be on it
        return pages[page - 1]
