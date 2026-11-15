"""Deterministic analytics behind the IGNIS modules (Explorer ranking, Bridge, Gap Radar, C.2 gate).

Every formula here is shown verbatim in the UI (Methods page) and covered by tests. Weights and
kernel widths are documented design choices, not fitted parameters.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from ignis.core.buoyancy import (
    ANCHOR_1G_CM_S,
    ANCHOR_SOURCES,
    ASSUMPTIONS,
    buoyant_velocity,
    equivalent_gravity_for_flow,
)
from ignis.core.margins import recompute_margins
from ignis.evidence.scenarios import Scenario
from ignis.evidence.schema import FindingCard

# ----------------------------------------------------------------------------- shared constants

G0 = 9.80665
NON_EVIDENCE_VARIABLES = {
    "interpretation",
    "methodological_limitation",
    "test_condition",
    "evidence_gap_statement",
    "test_duration_record",
    "planned_experiment",
    "test_matrix",
    "hazard_expectation",
}
VARIABLE_FAMILY = {
    "upward_limiting_oxygen_index": "oxygen_limit",
    "maximum_oxygen_concentration": "oxygen_limit",
    "oxygen_margin_of_safety": "oxygen_margin",
    "limiting_oxygen_index_model": "oxygen_limit",
    "chamber_o2_minimum_during_burn": "oxygen_history",
    "flame_spread_rate": "spread_rate",
    "flame_tip_spread_rate": "spread_rate",
    "flame_spread_rate_trend": "spread_rate",
    "flame_spread_rate_peak_location": "spread_rate",
    "flammability_boundary_shape": "flammability_boundary",
    "flammable_domain_comparison": "flammability_boundary",
    "burn_duration_difference": "burn_duration",
}
LONG_DURATION_S = 60.0  # evidence shorter than this cannot show developed (steady) fires
PARTIAL_G = (0.01, 0.90)


def family(var: str) -> str:
    return VARIABLE_FAMILY.get(var, var)


def is_evidence(card: FindingCard) -> bool:
    return card.measured_variable not in NON_EVIDENCE_VARIABLES and card.data_type.value in {
        "MEASURED",
        "DERIVED",
        "MODELED",
    }


def platform_duration_s(card: FindingCard) -> float | None:
    """Reduced-gravity test time. Orbital platforms are effectively unlimited; 1 g is unlimited."""
    if card.reduced_gravity_duration_s is not None:
        return card.reduced_gravity_duration_s
    if card.platform.value in {"ISS", "Cygnus_Saffire", "Space_Shuttle", "Skylab", "ground_1g", "lunar_surface"}:
        return math.inf
    return None


# ------------------------------------------------------------------------------- A. ranking

DATA_TYPE_WEIGHT = {"MEASURED": 1.0, "DERIVED": 0.9, "MODELED": 0.6, "CONCEPTUAL": 0.3}
EPISTEMIC_WEIGHT = {"DOCUMENTED_FACT": 1.0, "SCIENTIFIC_INTERPRETATION": 0.8, "HYPOTHESIS": 0.5, "UNKNOWN": 0.3}
CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.8, "low": 0.6}
SIGMA_G = 0.05  # g/g0
SIGMA_O2 = 4.0  # percentage points
SIGMA_LNP = 0.35  # natural-log pressure (about a factor 1.4)
MISSING_CONDITION = 0.7  # multiplicative penalty when a card does not report a condition
FREE_FALL = 0.01  # g/g0 below which a scenario is orbital free fall (no buoyancy)


def evidence_strength(card: FindingCard) -> float:
    """E = w(data type) x w(epistemic category) x w(confidence)."""
    return round(
        DATA_TYPE_WEIGHT[card.data_type.value]
        * EPISTEMIC_WEIGHT[card.epistemic.value]
        * CONFIDENCE_WEIGHT[card.confidence],
        6,
    )


def reproducibility(n_campaigns: int) -> float:
    """R = 1 - exp(-n/2): n independent campaigns reporting the same variable family + material class."""
    if n_campaigns < 0:
        raise ValueError("n_campaigns must be >= 0")
    return round(1.0 - math.exp(-n_campaigns / 2.0), 6)


def _gauss(d: float, sigma: float) -> float:
    return math.exp(-0.5 * (d / sigma) ** 2)


def mission_relevance(card: FindingCard, sc: Scenario) -> float:
    """M = k_g x k_O2 x k_p: Gaussian kernels on the distance between card and scenario conditions."""
    lo, hi = card.gravity_bounds
    if sc.gravity_g0 is None:
        k_g = 1.0
    elif sc.gravity_g0 < FREE_FALL:
        # Orbital free fall has no buoyant flow: only microgravity evidence is relevant.
        k_g = 1.0 if lo < FREE_FALL else 0.0
    else:
        d = 0.0 if lo <= sc.gravity_g0 <= hi else min(abs(sc.gravity_g0 - lo), abs(sc.gravity_g0 - hi))
        k_g = _gauss(d, SIGMA_G)
    card_o2 = (
        card.o2.value_si * 100
        if card.o2
        else (card.value.value_si * 100 if card.value and family(card.measured_variable) == "oxygen_limit" else None)
    )
    if sc.o2_percent is None:
        k_o2 = 1.0
    elif card_o2 is None:
        k_o2 = MISSING_CONDITION
    else:
        k_o2 = _gauss(card_o2 - sc.o2_percent, SIGMA_O2)
    if sc.pressure is None:
        k_p = 1.0
    elif card.pressure is None:
        k_p = MISSING_CONDITION
    else:
        sc_pa = sc.derived()["pressure_kpa"] * 1000.0
        k_p = _gauss(math.log(card.pressure.value_si / sc_pa), SIGMA_LNP)
    return round(k_g * k_o2 * k_p, 6)


def ranking_factors(cards: Sequence[FindingCard], scenarios: Sequence[Scenario]) -> dict[str, dict[str, Any]]:
    campaigns: dict[tuple[str, str], set[str]] = defaultdict(set)
    for c in cards:
        campaigns[(family(c.measured_variable), c.material_class)].add(c.campaign_id)
    out: dict[str, dict[str, Any]] = {}
    for c in cards:
        n = len(campaigns[(family(c.measured_variable), c.material_class)])
        out[c.id] = {
            "E": evidence_strength(c),
            "R": reproducibility(n),
            "n_campaigns_same_family": n,
            "M": {sc.id: mission_relevance(c, sc) for sc in scenarios},
        }
    return out


def weighted_geometric_score(factors: dict[str, float], weights: dict[str, float]) -> float:
    """S = prod(f_i ^ w_i) ^ (1 / sum w_i). Mirrored exactly in the frontend (parity-tested)."""
    total = sum(weights.values())
    if total <= 0:
        return 0.0
    log_sum = 0.0
    for k, w in weights.items():
        f = factors[k]
        if f <= 0:
            return 0.0
        log_sum += w * math.log(f)
    return round(math.exp(log_sum / total), 6)


# --------------------------------------------------------------------------- F.1 gap radar

GRAVITY_BINS: list[tuple[str, float, float]] = [
    ("µg (<0.01 g)", 0.0, 0.01),
    ("Sub-lunar (0.01-0.12 g)", 0.01, 0.12),
    ("Lunar (0.12-0.22 g)", 0.12, 0.22),
    ("0.22-0.30 g", 0.22, 0.30),
    ("Martian (0.30-0.46 g)", 0.30, 0.46),
    ("0.46-0.90 g", 0.46, 0.90),
    ("Earth (0.90-1.10 g)", 0.90, 1.10),
]
O2_BINS: list[tuple[str, float, float]] = [
    ("<19%", 0.0, 19.0),
    ("19-23%", 19.0, 23.0),
    ("23-27%", 23.0, 27.0),
    ("27-31%", 27.0, 31.0),
    ("31-35%", 31.0, 35.0),
    (">=35%", 35.0, 100.0),
]
PRESSURE_CLASSES = ("reduced (<85 kPa)", "ambient (>=85 kPa)", "unspecified")
# A scenario whose atmosphere is UNKNOWN (e.g. Mars surface habitat) is spread over all bins at 0.8.
UNKNOWN_SCENARIO_CONDITION = 0.8


def gravity_bins_for(lo: float, hi: float) -> list[int]:
    out = []
    for i, (_, a, b) in enumerate(GRAVITY_BINS):
        last = i == len(GRAVITY_BINS) - 1
        if (lo < b or (last and lo <= b)) and hi >= a:
            out.append(i)
    return out


def o2_bin_for(o2_percent: float) -> int:
    for i, (_, a, b) in enumerate(O2_BINS):
        if a <= o2_percent < b:
            return i
    return len(O2_BINS) - 1


def pressure_class(p_pa: float | None) -> str:
    if p_pa is None:
        return PRESSURE_CLASSES[2]
    return PRESSURE_CLASSES[0] if p_pa < 85_000 else PRESSURE_CLASSES[1]


@dataclass(frozen=True)
class EvidencePoint:
    """One measurement context, from a Finding Card or a PSI dataset row."""

    gravity_lo: float
    gravity_hi: float
    o2_percent: float | None
    pressure_pa: float | None
    campaign_id: str
    duration_s: float | None
    fuel_class: str  # "solid" | "droplet"
    ref: str  # card id or dataset row reference


def points_from_cards(cards: Iterable[FindingCard]) -> list[EvidencePoint]:
    pts = []
    for c in cards:
        if not is_evidence(c) or c.data_type.value == "MODELED":
            continue
        lo, hi = c.gravity_bounds
        o2 = (
            c.o2.value_si * 100
            if c.o2
            else (c.value.value_si * 100 if c.value and family(c.measured_variable) == "oxygen_limit" else None)
        )
        pts.append(
            EvidencePoint(
                lo,
                hi,
                o2,
                c.pressure.value_si if c.pressure else None,
                c.campaign_id,
                platform_duration_s(c),
                "droplet" if c.geometry.value == "droplet" else "solid",
                c.id,
            )
        )
    return pts


def points_from_datasets(datasets: dict[str, Any]) -> list[EvidencePoint]:
    pts = []
    for r in datasets.get("bass2", []):
        pts.append(
            EvidencePoint(
                0.0,
                0.0,
                r["o2_percent_initial"],
                None,
                r["campaign_id"],
                math.inf,
                "solid",
                f"{r['dataset']}:{r['test']}",
            )
        )
    for r in datasets.get("saffire", []):
        pts.append(
            EvidencePoint(
                0.0, 0.0, r["o2_percent"], None, r["campaign_id"], math.inf, "solid", f"{r['dataset']}:{r['test']}"
            )
        )
    for r in datasets.get("flex", []):
        o2 = None if r["x_o2"] is None else r["x_o2"] * 100
        p = None if r["pressure_kpa"] is None else r["pressure_kpa"] * 1000
        pts.append(EvidencePoint(0.0, 0.0, o2, p, r["campaign_id"], math.inf, "droplet", f"PSI-69:{r['test']}"))
    return pts


def scenario_cell_relevance(sc: Scenario, gi: int, oi: int, pclass: str) -> float:
    """R_s(cell): 1 inside the scenario's bin, Gaussian decay with distance outside it."""
    _, ga, gb = GRAVITY_BINS[gi]
    if sc.gravity_g0 is None:
        k_g = 1.0
    elif sc.gravity_g0 < FREE_FALL:
        k_g = 1.0 if gi == 0 else 0.0
    else:
        d = (
            0.0
            if ga <= sc.gravity_g0 < gb or (gi == len(GRAVITY_BINS) - 1 and sc.gravity_g0 == gb)
            else min(abs(sc.gravity_g0 - ga), abs(sc.gravity_g0 - gb))
        )
        k_g = _gauss(d, SIGMA_G)
    _, oa, ob = O2_BINS[oi]
    if sc.o2_percent is None:
        k_o = UNKNOWN_SCENARIO_CONDITION
    else:
        d = 0.0 if oa <= sc.o2_percent < ob else min(abs(sc.o2_percent - oa), abs(sc.o2_percent - ob))
        k_o = _gauss(d, SIGMA_O2)
    sc_class = pressure_class(sc.derived()["pressure_kpa"] * 1000 if sc.pressure else None)
    if sc.pressure is None:
        k_p = UNKNOWN_SCENARIO_CONDITION
    else:
        k_p = 1.0 if sc_class == pclass else (0.75 if pclass == PRESSURE_CLASSES[2] else 0.5)
    return round(k_g * k_o * k_p, 6)


