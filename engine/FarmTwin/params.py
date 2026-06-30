"""ParameterSet — live-parametrized physical constants (A0 principle).

All physical coefficients live here. Nothing is hard-coded in solver loops:
``solver.solve`` and ``headloss``/``components`` read every constant from a
``ParameterSet`` so the digital-twin assimilation loop can override any value at
runtime (see ``assimilation.py`` and docs/requirements.md §9).

``LiveParameter`` carries the provenance/uncertainty metadata required for the
governed write-back of twin-estimated parameters (R-NFR-1, R-TWIN-3).
Reference: engine/docs/12-solver-mathematics.md §1 (A0 parametrization).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import math


@dataclass
class ParameterSet:
    """Named physical constants for the FarmTwin engine.

    Every field is a live parameter — replaceable at runtime by the digital
    twin assimilation loop (see docs/requirements.md §9).
    """

    # ── Fundamental constants ────────────────────────────────────────
    gravity_ms2: float = 9.81
    water_density_kgm3: float = 1000.0
    kinematic_viscosity_m2s: float = 1.004e-6  # water at 20 °C

    # ── Hazen-Williams ───────────────────────────────────────────────
    hw_exponent: float = 1.852  # flow exponent
    hw_coefficient_factor: float = 10.67  # SI conversion factor
    hw_diameter_exponent: float = 4.87  # diameter exponent

    # ── Darcy-Weisbach / Swamee-Jain ────────────────────────────────
    dw_lambda: float = 0.5  # Mualem pore-connectivity (for K(Se))

    # ── GGA solver ──────────────────────────────────────────────────
    zero_flow_eps_m3s: float = 1.0e-6  # Elhay-Simpson regularization threshold
    convergence_tol: float = 1.0e-4
    max_iterations: int = 50

    # ── FAO-56 (ASCE-EWRI standardized form) ────────────────────────
    cn_short_grass: float = 900.0  # numerator constant (daytime)
    cd_short_grass: float = 0.34  # denominator wind coefficient

    # ── van Genuchten defaults (Palakkad red laterite) ───────────────
    vg_alpha_default: float = 0.059  # 1/m
    vg_n_default: float = 1.48
    vg_theta_r_default: float = 0.065
    vg_theta_s_default: float = 0.41
    vg_ks_mday_default: float = 0.62

    # ── Richards solver ─────────────────────────────────────────────
    picard_tol: float = 1.0e-3  # Modified Picard convergence [m]
    picard_max_iter: int = 20

    # ── B6 QC gate ──────────────────────────────────────────────────
    hampel_k: float = 3.0  # Hampel filter threshold multiplier
    hampel_window: int = 7  # rolling window half-width (samples)


@dataclass
class LiveParameter:
    """A calibrated parameter with the provenance the twin write-back needs.

    The digital-twin assimilation loop estimates a value and its uncertainty;
    only estimates that pass governance (low relative uncertainty, bounded step)
    are promoted to the shared core as a ``LiveParameter`` carrying where the
    value came from and when (R-NFR-1, R-TWIN-3).
    """

    value: float
    prior: float
    uncertainty: float  # standard deviation of the estimate (same units as value)
    source: str = "design"  # "design" | "field" | "calibration"
    version: int = 0
    updated_at: str | None = None
    lower: float = -math.inf
    upper: float = math.inf

    @property
    def relative_uncertainty(self) -> float:
        """Standard deviation as a fraction of |value| (inf if value is 0)."""
        return self.uncertainty / abs(self.value) if self.value != 0.0 else math.inf

    @staticmethod
    def now_iso() -> str:
        """UTC timestamp for ``updated_at`` stamps."""
        return datetime.now(UTC).isoformat()
