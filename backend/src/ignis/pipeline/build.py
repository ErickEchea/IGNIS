"""Build step: sources registry -> verified Finding Cards -> ledger (DuckDB) -> static bundles."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import yaml

from ignis.core.analysis import build_analysis
from ignis.evidence.cards import load_cards, verify_all
from ignis.evidence.documents import DocumentStore, pdf_pages
from ignis.evidence.scenarios import load_scenarios, verify_scenario
from ignis.evidence.schema import FindingCard, Source
from ignis.pipeline import datasets as ds
from ignis.pipeline.fetch import Manifest
from ignis.settings import REPO_ROOT, get_settings

CARDS_DIR = REPO_ROOT / "pipeline" / "cards"
SOURCES_YAML = REPO_ROOT / "pipeline" / "manifests" / "sources.yaml"
SCENARIOS_YAML = REPO_ROOT / "pipeline" / "manifests" / "scenarios.yaml"
STATIC_DIR = REPO_ROOT / "frontend" / "public" / "data"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_sources(processed: Path, raw: Path) -> tuple[list[Source], dict[str, str]]:
    """Registry of every citable source + map of source_id -> local PDF (raw-relative)."""
    manifest = Manifest(raw)
    sources: list[Source] = []
    pdfs: dict[str, str] = {}

    registry = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
    excluded = {f"NTRS-{x['id']}" for x in registry["ntrs"].get("exclude_full_text", [])}
    ntrs_path = processed / "ntrs_records.json"
    if ntrs_path.exists():
        for r in _read_json(ntrs_path)["records"]:
            entry = manifest.entries.get(r["pdf"]) if r["pdf"] else None
            sources.append(
                Source(
                    id=r["id"],
                    title=r["title"],
                    authors=r["authors"],
                    year=r["year"],
                    url=r["url"],
                    license=f"NTRS {r['copyright']}",
                    full_text_indexed=r["full_text_indexed"] and r["id"] not in excluded,
                    raw_path=r["pdf"],
                    sha256=entry.sha256 if entry else None,
                )
            )
            if r["pdf"]:
                pdfs[r["id"]] = r["pdf"]

    for ext in registry.get("external", []):
        rel = ext.get("local_pdf")
        entry = manifest.entries.get(rel) if rel else None
        doi = ext["id"][4:] if ext["id"].startswith("DOI-") else None
        sources.append(
            Source(
                id=ext["id"],
                title=ext["title"],
                url=ext["url"],
                doi=doi,
                license=ext["license"],
                full_text_indexed=bool(ext.get("index_full_text", False)) and entry is not None,
                raw_path=rel if entry else None,
                sha256=entry.sha256 if entry else None,
            )
        )
        if rel and entry:
            pdfs[ext["id"]] = rel

    catalog_path = processed / "psi_catalog.json"
    if catalog_path.exists():
        for inv in _read_json(catalog_path):
            sources.append(
                Source(
                    id=inv["accession"],
                    title=f"{inv['acronym'] or inv['accession']}: {inv['title']}",
                    url=inv["url"],
                    doi=inv["doi"] or None,
                    license=inv["license"] or "UNKNOWN",
                )
            )
    return sources, pdfs


def card_record(card: FindingCard) -> dict[str, Any]:
    data = card.model_dump(mode="json")
    lo, hi = card.gravity_bounds
    data["gravity_lo"] = lo
    data["gravity_hi"] = hi
    return data


def write_ledger(db_path: Path, sources: list[Source], cards: list[FindingCard],
                 catalog: list[dict[str, Any]]) -> None:
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            "CREATE TABLE sources (id VARCHAR PRIMARY KEY, title VARCHAR, year INTEGER, url VARCHAR,"
            " doi VARCHAR, license VARCHAR, full_text_indexed BOOLEAN, sha256 VARCHAR)"
        )
        con.executemany(
            "INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(s.id, s.title, s.year, s.url, s.doi, s.license, s.full_text_indexed, s.sha256)
             for s in sources],
        )
        con.execute(
            "CREATE TABLE cards (id VARCHAR PRIMARY KEY, claim VARCHAR, material VARCHAR,"
            " material_class VARCHAR, platform VARCHAR, measured_variable VARCHAR,"
            " gravity_lo DOUBLE, gravity_hi DOUBLE, o2 DOUBLE, pressure_pa DOUBLE, flow_m_s DOUBLE,"
            " value_si DOUBLE, data_type VARCHAR, epistemic VARCHAR, confidence VARCHAR,"
            " campaign_id VARCHAR, source_id VARCHAR, page INTEGER, quote VARCHAR)"
        )
        rows = []
        for c in cards:
            lo, hi = c.gravity_bounds
            rows.append((
                c.id, c.claim, c.material, c.material_class, c.platform.value, c.measured_variable,
                lo, hi,
                c.o2.value_si if c.o2 else None,
                c.pressure.value_si if c.pressure else None,
                c.flow_velocity.value_si if c.flow_velocity else None,
                c.value.value_si if c.value else None,
                c.data_type.value, c.epistemic.value, c.confidence, c.campaign_id,
                c.provenance.source_id, c.provenance.page, c.provenance.quote,
            ))
        placeholders = ", ".join("?" * 19)  # fixed count of bound parameters, no user input
        con.executemany(f"INSERT INTO cards VALUES ({placeholders})", rows)  # noqa: S608
        con.execute(
            "CREATE TABLE psi_investigations (accession VARCHAR PRIMARY KEY, acronym VARCHAR,"
            " title VARCHAR, project_type VARCHAR, platform VARCHAR, gravity_regime VARCHAR,"
            " start_date VARCHAR, end_date VARCHAR, doi VARCHAR, license VARCHAR,"
            " total_file_size_bytes BIGINT, n_publications INTEGER)"
        )
        con.executemany(
            "INSERT INTO psi_investigations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(i["accession"], i["acronym"], i["title"], i["project_type"], i["platform"],
              i["gravity_regime"], i["start_date"], i["end_date"], i["doi"], i["license"],
              i["total_file_size_bytes"], i["n_publications"]) for i in catalog],
        )
    finally:
        con.close()


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def build_all(*, strict: bool = True) -> int:
    settings = get_settings()
    processed, raw = settings.processed_dir, settings.raw_dir
    sources, pdfs = build_sources(processed, raw)
    known = {s.id for s in sources}
    store = DocumentStore(raw, pdfs)

    cards = load_cards(CARDS_DIR)
    results = verify_all(cards, known, store.page_text)
    failed = [r for r in results if not r.passed]
    unchecked = [r for r in results if r.quote_on_page is None]
    print(f"Cards: {len(cards)} loaded, {len(failed)} failed verification, "
          f"{len(unchecked)} quote-unchecked (source text not available locally)")
    for r in failed:
        print(f"  FAIL {r.card_id}: {'; '.join(r.messages)}")
    if failed and strict:
        return 1
    good_ids = {r.card_id for r in results if r.passed}
    verified = [c for c in cards if c.id in good_ids]

    scenarios = load_scenarios(SCENARIOS_YAML)
    scenario_rows = []
    for sc in scenarios:
        ok, msg = verify_scenario(sc, known, store.page_text)
        print(f"Scenario {sc.id}: {'OK' if ok else 'FAIL'} ({msg})")
        if not ok and strict:
            return 1
        scenario_rows.append({**sc.model_dump(mode="json"), "derived": sc.derived(), "verification": msg})

    catalog_path = processed / "psi_catalog.json"
    catalog: list[dict[str, Any]] = _read_json(catalog_path) if catalog_path.exists() else []
    write_ledger(processed / "ledger.duckdb", sources, verified, catalog)

    used_sources = (
        {c.provenance.source_id for c in verified}
        | {i["accession"] for i in catalog}
        | {sc.provenance.source_id for sc in scenarios if sc.provenance}
    )
    built_at = datetime.now(UTC).isoformat(timespec="seconds")
    _dump(STATIC_DIR / "cards.json", {"built_at": built_at, "cards": [card_record(c) for c in verified]})
    _dump(STATIC_DIR / "sources.json", {
        "built_at": built_at,
        "sources": [s.model_dump(mode="json") for s in sources if s.id in used_sources],
    })
    _dump(STATIC_DIR / "psi_catalog.json", {"built_at": built_at, "investigations": catalog})
    _dump(STATIC_DIR / "scenarios.json", {"built_at": built_at, "scenarios": scenario_rows})

    flex = ds.parse_flex(raw)
    bass2, saffire = ds.parse_bass2(raw), ds.parse_saffire(raw)
    tp_pdf = raw / "ntrs" / "pdf" / "20150023456.pdf"
    cross = ds.crosscheck_flex(flex, pdf_pages(str(tp_pdf))) if tp_pdf.exists() else None
    _dump(STATIC_DIR / "datasets.json", {
        "built_at": built_at,
        "flex": [r.as_record() for r in flex],
        "bass2": bass2,
        "saffire": saffire,
        "flex_crosscheck": None if cross is None else {
            "source_a": "PSI-69 experimental table (CSV)", "source_b": f"{ds.FLEX_TP_SOURCE} result tables",
            "join_key": "FLEX identifier",
            "n_csv": cross.n_csv, "n_tp": cross.n_tp, "n_compared": cross.n_compared,
            "n_identical": cross.n_identical, "mismatches": cross.mismatches,
            "only_in_tp": cross.only_in_tp, "only_in_csv": cross.only_in_csv,
        },
        "quality_log": [vars(q) for q in ds.QUALITY_LOG],
    })
    analysis = build_analysis(
        verified, scenarios, {"flex": [r.as_record() for r in flex], "bass2": bass2, "saffire": saffire}
    )
    _dump(STATIC_DIR / "analysis.json", {"built_at": built_at, **analysis})
    _dump(STATIC_DIR / "verification.json", {
        "built_at": built_at,
        "n_cards": len(cards),
        "n_passed": len(verified),
        "results": [
            {"card_id": r.card_id, "passed": r.passed, "quote_on_page": r.quote_on_page,
             "numbers_in_quote": r.numbers_in_quote, "messages": r.messages}
            for r in results
        ],
    })
    print(
        f"Ledger + static bundles written ({len(verified)} verified cards, "
        f"{len(catalog)} PSI investigations)"
    )
    return 0