PLANNED_FACTOR = 0.5  # a documented, not-yet-flown experiment already targets the cell


def planned_cells(cards: Iterable[FindingCard]) -> dict[tuple[int, int, str], list[str]]:
    """Cells targeted by documented planned experiments (cards with measured_variable planned_experiment)."""
    out: dict[tuple[int, int, str], list[str]] = defaultdict(list)
    for c in cards:
        if c.measured_variable != "planned_experiment" or c.o2 is None or c.gravity is None:
            continue
        oi = o2_bin_for(c.o2.value_si * 100)
        pc = pressure_class(c.pressure.value_si if c.pressure else None)
        for gi in gravity_bins_for(c.gravity.value_si, c.gravity.value_si):
            out[(gi, oi, pc)].append(c.id)
    return out


def gap_grid(
    points: Sequence[EvidencePoint],
    scenarios: Sequence[Scenario],
    fuel_class: str,
    planned: dict[tuple[int, int, str], list[str]] | None = None,
) -> dict[str, Any]:
    cells: dict[tuple[int, int, str], dict[str, Any]] = {}
    for gi in range(len(GRAVITY_BINS)):
        for oi in range(len(O2_BINS)):
            for pc in PRESSURE_CLASSES:
                cells[(gi, oi, pc)] = {"campaigns": set(), "n_points": 0, "max_duration_s": 0.0, "refs": []}
    unplaced = 0
    for p in points:
        if p.fuel_class != fuel_class:
            continue
        if p.o2_percent is None:
            unplaced += 1
            continue
        oi = o2_bin_for(p.o2_percent)
        pc = pressure_class(p.pressure_pa)
        for gi in gravity_bins_for(p.gravity_lo, p.gravity_hi):
            cell = cells[(gi, oi, pc)]
            cell["campaigns"].add(p.campaign_id)
            cell["n_points"] += 1
            dur = p.duration_s if p.duration_s is not None else 0.0
            cell["max_duration_s"] = max(cell["max_duration_s"], dur)
            if len(cell["refs"]) < 12:
                cell["refs"].append(p.ref)
    out_cells = []
    for (gi, oi, pc), cell in cells.items():
        n_c = len(cell["campaigns"])
        scarcity = round(1.0 / (1.0 + n_c), 6)
        short = 1.0 if cell["max_duration_s"] < LONG_DURATION_S else 0.5
        out_cells.append(
            {
                "g": gi,
                "o2": oi,
                "pressure": pc,
                "n_campaigns": n_c,
                "n_points": cell["n_points"],
                "campaigns": sorted(cell["campaigns"]),
                "max_duration_s": None if math.isinf(cell["max_duration_s"]) else cell["max_duration_s"],
                "long_duration_evidence": cell["max_duration_s"] >= LONG_DURATION_S,
                "scarcity": scarcity,
                "duration_factor": short,
                "relevance": {sc.id: scenario_cell_relevance(sc, gi, oi, pc) for sc in scenarios},
            "planned": (planned or {}).get((gi, oi, pc), []) if fuel_class == "solid" else [],
            "planned_factor": PLANNED_FACTOR
            if fuel_class == "solid" and (planned or {}).get((gi, oi, pc))
            else 1.0,
                "refs": cell["refs"],
            }
        )
    return {"fuel_class": fuel_class, "cells": out_cells, "unplaced_points": unplaced}


