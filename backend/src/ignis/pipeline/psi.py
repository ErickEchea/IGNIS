"""Harvest NASA Physical Sciences Informatics (PSI) combustion investigations.

PSI renders in the browser; its data come from a JSON web service (``/geode-py/ws``). The service
is public but undocumented, so every raw response is snapshotted under ``data/raw/psi`` with a
sha256 in the manifest. Investigation data are released under CC0-1.0 (field ``licenseIdentifier``).
"""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any

from ignis.pipeline.fetch import Fetcher

PSI_API = "https://psi.nasa.gov/geode-py/ws"
PSI_PAGE = "https://psi.nasa.gov/physci/repo/data/investigations/{acc}"
SEARCH_TERMS = ("combustion", "flame", "fire", "flammability", "smoke")
COMBUSTION_AREA = "Combustion Science"


def search_accessions(fetcher: Fetcher) -> list[str]:
    """Union of PSI searches, filtered to Research Area == Combustion Science."""
    found: set[str] = set()
    for term in SEARCH_TERMS:
        url = f"{PSI_API}/repo/search?" + urllib.parse.urlencode({"term": term, "size": 200})
        rel = f"psi/search_{term}.json"
        path = fetcher.download(url, rel, "CC0-1.0")
        payload = json.loads(path.read_text(encoding="utf-8"))
        for hit in payload["hits"]["hits"]:
            src = hit["_source"]
            if src.get("Research Area") == COMBUSTION_AREA:
                found.add(src["Accession"])
    return sorted(found, key=lambda a: int(a.split("-")[1]))


def fetch_investigation(fetcher: Fetcher, accession: str) -> dict[str, Any]:
    rel = f"psi/investigations/{accession}.json"
    path = fetcher.download(f"{PSI_API}/repo/investigations/{accession}", rel, "CC0-1.0")
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def fetch_tables(fetcher: Fetcher, accession: str, detail: dict[str, Any]) -> list[str]:
    """Download the small 'Experimental table' CSV files (the numeric test matrices)."""
    rels: list[str] = []
    for item in detail.get("experimentalTable") or []:
        name = item.get("file_name")
        if not name or item.get("restricted") or int(item.get("file_size") or 0) > 5_000_000:
            continue
        url = f"{PSI_API}/studies/{accession}/download?" + urllib.parse.urlencode({"file": name})
        rel = f"psi/tables/{name}"
        fetcher.download(url, rel, detail.get("licenseIdentifier") or "UNKNOWN")
        rels.append(rel)
    return rels


def _person_names(detail: dict[str, Any]) -> list[dict[str, str]]:
    """Names, roles and affiliations only (no e-mail or phone numbers are republished)."""
    people = []
    for c in detail.get("contacts") or []:
        roles = ", ".join(r.get("annotationValue", "") for r in c.get("roles") or [])
        name = " ".join(p for p in (c.get("firstName"), c.get("lastName")) if p).strip()
        if name:
            people.append({"name": name, "role": roles, "affiliation": c.get("affiliation", "")})
    return people


def catalog_record(detail: dict[str, Any], tables: list[str]) -> dict[str, Any]:
    acc = detail["accession"]
    platform = detail.get("flightProgram") or ""
    project_type = detail.get("projectType") or ""
    return {
        "accession": acc,
        "acronym": detail.get("investigationAcronym") or "",
        "title": detail.get("title") or "",
        "project_type": project_type,
        "platform": platform,
        "hardware": detail.get("experimentHardware") or "",
        "sub_area": detail.get("subResearchArea") or "",
        "start_date": detail.get("investigationStartDate") or "",
        "end_date": detail.get("investigationEndDate") or "",
        "objective": detail.get("objective") or "",
        "hypothesis": detail.get("hypothesis") or "",
        "approach": detail.get("approach") or "",
        "doi": detail.get("doi") or "",
        "license": detail.get("licenseIdentifier") or "",
        "total_file_size_bytes": int(detail.get("totalFileSize") or 0),
        "n_publications": len(detail.get("publications") or []),
        "people": _person_names(detail),
        "tables": tables,
        "url": PSI_PAGE.format(acc=acc),
        # Gravity coverage, derived from platform metadata. PSI flight data are low-gravity
        # (ISS / Cygnus); ground investigations are 1 g or computational.
        "gravity_regime": ("microgravity" if project_type == "Microgravity Investigation" else "ground_or_model"),
    }


def harvest(fetcher: Fetcher, out_path: Path) -> list[dict[str, Any]]:
    records = []
    for acc in search_accessions(fetcher):
        detail = fetch_investigation(fetcher, acc)
        tables = fetch_tables(fetcher, acc, detail)
        records.append(catalog_record(detail, tables))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return records
