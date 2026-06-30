"""Tests for live parametrization (A0) and the digital-twin EKF assimilation.

Covers:
  - ParameterSet is actually wired into the solver (changing a coefficient
    changes the solved head loss) — the A0 "no hard-coded constants" claim.
  - The EKF recovers known pipe roughness from synthetic sensor pressures.
  - QC FAIL readings are dropped (fail-safe) and outliers are gated out.
  - Governed write-back promotes only confident estimates (R-TWIN-3).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FarmTwin import (  # noqa: E402
    CalibrationTarget,
    HydraulicTwin,
    Junction,
    LiveParameter,
    Network,
    Observation,
    ParameterSet,
    Pipe,
    Reservoir,
    solve,
)
from FarmTwin.quality import QCFlag  # noqa: E402

pytestmark = pytest.mark.unit


def _line_network(c1: float, c2: float) -> Network:
    """Reservoir -> P1 -> J1 -> P2 -> J2, two demands, HW pipes."""
    net = Network()
    net.add_reservoir(Reservoir(id="R", head=50.0))
    net.add_junction(Junction(id="J1", elevation=0.0, demand=5.0 / 3600.0))
    net.add_junction(Junction(id="J2", elevation=0.0, demand=5.0 / 3600.0))
    net.add_pipe(Pipe(id="P1", start="R", end="J1", length=100.0, diameter=0.05, coeff=c1))
    net.add_pipe(Pipe(id="P2", start="J1", end="J2", length=100.0, diameter=0.05, coeff=c2))
    return net


# ── A0 live parametrization ────────────────────────────────────────────────


def test_parameterset_wired_into_solver():
    """Doubling the Hazen-Williams factor must increase head loss (lower pressure)."""
    net = _line_network(c1=130.0, c2=130.0)
    p_default = solve(net).pressures["J2"]
    p_doubled = solve(net, params=ParameterSet(hw_coefficient_factor=21.34)).pressures["J2"]
    assert p_doubled < p_default
    print("PASS A0 wiring  P_J2 default=", round(p_default, 3), " doubled=", round(p_doubled, 3))


def test_zero_flow_regularization_does_not_change_physical_solution():
    """A larger zero-flow epsilon must not perturb a converged physical solve."""
    net = _line_network(c1=120.0, c2=120.0)
    p_small = solve(net, params=ParameterSet(zero_flow_eps_m3s=1e-9)).pressures["J2"]
    p_large = solve(net, params=ParameterSet(zero_flow_eps_m3s=1e-4)).pressures["J2"]
    assert abs(p_small - p_large) < 1e-6


# ── EKF recovery ────────────────────────────────────────────────────────────


def test_ekf_recovers_two_pipe_roughness():
    """From biased priors, the EKF must recover both pipes' true C-factors."""
    c1_true, c2_true = 130.0, 110.0
    truth = _line_network(c1_true, c2_true)
    res = solve(truth)
    obs = [
        Observation("pressure", "J1", res.pressures["J1"], std=0.02),
        Observation("pressure", "J2", res.pressures["J2"], std=0.02),
    ]

    est = _line_network(c1=100.0, c2=140.0)  # biased starting guess
    twin = HydraulicTwin(
        est,
        targets=[
            CalibrationTarget.pipe_coeff("P1", prior_std=30.0, lower=50.0, upper=160.0),
            CalibrationTarget.pipe_coeff("P2", prior_std=30.0, lower=50.0, upper=160.0),
        ],
    )
    result = None
    for _ in range(12):
        result = twin.assimilate(obs)
    assert result is not None and result.accepted

    state = twin.state()
    assert abs(state["pipe[P1].coeff"] - c1_true) < 1.0
    assert abs(state["pipe[P2].coeff"] - c2_true) < 1.0
    # The estimated network now reproduces the observed pressures.
    check = solve(est)
    assert abs(check.pressures["J1"] - res.pressures["J1"]) < 0.05
    assert abs(check.pressures["J2"] - res.pressures["J2"]) < 0.05
    print(
        "PASS EKF recovery  C1=",
        round(state["pipe[P1].coeff"], 2),
        " C2=",
        round(state["pipe[P2].coeff"], 2),
    )


def test_qc_fail_observations_are_dropped():
    """An update with only FAIL-flagged readings must not change the state."""
    est = _line_network(c1=120.0, c2=120.0)
    twin = HydraulicTwin(est, targets=[CalibrationTarget.pipe_coeff("P1", prior_std=20.0)])
    before = twin.state()["pipe[P1].coeff"]
    result = twin.assimilate([Observation("pressure", "J1", 999.0, std=0.02, flag=QCFlag.FAIL)])
    assert result.accepted is False
    assert result.n_used == 0
    assert twin.state()["pipe[P1].coeff"] == before


def test_innovation_gate_rejects_outlier():
    """A physically implausible reading must be gated out, leaving state unchanged."""
    truth = _line_network(c1=120.0, c2=120.0)
    good = solve(truth).pressures["J1"]
    est = _line_network(c1=120.0, c2=120.0)
    twin = HydraulicTwin(
        est,
        targets=[CalibrationTarget.pipe_coeff("P1", prior_std=20.0)],
        innovation_gate=50.0,
    )
    before = twin.state()["pipe[P1].coeff"]
    # Observation 40 m away from the truth with a tight std -> huge normalised innovation.
    result = twin.assimilate([Observation("pressure", "J1", good - 40.0, std=0.05)])
    assert result.accepted is False
    assert result.mahalanobis > 50.0
    assert twin.state()["pipe[P1].coeff"] == before


# ── governed write-back ───────────────────────────────────────────────────


def test_governed_writeback_promotes_only_confident_estimates():
    """promote() returns LiveParameters only once uncertainty is low enough."""
    c1_true = 125.0
    res = solve(_line_network(c1_true, c1_true))
    obs = [
        Observation("pressure", "J1", res.pressures["J1"], std=0.02),
        Observation("pressure", "J2", res.pressures["J2"], std=0.02),
    ]
    est = _line_network(c1=100.0, c2=100.0)
    twin = HydraulicTwin(
        est,
        targets=[
            CalibrationTarget.pipe_coeff("P1", prior_std=30.0, lower=50.0, upper=160.0),
            CalibrationTarget.pipe_coeff("P2", prior_std=30.0, lower=50.0, upper=160.0),
        ],
    )

    # Before assimilation the prior uncertainty (30/100) is far too high.
    assert twin.promote(max_relative_uncertainty=0.05) == {}

    for _ in range(12):
        twin.assimilate(obs)

    promoted = twin.promote(max_relative_uncertainty=0.05)
    assert "pipe[P1].coeff" in promoted
    lp = promoted["pipe[P1].coeff"]
    assert isinstance(lp, LiveParameter)
    assert lp.source == "field"
    assert lp.version >= 1
    assert lp.updated_at is not None
    assert lp.relative_uncertainty <= 0.05
    assert abs(lp.value - c1_true) < 1.0
