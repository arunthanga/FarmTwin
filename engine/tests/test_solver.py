"""Validation tests for the FarmTwin GGA solver.

Runnable directly (`python tests/test_solver.py`) or via pytest. Each test
checks the solver against an independent hand calculation.
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from krishiflow import (  # noqa: E402
    Network, Junction, Reservoir, Pipe, Pump, Valve, Emitter, PumpCurve, solve,
)
from krishiflow.components import pipe_headloss_gradient  # noqa: E402

pytestmark = pytest.mark.unit


def test_single_pipe_headloss():
    """Reservoir -> junction with fixed demand. H_J = H_res - hL(demand)."""
    net = Network()
    net.add_reservoir(Reservoir(id="R", head=30.0))
    demand = 5.0 / 3600.0
    net.add_junction(Junction(id="J", elevation=0.0, demand=demand))
    net.add_pipe(Pipe(id="P1", start="R", end="J", length=100.0,
                      diameter=0.1, coeff=130.0, model="HW"))
    res = solve(net)
    assert res.converged
    # pipe must carry exactly the demand
    assert abs(res.flows["P1"] - demand) < 1e-9
    hL, _ = pipe_headloss_gradient(demand, 100.0, 0.1, 130.0, "HW", 0.0)
    assert abs(res.heads["J"] - (30.0 - hL)) < 1e-6
    print("PASS test_single_pipe_headloss  H_J =", round(res.heads["J"], 4))


@pytest.mark.regression
def test_two_reservoirs():
    """R1=100, R2=80 through a junction with two identical pipes -> H_J=90."""
    net = Network()
    net.add_reservoir(Reservoir(id="R1", head=100.0))
    net.add_reservoir(Reservoir(id="R2", head=80.0))
    net.add_junction(Junction(id="J", elevation=0.0, demand=0.0))
    net.add_pipe(Pipe(id="A", start="R1", end="J", length=500.0,
                      diameter=0.2, coeff=120.0))
    net.add_pipe(Pipe(id="B", start="J", end="R2", length=500.0,
                      diameter=0.2, coeff=120.0))
    res = solve(net)
    assert res.converged
    assert abs(res.heads["J"] - 90.0) < 1e-3, res.heads["J"]
    # flows equal and positive (R1->J->R2)
    assert abs(res.flows["A"] - res.flows["B"]) < 1e-9
    assert res.flows["A"] > 0
    print("PASS test_two_reservoirs  H_J =", round(res.heads["J"], 4),
          " Q =", round(res.flows["A"] * 3600, 3), "m3/h")


def test_emitter_consistency():
    """Pipe flow into an emitter node equals q = k*sqrt(P)."""
    net = Network()
    net.add_reservoir(Reservoir(id="R", head=20.0))
    k, x = 3.51e-7, 0.5
    net.add_junction(Junction(id="E1", elevation=0.0,
                              emitter=Emitter(k=k, x=x)))
    net.add_pipe(Pipe(id="P", start="R", end="E1", length=1.0,
                      diameter=0.016, coeff=150.0))
    res = solve(net)
    assert res.converged
    p = res.pressures["E1"]
    q_emit = k * p ** x
    assert abs(res.flows["P"] - q_emit) < 1e-9, (res.flows["P"], q_emit)
    assert 0 < p < 20.0
    print("PASS test_emitter_consistency  P =", round(p, 3),
          "m  q =", round(q_emit * 3.6e6, 3), "L/h")


def test_pump_head_gain():
    """Pump lifts water from a sump; head gain matches the curve at duty Q."""
    net = Network()
    net.add_reservoir(Reservoir(id="SUMP", head=0.0))
    net.add_junction(Junction(id="OUT", elevation=0.0))
    net.add_junction(Junction(id="J", elevation=0.0, demand=10.0 / 3600.0))
    curve = PumpCurve.from_design_point(q_design=12.0 / 3600.0, h_design=25.0)
    net.add_pump(Pump(id="PUMP", start="SUMP", end="OUT", curve=curve))
    net.add_pipe(Pipe(id="P", start="OUT", end="J", length=50.0,
                      diameter=0.05, coeff=140.0))
    res = solve(net)
    assert res.converged
    q = res.flows["PUMP"]
    gain = curve.head_gain(q)
    assert abs(res.heads["OUT"] - gain) < 1e-6     # H_OUT - H_SUMP(0) = gain
    hp = curve.motor_hp(q, gain)
    assert hp > 0
    print("PASS test_pump_head_gain  Q =", round(q * 3600, 3),
          "m3/h  gain =", round(gain, 2), "m  HP =", round(hp, 2))


def test_minor_losses_increase_drop():
    """Adding fittings raises head loss, lowering downstream pressure."""
    def pressure_with(fittings):
        net = Network()
        net.add_reservoir(Reservoir(id="R", head=30.0))
        net.add_junction(Junction(id="J", elevation=0.0, demand=20.0 / 3600.0))
        net.add_pipe(Pipe(id="P", start="R", end="J", length=50.0,
                          diameter=0.05, coeff=140.0, fittings=fittings))
        return solve(net).pressures["J"]
    p_plain = pressure_with([])
    p_fitted = pressure_with(["tee_branch", "elbow_90_threaded", "check_valve"])
    assert p_fitted < p_plain
    print("PASS test_minor_losses  P_plain =", round(p_plain, 3),
          "  P_fitted =", round(p_fitted, 3))


def main():
    test_single_pipe_headloss()
    test_two_reservoirs()
    test_emitter_consistency()
    test_pump_head_gain()
    test_minor_losses_increase_drop()
    print("\nAll solver tests passed.")


if __name__ == "__main__":
    main()
