"""Pipe head-loss models for the FarmTwin hydraulic solver.

All quantities are SI: flow Q in m^3/s, length L and diameter d in m, head in m.

Each model returns the *resistance coefficient* r and *exponent* n such that the
signed head loss across a pipe is

    h_L = r * Q * |Q|^(n-1)

and the gradient (derivative of h_L w.r.t. Q, used by the Global Gradient
Algorithm) is

    g = dh_L/dQ = n * r * |Q|^(n-1)

For Darcy-Weisbach the friction factor depends on Q (Reynolds number), so r is
recomputed each iteration from the current flow estimate.
"""

from __future__ import annotations

import math

from .params import ParameterSet

# Module-level defaults (kept for backward-compatible imports). The live
# coefficients used by the solver come from a ParameterSet, not these literals.
_DEFAULTS = ParameterSet()
G = _DEFAULTS.gravity_ms2  # gravitational acceleration, m/s^2
NU_WATER = _DEFAULTS.kinematic_viscosity_m2s  # kinematic viscosity of water, m^2/s


def hazen_williams_r(
    length: float, diameter: float, c: float, params: ParameterSet | None = None
) -> float:
    """Hazen-Williams resistance coefficient (SI).

    r = factor * L / (C^n * d^m), with factor/n/m taken from the ParameterSet
    (defaults 10.67 / 1.852 / 4.87) so the twin can recalibrate them.
    """
    p = params or _DEFAULTS
    return p.hw_coefficient_factor * length / (c**p.hw_exponent * diameter**p.hw_diameter_exponent)


def swamee_jain_f(reynolds: float, roughness: float, diameter: float) -> float:
    """Explicit friction factor.

    Laminar (Re < 2000): f = 64 / Re.
    Turbulent: Swamee-Jain approximation to Colebrook-White.
    A smooth blend is used in the transitional band to keep the solver stable.
    """
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2000.0:
        return 64.0 / reynolds
    turbulent = 0.25 / (math.log10(roughness / (3.7 * diameter) + 5.74 / reynolds**0.9) ** 2)
    if reynolds < 4000.0:
        # linear blend laminar<->turbulent across the transition band
        f_lam = 64.0 / 2000.0
        w = (reynolds - 2000.0) / 2000.0
        return (1.0 - w) * f_lam + w * turbulent
    return turbulent


def darcy_weisbach_r(
    flow: float,
    length: float,
    diameter: float,
    roughness: float,
    params: ParameterSet | None = None,
) -> float:
    """Darcy-Weisbach resistance coefficient for the *current* flow estimate.

    h_L = f * (L/d) * V^2 / (2 g) = r * Q^2, with
    r = 8 * f * L / (pi^2 * g * d^5).
    Exponent n = 2. Uses Swamee-Jain for f; g and viscosity come from params.
    """
    p = params or _DEFAULTS
    area = math.pi * diameter**2 / 4.0
    velocity = abs(flow) / area if area > 0 else 0.0
    reynolds = velocity * diameter / p.kinematic_viscosity_m2s
    f = swamee_jain_f(reynolds, roughness, diameter)
    return 8.0 * f * length / (math.pi**2 * p.gravity_ms2 * diameter**5)


def resistance(
    model: str,
    flow: float,
    length: float,
    diameter: float,
    coeff: float,
    params: ParameterSet | None = None,
):
    """Return (r, n) for the chosen head-loss model.

    model: "HW" (Hazen-Williams, coeff = C) or "DW" (Darcy-Weisbach,
    coeff = absolute roughness epsilon in m).
    """
    p = params or _DEFAULTS
    m = model.upper()
    if m in ("HW", "HAZEN-WILLIAMS", "HAZEN_WILLIAMS"):
        return hazen_williams_r(length, diameter, coeff, p), p.hw_exponent
    if m in ("DW", "DARCY-WEISBACH", "DARCY_WEISBACH"):
        return darcy_weisbach_r(flow, length, diameter, coeff, p), 2.0
    raise ValueError(f"Unknown head-loss model: {model!r} (use 'HW' or 'DW')")
