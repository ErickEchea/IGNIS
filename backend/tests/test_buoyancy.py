import pytest
from hypothesis import given
from hypothesis import strategies as st

from ignis.core.buoyancy import (
    analog_flow_window,
    buoyant_velocity,
    buoyant_velocity_ratio,
    equivalent_gravity_for_flow,
)


def test_one_g_returns_anchor_interval() -> None:
    bv = buoyant_velocity(1.0)
    assert (bv.low_cm_s, bv.high_cm_s) == (33.0, 35.0)
    assert bv.data_type == "MODELED"


def test_lunar_and_martian_ratios() -> None:
    # 0.165^(1/3) = 0.5484 ; 0.380^(1/3) = 0.7243
    assert buoyant_velocity_ratio(0.165) == pytest.approx(0.5484, abs=1e-4)
    assert buoyant_velocity_ratio(0.380) == pytest.approx(0.7243, abs=1e-4)
    moon = buoyant_velocity(0.165)
    assert moon.low_cm_s == pytest.approx(18.10, abs=0.01)
    assert moon.high_cm_s == pytest.approx(19.19, abs=0.01)


def test_zero_gravity_has_no_buoyant_flow() -> None:
    assert buoyant_velocity(0.0).high_cm_s == 0.0


def test_negative_inputs_rejected() -> None:
    with pytest.raises(ValueError):
        buoyant_velocity(-0.1)
    with pytest.raises(ValueError):
        equivalent_gravity_for_flow(-1)


@given(st.floats(min_value=1e-4, max_value=3.0, allow_nan=False))
def test_inverse_consistency(g: float) -> None:
    bv = buoyant_velocity(g)
    lo_g, hi_g = equivalent_gravity_for_flow(bv.mid_cm_s)
    assert lo_g <= g * (1 + 1e-9) and g <= hi_g * (1 + 1e-9)


@given(st.floats(min_value=0.0, max_value=3.0), st.floats(min_value=0.0, max_value=3.0))
def test_monotonic(g1: float, g2: float) -> None:
    if g1 < g2:
        assert buoyant_velocity_ratio(g1) <= buoyant_velocity_ratio(g2)


def test_analog_window_contains_estimate() -> None:
    lo, hi = analog_flow_window(0.38, tolerance=0.25)
    bv = buoyant_velocity(0.38)
    assert lo < bv.low_cm_s and hi > bv.high_cm_s
