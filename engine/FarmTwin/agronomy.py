"""Agronomy & yield layer for FarmTwin (R-AGRO-1..3).

Lightweight, edge-runnable models that turn the hydraulic/soil state into the
numbers a farmer cares about:

* **GDD phenology** — growing-degree-day accumulation drives crop-stage advance.
* **FAO-33 water-production** — relative yield loss from water stress,
  ``(1 - Ya/Ym) = Ky * (1 - ETa/ETc)`` (Doorenbos & Kassam, 1979).
* **Maas-Hoffman salinity** — relative yield loss above an EC threshold.

Heavy mechanistic models (AquaCrop / DSSAT / APSIM) run offline to calibrate
these coefficients; here we keep the real-time model lean.

White papers:
    Doorenbos & Kassam (1979) FAO-33 (Ky).
    Maas & Hoffman (1977) crop salt tolerance.
    Steduto et al. (2012) FAO-66 / AquaCrop (offline calibration).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# FAO-56 dual-Kc growth stages, in order.
STAGES = ("initial", "development", "mid_season", "late_season")


@dataclass
class CropParameters:
    """Per-crop agronomic parameter set (seeded from FAO + KAU PoP)."""

    name: str
    base_temp_c: float  # GDD base temperature
    gdd_to_stage: dict[str, float]  # cumulative GDD at which each stage ends
    ky_overall: float  # FAO-33 seasonal yield-response factor
    ec_threshold_ds_m: float  # Maas-Hoffman salinity threshold
    ec_slope_pct_per_ds_m: float  # Maas-Hoffman slope (% yield loss / dS/m)
    max_yield_t_ha: float = 0.0  # Ym reference (for absolute yield)


# Small built-in library (illustrative; calibrate against local trials).
CROP_PARAMS = {
    "coconut": CropParameters(
        "coconut",
        10.0,
        {"initial": 600, "development": 1800, "mid_season": 3600, "late_season": 4800},
        0.85,
        1.5,
        7.1,
        0.0,
    ),
    "tomato": CropParameters(
        "tomato",
        10.0,
        {"initial": 150, "development": 500, "mid_season": 1100, "late_season": 1500},
        1.05,
        2.5,
        9.9,
        80.0,
    ),
    "paddy": CropParameters(
        "paddy",
        8.0,
        {"initial": 200, "development": 650, "mid_season": 1400, "late_season": 1900},
        1.10,
        3.0,
        12.0,
        6.0,
    ),
}


def growing_degree_days(t_max_c: float, t_min_c: float, base_temp_c: float) -> float:
    """Single-day growing degree days (capped at zero).

    Args:
        t_max_c: Daily maximum air temperature (C).
        t_min_c: Daily minimum air temperature (C).
        base_temp_c: Crop base temperature (C).

    Returns:
        GDD for the day (C-day), never negative.
    """
    return max(0.0, 0.5 * (t_max_c + t_min_c) - base_temp_c)


def stage_from_gdd(crop: CropParameters, cumulative_gdd: float) -> str:
    """Return the current growth stage for an accumulated GDD total."""
    for stage in STAGES:
        if cumulative_gdd <= crop.gdd_to_stage[stage]:
            return stage
    return STAGES[-1]


@dataclass
class PhenologyState:
    """Accumulated phenology for one zone/season."""

    cumulative_gdd: float = 0.0
    stage: str = STAGES[0]
    history: list[float] = field(default_factory=list)

    def advance(self, crop: CropParameters, t_max_c: float, t_min_c: float) -> str:
        """Add one day's GDD and update the stage; returns the new stage."""
        self.cumulative_gdd += growing_degree_days(t_max_c, t_min_c, crop.base_temp_c)
        self.stage = stage_from_gdd(crop, self.cumulative_gdd)
        self.history.append(self.cumulative_gdd)
        return self.stage


def relative_yield_water(ky: float, eta: float, etc: float) -> float:
    """FAO-33 relative yield from water stress.

    ``Ya/Ym = 1 - Ky * (1 - ETa/ETc)`` (Doorenbos & Kassam, 1979), clamped to
    ``[0, 1]``.

    Args:
        ky: Yield-response factor for the stage/season.
        eta: Actual evapotranspiration over the period.
        etc: Potential (well-watered) crop ET over the period.

    Returns:
        Relative yield ``Ya/Ym`` in ``[0, 1]``.
    """
    if etc <= 0.0:
        return 1.0
    deficit = 1.0 - min(max(eta / etc, 0.0), 1.0)
    return max(0.0, min(1.0, 1.0 - ky * deficit))


def relative_yield_salinity(crop: CropParameters, ec_e_ds_m: float) -> float:
    """Maas-Hoffman relative yield from root-zone salinity.

    ``Ya/Ym = 1 - slope/100 * (ECe - threshold)`` for ``ECe > threshold``.

    Args:
        crop: Crop parameters (threshold and slope).
        ec_e_ds_m: Saturated-paste root-zone electrical conductivity (dS/m).

    Returns:
        Relative yield ``Ya/Ym`` in ``[0, 1]``.
    """
    if ec_e_ds_m <= crop.ec_threshold_ds_m:
        return 1.0
    loss = crop.ec_slope_pct_per_ds_m / 100.0 * (ec_e_ds_m - crop.ec_threshold_ds_m)
    return max(0.0, 1.0 - loss)


def combined_relative_yield(
    crop: CropParameters,
    *,
    eta: float,
    etc: float,
    ec_e_ds_m: float,
) -> float:
    """Combine water and salinity stress multiplicatively (FAO-33 + Maas-Hoffman).

    Args:
        crop: Crop parameters.
        eta: Actual evapotranspiration.
        etc: Potential crop evapotranspiration.
        ec_e_ds_m: Root-zone salinity (dS/m).

    Returns:
        Combined relative yield ``Ya/Ym`` in ``[0, 1]``.
    """
    yw = relative_yield_water(crop.ky_overall, eta, etc)
    ys = relative_yield_salinity(crop, ec_e_ds_m)
    return yw * ys