def priority(cell: dict[str, Any], scenario_ids: Sequence[str]) -> float:
    """P = max_s R_s(cell) x 1/(1 + n_campaigns) x D x F.

    D = 1 if no evidence >= 60 s else 0.5; F = 0.5 if a documented planned experiment targets the cell.
    """
    if not scenario_ids:
        return 0.0
    r = max(float(cell["relevance"][s]) for s in scenario_ids)
    f = float(cell.get("planned_factor", 1.0))
    return round(r * float(cell["scarcity"]) * float(cell["duration_factor"]) * f, 6)


def suggest_platform(gi: int) -> dict[str, str]:
    label = GRAVITY_BINS[gi][0]
    if gi == 0:
        return {
            "platform": "ISS (SoFIE / Saffire-class facility)",
            "why": "Long-duration microgravity with controlled low-speed forced flow.",
        }
    if gi in (2,):
        return {
            "platform": "Lunar surface (FM2-class) or spinning suborbital vehicle (LUCI-class)",
            "why": f"{label}: only real or spin-simulated lunar gravity gives tests longer than ~25 s; "
            "drop-tower centrifuges (5 s) and aircraft (~25 s) suit screening only.",
        }
    if gi in (1, 3, 4, 5):
        return {
            "platform": "Spinning suborbital vehicle (LUCI-class) or long-radius centrifuge",
            "why": f"{label}: no real-gravity platform exists; spin simulation gives >2.5 min "
            "but adds Coriolis effects that must be characterized.",
        }
    return {
        "platform": "Ground test facility (NASA-STD-6001 Test 1 apparatus)",
        "why": "1-g reference limits under the same atmosphere are needed to compute oxygen margins.",
    }


