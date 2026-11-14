"""Deterministic unit handling (pint). Every quantity in the ledger is stored in SI.

Conventions
-----------
* Gravity is stored as a ratio to standard gravity, ``g/g0`` with g0 = 9.80665 m/s^2 (exact).
* Oxygen concentration is stored as a mole fraction (0-1); percent inputs are divided by 100.
* Pressure in Pa, velocity in m/s, length in m, burning-rate constant in m^2/s.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pint

G0_M_S2 = 9.80665  # standard gravity, exact by definition (CGPM 1901)

# Canonical SI unit for each physical dimension we store.
SI_UNITS: dict[str, str] = {
    "length": "m",
    "velocity": "m/s",
    "pressure": "Pa",
    "fraction": "dimensionless",
    "gravity_ratio": "dimensionless",
    "time": "s",
    "area_rate": "m**2/s",
    "power": "W",
    "temperature": "K",
    "mass_per_area": "kg/m**2",
}

# Units allowed in source documents, mapped to the dimension they measure.
_ALIASES: dict[str, str] = {
    "%": "percent",
    "pct": "percent",
    "mole_percent": "percent",
    "vol%": "percent",
    "psia": "psi",
    # In Finding Cards "g" always means multiples of standard gravity, never grams.
    "g": "g_ratio",
    "g0": "g_ratio",
    "g/g0": "g_ratio",
    "mm2/s": "mm**2/s",
    "mm^2/s": "mm**2/s",
    "cm/s": "cm/s",
    "mm/s": "mm/s",
    "um": "micrometer",
    "µm": "micrometer",
    "micron": "micrometer",
    "mil": "thou",  # 0.001 inch (pint parses bare "mil" as an angle)
    "mmhg": "mmHg",
    "torr": "torr",
}


@lru_cache(maxsize=1)
def registry() -> Any:
    ureg: Any = pint.UnitRegistry()
    # Dimensionless ratio g/g0 (pint's own `g0` is the acceleration 9.80665 m/s^2, not a ratio).
    ureg.define("g_ratio = 1")
    return ureg


def _parse_unit(unit: str) -> Any:
    ureg = registry()
    key = unit.strip()
    key = _ALIASES.get(key.lower(), _ALIASES.get(key, key))
    return ureg.parse_units(key)


def to_si(value: float, unit: str, dimension: str) -> float:
    """Convert ``value`` expressed in ``unit`` to the canonical SI unit of ``dimension``.

    Raises ``ValueError`` if the unit is incompatible with the dimension (e.g. kPa for velocity).
    """
    if dimension not in SI_UNITS:
        raise ValueError(f"Unknown dimension '{dimension}'")
    ureg = registry()
    q = ureg.Quantity(value, _parse_unit(unit))
    target = SI_UNITS[dimension]
    try:
        converted = q.to(target)
    except pint.DimensionalityError as exc:
        raise ValueError(f"Unit '{unit}' is not a {dimension}") from exc
    return float(converted.magnitude)


def from_si(value_si: float, unit: str, dimension: str) -> float:
    """Inverse of :func:`to_si` (for display)."""
    ureg = registry()
    q = ureg.Quantity(value_si, ureg.parse_units(SI_UNITS[dimension]))
    return float(q.to(_parse_unit(unit)).magnitude)


def psi_to_kpa(psi: float) -> float:
    return to_si(psi, "psi", "pressure") / 1000.0


def o2_partial_pressure_kpa(o2_mole_fraction: float, total_pressure_pa: float) -> float:
    """Dalton's law: pO2 = X_O2 * P (returned in kPa)."""
    if not 0.0 <= o2_mole_fraction <= 1.0:
        raise ValueError("O2 mole fraction must be within [0, 1]")
    if total_pressure_pa < 0:
        raise ValueError("Pressure must be non-negative")
    return o2_mole_fraction * total_pressure_pa / 1000.0
