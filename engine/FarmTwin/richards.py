"""Soil-water (root-zone twin) via the Richards equation (R-SOIL-1..2).

Provides the **van Genuchten-Mualem** retention/conductivity closures and a
mass-conservative 1-D vertical column solver written as a method of lines
(the openRE approach): the moisture content ``theta`` is the state variable and
the flux divergence is integrated by an ODE solver, which conserves mass by
construction. SciPy's adaptive integrator is used when available; otherwise an
explicit fallback step is provided. Validate against HYDRUS.

White papers:
    van Genuchten (1980) *SSSAJ* 44(5):892-898 (retention/conductivity).
    Celia, Bouloutas & Zarba (1990) *WRR* 26(7) (mass-conservative form).
    openRE v1.0, *Geosci. Model Dev.* 16:659 (2023) (method-of-lines + SFOM).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math

import numpy as np

RhsFunc = Callable[[float, np.ndarray], np.ndarray]

SECONDS_PER_DAY = 86400.0


@dataclass
class VanGenuchten:
    """Van Genuchten-Mualem soil hydraulic parameters (SI).

    Attributes:
        alpha_per_m: Inverse air-entry scale ``alpha`` (1/m).
        n: Pore-size distribution index ``n`` (> 1).
        theta_r: Residual volumetric water content (m^3/m^3).
        theta_s: Saturated volumetric water content (m^3/m^3).
        ks_m_per_day: Saturated hydraulic conductivity (m/day).
        l_pore: Mualem pore-connectivity (usually 0.5).
    """

    alpha_per_m: float
    n: float
    theta_r: float
    theta_s: float
    ks_m_per_day: float
    l_pore: float = 0.5

    @property
    def m(self) -> float:
        """Van Genuchten exponent ``m = 1 - 1/n``."""
        return 1.0 - 1.0 / self.n

    def effective_saturation(self, psi_m: float) -> float:
        """Effective saturation ``Se`` from pressure head ``psi`` (m).

        ``psi >= 0`` (saturated) gives ``Se = 1``.
        """
        if psi_m >= 0.0:
            return 1.0
        return (1.0 + (self.alpha_per_m * abs(psi_m)) ** self.n) ** (-self.m)

    def theta(self, psi_m: float) -> float:
        """Volumetric water content from pressure head (m^3/m^3)."""
        return self.theta_r + (self.theta_s - self.theta_r) * self.effective_saturation(psi_m)

    def head_from_theta(self, theta: float) -> float:
        """Invert retention: pressure head ``psi`` (m) from water content."""
        span = self.theta_s - self.theta_r
        se = min(max((theta - self.theta_r) / span, 1.0e-9), 1.0)
        if se >= 1.0:
            return 0.0
        term = se ** (-1.0 / self.m) - 1.0
        return -(term ** (1.0 / self.n)) / self.alpha_per_m

    def conductivity_from_se(self, se: float) -> float:
        """Mualem unsaturated conductivity ``K(Se)`` (m/day)."""
        se = min(max(se, 0.0), 1.0)
        if se >= 1.0:
            return self.ks_m_per_day
        bracket = (1.0 - (1.0 - se ** (1.0 / self.m)) ** self.m) ** 2
        return self.ks_m_per_day * se**self.l_pore * bracket

    def capacity(self, psi_m: float) -> float:
        """Specific moisture capacity ``C = dtheta/dpsi`` (1/m)."""
        if psi_m >= 0.0:
            return 0.0
        ah = self.alpha_per_m * abs(psi_m)
        span = self.theta_s - self.theta_r
        denom = (1.0 + ah**self.n) ** (self.m + 1.0)
        return (span * self.m * self.n * self.alpha_per_m * ah ** (self.n - 1.0)) / denom


def _fluxes(
    theta: np.ndarray,
    vg: VanGenuchten,
    dz: float,
    top_flux: float,
) -> np.ndarray:
    """Internal/boundary Darcy fluxes (m/day) at the cell faces.

    Sign convention: positive flux is downward (+z points down).
    Top face uses the prescribed infiltration flux; bottom face uses unit
    gradient (free drainage).
    """
    span = vg.theta_s - vg.theta_r
    psi = np.array([vg.head_from_theta(t) for t in theta])
    se = np.clip((theta - vg.theta_r) / span, 0.0, 1.0)
    k = np.array([vg.conductivity_from_se(s) for s in se])
    n = len(theta)
    faces = np.zeros(n + 1)
    faces[0] = top_flux
    for i in range(1, n):
        k_face = 0.5 * (k[i - 1] + k[i])
        # q = -K (dpsi/dz - 1); +z downward so gravity adds +K.
        faces[i] = -k_face * ((psi[i] - psi[i - 1]) / dz) + k_face
    faces[-1] = k[-1]  # free drainage
    return faces


@dataclass
class ColumnResult:
    """Result of a Richards column simulation."""

    depth_m: list[float]
    theta_final: list[float]
    mass_balance_error: float


def simulate_column(  # noqa: PLR0913
    vg: VanGenuchten,
    *,
    theta_initial: float,
    n_cells: int = 40,
    depth_m: float = 1.0,
    infiltration_m_per_day: float = 0.0,
    root_uptake_m_per_day: float = 0.0,
    duration_days: float = 1.0,
) -> ColumnResult:
    """Integrate a 1-D vertical soil column with the method of lines.

    Args:
        vg: van Genuchten parameters.
        theta_initial: Uniform initial water content (m^3/m^3).
        n_cells: Number of vertical cells.
        depth_m: Column depth (m).
        infiltration_m_per_day: Top boundary flux (e.g. FAO-56 gross irrigation).
        root_uptake_m_per_day: Uniform root sink over the column (m/day).
        duration_days: Simulation length (days).

    Returns:
        A :class:`ColumnResult` with the final profile and the relative mass
        balance error (should be ~machine precision for the openRE form).
    """
    dz = depth_m / n_cells
    theta0 = np.full(n_cells, theta_initial, dtype=float)
    sink = root_uptake_m_per_day / depth_m  # per-cell volumetric sink (1/day)

    def rhs(_t: float, theta: np.ndarray) -> np.ndarray:
        faces = _fluxes(theta, vg, dz, infiltration_m_per_day)
        return -(faces[1:] - faces[:-1]) / dz - sink

    theta_final, n_steps = _integrate(rhs, theta0, duration_days)

    inflow = infiltration_m_per_day * duration_days
    outflow = (
        vg.conductivity_from_se(
            float(np.clip((theta_final[-1] - vg.theta_r) / (vg.theta_s - vg.theta_r), 0, 1))
        )
    ) * duration_days
    uptake = root_uptake_m_per_day * duration_days
    stored = float(np.sum(theta_final - theta0) * dz)
    expected = inflow - outflow - uptake
    denom = max(abs(inflow) + abs(outflow) + abs(uptake), 1.0e-9)
    mass_err = abs(stored - expected) / denom
    del n_steps
    return ColumnResult(
        depth_m=[(i + 0.5) * dz for i in range(n_cells)],
        theta_final=[float(v) for v in theta_final],
        mass_balance_error=mass_err,
    )


def _integrate(rhs: RhsFunc, theta0: np.ndarray, duration_days: float) -> tuple[np.ndarray, int]:
    """Integrate the ODE system, using SciPy's BDF solver when available."""
    try:
        from scipy.integrate import solve_ivp
    except ImportError:
        return _integrate_explicit(rhs, theta0, duration_days)
    sol = solve_ivp(
        rhs,
        (0.0, duration_days),
        theta0,
        method="BDF",
        rtol=1.0e-6,
        atol=1.0e-9,
    )
    return sol.y[:, -1], sol.y.shape[1]


def _integrate_explicit(
    rhs: RhsFunc,
    theta0: np.ndarray,
    duration_days: float,
    dt_days: float = 1.0e-4,
) -> tuple[np.ndarray, int]:
    """Explicit forward-Euler fallback when SciPy is unavailable."""
    n_steps = max(1, int(math.ceil(duration_days / dt_days)))
    dt = duration_days / n_steps
    theta = theta0.copy()
    for step in range(n_steps):
        theta = theta + dt * rhs(step * dt, theta)
    return theta, n_steps
