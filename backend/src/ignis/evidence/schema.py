"""Strict schemas for the Evidence Ledger (Finding Cards, sources, validation results)."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ignis.core.units import to_si


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DataType(StrEnum):
    MEASURED = "MEASURED"  # directly measured and reported by the source
    DERIVED = "DERIVED"  # computed from measurements (by the source or by the IGNIS Core)
    MODELED = "MODELED"  # output of a physical or statistical model
    CONCEPTUAL = "CONCEPTUAL"  # illustrative only, not a quantitative result


class Epistemic(StrEnum):
    DOCUMENTED_FACT = "DOCUMENTED_FACT"
    SCIENTIFIC_INTERPRETATION = "SCIENTIFIC_INTERPRETATION"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"


class Platform(StrEnum):
    ISS = "ISS"
    CYGNUS_SAFFIRE = "Cygnus_Saffire"
    SHUTTLE = "Space_Shuttle"
    SKYLAB = "Skylab"
    DROP_TOWER = "drop_tower"
    DROP_TOWER_CENTRIFUGE = "drop_tower_centrifuge"
    PARABOLIC_FLIGHT = "parabolic_flight"
    SUBORBITAL_SPIN = "suborbital_spin"  # e.g. LUCI on a spinning New Shepard capsule
    SOUNDING_ROCKET = "sounding_rocket"
    CENTRIFUGE = "centrifuge"
    GROUND_1G = "ground_1g"
    REDUCED_PRESSURE_ANALOG = "reduced_pressure_analog"
    LUNAR_SURFACE = "lunar_surface"
    MODEL = "model"


class Geometry(StrEnum):
    THIN_SHEET = "thin_sheet"
    THICK_SLAB = "thick_slab"
    ROD = "rod"
    WIRE_INSULATION = "wire_insulation"
    DROPLET = "droplet"
    FABRIC = "fabric"
    OTHER = "other"


class FlowDirection(StrEnum):
    OPPOSED = "opposed"
    CONCURRENT = "concurrent"
    QUIESCENT = "quiescent"
    BUOYANT_UPWARD = "buoyant_upward"  # natural convection, flame spreading upward
    BUOYANT_DOWNWARD = "buoyant_downward"  # natural convection, flame spreading downward
    MIXED = "mixed"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


Dimension = Literal[
    "length", "velocity", "pressure", "fraction", "gravity_ratio", "time", "area_rate", "power",
    "temperature", "mass_per_area",
]
UncertaintyKind = Literal[
    "reported_sd", "reported_range", "instrument", "platform_jitter", "digitization", "unknown"
]


class Quantity(Strict):
    """A value as written in the source, plus its deterministic SI conversion."""

    value: float
    unit: str
    dimension: Dimension
    uncertainty: float | None = Field(default=None, ge=0)
    uncertainty_kind: UncertaintyKind = "unknown"
    value_si: float = 0.0
    uncertainty_si: float | None = None

    @model_validator(mode="before")
    @classmethod
    def _convert(cls, data: object) -> object:
        if isinstance(data, dict) and "value" in data and "unit" in data and "dimension" in data:
            data = dict(data)
            data["value_si"] = to_si(float(data["value"]), str(data["unit"]), str(data["dimension"]))
            unc = data.get("uncertainty")
            if unc is not None:
                # Uncertainty is an interval half-width: convert as a difference (no offset units).
                data["uncertainty_si"] = abs(
                    to_si(float(data["value"]) + float(unc), str(data["unit"]), str(data["dimension"]))
                    - data["value_si"]
                )
        return data


class Provenance(Strict):
    source_id: str
    page: int | None = Field(default=None, ge=1)
    locator: str | None = None  # "Table I", "Fig. 7", "Abstract"
    quote: str = Field(min_length=8, max_length=600)
    extraction: Literal[
        "manual", "llm_assisted_human_verified", "llm_assisted_quote_verified",
        "digitized_plot", "dataset_file",
    ]
    verified_by: str | None = None
    verified_at: date | None = None


class FindingCard(Strict):
    id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_.\-]+$")
    claim: str = Field(min_length=10)
    material: str
    material_class: str
    geometry: Geometry
    thickness: Quantity | None = None
    o2: Quantity | None = None
    pressure: Quantity | None = None
    flow_velocity: Quantity | None = None
    flow_direction: FlowDirection = FlowDirection.UNKNOWN
    gravity: Quantity | None = None  # single gravity level (g/g0)
    gravity_range_g0: tuple[float, float] | None = None  # for claims spanning several levels
    platform: Platform
    reduced_gravity_duration_s: float | None = Field(default=None, ge=0)
    measured_variable: str
    value: Quantity | None = None
    comparison_1g: Quantity | None = None  # paired 1-g value from the same source, when reported
    data_type: DataType
    epistemic: Epistemic
    confidence: Literal["high", "medium", "low"]
    confidence_rationale: str
    caveats: list[str] = Field(default_factory=list)
    campaign_id: str
    tags: list[str] = Field(default_factory=list)
    provenance: Provenance

    @model_validator(mode="after")
    def _check_dimensions(self) -> FindingCard:
        expected = {
            "o2": "fraction",
            "pressure": "pressure",
            "flow_velocity": "velocity",
            "gravity": "gravity_ratio",
            "thickness": "length",
        }
        for name, dim in expected.items():
            q = getattr(self, name)
            if q is not None and q.dimension != dim:
                raise ValueError(f"{self.id}: field '{name}' must have dimension '{dim}'")
        if (
            self.data_type == DataType.CONCEPTUAL
            and self.epistemic == Epistemic.DOCUMENTED_FACT
            and self.measured_variable != "planned_experiment"  # a documented plan, no result
        ):
            raise ValueError(f"{self.id}: a CONCEPTUAL item cannot be a DOCUMENTED_FACT")
        if self.gravity is None and self.gravity_range_g0 is None:
            raise ValueError(f"{self.id}: give either 'gravity' or 'gravity_range_g0'")
        if self.gravity_range_g0 is not None:
            lo, hi = self.gravity_range_g0
            if not 0 <= lo <= hi:
                raise ValueError(f"{self.id}: invalid gravity_range_g0 {self.gravity_range_g0}")
        return self

    @property
    def gravity_bounds(self) -> tuple[float, float]:
        if self.gravity is not None:
            return (self.gravity.value_si, self.gravity.value_si)
        assert self.gravity_range_g0 is not None
        return self.gravity_range_g0


class Source(Strict):
    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    url: str
    doi: str | None = None
    license: str
    full_text_indexed: bool = False
    raw_path: str | None = None
    sha256: str | None = None