def scenario_owns_cell(sc: Scenario, cell: dict[str, Any]) -> bool:
    """True if the scenario's gravity (and O2 / pressure class, when known) fall inside the cell."""
    if sc.gravity_g0 is None:
        return False
    gi = gravity_bins_for(sc.gravity_g0, sc.gravity_g0)
    if cell["g"] not in gi[:1]:
        return False
    if sc.o2_percent is not None and o2_bin_for(sc.o2_percent) != cell["o2"]:
        return False
    if sc.pressure is not None:
        pa = sc.derived()["pressure_kpa"] * 1000.0
        if pressure_class(pa) != cell["pressure"]:
            return False
    return True


EXPLORATION_SCENARIOS = (
    "LUNAR-SURFACE-HABITAT",
    "LUNAR-SURFACE-HABITAT-EVA",
    "MARS-SURFACE-HABITAT",
    "GATEWAY-NOMINAL",
)


def next_experiments(grid: dict[str, Any], scenarios: Sequence[Scenario], top_k: int = 6) -> list[dict[str, Any]]:
    """Level-1 Next-Experiment Designer: transparent priority ranking (NOT Bayesian design).

    Cells are ranked by P for the exploration scenarios; selection is greedy with diversity
    (at most one cell per gravity bin and pressure class) so the list is not six variants of one gap.
    """
    ids = [s.id for s in scenarios if s.id in EXPLORATION_SCENARIOS]
    ranked = sorted(grid["cells"], key=lambda c: (priority(c, ids), -c["g"]), reverse=True)
    out: list[dict[str, Any]] = []
    used: set[tuple[Any, ...]] = set()
    for cell in ranked:
        if len(out) >= top_k:
            break
        if cell["pressure"] == PRESSURE_CLASSES[2]:
            continue
        own = [s for s in scenarios if s.id in ids and scenario_owns_cell(s, cell)]
        if not own:
            continue  # proposals sit exactly at a mission's conditions, never in a neighbouring bin
        sc = own[0]
        best = sc.id
        unknown_atm = sc.o2_percent is None
        key = (cell["g"], "TBD" if unknown_atm else cell["pressure"], best)
        if key in used:
            continue
        used.add(key)
        plat = suggest_platform(cell["g"])
        out.append(
            {
                "gravity_bin": GRAVITY_BINS[cell["g"]][0],
                "o2_bin": "TBD: scenario atmosphere UNKNOWN in NASA sources" if unknown_atm else O2_BINS[cell["o2"]][0],
                "pressure_class": "TBD" if unknown_atm else cell["pressure"],
                "priority": priority(cell, ids),
                "relevance": cell["relevance"][best],
                "scarcity": cell["scarcity"],
                "duration_factor": cell["duration_factor"],
                "closest_scenario": {"id": sc.id, "name": sc.name},
                "existing_campaigns": cell["campaigns"],
            "already_planned": cell["planned"],
            "planned_factor": cell["planned_factor"],
                "platform": plat["platform"],
                "platform_rationale": plat["why"],
                "hypothesis": (
                    "H2 test: is the low-gravity upward flammability limit (ULOI*/MOC*) of candidate cabin "
                    "materials below their 1-g NASA-STD-6001 Test 1 MOC at this atmosphere? Pair every "
                    "low-g test with a 1-g test in the same atmosphere to compute the oxygen margin (Eq. 1)."
                ),
                "measure": "ULOI*/MOC* in 1% O2 steps, flame spread rate, flame length history, burn duration "
                ">= 60 s, and local g-level vs time.",
            }
        )
    return out


