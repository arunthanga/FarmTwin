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

G = 9.81  # gravitational acceleration, m/s^2
NU_WATER = 1.0e-6  # kinematic viscosity of water at ~20 C, m^2/s


def hazen_williams_r(length: float, diameter: float, c: float) -> float:
    """Hazen-Williams resistance coefficient (SI). Exponent n = 1.852.

    r = 10.67 * L / (C^1.852 * d^4.87)
    """
    return 10.67 * length / (c**1.852 * diameter**4.87)


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


def darcy_weisbach_r(flow: float, length: float, diameter: float, roughness: float) -> float:
    """Darcy-Weisbach resistance coefficient for the *current* flow estimate.

    h_L = f * (L/d) * V^2 / (2 g) = r * Q^2, with
    r = 8 * f * L / (pi^2 * g * d^5).
    Exponent n = 2. Uses Swamee-Jain for f.
    """
    area = math.pi * diameter**2 / 4.0
    velocity = abs(flow) / area if area > 0 else 0.0
    reynolds = velocity * diameter / NU_WATER
    f = swamee_jain_f(reynolds, roughness, diameter)
    return 8.0 * f * length / (math.pi**2 * G * diameter**5)


def resistance(model: str, flow: float, length: float, diameter: float, coeff: float):
    """Return (r, n) for the chosen head-loss model.

    model: "HW" (Hazen-Williams, coeff = C) or "DW" (Darcy-Weisbach,
    coeff = absolute roughness epsilon in m).
    """
    m = model.upper()
    if m in ("HW", "HAZEN-WILLIAMS", "HAZEN_WILLIAMS"):
        return hazen_williams_r(length, diameter, coeff), 1.852
    if m in ("DW", "DARCY-WEISBACH", "DARCY_WEISBACH"):
        return darcy_weisbach_r(flow, length, diameter, coeff), 2.0
    raise ValueError(f"Unknown head-loss model: {model!r} (use 'HW' or 'DW')")
