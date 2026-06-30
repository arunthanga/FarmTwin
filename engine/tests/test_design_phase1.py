"""Phase 1 tests: GPS geometry, pump-curve ingest, FTS -> solvable Network.

See specifications.md §3.1-3.3.
"""

import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FarmTwin import geo, solver  # noqa: E402
from FarmTwin.components import PumpCurve  # noqa: E402
from FarmTwin.preprocess import (  # noqa: E402
    fts_to_network,
    zone_emitter_count,
    zone_nominal_flow_m3s,
)

pytestmark = pytest.mark.unit

_PILOT = Path(__file__).parent.parent.parent / "docs/examples/eruthempathy_pilot.fts.json"


@pytest.fixture
def pilot() -> dict:
    if not _PILOT.exists():
        pytest.skip("pilot FTS document not found")
    with _PILOT.open() as fh:
        return json.load(fh)


# ── geo ────────────────────────────────────────────────────────────────────


def test_haversine_known_distance():
    # 0.001 deg latitude ~ 111.2 m.
    d = geo.haversine_m(10.0, 76.0, 10.001, 76.0)
    assert 110.0 < d < 112.5


def test_segment_length_includes_elevation():
    a = {"lat": 10.0, "lon": 76.0, "elevation_m": 100.0}
    b = {"lat": 10.0, "lon": 76.0, "elevation_m": 130.0}
    # Same lat/lon: horizontal ~0, so 3-D length is the 30 m drop.
    assert geo.segment_length_m(a, b) == pytest.approx(30.0, abs=1e-3)


def test_source_head_prefers_sump_elevation():
    assert geo.source_head_m({"sump_elevation_m": 141.2}) == pytest.approx(141.2)
    assert geo.source_head_m(
        {"location": {"elevation_m": 100.0}, "dynamic_water_level_m": 55.0}
    ) == pytest.approx(45.0)


def test_fill_link_lengths_only_missing(pilot):
    # Blank one length; keep a manual one. fill should set the blank from GPS
    # and preserve the manual length.
    pilot["links"][2]["length_m"] = None  # L_FILTER_J1 (gps_straight)
    manual_len = pilot["links"][0]["length_m"]  # L_SUMP_PUMP (manual)
    geo.fill_link_lengths(pilot)
    assert pilot["links"][2]["length_m"] is not None
    assert pilot["links"][2]["length_m"] > 0
    assert pilot["links"][0]["length_m"] == manual_len


# ── pump curve from FTS ──────────────────────────────────────────────────────


def test_pumpcurve_from_fts_matches_points():
    attrs = {
        "curve_shutoff_m": 38.0,
        "curve_design_q_m3s": 0.00111,
        "curve_design_h_m": 28.0,
        "motor_efficiency_pct": 88,
    }
    curve = PumpCurve.from_fts(attrs)
    assert curve.head_gain(0.0) == pytest.approx(38.0)
    assert curve.head_gain(0.00111) == pytest.approx(28.0, abs=1e-6)
    assert curve.motor_eff == pytest.approx(0.88)


# ── FTS -> Network ───────────────────────────────────────────────────────────


def test_zone_flow_helpers(pilot):
    z = pilot["zones"][0]
    # 311 plants x 2 emitters = 622 emitters.
    assert zone_emitter_count(z) == 622
    assert zone_nominal_flow_m3s(z) > 0


def test_pilot_fts_builds_and_solves(pilot):
    geo.fill_link_lengths(pilot)
    net = fts_to_network(pilot)
    # Pump node split into __in/__out joined by a Pump link.
    assert "PUMP_N_PUMP" in net.pumps
    assert "N_PUMP__in" in net.junctions
    assert "N_PUMP__out" in net.junctions
    # Each zone became an emitter at its valve node.
    assert net.junctions["N_V1"].emitter is not None
    assert net.junctions["N_V2"].emitter is not None

    res = solver.solve(net)
    assert res.converged
    # Zone-inlet pressures should be finite and positive with the 5 HP pump.
    assert res.pressures["N_V1"] > 0
    assert res.pressures["N_V2"] > 0


def test_active_zone_subset(pilot):
    geo.fill_link_lengths(pilot)
    net = fts_to_network(pilot, active_zones=["Z01"])
    assert net.junctions["N_V1"].emitter is not None
    assert net.junctions["N_V2"].emitter is None