# --------------------------------------------------------------------------------- C.2 gate

GATE_CRITERIA = {
    "min_partial_g_campaigns": 3,
    "min_compatible_points": 20,
    "min_holdout_partial_g_points": 5,
    "coverage_target": (0.85, 0.95),
}


def evaluate_gate(cards: Sequence[FindingCard]) -> dict[str, Any]:
    """Pre-registered criteria for enabling the C.2 predictor. Computed from the ledger, not hand-set."""
    groups: dict[tuple[str, str], list[FindingCard]] = defaultdict(list)
    for c in cards:
        if is_evidence(c) and c.value is not None and c.gravity is not None and c.data_type.value != "MODELED":
            groups[(family(c.measured_variable), c.material_class)].append(c)
    candidates: list[dict[str, Any]] = []
    for (fam, mclass), group in groups.items():
        partial = [c for c in group if c.gravity is not None and PARTIAL_G[0] < c.gravity.value_si < PARTIAL_G[1]]
        candidates.append(
            {
                "variable_family": fam,
                "material_class": mclass,
                "n_points": len(group),
                "n_partial_g_points": len(partial),
                "n_partial_g_campaigns": len({c.campaign_id for c in partial}),
                "partial_g_campaigns": sorted({c.campaign_id for c in partial}),
            }
        )
    candidates.sort(key=lambda x: (x["n_partial_g_campaigns"], x["n_points"]), reverse=True)
    best = candidates[0] if candidates else None
    checks = []
    if best:
        checks = [
            {
                "criterion": ">= 3 independent partial-g campaigns, same variable and material class",
                "value": best["n_partial_g_campaigns"],
                "passed": best["n_partial_g_campaigns"] >= 3,
            },
            {
                "criterion": ">= 20 compatible points (all gravity levels)",
                "value": best["n_points"],
                "passed": best["n_points"] >= 20,
            },
            {
                "criterion": ">= 5 partial-g points reserved for external validation",
                "value": best["n_partial_g_points"],
                "passed": best["n_partial_g_points"] >= 5,
            },
            {
                "criterion": "Grouped (leave-one-campaign-out) conformal coverage within 0.85-0.95 and "
                "better than the physics baseline",
                "value": None,
                "passed": None,
            },
        ]
    enabled = bool(checks) and all(ch["passed"] for ch in checks[:3])
    return {
        "enabled": False if not enabled else None,  # 4th criterion requires an actual validation run
        "status": "DISABLED" if not enabled else "PENDING_VALIDATION",
        "best_candidate": best,
        "checks": checks,
        "candidates": candidates[:10],
        "criteria": {k: list(v) if isinstance(v, tuple) else v for k, v in GATE_CRITERIA.items()},
    }


