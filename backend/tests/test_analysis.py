import itertools
import json
import math

import pytest

from ignis.core.analysis import (
    centrifugal_gravity_g0,
    evaluate_gate,
    evidence_strength,
    gap_grid,
    gravity_bins_for,
    mission_relevance,
    o2_bin_for,
    points_from_cards,
    priority,
    reproducibility,
    weighted_geometric_score,
)
from ignis.evidence.cards import load_cards
from ignis.evidence.scenarios import load_scenarios
from ignis.pipeline.build import CARDS_DIR, SCENARIOS_YAML


@pytest.fixture(scope="module")
def cards():  # type: ignore[no-untyped-def]
    return load_cards(CARDS_DIR)


@pytest.fixture(scope="module")
def scenarios():  # type: ignore[no-untyped-def]
    return load_scenarios(SCENARIOS_YAML)


def test_luci_spin_rate_reproduces_lunar_gravity() -> None:
    # 11 rpm at 1.22 m (NTRS 20250010653 slide 12) -> 1.62 m/s^2 = 0.165 g
    assert centrifugal_gravity_g0(11.0, 1.22) == pytest.approx(0.1651, abs=1e-4)
    with pytest.raises(ValueError):
        centrifugal_gravity_g0(-1, 1)


def test_reproducibility_monotonic_and_bounded() -> None:
    vals = [reproducibility(n) for n in range(0, 10)]
    assert vals[0] == 0.0
    assert all(a < b for a, b in itertools.pairwise(vals))
    assert vals[-1] < 1.0


def test_weighted_geometric_score() -> None:
    f = {"M": 0.5, "E": 0.8, "R": 0.4}
    assert weighted_geometric_score(f, {"M": 1, "E": 1, "R": 1}) == pytest.approx((0.5 * 0.8 * 0.4) ** (1 / 3))
    assert weighted_geometric_score(f, {"M": 1, "E": 0, "R": 0}) == pytest.approx(0.5)
    assert weighted_geometric_score({"M": 0.0, "E": 1, "R": 1}, {"M": 1, "E": 1, "R": 1}) == 0.0
    assert weighted_geometric_score(f, {"M": 0, "E": 0, "R": 0}) == 0.0


def test_evidence_strength_orders_measured_above_hypothesis(cards) -> None:  # type: ignore[no-untyped-def]
    by_id = {c.id: c for c in cards}
    assert evidence_strength(by_id["OF2012-1G-MOC-MYLAR"]) > evidence_strength(by_id["LPSC2026-HABITAT-HAZARD"])


def test_free_fall_scenario_ignores_partial_gravity_cards(cards, scenarios) -> None:  # type: ignore[no-untyped-def]
    iss = next(s for s in scenarios if s.id == "ISS-NOMINAL")
    lunar_card = next(c for c in cards if c.id == "OF2012-LUNAR-MOC-MYLAR")
    assert mission_relevance(lunar_card, iss) == 0.0


def test_bins() -> None:
    assert gravity_bins_for(0.165, 0.165) == [2]
    assert gravity_bins_for(0.38, 0.38) == [4]
    assert gravity_bins_for(1.0, 1.0) == [6]
    assert o2_bin_for(26.5) == 2 and o2_bin_for(34) == 4 and o2_bin_for(14.1) == 0


def test_lunar_habitat_cells_have_only_short_tests(cards, scenarios) -> None:  # type: ignore[no-untyped-def]
    from ignis.core.analysis import planned_cells

    grid = gap_grid(points_from_cards(cards), scenarios, "solid", planned_cells(cards))
    ids = ["LUNAR-SURFACE-HABITAT", "LUNAR-SURFACE-HABITAT-EVA"]
    lunar = {c["o2"]: c for c in grid["cells"] if c["g"] == 2 and c["pressure"].startswith("reduced")}
    # 10.2 psia / 26.5% O2: only the 5.18 s drop-tower limit series informs it -> P = 1 x 1/2 x 1 x 1
    nominal = lunar[2]
    assert nominal["campaigns"] == ["GRC-ZGF-CENTRIFUGE-LUNAR"]
    assert nominal["max_duration_s"] == 5.18 and not nominal["long_duration_evidence"]
    assert priority(nominal, ids) == 0.5 and nominal["planned"] == []
    # 8.2 psia / 34% O2: same short series, and FM2 plans it -> halved again
    assert "FM2-2024-ATM-34-8.2" in lunar[4]["planned"] and priority(lunar[4], ids) == 0.25


def test_gate_is_disabled_with_quantified_reasons(cards) -> None:  # type: ignore[no-untyped-def]
    gate = evaluate_gate(cards)
    assert gate["status"] == "DISABLED"
    assert any(ch["passed"] is False for ch in gate["checks"])
    assert gate["best_candidate"]["n_partial_g_campaigns"] < 3


def test_static_analysis_bundle_is_consistent() -> None:
    from ignis.pipeline.build import STATIC_DIR

    path = STATIC_DIR / "analysis.json"
    if not path.exists():
        pytest.skip("run `ignis-pipeline build` first")
    a = json.loads(path.read_text(encoding="utf-8"))
    assert all(m["matches"] for m in a["bridge"]["margin_checks"])
    assert math.isclose(a["bridge"]["luci_centrifugal_check"]["g0"], 0.1651, abs_tol=1e-4)
