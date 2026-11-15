"""Parse the small PSI experimental tables into normalized, quality-flagged records.

Every header or unit correction is logged in ``QUALITY_LOG`` with the source that justifies it.
FLEX rows are additionally cross-checked, field by field, against the tables printed in
NASA/TP-2015-216046 (NTRS 20150023456): a deterministic agreement test between two NASA sources.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ignis.core.units import to_si
from ignis.evidence.cards import normalize_text

TABLES = Path("psi") / "tables"
FLEX_CSV = TABLES / "PSI-69_Experimental table_FLEX.csv"
BASS2_CSV = TABLES / "PSI-25_Experimental table_BASS-II.csv"
SAFFIRE_CSV = {
    "PSI-98": TABLES / "PSI-98_Experimental table_SAFFIRE-1.csv",
    "PSI-99": TABLES / "PSI-99_Experimental table_SAFFIRE-2.csv",
    "PSI-100": TABLES / "PSI-100_Experimental table_SAFFIRE-3.csv",
}
FLEX_TP_SOURCE = "NTRS-20150023456"


@dataclass
class QualityIssue:
    dataset: str
    issue: str
    action: str
    evidence: str  # source_id + page, or "internal inconsistency"


QUALITY_LOG: list[QualityIssue] = [
    QualityIssue(
        "PSI-69 FLEX",
        "CSV header 'Burning rate; mm' gives a length unit for a burning-rate constant.",
        "Unit corrected to mm^2/s.",
        f"{FLEX_TP_SOURCE} p. 26 header: 'Burning rate, mm2 /s' and p. 25 definition (linear fit of "
        "diameter squared versus time).",
    ),
    QualityIssue(
        "PSI-69 FLEX",
        "CSV composition headers read 'O', 'N', 'CO', 'He' (subscripts lost in encoding).",
        "Interpreted as O2, N2, CO2, He mole fractions.",
        f"{FLEX_TP_SOURCE} p. 26 table header 'O2 N2 CO2 He'.",
    ),
    QualityIssue(
        "PSI-99 SAFFIRE-II",
        "CSV headers '?-g Burn Length', '?-g Spread Length' (the micro sign was lost in encoding).",
        "Interpreted as microgravity (µ-g) burn and spread length.",
        "Internal: paired with '1-g Burn Length' columns in the same table.",
    ),
    QualityIssue(
        "PSI-98 SAFFIRE-I",
        "Sample length 40.6 cm and width 94 cm appear swapped relative to SAFFIRE-III (length 94 cm, "
        "width 40.6 cm) for the same SIBAL sample geometry.",
        "Flagged, not corrected (no primary source checked).",
        "Internal inconsistency between PSI-98 and PSI-100 tables.",
    ),
    QualityIssue(
        "PSI-98 SAFFIRE-I (metadata)",
        "PSI record lists dates 03-02-2001 to 02-28-2008 and platform ISS, identical to SAME (PSI-102), "
        "while Saffire flew on Cygnus in 2016.",
        "Flagged; IGNIS uses the Cygnus platform for Saffire tables.",
        "Internal inconsistency between PSI-98, PSI-99 (Cygnus) and PSI-102 records.",
    ),
    QualityIssue(
        "NTRS 20130010991 (metadata)",
        "First author listed as 'Oslon, Sandra. L.' in NTRS metadata; the PDF reads 'S.L. Olson'.",
        "Display name taken from the PDF title page.",
        "NTRS-20130010991 p. 1.",
    ),
    QualityIssue(
        "Olson & Ferkul 2012, Fig. 6 caption",
        "Caption states average 0g margin -2.6% and average Martian margin '2.7%'; Table I values give "
        "means of -1.38% (0g) and -2.72% (Martian).",
        "IGNIS uses Table I values (recomputed and verified with Eq. 1); the caption averages are not used.",
        "NTRS-20130010991 p. 6 (Table I) and p. 7 (Fig. 6 caption).",
    ),
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    text = path.read_bytes().decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def _num(s: str | None) -> float | None:
    if s is None:
        return None
    m = re.search(r"[-+]?\d*\.?\d+", s.replace(",", ""))
    return float(m.group()) if m else None


# --------------------------------------------------------------------------------------- FLEX


@dataclass
class FlexRow:
    test: int
    identifier: str
    date: str
    fuel: str
    pressure_mmhg: float | None
    x_o2: float | None
    x_n2: float | None
    x_co2: float | None
    x_he: float | None
    d0_mm: float | None
    d_ext_mm: float | None
    k_mm2_s: float | None
    burn_time_s: float | None
    test_end: str

    def as_record(self) -> dict[str, Any]:
        return {
            "dataset": "PSI-69",
            "campaign_id": "PSI-69-FLEX",
            "test": self.test,
            "identifier": self.identifier,
            "date": self.date,
            "fuel": self.fuel,
            "pressure_kpa": None
            if self.pressure_mmhg is None
            else round(to_si(self.pressure_mmhg, "mmHg", "pressure") / 1000, 3),
            "x_o2": self.x_o2,
            "x_n2": self.x_n2,
            "x_co2": self.x_co2,
            "x_he": self.x_he,
            "d0_mm": self.d0_mm,
            "d_ext_mm": self.d_ext_mm,
            "k_mm2_s": self.k_mm2_s,
            "burn_time_s": self.burn_time_s,
            "test_end": self.test_end,
            "gravity_g0": 0.0,
            "platform": "ISS",
            "data_type": "MEASURED",
        }


def parse_flex(raw_dir: Path) -> list[FlexRow]:
    rows = []
    for r in _read_csv(raw_dir / FLEX_CSV):
        vals = list(r.values())
        rows.append(
            FlexRow(
                test=int(vals[0]),
                identifier=vals[1].strip(),
                date=vals[2].strip(),
                fuel=vals[4].strip(),
                pressure_mmhg=_num(vals[5]),
                x_o2=_num(vals[6]),
                x_n2=_num(vals[7]),
                x_co2=_num(vals[8]),
                x_he=_num(vals[9]),
                d0_mm=_num(vals[10]),
                d_ext_mm=_num(vals[11]),
                k_mm2_s=_num(vals[12]),
                burn_time_s=_num(vals[13]),
                test_end=vals[14].strip(),
            )
        )
    return rows


_TP_ROW = re.compile(
    r"flex-(\d{3}) (\S+) (\S+) (\S+) (methanol|heptane) ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) "
    r"([\d.]+) (\S+) (\S+) (\S+)"
)


@dataclass
class CrossCheck:
    n_csv: int
    n_tp: int
    n_compared: int
    n_identical: int
    mismatches: list[dict[str, Any]] = field(default_factory=list)
    only_in_tp: list[int] = field(default_factory=list)
    only_in_csv: list[int] = field(default_factory=list)


def crosscheck_flex(csv_rows: list[FlexRow], tp_pages: tuple[str, ...]) -> CrossCheck:
    """Compare PSI CSV rows with the TP result tables, matched by FLEX identifier (e.g. 20CAL08).

    The PSI 'FLEX Test #' column is a running index that can differ from the TP's FLEX-nnn number,
    so the instrument identifier (plus fuel) is used as the join key. Numeric fields must agree exactly.
    """
    tp: dict[str, tuple[str, ...]] = {}
    dup_tp: set[str] = set()
    for page in tp_pages:
        for m in _TP_ROW.finditer(normalize_text(page)):
            key = m.group(2)
            if key in tp and tp[key] != m.groups():
                dup_tp.add(key)
            tp.setdefault(key, m.groups())
    by_id: dict[str, FlexRow] = {}
    for r in csv_rows:
        by_id.setdefault(r.identifier.lower(), r)
    keys_tp, keys_csv = set(tp) - dup_tp, set(by_id) - dup_tp
    check = CrossCheck(n_csv=len(csv_rows), n_tp=len(tp), n_compared=0, n_identical=0)
    check.only_in_tp = sorted(int(tp[k][0]) for k in keys_tp - keys_csv)
    check.only_in_csv = sorted(by_id[k].test for k in keys_csv - keys_tp)
    for k in sorted(keys_tp & keys_csv):
        g, r = tp[k], by_id[k]
        pairs = {
            "pressure_mmhg": (r.pressure_mmhg, _num(g[5])),
            "x_o2": (r.x_o2, _num(g[6])),
            "x_n2": (r.x_n2, _num(g[7])),
            "x_co2": (r.x_co2, _num(g[8])),
            "x_he": (r.x_he, _num(g[9])),
            "d0_mm": (r.d0_mm, _num(g[10])),
            "k_mm2_s": (r.k_mm2_s, _num(g[12])),
        }
        diffs = {
            f: v
            for f, v in pairs.items()
            if not (v[0] is None and v[1] is None) and (v[0] is None or v[1] is None or abs(v[0] - v[1]) > 1e-9)
        }
        check.n_compared += 1
        if diffs:
            check.mismatches.append(
                {
                    "identifier": r.identifier,
                    "csv_test": r.test,
                    "tp_test": int(g[0]),
                    "fields": {f: list(v) for f, v in diffs.items()},
                }
            )
        else:
            check.n_identical += 1
    return check


# ------------------------------------------------------------------------ BASS-II and SAFFIRE


def parse_bass2(raw_dir: Path) -> list[dict[str, Any]]:
    out = []
    for r in _read_csv(raw_dir / BASS2_CSV):
        vals = list(r.values())
        o2 = _num(vals[11])
        out.append(
            {
                "dataset": "PSI-25",
                "campaign_id": "PSI-25-BASS-II",
                "test": vals[1].strip(),
                "material_text": " ".join(vals[5].split()),
                "o2_percent_initial": o2,
                "gravity_g0": 0.0,
                "platform": "ISS",
                "pressure_kpa": None,
                "data_type": "MEASURED",
            }
        )
    return out


def parse_saffire(raw_dir: Path) -> list[dict[str, Any]]:
    out = []
    for acc, rel in SAFFIRE_CSV.items():
        for r in _read_csv(raw_dir / rel):
            vals = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
            sample = next(iter(vals.values()), "")
            material = vals.get("material", "")
            if not material or "pre-test" in material.lower():
                continue
            flow = _num(vals.get("air flow (cm/s)") or vals.get("air flow"))
            o2 = _num(vals.get("percent o2") or vals.get("percent o2 (note 1)"))
            out.append(
                {
                    "dataset": acc,
                    "campaign_id": f"{acc}-SAFFIRE",
                    "test": sample,
                    "material_text": material,
                    "flow_cm_s": flow,
                    "o2_percent": o2,
                    "flow_direction": (vals.get("flow direction") or vals.get("direction") or "").lower(),
                    "ug_burn_length": vals.get("?-g burn length"),
                    "one_g_spread_rate": vals.get("1-g spread rate"),
                    "gravity_g0": 0.0,
                    "platform": "Cygnus_Saffire",
                    "pressure_kpa": None,
                    "data_type": "MEASURED",
                }
            )
    return out
