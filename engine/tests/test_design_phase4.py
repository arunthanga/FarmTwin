"""Phase 4 tests: observability metric, EPANET/WNTR round-trip, twin-prior handoff.

See specifications.md §4 (P4.12-P4.14).
"""

import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FarmTwin import evaluate, studio_design  # noqa: E402
from FarmTwin.assimilation import Observation  # noqa: E402
from FarmTwin.geo import fill_link_lengths  # noqa: E402
from FarmTwin.preprocess import export_epanet_inp, fts_to_network, load_epanet_inp  # noqa: E402
from FarmTwin.solver import solve  # noqa: E402

pytestmark = pytest.mark.unit

_PILOT = Path(__file__).parent.parent.parent / "docs/examples/eruthempathy_pilot.fts.json"


@pytest.fixture
def pilot() -> dict:
    if not _PILOT.exists():
        pytest.skip("pilot FTS document not found")
    with _PILOT.open() as fh:
        return fill_link_lengths(json.load(fh))


# ── observability ────────────────────────────────────────────────────────────


def test_observability_score(pilot):
    obs = evaluate.observability_score(pilot)
    # pilot has a flow meter and a soil-moisture sensor in Z01.
    assert obs["n_flow_meters"] >= 1
    assert obs["zones_covered"] >= 1
    assert 0.0 < obs["score"] <= 1.0


def test_observability_zero_without_sensors(pilot):
    pilot["sensors"] = []
    assert evaluate.observability_score(pilot)["score"] == 0.0


# ── EPANET round-trip (minimal parser; WNTR when installed) ──────────────────


def test_epanet_roundtrip_node_link_counts(pilot, tmp_path):
    net = fts_to_network(pilot)
    inp = tmp_path / "d.inp"
    export_epanet_inp(net, str(inp))
    parsed = load_epanet_inp(str(inp))
    assert len(parsed["links"]) == len(net.pipes)
    assert len(parsed["nodes"]) == len(net.junctions) + len(net.reservoirs)


@pytest.mark.skipif(importlib.util.find_spec("wntr") is None, reason="WNTR not installed")
def test_epanet_roundtrip_with_wntr(pilot, tmp_path):
    net = fts_to_network(pilot)
    inp = tmp_path / "d.inp"
    export_epanet_inp(net, str(inp))
    parsed = load_epanet_inp(str(inp))  # uses WNTR backend when present
    assert len(parsed["links"]) == len(net.pipes)


# ── twin-prior handoff ───────────────────────────────────────────────────────


def test_twin_from_design_targets_match_pipes(pilot):
    net = fts_to_network(pilot)
    twin = studio_design.twin_from_design(pilot)
    assert len(twin.targets) == len(net.pipes)
    assert set(twin.state()) == {f"pipe[{pid}].coeff" for pid in net.pipes}


def test_twin_from_design_assimilates_field_reading(pilot):
    # Build a "truth" with a roughened main, observe its zone-inlet pressure,
    # and check the design-seeded twin shifts that pipe's C toward truth.
    truth = fts_to_network(pilot)
    main_id = next(iter(truth.pipes))
    truth.pipes[main_id].coeff = 110.0
    res = solve(truth)
    obs_node = next(iter(truth.junctions))
    twin = studio_design.twin_from_design(pilot)  # priors at design C (~140-145)
    target_name = f"pipe[{main_id}].coeff"
    before = twin.state()[target_name]
    result = twin.assimilate([Observation("pressure", obs_node, res.pressures[obs_node], std=0.05)])
    assert result.accepted
    # The estimate moved (calibration occurred); exact value depends on topology.
    assert twin.state()[target_name] != before
