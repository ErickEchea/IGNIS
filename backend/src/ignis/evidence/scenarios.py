"""Mission scenarios (cabin atmospheres) with verified provenance."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from ignis.core.units import o2_partial_pressure_kpa, to_si
from ignis.evidence.cards import PageTextFn, normalize_text


class ScenarioProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str
    page: int | None = None
    quote: str


class Pressure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    value: float
    unit: str


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    name: str
    gravity_g0: float | None
    gravity_note: str
    pressure: Pressure | None
    o2_percent: float | None = Field(default=None, ge=0, le=100)
    unknown_note: str | None = None
    provenance: ScenarioProvenance | None

    def derived(self) -> dict[str, Any]:
        """Deterministic SI values for display (DERIVED by the IGNIS Core)."""
        p_pa = to_si(self.pressure.value, self.pressure.unit, "pressure") if self.pressure else None
        x_o2 = self.o2_percent / 100.0 if self.o2_percent is not None else None
        return {
            "pressure_kpa": None if p_pa is None else round(p_pa / 1000.0, 2),
            "o2_mole_fraction": x_o2,
            "o2_partial_pressure_kpa": (
                None if (p_pa is None or x_o2 is None) else round(o2_partial_pressure_kpa(x_o2, p_pa), 2)
            ),
        }


def load_scenarios(path: Path) -> list[Scenario]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Scenario.model_validate(s) for s in data["scenarios"]]


def verify_scenario(s: Scenario, known: set[str], page_text: PageTextFn) -> tuple[bool, str]:
    if s.provenance is None:
        return (s.unknown_note is not None, "no source: values must be UNKNOWN")
    if s.provenance.source_id not in known:
        return (False, f"unknown source {s.provenance.source_id}")
    text = page_text(s.provenance.source_id, s.provenance.page)
    if text is None:
        return (True, "source text unavailable locally (not machine-verified)")
    ok = normalize_text(s.provenance.quote) in normalize_text(text)
    return (ok, "quote verified" if ok else f"quote not found on page {s.provenance.page}")