# ------------------------------------------------------------------------- C.1 bridge helpers


def centrifugal_gravity_g0(rpm: float, radius_m: float) -> float:
    """a = omega^2 r, omega = 2 pi rpm / 60, returned in multiples of g0."""
    if rpm < 0 or radius_m < 0:
        raise ValueError("rpm and radius must be non-negative")
    omega = 2.0 * math.pi * rpm / 60.0
    return omega * omega * radius_m / G0


def buoyancy_curve(n: int = 101) -> list[dict[str, float]]:
    pts = []
    for i in range(n):
        g = i / (n - 1)
        bv = buoyant_velocity(g)
        pts.append({"g": round(g, 4), "low_cm_s": round(bv.low_cm_s, 4), "high_cm_s": round(bv.high_cm_s, 4)})
    return pts


def flow_analogs(cards: Sequence[FindingCard], datasets: dict[str, Any]) -> list[dict[str, Any]]:
    """Microgravity forced-flow evidence placed on the gravity axis by u_b equivalence (analogs only)."""
    rows = []
    seen: set[tuple[Any, ...]] = set()
    for c in cards:
        if c.gravity is not None and c.gravity.value_si < 0.01 and c.flow_velocity is not None and is_evidence(c):
            v = round(c.flow_velocity.value_si * 100, 6)
            ckey = (c.material, v, c.flow_direction.value)
            if ckey in seen:
                continue
            seen.add(ckey)
            lo, hi = equivalent_gravity_for_flow(v)
            rows.append(
                {
                    "ref": c.id,
                    "label": f"{c.material} ({c.flow_direction.value})",
                    "flow_cm_s": v,
                    "equiv_g_low": round(lo, 4),
                    "equiv_g_high": round(hi, 4),
                    "kind": "model" if c.data_type.value == "MODELED" else "card",
                }
            )
    for r in datasets.get("saffire", []):
        if r["flow_cm_s"] is None:
            continue
        key = (r["dataset"], r["flow_cm_s"], r["material_text"], r["flow_direction"])
        if key in seen:
            continue
        seen.add(key)
        lo, hi = equivalent_gravity_for_flow(r["flow_cm_s"])
        rows.append(
            {
                "ref": f"{r['dataset']}:{r['test']}",
                "label": f"{r['material_text']} ({r['flow_direction']})",
                "flow_cm_s": r["flow_cm_s"],
                "equiv_g_low": round(lo, 4),
                "equiv_g_high": round(hi, 4),
                "kind": "dataset",
            }
        )
    return rows


