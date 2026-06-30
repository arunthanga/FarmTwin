"""Validation tests for the FAO-56 agronomy module."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FarmTwin import fao56  # noqa: E402

pytestmark = pytest.mark.unit


@pytest.mark.regression
def test_et0_sane_range():
    et0 = fao56.et0_penman_monteith(
        t_mean=29.0, t_min=23.0, t_max=35.0, rh_mean=60.0, wind_2m=1.8, rn=16.0, elevation=120.0
    )
    assert 2.0 < et0 < 12.0, et0
    print("PASS test_et0_sane_range  ET0 =", round(et0, 3), "mm/day")


def test_et0_monotonic_in_radiation():
    base = {
        "t_mean": 29.0,
        "t_min": 23.0,
        "t_max": 35.0,
        "rh_mean": 60.0,
        "wind_2m": 1.8,
        "elevation": 120.0,
    }
    low = fao56.et0_penman_monteith(rn=8.0, **base)
    high = fao56.et0_penman_monteith(rn=20.0, **base)
    assert high > low
    print("PASS test_et0_monotonic_in_radiation ", round(low, 2), "<", round(high, 2))


def test_water_balance_triggers_irrigation():
    crop = fao56.CROP_LIBRARY["tomato"]
    soil = fao56.Soil(field_capacity=0.30, wilting_point=0.12)
    state = fao56.WaterBalanceState(depletion=0.0, root_depth=0.4)
    triggered = False
    for _ in range(30):
        state, info = fao56.crop_water_balance_step(
            state=state, crop=crop, soil=soil, et0=6.0, kcb=crop.kcb_mid
        )
        if info["net_irrigation_mm"] > 0:
            triggered = True
            break
    assert triggered, "irrigation should be required as depletion exceeds RAW"
    assert 0.0 <= info["Ks"] <= 1.0
    print(
        "PASS test_water_balance  TAW =",
        round(info["TAW"], 1),
        "RAW =",
        round(info["RAW"], 1),
        "Dr =",
        round(info["Dr"], 1),
    )


def test_emitter_design_flow_positive():
    q = fao56.emitter_design_flow(
        net_irrigation_mm_per_day=5.0, area_per_emitter_m2=0.3, hours_per_day=2.0, efficiency=0.9
    )
    assert q > 0
    print("PASS test_emitter_design_flow  q =", round(q * 3.6e6, 3), "L/h")


def main():
    test_et0_sane_range()
    test_et0_monotonic_in_radiation()
    test_water_balance_triggers_irrigation()
    test_emitter_design_flow_positive()
    print("\nAll FAO-56 tests passed.")


if __name__ == "__main__":
    main()
