import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ignis.core.units import from_si, o2_partial_pressure_kpa, psi_to_kpa, to_si


def test_psi_to_kpa_exploration_atmospheres() -> None:
    # 14.7 psia = 101.35 kPa; 10.2 psia = 70.33 kPa; 8.2 psia = 56.54 kPa (1 psi = 6.894757 kPa)
    assert psi_to_kpa(14.7) == pytest.approx(101.353, abs=1e-3)
    assert psi_to_kpa(10.2) == pytest.approx(70.327, abs=1e-3)
    assert psi_to_kpa(8.2) == pytest.approx(56.537, abs=1e-3)


def test_percent_to_mole_fraction() -> None:
    assert to_si(34, "%", "fraction") == pytest.approx(0.34)
    assert to_si(26.5, "percent", "fraction") == pytest.approx(0.265)


def test_gravity_ratio_is_dimensionless_and_g_is_not_grams() -> None:
    assert to_si(0.165, "g", "gravity_ratio") == pytest.approx(0.165)
    assert to_si(0.38, "g0", "gravity_ratio") == pytest.approx(0.38)


def test_velocity_and_burning_rate() -> None:
    assert to_si(20, "cm/s", "velocity") == pytest.approx(0.20)
    assert to_si(0.52, "mm2/s", "area_rate") == pytest.approx(0.52e-6)


def test_mil_is_a_thousandth_of_an_inch() -> None:
    assert to_si(5, "mil", "length") == pytest.approx(127e-6)


def test_mmhg_to_pa() -> None:
    assert to_si(760, "mmHg", "pressure") == pytest.approx(101325, rel=1e-4)


def test_incompatible_unit_rejected() -> None:
    with pytest.raises(ValueError):
        to_si(10, "kPa", "velocity")
    with pytest.raises(ValueError):
        to_si(1, "m", "nonexistent")


def test_partial_pressure() -> None:
    # 34% O2 at 8.2 psia -> 19.2 kPa; 21% at 14.7 psia -> 21.3 kPa
    assert o2_partial_pressure_kpa(0.34, to_si(8.2, "psi", "pressure")) == pytest.approx(19.22, abs=0.01)
    assert o2_partial_pressure_kpa(0.21, to_si(14.7, "psi", "pressure")) == pytest.approx(21.28, abs=0.01)
    with pytest.raises(ValueError):
        o2_partial_pressure_kpa(1.2, 1e5)


@given(st.floats(min_value=1e-6, max_value=1e6, allow_nan=False))
def test_round_trip_pressure(value: float) -> None:
    for unit in ("psi", "kPa", "mmHg", "atm", "bar"):
        assert from_si(to_si(value, unit, "pressure"), unit, "pressure") == pytest.approx(value, rel=1e-9)


@given(st.floats(min_value=0, max_value=100, allow_nan=False))
def test_percent_bounds(value: float) -> None:
    frac = to_si(value, "%", "fraction")
    assert 0.0 <= frac <= 1.0
    assert math.isclose(frac * 100, value, rel_tol=1e-12, abs_tol=1e-12)
