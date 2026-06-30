"""Surface irrigation reference model for FarmTwin (R-SURF-1..2).

A Python reference for furrow/border/basin irrigation: **Kostiakov-Lewis**
cumulative infiltration coupled to a **volume-balance** advance model (Walker).
This sizes advance/opportunity time and application uniformity for paddy and
open-field surface systems. The full hydrodynamic **zero-inertia Saint-Venant**
solver (Preissmann four-point implicit) is the production upgrade and is best
validated against **WinSRFR** (USDA-ARS); see ``requirements.md`` §4.6.

White papers:
    Strelkoff & Katopodes (1977) zero-inertia border irrigation.
    Bautista, Clemmens, Strelkoff & Schlegel (2009) WinSRFR, *Agric. Water Manage.* 96(7).
    Walker & Skogerboe (1987) *Surface Irrigation* (volume-balance advance).
"""

from __future__ import annotations

from dataclasses import dataclass
import math

# Surface-storage shape factor for the volume-balance advance (Walker).
SURFACE_SHAPE_FACTOR = 0.77


@dataclass
class KostiakovLewis:
    """Kostiakov-Lewis cumulative infiltration ``Z = k*tau^a + b*tau``.

    Attributes:
        k: Kostiakov coefficient (m^3/m/min^a per unit length, or m/min^a).
        a: Kostiakov exponent (dimensionless, 0 < a < 1).
        b: Steady (basic) intake rate term (m/min); 0 for pure Kostiakov.
    """

    k: float
    a: float
    b: float = 0.0

    def cumulative(self, tau_min: float) -> float:
        """Cumulative infiltrated depth at opportunity time ``tau`` (minutes)."""
        if tau_min <= 0.0:
            return 0.0
        return self.k * tau_min**self.a + self.b * tau_min

    def rate(self, tau_min: float) -> float:
        """Instantaneous infiltration rate ``dZ/dtau`` at ``tau`` (per minute)."""
        if tau_min <= 0.0:
            return math.inf
        return self.a * self.k * tau_min ** (self.a - 1.0) + self.b


@dataclass
class AdvancePoint:
    """One (distance, time) point on the advance trajectory."""

    distance_m: float
    time_min: float


@dataclass
class SurfaceResult:
    """Result of a surface-irrigation advance/uniformity computation."""

    advance: list[AdvancePoint]
    advance_time_min: float
    applied_depth_m: float
    infiltrated_low_quarter_m: float
    distribution_uniformity: float


def advance_trajectory(
    infil: KostiakovLewis,
    *,
    inflow_m3_per_min: float,
    furrow_length_m: float,
    flow_area_m2: float,
    n_segments: int = 20,
) -> SurfaceResult:
    """Compute the advance curve by the volume-balance method (Walker).

    At each advance station the inflow volume equals surface storage plus the
    integral of infiltrated volume behind the front:

        ``Q * t = sigma_y * A * x + sigma_z * Z(t) * x``

    solved for advance time ``t`` at each distance ``x`` by bisection.

    Args:
        infil: Kostiakov-Lewis infiltration function.
        inflow_m3_per_min: Inflow rate per furrow/unit width (m^3/min).
        furrow_length_m: Field run length (m).
        flow_area_m2: Average surface flow cross-section (m^2).
        n_segments: Number of advance stations.

    Returns:
        A :class:`SurfaceResult` with the advance trajectory, total advance
        time, and low-quarter distribution uniformity.
    """
    sigma_z = (infil.a + SURFACE_SHAPE_FACTOR * (1.0 - infil.a) + 1.0) / (
        (1.0 + infil.a) * (1.0 + SURFACE_SHAPE_FACTOR)
    )
    dx = furrow_length_m / n_segments
    advance: list[AdvancePoint] = [AdvancePoint(0.0, 0.0)]
    for seg in range(1, n_segments + 1):
        x = seg * dx
        t = _solve_advance_time(infil, inflow_m3_per_min, x, flow_area_m2, sigma_z)
        advance.append(AdvancePoint(x, t))

    advance_time = advance[-1].time_min
    # Opportunity time per station = total advance time - arrival time.
    depths = [infil.cumulative(advance_time - p.time_min) for p in advance[1:]]
    depths.sort()
    nlq = max(1, len(depths) // 4)
    low_quarter = sum(depths[:nlq]) / nlq
    mean_depth = sum(depths) / len(depths) if depths else 0.0
    du = low_quarter / mean_depth if mean_depth > 0 else 0.0
    applied = inflow_m3_per_min * advance_time / furrow_length_m
    return SurfaceResult(
        advance=advance,
        advance_time_min=advance_time,
        applied_depth_m=applied,
        infiltrated_low_quarter_m=low_quarter,
        distribution_uniformity=du,
    )


def _solve_advance_time(
    infil: KostiakovLewis,
    inflow_m3_per_min: float,
    x: float,
    flow_area_m2: float,
    sigma_z: float,
) -> float:
    """Bisection solve of the volume-balance equation for advance time at ``x``."""

    def residual(t: float) -> float:
        surface_vol = SURFACE_SHAPE_FACTOR * flow_area_m2 * x
        subsurface_vol = sigma_z * infil.cumulative(t) * x
        return inflow_m3_per_min * t - surface_vol - subsurface_vol

    lo, hi = 1.0e-6, 1.0
    while residual(hi) < 0.0 and hi < 1.0e7:
        hi *= 2.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if residual(mid) > 0.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)