def margin_checks(cards: Sequence[FindingCard]) -> list[dict[str, Any]]:
    return [
        {
            "material": m.material,
            "gravity_g0": m.gravity_g0,
            "computed": m.computed,
            "reported": m.reported,
            "matches": m.matches,
            "card_ids": list(m.card_ids),
        }
        for m in recompute_margins(cards)
    ]


def comparability_notes(card: FindingCard) -> list[str]:
    """Machine-generated reasons why a card may not be directly comparable with 1-g screening data."""
    notes = []
    dur = platform_duration_s(card)
    if dur is not None and not math.isinf(dur) and dur < LONG_DURATION_S:
        notes.append(f"Short reduced-gravity time ({dur:g} s): flames may not reach steady state.")
    if card.platform.value in {"suborbital_spin", "drop_tower_centrifuge", "centrifuge"}:
        notes.append("Spin-generated gravity: Coriolis forces and g-gradients along the sample.")
    if card.flow_velocity is not None and card.gravity is not None and card.gravity.value_si < 0.01:
        notes.append("Forced flow in microgravity is not equivalent to buoyant flow at partial gravity.")
    if (
        card.measured_variable in {"upward_limiting_oxygen_index", "maximum_oxygen_concentration"}
        and card.gravity is not None
        and card.gravity.value_si < 0.9
    ):
        notes.append("Low-g limit criteria (ULOI*/MOC*) differ from 1-g Test 1 criteria.")
    if card.platform.value == "model":
        notes.append("Model result, not a measurement.")
    return notes


