"""Transient / water-hammer analysis for FarmTwin (R-TRANS-1..3).

Provides a dependency-free **Method of Characteristics (MOC)** reference solver
for the classic reservoir-pipe-valve water-hammer problem, used to size surge
protection and justify pump<->valve sequencing interlocks. For full network
transients (bursts, leaks, surge tanks, pump trips, unsteady friction) the
module delegates to the open-source **TSNet** package when it is installed
(``pip install farmtwin[pro]``); TSNet runs MOC on a WNTR/EPANET model.

White papers:
    Wylie & Streeter (1993) *Fluid Transients in Systems* (MOC).
    Chaudhry, *Applied Hydraulic Transients* (boundary devices).
    Tian et al. (2019) TSNet, *Environ. Model. Softw.* (open-source Python MOC).
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

G = 9.81  # gravitational acceleration, m/s^2


def joukowsky_head_rise(wave_speed_ms: float, delta_velocity_ms: float) -> float:
    """Joukowsky pressure-head rise for an instantaneous velocity change.

    Args:
        wave_speed_ms: Pressure-wave celerity ``a`` (m/s).
        delta_velocity_ms: Magnitude of the velocity change ``|dV|`` (m/s).

    Returns:
        Head rise ``a * dV / g`` (m).
    """
    return wave_speed_ms * delta_velocity_ms / G


@dataclass
class PipeProfile:
    """Single-pipe transient configuration (reservoir upstream, valve down)."""

    length_m: float
    diameter_m: float
    wave_speed_ms: float
    reservoir_head_m: float
    initial_velocity_ms: float
    friction_factor: float = 0.0  # Darcy-Weisbach f (0 = frictionless)

    @property
    def area_m2(self) -> float:
        """Pipe cross-sectional area (m^2)."""
        return math.pi * self.diameter_m**2 / 4.0


@dataclass
class TransientResult:
    """Time history of a transient run at the valve (downstream) node."""

    time_s: list[float]
    head_valve_m: list[float]
    max_head_m: float
    min_head_m: float
    joukowsky_head_m: float
    courant: float


def _valve_head(c_plus: float, b_coeff: float, cd: float) -> tuple[float, float]:
    """Solve the valve boundary (C+ characteristic + orifice law).

    Args:
        c_plus: Known C+ characteristic value.
        b_coeff: Characteristic impedance ``B = a/(gA)``.
        cd: Effective valve coefficient ``tau * Q0 / sqrt(H0)`` (0 = shut).

    Returns:
        ``(head, flow)`` at the valve for this timestep.
    """
    if cd <= 0.0:
        return c_plus, 0.0  # fully closed: Q = 0, H = C+
    # H = C+ - B*Q and Q = Cd*sqrt(H) -> solve quadratic in s = sqrt(H).
    disc = (b_coeff * cd) ** 2 + 4.0 * c_plus
    s = 0.5 * (-b_coeff * cd + math.sqrt(max(disc, 0.0)))
    head = s * s
    return head, cd * s


def simulate_valve_closure(
    profile: PipeProfile,
    *,
    valve_closure_time_s: float,
    total_time_s: float,
    n_reaches: int = 20,
) -> TransientResult:
    """Simulate downstream-valve closure on a single pipe by MOC.

    The grid uses a Courant number of exactly 1 (``dt = dx / a``), the standard
    MOC choice, so the scheme is non-dissipative for the reference case.

    Args:
        profile: Pipe and steady-state description.
        valve_closure_time_s: Linear closure duration (s); 0 = instantaneous.
        total_time_s: Simulated duration (s).
        n_reaches: Number of spatial reaches (pipe divided into N segments).

    Returns:
        A :class:`TransientResult` with the head history at the valve and the
        Joukowsky reference rise for validation.
    """
    a = profile.wave_speed_ms
    area = profile.area_m2
    dx = profile.length_m / n_reaches
    dt = dx / a
    n_steps = max(1, int(round(total_time_s / dt)))
    b_coeff = a / (G * area)
    r_coeff = profile.friction_factor * dx / (2.0 * G * profile.diameter_m * area**2)

    q0 = profile.initial_velocity_ms * area
    head = np.array(
        [profile.reservoir_head_m - i * r_coeff * q0 * abs(q0) for i in range(n_reaches + 1)],
        dtype=float,
    )
    flow = np.full(n_reaches + 1, q0, dtype=float)
    cv = q0 / math.sqrt(profile.reservoir_head_m) if profile.reservoir_head_m > 0 else 0.0

    times = [0.0]
    valve_head = [float(head[-1])]
    h_new = head.copy()
    q_new = flow.copy()
    for step in range(1, n_steps + 1):
        t = step * dt
        cp_int = head[:-2] + b_coeff * flow[:-2] - r_coeff * flow[:-2] * np.abs(flow[:-2])
        cm_int = head[2:] - b_coeff * flow[2:] + r_coeff * flow[2:] * np.abs(flow[2:])
        h_new[1:-1] = 0.5 * (cp_int + cm_int)
        q_new[1:-1] = (cp_int - cm_int) / (2.0 * b_coeff)

        cm0 = head[1] - b_coeff * flow[1] + r_coeff * flow[1] * abs(flow[1])
        h_new[0] = profile.reservoir_head_m
        q_new[0] = (h_new[0] - cm0) / b_coeff

        cp_n = head[-2] + b_coeff * flow[-2] - r_coeff * flow[-2] * abs(flow[-2])
        tau = max(0.0, 1.0 - t / valve_closure_time_s) if valve_closure_time_s > 0 else 0.0
        h_new[-1], q_new[-1] = _valve_head(cp_n, b_coeff, tau * cv)

        head, h_new = h_new, head
        flow, q_new = q_new, flow
        times.append(t)
        valve_head.append(float(head[-1]))

    return TransientResult(
        time_s=times,
        head_valve_m=valve_head,
        max_head_m=max(valve_head),
        min_head_m=min(valve_head),
        joukowsky_head_m=joukowsky_head_rise(a, abs(profile.initial_velocity_ms)),
        courant=1.0,
    )


def tsnet_available() -> bool:
    """Return True if the optional TSNet backend is importable."""
    try:
        import tsnet  # noqa: F401
    except ImportError:
        return False
    return True


def simulate_network_tsnet(  # noqa: PLR0913
    inp_path: str,
    *,
    valve_name: str,
    close_at_s: float = 0.0,
    close_dur_s: float = 1.0,
    total_time_s: float = 20.0,
    friction: str = "unsteady",
) -> object:
    """Run a full-network transient with TSNet (MOC on a WNTR/EPANET model).

    This is the production path for multi-pipe transients with surge devices
    and unsteady friction; it is only available when ``tsnet`` is installed.

    Args:
        inp_path: EPANET ``.inp`` file describing the network.
        valve_name: Name of the valve to operate.
        close_at_s: Time at which closure starts (s).
        close_dur_s: Closure duration (s).
        total_time_s: Total simulated duration (s).
        friction: ``"steady"``, ``"quasi-steady"`` or ``"unsteady"``.

    Returns:
        The TSNet transient model object holding per-node result histories.

    Raises:
        ImportError: If TSNet is not installed.
    """
    import tsnet

    tm = tsnet.network.TransientModel(inp_path)
    tm.set_wavespeed(1200.0)
    dt = tm.set_time(total_time_s)
    del dt
    tm.valve_closure(valve_name, [close_at_s, close_dur_s, 1.0, 0.0])
    tsnet.simulation.Initializer(tm, 0)
    return tsnet.simulation.MOCSimulator(tm, friction=friction)
