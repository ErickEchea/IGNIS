"""``ignis-pipeline``: one command to rebuild IGNIS from raw sources.

Steps
-----
fetch   download PSI catalog + tables and NTRS records/PDFs into data/raw (immutable, sha256)
verify  check every raw file against MANIFEST.json
build   parse, verify Finding Cards against their sources, build the ledger and static bundles
all     fetch + verify + build
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import yaml

from ignis.pipeline import ntrs, psi
from ignis.pipeline.fetch import Fetcher, Manifest
from ignis.settings import REPO_ROOT, get_settings

SOURCES_YAML = REPO_ROOT / "pipeline" / "manifests" / "sources.yaml"


def load_sources() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
    return data


def cmd_fetch() -> None:
    settings = get_settings()
    sources = load_sources()
    fetcher = Fetcher(settings.raw_dir)
    try:
        records = psi.harvest(fetcher, settings.processed_dir / "psi_catalog.json")
        print(f"PSI: {len(records)} Combustion Science investigations")
        cfg = sources["ntrs"]
        ntrs_records = ntrs.harvest(
            fetcher,
            [c["id"] for c in cfg["curated"]],
            cfg["queries"],
            int(cfg["per_query"]),
            settings.processed_dir / "ntrs_records.json",
        )
        n_pdf = sum(1 for r in ntrs_records if r["full_text_indexed"])
        print(f"NTRS: {len(ntrs_records)} records, {n_pdf} public-use PDFs downloaded")
    finally:
        fetcher.close()


def cmd_verify() -> int:
    manifest = Manifest(get_settings().raw_dir)
    bad = manifest.verify()
    print(f"Manifest: {len(manifest.entries)} files, {len(bad)} mismatches")
    for rel in bad:
        print(f"  MISMATCH {rel}")
    return 1 if bad else 0


def cmd_build() -> int:
    from ignis.pipeline.build import build_all

    return build_all()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ignis-pipeline", description=__doc__)
    parser.add_argument("step", choices=["fetch", "verify", "build", "all"])
    args = parser.parse_args(argv)
    code = 0
    if args.step in ("fetch", "all"):
        cmd_fetch()
    if args.step in ("verify", "all"):
        code = cmd_verify()
    if args.step in ("build", "all") and code == 0:
        code = cmd_build()
    sys.exit(code)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])


