"""Gravity bridging by buoyancy-induced velocity scaling (deterministic, documented).

Physics
-------
Balancing inertia against buoyancy over the gas-phase thermal length L_g = alpha_g / u gives

    u^2 / L_g ~ a * beta * dT   =>   u_b = (alpha_g * a * beta * dT)^(1/3)  ∝  a^(1/3)

(Konno, Ishikawa, Hashimoto & Fujita 2024, Proc. Combust. Inst. 40:105199, following Altenkirch,
Eichhorn & Shang 1980; Nakaya, KAKEN 21K18775 report uses V_b ~ [alpha_g g (T_f - T_inf)/T_v]^(1/3)).

The proportionality constant is anchored at 1 g by values reported in those sources:
33.0 cm/s (Nakaya, fit at 1 G, 21% O2) and 35 cm/s (Konno et al. 2024, citing Takahashi et al. 2015).
We carry the anchor as an interval [33, 35] cm/s rather than picking one value.

Assumptions (shown in the UI next to every number)
* alpha_g, beta and dT are independent of the gravity level (gas properties at fixed O2/pressure).
* Characteristic buoyant velocity only: real buoyant flows are non-uniform and direction-dependent,
  so this is an order-of-magnitude *equivalent forced-flow* scale, not a flow field.
* Gas radiation and transient (short-test) effects are ignored.
* Anchors come from downward/opposed flame spread configurations at 1 atm, 21% O2.

Data type: MODELED (scaling estimate). Never a measurement.
"""

from __future__ import annotations

from dataclasses import dataclass

ANCHOR_1G_CM_S = (33.0, 35.0)
ANCHOR_SOURCES = ("KAKEN-21K18775", "DOI-10.1016/j.proci.2024.105199")
EXPONENT = 1.0 / 3.0

ASSUMPTIONS = (
    "Gas properties (thermal diffusivity, expansion coefficient, flame-ambient temperature difference)"
    " are taken as independent of gravity level.",
    "u_b is a characteristic velocity scale, not a flow field; real buoyant flows are non-uniform and"
    " depend on flame orientation.",
    "Radiation and short-duration (transient) effects are neglected.",
    "The 1-g anchor (33-35 cm/s) comes from downward/opposed spread at 1 atm and 21% O2; other"
    " atmospheres change the anchor.",
)


@dataclass(frozen=True)
class BuoyantVelocity:
    gravity_g0: float
    low_cm_s: float
    high_cm_s: float
    ratio_to_1g: float
    data_type: str = "MODELED"

    @property
    def mid_cm_s(self) -> float:
        return 0.5 * (self.low_cm_s + self.high_cm_s)


def buoyant_velocity_ratio(gravity_g0: float) -> float:
    """u_b(g) / u_b(1 g) = (g/g0)^(1/3)."""
    if gravity_g0 < 0:
        raise ValueError("gravity level must be non-negative")
    return float(gravity_g0**EXPONENT)


def buoyant_velocity(gravity_g0: float) -> BuoyantVelocity:
    """Interval estimate of the characteristic buoyant velocity at ``gravity_g0`` (multiples of g0)."""
    ratio = buoyant_velocity_ratio(gravity_g0)
    lo, hi = ANCHOR_1G_CM_S
    return BuoyantVelocity(
        gravity_g0=gravity_g0, low_cm_s=lo * ratio, high_cm_s=hi * ratio, ratio_to_1g=ratio
    )


def equivalent_gravity_for_flow(flow_cm_s: float) -> tuple[float, float]:
    """Gravity interval (g/g0) whose buoyant velocity scale equals a forced flow ``flow_cm_s``.

    Inverse of :func:`buoyant_velocity`: g = (u / u_1g)^3. Used to place microgravity forced-flow
    experiments on the gravity axis as *analogs*, never as equivalents.
    """
    if flow_cm_s < 0:
        raise ValueError("flow velocity must be non-negative")
    lo, hi = ANCHOR_1G_CM_S
    return ((flow_cm_s / hi) ** 3, (flow_cm_s / lo) ** 3)


def analog_flow_window(gravity_g0: float, tolerance: float = 0.25) -> tuple[float, float]:
    """Forced-flow window (cm/s) whose speed matches u_b(g) within ±tolerance (fractional)."""
    bv = buoyant_velocity(gravity_g0)
    return (bv.low_cm_s * (1 - tolerance), bv.high_cm_s * (1 + tolerance))
