"""Component library for FarmTwin: fittings, valves, filters, pumps, venturi.

Design principle: every in-line component is a *link* that exposes
    headloss(Q)  -> signed head change (loss positive, pump gain negative)
    gradient(Q)  -> d(headloss)/dQ   (always >= 0 form used by the GGA)
Node-level outlets (emitters) live in emitters.py.

All SI: Q in m^3/s, head in m, diameter in m.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .headloss import G, resistance
from .params import ParameterSet

# 1 horsepower in kilowatts
HP_KW = 0.7457

# ---------------------------------------------------------------------------
# Minor-loss (K) coefficient library for common irrigation fittings/accessories
# Values are typical engineering ranges; override per manufacturer data.
# ---------------------------------------------------------------------------
K_LIBRARY = {
    "elbow_90_threaded": 0.9,  # L-connector, 90 deg
    "elbow_90_long": 0.30,  # long-radius bend
    "elbow_45": 0.40,
    "tee_run": 0.60,  # T-connector, flow through the run
    "tee_branch": 1.80,  # T-connector, flow turns into branch
    "coupler": 0.10,
    "reducer": 0.25,
    "ball_valve_open": 0.05,  # fully open
    "ball_valve_half": 2.10,  # ~half closed
    "gate_valve_open": 0.15,
    "check_valve": 2.50,
    "foot_valve_strainer": 6.0,
    "screen_filter": 12.0,  # clean; rises with clogging
    "disc_filter": 18.0,
    "media_filter": 30.0,
    "entrance": 0.50,
    "exit": 1.00,
}


def k_of(name: str) -> float:
    """Look up a minor-loss K coefficient by fitting name."""
    try:
        return K_LIBRARY[name]
    except KeyError as exc:
        raise KeyError(f"Unknown fitting {name!r}. Known: {sorted(K_LIBRARY)}") from exc


def sum_k(*names: str) -> float:
    """Total K for a list of fittings on a pipe, e.g. sum_k('tee_run','elbow_45')."""
    return sum(k_of(n) for n in names)


def minor_loss_m(total_k: float, diameter: float, params: ParameterSet | None = None) -> float:
    """Convert total K into the coefficient m such that h_minor = m * Q*|Q|.

    h_minor = K * V^2 / (2 g) = K / (2 g A^2) * Q^2,  A = pi d^2 / 4.
    """
    p = params or ParameterSet()
    area = math.pi * diameter**2 / 4.0
    return total_k / (2.0 * p.gravity_ms2 * area**2)


# ---------------------------------------------------------------------------
# Pipe link evaluation (friction + minor losses)
# ---------------------------------------------------------------------------
def pipe_headloss_gradient(flow, length, diameter, coeff, model, total_k, params=None):
    """Return (headloss, gradient) for a pipe carrying signed `flow`.

    headloss = r*Q*|Q|^(n-1) + m*Q*|Q|   (signed, loss in direction of flow)
    gradient = n*r*|Q|^(n-1) + 2*m*|Q|    (EPANET eq. 12.8 form)

    The gradient evaluates |Q| at no less than ``zero_flow_eps_m3s`` so it stays
    bounded as Q -> 0 (Elhay-Simpson regularization); for physical flows this is
    a no-op since the threshold (~1e-6 m^3/s) is far below any solved flow.
    """
    p = params or ParameterSet()
    r, n = resistance(model, flow, length, diameter, coeff, p)
    m = minor_loss_m(total_k, diameter, p)
    aq = abs(flow)
    aq_grad = max(aq, p.zero_flow_eps_m3s)
    headloss = r * flow * aq ** (n - 1.0) + m * flow * aq
    gradient = n * r * aq_grad ** (n - 1.0) + 2.0 * m * aq_grad
    # floor the gradient to avoid divide-by-zero at Q=0 in the GGA
    return headloss, max(gradient, 1e-8)


# ---------------------------------------------------------------------------
# Venturi injector: a deliberate loss element + fertigation source.
# Modeled as h_loss = a * Q*|Q| (manufacturer loss curve), plus injection meta.
# ---------------------------------------------------------------------------
@dataclass
class Venturi:
    a: float  # loss-curve coefficient (s^2/m^5): dH = a*Q^2
    injection_rate: float = 0.0  # fertilizer solution flow injected (m^3/s)
    concentration: float = 0.0  # injected nutrient concentration (kg/m^3)

    def headloss_gradient(self, flow):
        aq = abs(flow)
        return self.a * flow * aq, max(2.0 * self.a * aq, 1e-8)


# ---------------------------------------------------------------------------
# Pump: head-gain curve  h_gain(Q) = h0 - r_p * Q^c   (c default 2)
# As a link, the "headloss" returned is NEGATIVE of the gain so the GGA energy
# equation H_start - H_end = headloss is satisfied with a head rise.
# ---------------------------------------------------------------------------
@dataclass
class PumpCurve:
    h0: float  # shutoff head (Q=0), m
    r_p: float  # curve coefficient
    c: float = 2.0  # curve exponent
    pump_eff: float = 0.70  # pump efficiency (fraction)
    motor_eff: float = 0.90  # motor efficiency (fraction)

    @classmethod
    def from_design_point(
        cls, q_design, h_design, pump_eff=0.70, motor_eff=0.90, c=2.0, shutoff_factor=1.33
    ):
        """Build a curve from a single design (duty) point.

        Assumes shutoff head h0 = shutoff_factor * h_design (typical ~1.33),
        then solves r_p so the curve passes through (q_design, h_design).
        """
        h0 = shutoff_factor * h_design
        if q_design <= 0:
            raise ValueError("q_design must be > 0")
        r_p = (h0 - h_design) / q_design**c
        return cls(h0=h0, r_p=r_p, c=c, pump_eff=pump_eff, motor_eff=motor_eff)

    @classmethod
    def from_three_points(cls, h0, q_design, h_design, pump_eff=0.70, motor_eff=0.90, c=2.0):
        """Build a curve with a known shutoff head h0 fitted through the duty point.

        With the exponent ``c`` fixed (default 2), solves ``r_p`` so the curve
        ``h0 - r_p*Q^c`` passes through ``(q_design, h_design)``. A runout point
        can be used by the caller to sanity-check; here it is implied by the fit.
        """
        if q_design <= 0:
            raise ValueError("q_design must be > 0")
        r_p = max((h0 - h_design) / q_design**c, 0.0)
        return cls(h0=h0, r_p=r_p, c=c, pump_eff=pump_eff, motor_eff=motor_eff)

    @classmethod
    def from_fts(cls, attributes: dict):
        """Build a PumpCurve from an FTS pump node's ``attributes`` block.

        Uses ``curve_shutoff_m`` + ``curve_design_q_m3s``/``curve_design_h_m``
        when available (a true shutoff-anchored fit); falls back to a single
        design point. Nameplate efficiencies (``*_efficiency_pct``) are carried
        through for motor sizing.
        """
        h0 = attributes.get("curve_shutoff_m")
        qd = attributes.get("curve_design_q_m3s")
        hd = attributes.get("curve_design_h_m")
        pump_eff = float(attributes.get("pump_efficiency_pct", 70.0)) / 100.0
        motor_eff = float(attributes.get("motor_efficiency_pct", 90.0)) / 100.0
        if qd is None or hd is None:
            raise ValueError("FTS pump attributes need curve_design_q_m3s and curve_design_h_m")
        if h0 is not None:
            return cls.from_three_points(h0, qd, hd, pump_eff=pump_eff, motor_eff=motor_eff)
        return cls.from_design_point(qd, hd, pump_eff=pump_eff, motor_eff=motor_eff)

    def head_gain(self, flow):
        q = max(flow, 0.0)
        return self.h0 - self.r_p * q**self.c

    def headloss_gradient(self, flow):
        # link "loss" = -gain ; gradient of loss wrt Q = + c r_p Q^(c-1)
        q = max(flow, 0.0)
        headloss = -(self.h0 - self.r_p * q**self.c)
        gradient = self.c * self.r_p * q ** (self.c - 1.0) if q > 0 else 1e-8
        return headloss, max(gradient, 1e-8)

    # ---- motor sizing (the 1..50 HP requirement) ----
    def hydraulic_power_kw(self, flow, head, rho=1000.0):
        return rho * G * flow * head / 1000.0

    def motor_hp(self, flow, head, rho=1000.0):
        """Required motor rating in HP for duty point (flow, head)."""
        p_hyd = self.hydraulic_power_kw(flow, head, rho)
        p_shaft = p_hyd / max(self.pump_eff, 1e-6)
        p_motor_kw = p_shaft / max(self.motor_eff, 1e-6)
        return p_motor_kw / HP_KW


# Standard single-phase/three-phase motor catalog sizes (HP) for snapping.
MOTOR_CATALOG_HP = [1, 1.5, 2, 3, 5, 7.5, 10, 12.5, 15, 20, 25, 30, 40, 50]


def select_motor_hp(required_hp: float, safety: float = 1.15):
    """Snap a required HP (x safety margin) up to the next catalog size.

    Returns (catalog_hp, used_safety_required_hp). Caps at 50 HP and flags
    over-range with a ValueError so the caller knows to split/redesign.
    """
    target = required_hp * safety
    for hp in MOTOR_CATALOG_HP:
        if hp >= target:
            return hp, target
    raise ValueError(
        f"Required {target:.1f} HP exceeds the 1-50 HP range; "
        f"split the system into zones or use multiple pumps."
    )
