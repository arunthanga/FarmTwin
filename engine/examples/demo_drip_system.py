"""End-to-end KrishiFlow demo: pump + filter + valve + venturi + drip lateral,
coupled to a FAO-56 design-flow calculation.

Run:  python examples/demo_drip_system.py
(from the engine/ directory, with numpy installed)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from krishiflow import (  # noqa: E402
    Network, Junction, Reservoir, Pipe, Pump, Valve, VenturiLink, Emitter,
    PumpCurve, Venturi, sum_k, solve,
)
from krishiflow import fao56  # noqa: E402
from krishiflow.postprocess import report, plot_lateral_profile  # noqa: E402


def build_system():
    net = Network()
    # Water source (sump) at ground, low head.
    net.add_reservoir(Reservoir(id="SUMP", head=0.0))

    # Nodes along the head control: pump outlet -> filter out -> manifold.
    net.add_junction(Junction(id="PUMP_OUT", elevation=0.0))
    net.add_junction(Junction(id="FILT_OUT", elevation=0.0))
    net.add_junction(Junction(id="MANIFOLD", elevation=0.0))

    # Pump: design duty ~ 12 m3/h at 25 m head (sized to drive the system).
    curve = PumpCurve.from_design_point(q_design=12.0 / 3600.0, h_design=25.0)
    net.add_pump(Pump(id="PUMP1", start="SUMP", end="PUMP_OUT", curve=curve))

    # Short pump-discharge pipe with a check valve + elbow (minor losses).
    net.add_pipe(Pipe(id="P_DISCH", start="PUMP_OUT", end="FILT_OUT",
                      length=3.0, diameter=0.05, coeff=140,
                      fittings=["check_valve", "elbow_90_threaded"]))

    # Disc filter modeled as a valve-type minor loss (clean K ~ disc_filter).
    from krishiflow.components import k_of
    net.add_valve(Valve(id="FILTER", start="FILT_OUT", end="MANIFOLD",
                        diameter=0.05, k=k_of("disc_filter"), type="TCV"))

    # Venturi fertigation injector in-line on the manifold feeder.
    net.add_junction(Junction(id="VENT_OUT", elevation=0.0))
    net.add_venturi(VenturiLink(id="VENTURI", start="MANIFOLD", end="VENT_OUT",
                                venturi=Venturi(a=4.0e6, injection_rate=2e-6,
                                                concentration=50.0)))

    # Submain to the lateral head with a ball valve + tee.
    net.add_junction(Junction(id="LAT_IN", elevation=0.0))
    net.add_pipe(Pipe(id="SUBMAIN", start="VENT_OUT", end="LAT_IN",
                      length=20.0, diameter=0.04, coeff=140,
                      fittings=["ball_valve_open", "tee_run"]))

    # Drip lateral: 20 emitters @ 0.5 m, 16 mm, turbulent 4 L/h-at-10m emitters.
    prev = "LAT_IN"
    k_em, x_em = 3.51e-7, 0.5
    for i in range(1, 21):
        nid = f"E{i}"
        net.add_junction(Junction(id=nid, elevation=0.0,
                                  emitter=Emitter(k=k_em, x=x_em)))
        net.add_pipe(Pipe(id=f"L{i}", start=prev, end=nid, length=0.5,
                          diameter=0.016, coeff=150, model="HW"))
        prev = nid
    return net


def fao56_design_flow():
    """Compute a per-emitter design flow from FAO-56 for tomato in Palakkad."""
    et0 = fao56.et0_penman_monteith(
        t_mean=29.0, t_min=23.0, t_max=35.0, rh_mean=60.0,
        wind_2m=1.8, rn=16.0, elevation=120.0)
    crop = fao56.CROP_LIBRARY["tomato"]
    q = fao56.emitter_design_flow(
        net_irrigation_mm_per_day=crop.kcb_mid * et0,  # mid-season approx
        area_per_emitter_m2=0.5 * 0.6,                 # spacing x row
        hours_per_day=2.0, efficiency=0.9)
    return et0, q


if __name__ == "__main__":
    et0, q_design = fao56_design_flow()
    print(f"FAO-56: ET0 = {et0:.2f} mm/day,  emitter design flow = "
          f"{q_design*3.6e6:.2f} L/h\n")

    net = build_system()
    result = solve(net)
    print(report(net, result))

    out = plot_lateral_profile(net, result,
                               path=os.path.join(os.path.dirname(__file__),
                                                 "lateral_profile.png"))
    print(f"\nProfile plot: {out}")
