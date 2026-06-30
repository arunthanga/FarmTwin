"""ParameterSet — live-parametrized physical constants (A0 principle).

All physical coefficients live here. Nothing is hard-coded in solver loops.
Reference: engine/docs/12-solver-mathematics.md §1 (A0 parametrization).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParameterSet:
    """Named physical constants for the krishiflow engine.

    Every field is a live parameter — replaceable at runtime by the digital
    twin assimilation loop (see docs/requirements.md §9).
    """

    # ── Fundamental constants ────────────────────────────────────────
    gravity_ms2: float = 9.81
    water_density_kgm3: float = 1000.0
    kinematic_viscosity_m2s: float = 1.004e-6  # water at 20 °C

    # ── Hazen-Williams ───────────────────────────────────────────────
    hw_exponent: float = 1.852
    hw_coefficient_factor: float = 10.67

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
