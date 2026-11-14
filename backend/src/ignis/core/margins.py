"""Oxygen margin of safety between low-gravity and 1-g flammability limits.

Definition (Olson & Ferkul 2012, Eq. 1, NTRS 20130010991):

    dO2 = (ULOI* + MOC*)/2  -  (ULOI_1g + MOC_1g)/2        [% O2, molar]

A negative dO2 means the material keeps burning in low gravity at a lower oxygen concentration
than in 1 g, i.e. the 1-g screening limit is not conservative for that condition.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ignis.evidence.schema import FindingCard

ULOI = "upward_limiting_oxygen_index"
MOC = "maximum_oxygen_concentration"
MARGIN = "oxygen_margin_of_safety"


def oxygen_margin(uloi_low: float, moc_low: float, uloi_1g: float, moc_1g: float) -> float:
    """Eq. (1) of Olson & Ferkul (2012). Inputs and output in % O2 (molar)."""
    for v in (uloi_low, moc_low, uloi_1g, moc_1g):
        if not 0.0 <= v <= 100.0:
            raise ValueError("oxygen concentrations must be within [0, 100] %")
    return round((uloi_low + moc_low) / 2.0 - (uloi_1g + moc_1g) / 2.0, 6)


@dataclass(frozen=True)
class MarginCheck:
    material: str
    gravity_g0: float
    computed: float
    reported: float | None
    matches: bool | None  # None when the source reports no margin for this pair
    card_ids: tuple[str, ...]


def recompute_margins(cards: Iterable[FindingCard], tolerance: float = 0.005) -> list[MarginCheck]:
    """Recompute every dO2 derivable from limit cards and compare with source-reported margins.

    Cards are grouped by (source, material, pressure). For each low-g level with both ULOI and MOC,
    the 1-g ULOI and MOC of the same group are required.
    """
    groups: dict[tuple[str, str, float | None], list[FindingCard]] = {}
    for c in cards:
        if c.measured_variable not in (ULOI, MOC, MARGIN) or c.value is None or c.gravity is None:
            continue
        key = (c.provenance.source_id, c.material, c.pressure.value_si if c.pressure else None)
        groups.setdefault(key, []).append(c)

    checks: list[MarginCheck] = []
    for (_, material, _), group in sorted(groups.items(), key=lambda kv: kv[0][1]):
        def find(var: str, g: float, group: list[FindingCard] = group) -> FindingCard | None:
            for c in group:
                if (
                    c.measured_variable == var
                    and c.gravity is not None
                    and abs(c.gravity.value_si - g) < 1e-9
                ):
                    return c
            return None

        u1, m1 = find(ULOI, 1.0), find(MOC, 1.0)
        if u1 is None or m1 is None or u1.value is None or m1.value is None:
            continue
        levels = sorted(
            {c.gravity.value_si for c in group if c.gravity is not None and c.gravity.value_si < 1.0}
        )
        for g in levels:
            ul, ml = find(ULOI, g), find(MOC, g)
            if ul is None or ml is None or ul.value is None or ml.value is None:
                continue
            computed = oxygen_margin(ul.value.value, ml.value.value, u1.value.value, m1.value.value)
            rep_card = find(MARGIN, g)
            reported = rep_card.value.value if rep_card and rep_card.value else None
            matches = None if reported is None else abs(computed - reported) <= tolerance
            ids = tuple(c.id for c in (ul, ml, u1, m1, rep_card) if c is not None)
            checks.append(MarginCheck(material, g, computed, reported, matches, ids))
    return checks
