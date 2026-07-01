"""Phase 3 tests: decision space, optimizer/ranking, priced BoM, EPANET export,
end-to-end orchestration. See specifications.md §3.6-3.10."""

import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FarmTwin import optimize, studio_design  # noqa: E402
from FarmTwin.geo import fill_link_lengths  # noqa: E402
from FarmTwin.postprocess import priced_bom  # noqa: E402
from FarmTwin.preprocess import export_epanet_inp, fts_to_network, load_epanet_inp  # noqa: E402

pytestmark = pytest.mark.unit

_PILOT = Path(__file__).parent.parent.parent / "docs/examples/eruthempathy_pilot.fts.json"


@pytest.fixture
def pilot() -> dict:
    if not _PILOT.exists():
        pytest.skip("pilot FTS document not found")
    with _PILOT.open() as fh:
        return fill_link_lengths(json.load(fh))


# ── decision space ───────────────────────────────────────────────────────────


def test_decision_space_and_apply(pilot):
    variables = optimize.decision_space(pilot)
    assert len(variables) == len(pilot["links"])  # pilot links are all mainline/submain
    smallest = optimize.apply_genome(pilot, variables, [0] * len(variables))
    largest = optimize.apply_genome(pilot, variables, [len(v.options) - 1 for v in variables])
    small_d = smallest["links"][0]["internal_diameter_m"]
    large_d = largest["links"][0]["internal_diameter_m"]
    assert large_d > small_d


# ── optimizer + ranking ──────────────────────────────────────────────────────


def test_optimize_returns_ranked_top_designs(pilot):
    designs = optimize.optimize_design(pilot)
    labels = {d.label for d in designs}
    assert labels == {"lowest_cost", "highest_uniformity", "balanced"}
    by = {d.label: d for d in designs}
    # lowest-cost is the cheapest of the pool; highest-uniformity has the best EU.
    assert (
        by["lowest_cost"].report.objectives.capital_inr
        <= by["highest_uniformity"].report.objectives.capital_inr
    )
    assert (
        by["highest_uniformity"].report.objectives.eu_pct
        >= by["lowest_cost"].report.objectives.eu_pct
    )
    for d in designs:
        assert d.bom["capital_inr"] > 0


def test_optimize_is_deterministic(pilot):
    a = optimize.optimize_design(pilot)
    b = optimize.optimize_design(pilot)
    assert [d.label for d in a] == [d.label for d in b]
    assert [round(d.report.objectives.capital_inr, 2) for d in a] == [
        round(d.report.objectives.capital_inr, 2) for d in b
    ]


# ── priced BoM ───────────────────────────────────────────────────────────────


def test_priced_bom_has_totals(pilot):
    bom = priced_bom(pilot)
    assert bom["capital_inr"] > 0
    assert bom["pipe_inr"] > 0
    assert all("line_inr" in line for line in bom["pipes"])


# ── EPANET export round-trip ─────────────────────────────────────────────────


def test_epanet_export_roundtrip(pilot, tmp_path):
    net = fts_to_network(pilot)
    inp = tmp_path / "design.inp"
    export_epanet_inp(net, str(inp))
    parsed = load_epanet_inp(str(inp))
    assert len(parsed["links"]) == len(net.pipes)
    assert len(parsed["nodes"]) == len(net.junctions) + len(net.reservoirs)


# ── end-to-end ───────────────────────────────────────────────────────────────


def test_design_from_fts_end_to_end(pilot):
    designs = studio_design.design_from_fts(pilot)
    assert len(designs) == 3
    low = next(d for d in designs if d.label == "lowest_cost")
    high = next(d for d in designs if d.label == "highest_uniformity")
    assert low.report.objectives.capital_inr <= high.report.objectives.capital_inr
    # every recommendation carries a priced BoM and a solved feasibility report.
    for d in designs:
        assert d.bom["capital_inr"] > 0
        assert isinstance(d.report.feasible, bool)
