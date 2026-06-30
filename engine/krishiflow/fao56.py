"""FAO-56 agronomy module for FarmTwin.

Implements the FAO Irrigation & Drainage Paper 56 method (Allen et al., 1998)
with the ASCE-EWRI (2005) standardized reference-ET refinement:

- Penman-Monteith reference evapotranspiration ET0 (daily, grass reference).
- Dual crop coefficient: ETc = (Kcb + Ke) * ET0.
- Root-zone soil water balance with readily-available water (RAW) and a water
  stress coefficient Ks.
- Net and gross irrigation requirement -> emitter design flow for the hydraulic
  solver (this is the coupling that makes the twin "plant/soil/environment
  aware").

All inputs SI: temperature C, wind m/s, radiation MJ/m2/day, pressure kPa,
depths mm. This is a clean reference implementation, not a meteorological
library; calibrate constants against local stations (e.g. IMD Palakkad).
"""

from __future__ import annotations

from dataclasses import dataclass
import math


# ---------------------------------------------------------------------------
# Penman-Monteith ET0 (FAO-56 eq. 6 / ASCE standardized, daily grass reference)
# ---------------------------------------------------------------------------
def saturation_vapour_pressure(temp_c: float) -> float:
    """es(T) in kPa (FAO-56 eq. 11)."""
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def delta_svp(temp_c: float) -> float:
    """Slope of the saturation vapour pressure curve, kPa/C (eq. 13)."""
    es = saturation_vapour_pressure(temp_c)
    return 4098.0 * es / (temp_c + 237.3) ** 2


def psychrometric_constant(pressure_kpa: float) -> float:
    """gamma, kPa/C (eq. 8). ~0.066 at sea level."""
    return 0.000665 * pressure_kpa


def atm_pressure(elevation_m: float) -> float:
    """Atmospheric pressure from elevation, kPa (eq. 7)."""
    return 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26


def et0_penman_monteith(
    *,
    t_mean: float,
    t_min: float,
    t_max: float,
    rh_mean: float,
    wind_2m: float,
    rn: float,
    elevation: float = 100.0,
    g_soil: float = 0.0,
) -> float:
    """FAO-56 Penman-Monteith daily ET0 in mm/day.

    rn: net radiation at the crop surface (MJ/m2/day).
    wind_2m: wind speed at 2 m (m/s). rh_mean: mean relative humidity (%).
    """
    p = atm_pressure(elevation)
    gamma = psychrometric_constant(p)
    delta = delta_svp(t_mean)
    es = (saturation_vapour_pressure(t_max) + saturation_vapour_pressure(t_min)) / 2.0
    ea = es * rh_mean / 100.0
    num = 0.408 * delta * (rn - g_soil) + gamma * 900.0 / (t_mean + 273.0) * wind_2m * (es - ea)
    den = delta + gamma * (1.0 + 0.34 * wind_2m)
    return max(0.0, num / den)


# ---------------------------------------------------------------------------
# Crop & soil description for the dual-Kc water balance
# ---------------------------------------------------------------------------
@dataclass
class Crop:
    name: str
    kcb_ini: float  # basal crop coefficient, initial
    kcb_mid: float  # basal crop coefficient, mid-season
    kcb_end: float  # basal crop coefficient, late season
    root_depth_max: float  # m
    depletion_fraction: float = 0.5  # p (FAO-56 Table 22)


@dataclass
class Soil:
    field_capacity: float  # theta_FC (vol fraction)
    wilting_point: float  # theta_WP (vol fraction)
    teu: float = 8.0  # total evaporable water, mm (FAO-56 ~ 6-12)
    rew: float = 4.0  # readily evaporable water, mm

    def taw(self, root_depth_m: float) -> float:
        """Total available water in the root zone, mm."""
        return 1000.0 * (self.field_capacity - self.wilting_point) * root_depth_m


# A small built-in crop library (basal Kc; adjust per local trials)
CROP_LIBRARY = {
    "tomato": Crop("tomato", 0.15, 1.10, 0.70, 0.7, 0.40),
    "cucumber": Crop("cucumber", 0.15, 0.95, 0.70, 0.7, 0.50),
    "banana": Crop("banana", 0.35, 1.10, 0.90, 0.6, 0.35),
    "mango": Crop("mango", 0.40, 0.85, 0.70, 1.2, 0.50),
}


def stress_coefficient(depletion_mm: float, taw_mm: float, p: float) -> float:
    """Ks water-stress coefficient (FAO-56 eq. 84)."""
    raw = p * taw_mm
    if depletion_mm <= raw:
        return 1.0
    return max(0.0, (taw_mm - depletion_mm) / (taw_mm - raw))


@dataclass
class WaterBalanceState:
    depletion: float  # root-zone depletion Dr, mm (0 = at field capacity)
    root_depth: float  # current rooting depth, m


def crop_water_balance_step(
    *,
    state: WaterBalanceState,
    crop: Crop,
    soil: Soil,
    et0: float,
    kcb: float,
    rainfall: float = 0.0,
    ke: float = 0.0,
    irrigation: float = 0.0,
):
    """Advance the root-zone water balance one day (FAO-56 dual-Kc).

    Returns (new_state, info) where info has ETc, Ks, ETc_adj, and the day's
    net irrigation requirement (mm) to refill to field capacity.
    """
    taw = soil.taw(state.root_depth)
    p = crop.depletion_fraction
    ks = stress_coefficient(state.depletion, taw, p)
    etc = (kcb + ke) * et0
    etc_adj = (ks * kcb + ke) * et0

    # update depletion: Dr increases with ET, decreases with rain + irrigation
    dr = state.depletion + etc_adj - rainfall - irrigation
    dr = min(max(dr, 0.0), taw)  # clamp [0, TAW]
    new_state = WaterBalanceState(depletion=dr, root_depth=state.root_depth)

    # net irrigation requirement to bring back to field capacity (RAW trigger)
    raw = p * taw
    nir = dr if dr >= raw else 0.0
    info = {
        "ET0": et0,
        "ETc": etc,
        "Ks": ks,
        "ETc_adj": etc_adj,
        "TAW": taw,
        "RAW": raw,
        "Dr": dr,
        "net_irrigation_mm": nir,
    }
    return new_state, info


def gross_irrigation_depth(net_mm: float, efficiency: float = 0.9) -> float:
    """Gross depth (mm) accounting for application/uniformity efficiency."""
    return net_mm / max(efficiency, 1e-6)


def emitter_design_flow(
    *,
    net_irrigation_mm_per_day: float,
    area_per_emitter_m2: float,
    hours_per_day: float = 2.0,
    efficiency: float = 0.9,
) -> float:
    """Convert FAO-56 daily requirement into an emitter design flow (m^3/s).

    This is the value fed to the hydraulic solver as the emitter nominal_q (PC)
    or used to back-out the discharge coefficient k for non-PC emitters.
    """
    gross_mm = gross_irrigation_depth(net_irrigation_mm_per_day, efficiency)
    volume_m3 = gross_mm / 1000.0 * area_per_emitter_m2  # m^3/day per emitter
    seconds = hours_per_day * 3600.0
    return volume_m3 / seconds if seconds > 0 else 0.0