def partial_gravity_summary(cards: Sequence[FindingCard]) -> dict[str, Any]:
    """H1 quantification from the ledger: evidence cards whose gravity lies in (0.01, 0.9) g."""
    ev = [
        c
        for c in cards
        if is_evidence(c)
        and c.data_type.value in {"MEASURED", "DERIVED"}
        and c.gravity_bounds[1] > PARTIAL_G[0]
        and c.gravity_bounds[0] < PARTIAL_G[1]
    ]
    durations = [d for c in ev if (d := platform_duration_s(c)) is not None and not math.isinf(d)]
    levels: set[float] = set()
    for c in ev:
        if c.gravity is not None:
            levels.add(round(c.gravity.value_si, 3))
    ranges = sorted({c.gravity_range_g0 for c in ev if c.gravity_range_g0 is not None})
    numeric = [c for c in ev if c.value is not None and c.data_type.value == "MEASURED"]
    return {
        "n_cards": len(ev),
        "campaigns": sorted({c.campaign_id for c in ev}),
        "sources": sorted({c.provenance.source_id for c in ev}),
        "platforms": sorted({c.platform.value for c in ev}),
        "material_classes": sorted({c.material_class for c in ev if c.material_class != "multiple"}),
        "single_gravity_levels": sorted(levels),
        "gravity_ranges": [list(r) for r in ranges],
        "max_reduced_g_duration_s": max(durations) if durations else None,
        "n_numeric_measurements": len(numeric),
    }


def build_analysis(
    cards: Sequence[FindingCard], scenarios: Sequence[Scenario], datasets: dict[str, Any]
) -> dict[str, Any]:
    pts = points_from_cards(cards) + points_from_datasets(datasets)
    solid = gap_grid(pts, scenarios, "solid", planned_cells(cards))
    return {
        "ranking": ranking_factors(cards, scenarios),
        "ranking_constants": {
            "data_type_weight": DATA_TYPE_WEIGHT,
            "epistemic_weight": EPISTEMIC_WEIGHT,
            "confidence_weight": CONFIDENCE_WEIGHT,
            "sigma_g": SIGMA_G,
            "sigma_o2_pct": SIGMA_O2,
            "sigma_ln_p": SIGMA_LNP,
            "missing_condition": MISSING_CONDITION,
        },
        "comparability": {c.id: comparability_notes(c) for c in cards},
        "gaps": {
            "gravity_bins": [b[0] for b in GRAVITY_BINS],
            "o2_bins": [b[0] for b in O2_BINS],
            "pressure_classes": list(PRESSURE_CLASSES),
            "long_duration_s": LONG_DURATION_S,
            "solid": solid,
            "droplet": gap_grid(pts, scenarios, "droplet"),
        },
        "next_experiments": next_experiments(solid, scenarios),
        "partial_gravity": partial_gravity_summary(cards),
        "gate": evaluate_gate(cards),
        "bridge": {
            "buoyancy_curve": buoyancy_curve(),
            "anchor_cm_s": list(ANCHOR_1G_CM_S),
            "anchor_sources": list(ANCHOR_SOURCES),
            "assumptions": list(ASSUMPTIONS),
            "moon": vars(buoyant_velocity(0.165)),
            "mars": vars(buoyant_velocity(0.380)),
            "flow_analogs": flow_analogs(cards, datasets),
            "margin_checks": margin_checks(cards),
            "luci_centrifugal_check": {
                "rpm": 11.0,
                "radius_m": 1.22,
                "g0": round(centrifugal_gravity_g0(11.0, 1.22), 4),
                "source": "NTRS-20250010653 slide 12",
            },
        },
    }
