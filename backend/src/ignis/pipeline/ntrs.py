"""Harvest NASA Technical Reports Server (NTRS) records and public-use PDFs.

Copyright policy (NTRS ``copyright.determinationType``):

* ``PUBLIC_USE_PERMITTED``, ``GOV_PUBLIC_USE_PERMITTED``, ``GOV_PERMITTED``: PDF downloaded and
  full text indexed for retrieval.
* ``MAY_INCLUDE_COPYRIGHT_MATERIAL``: PDF downloaded **only** to verify Finding Card quotes locally;
  never indexed or redistributed.
* anything else: metadata only.
"""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any

import httpx

from ignis.pipeline.fetch import Fetcher

NTRS = "https://ntrs.nasa.gov"
PUBLIC_USE = {"PUBLIC_USE_PERMITTED", "GOV_PUBLIC_USE_PERMITTED", "GOV_PERMITTED"}
VERIFY_ONLY = {"MAY_INCLUDE_COPYRIGHT_MATERIAL"}


def record_url(ntrs_id: str) -> str:
    return f"{NTRS}/citations/{ntrs_id}"


def fetch_record(fetcher: Fetcher, ntrs_id: str) -> dict[str, Any] | None:
    try:
        path = fetcher.download(f"{NTRS}/api/citations/{ntrs_id}", f"ntrs/records/{ntrs_id}.json", "NASA-STI-metadata")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        raise
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def search_ids(fetcher: Fetcher, query: str, size: int) -> list[str]:
    url = f"{NTRS}/api/citations/search?" + urllib.parse.urlencode({"q": query, "page.size": size})
    slug = "".join(ch if ch.isalnum() else "_" for ch in query.lower()).strip("_")
    path = fetcher.download(url, f"ntrs/search/{slug}.json", "NASA-STI-metadata")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [str(r["id"]) for r in payload.get("results", [])]


def determination(record: dict[str, Any]) -> str:
    return str((record.get("copyright") or {}).get("determinationType") or "UNKNOWN")


def pdf_link(record: dict[str, Any]) -> str | None:
    for d in record.get("downloads") or []:
        links = d.get("links") or {}
        if d.get("mimetype") == "application/pdf" and links.get("pdf"):
            return f"{NTRS}{links['pdf']}"
    return None


def fetch_pdf(fetcher: Fetcher, record: dict[str, Any]) -> str | None:
    """Download the PDF when public use or local quote verification is allowed."""
    if determination(record) not in PUBLIC_USE | VERIFY_ONLY:
        return None
    link = pdf_link(record)
    if link is None:
        return None
    rel = f"ntrs/pdf/{record['id']}.pdf"
    fetcher.download(link, rel, determination(record))
    return rel


def summarize(record: dict[str, Any], pdf_rel: str | None) -> dict[str, Any]:
    authors = []
    for a in record.get("authorAffiliations") or []:
        name = ((a.get("meta") or {}).get("author") or {}).get("name")
        if name:
            authors.append(name)
    pubs = record.get("publications") or []
    date = (pubs[0].get("publicationDate") if pubs else None) or record.get("created") or ""
    return {
        "id": f"NTRS-{record['id']}",
        "ntrs_id": str(record["id"]),
        "title": record.get("title", ""),
        "authors": authors,
        "year": int(date[:4]) if date[:4].isdigit() else None,
        "sti_type": record.get("stiType", ""),
        "copyright": determination(record),
        "full_text_indexed": pdf_rel is not None and determination(record) in PUBLIC_USE,
        "pdf": pdf_rel,
        "url": record_url(str(record["id"])),
        "abstract": record.get("abstract") or "",
    }


def harvest(
    fetcher: Fetcher,
    curated_ids: list[str],
    queries: list[str],
    per_query: int,
    out_path: Path,
) -> list[dict[str, Any]]:
    ids: list[str] = list(dict.fromkeys(curated_ids))
    for q in queries:
        for rid in search_ids(fetcher, q, per_query):
            if rid not in ids:
                ids.append(rid)
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    for rid in ids:
        rec = fetch_record(fetcher, rid)
        if rec is None:
            missing.append(rid)
            continue
        pdf_rel = fetch_pdf(fetcher, rec)
        records.append(summarize(rec, pdf_rel))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"records": records, "missing_ids": missing}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return records
