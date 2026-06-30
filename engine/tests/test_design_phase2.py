"""Phase 2 tests: demand model, catalog/cost model, candidate evaluation.

See specifications.md §3.4-3.7.
"""

import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FarmTwin import catalog, evaluate  # noqa: E402
from FarmTwin.fao56 import zone_design_flow  # noqa: E402
from FarmTwin.geo import fill_link_lengths  # noqa: E402

pytestmark = pytest.mark.unit

_PILOT = Path(__file__).parent.parent.parent / "docs/examples/eruthempathy_pilot.fts.json"


@pytest.fixture
def pilot() -> dict:
    if not _PILOT.exists():
        pytest.skip("pilot FTS document not found")
    with _PILOT.open() as fh:
        return fill_link_lengths(json.load(fh))


# ── demand model ─────────────────────────────────────────────────────────────


def test_zone_design_flow_scales_with_area_and_et0(pilot):
    z = pilot["zones"][0]
    q_lo = zone_design_flow(z, et0_peak_mm_day=4.0, hours_per_day=3.0)
    q_hi = zone_design_flow(z, et0_peak_mm_day=8.0, hours_per_day=3.0)
    assert q_hi > q_lo > 0
    # Halving the watering window doubles the required flow.
    q_short = zone_design_flow(z, et0_peak_mm_day=8.0, hours_per_day=1.5)
    assert q_short == pytest.approx(2.0 * q_hi, rel=1e-6)


# ── catalog + cost ───────────────────────────────────────────────────────────


def test_pipe_options_ascending():
    opts = catalog.pipe_options("pvc_upvc")
    assert opts and all(
        opts[i].internal_diameter_m < opts[i + 1].internal_diameter_m for i in range(len(opts) - 1)
    )


def test_capital_cost_increases_with_diameter(pilot):
    base = catalog.capital_cost(pilot)
    fat = json.loads(json.dumps(pilot))
    for link in fat["links"]:
        link["nominal_diameter_mm"] = 110
        link["material"] = "pvc_upvc"
    assert catalog.capital_cost(fat) > base


# ── scenarios + evaluate ─────────────────────────────────────────────────────


def test_build_scenarios_respects_max_simultaneous(pilot):
    # Pilot sets max_simultaneous_zones = 1 -> one block per zone.
    scns = evaluate.build_scenarios(pilot)
    assert len(scns) == len(pilot["zones"])
    assert all(len(s.active_zones) == 1 for s in scns)


def test_constraints_from_fts(pilot):
    c = evaluate.DesignConstraints.from_fts(pilot)
    assert c.v_max_ms == pytest.approx(1.8)
    assert c.min_eu_pct == pytest.approx(85.0)
    assert c.p_min_m > 0 and c.p_max_m > c.p_min_m


def test_evaluate_returns_objectives(pilot):
    report = evaluate.evaluate(pilot)
    o = report.objectives
    assert o.capital_inr > 0
    assert o.energy_inr > 0
    assert 0.0 <= o.eu_pct <= 100.0
    assert isinstance(report.feasible, bool)


def test_undersized_pipes_raise_velocity_violation(pilot):
    # Force the smallest diameter everywhere -> high velocity -> infeasible.
    tiny = json.loads(json.dumps(pilot))
    for link in tiny["links"]:
        link["internal_diameter_m"] = 0.0144  # ~ DN16 lateral, far too small for mains
    report = evaluate.evaluate(tiny)
    assert report.feasible is False
    assert any("velocity" in v for v in report.violations)
