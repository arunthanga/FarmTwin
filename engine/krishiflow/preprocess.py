"""Pre-processing for FarmTwin: JSON network I/O and a drip-lateral generator.

The JSON schema mirrors the data model so designs can be authored by hand, by
the FreeCAD workbench, or generated programmatically.
"""

from __future__ import annotations

import json

from .components import PumpCurve, Venturi
from .network import (
    Emitter, Junction, Network, Pipe, Pump, Reservoir, Valve, VenturiLink,
)


def network_from_dict(d: dict) -> Network:
    net = Network()
    for r in d.get("reservoirs", []):
        net.add_reservoir(Reservoir(**r))
    for j in d.get("junctions", []):
        em = j.pop("emitter", None)
        junction = Junction(**j)
        if em:
            junction.emitter = Emitter(**em)
        net.add_junction(junction)
    for p in d.get("pipes", []):
        net.add_pipe(Pipe(**p))
    for p in d.get("pumps", []):
        curve = PumpCurve(**p.pop("curve"))
        net.add_pump(Pump(curve=curve, **p))
    for v in d.get("valves", []):
        net.add_valve(Valve(**v))
    for v in d.get("venturis", []):
        vent = Venturi(**v.pop("venturi"))
        net.add_venturi(VenturiLink(venturi=vent, **v))
    return net


def load_network(path: str) -> Network:
    with open(path, "r", encoding="utf-8") as fh:
        return network_from_dict(json.load(fh))


def build_drip_lateral(
    *,
    source_head: float,
    source_elevation: float = 0.0,
    n_emitters: int = 20,
    spacing: float = 0.5,
    diameter: float = 0.016,
    hw_c: float = 150.0,
    slope: float = 0.0,
    emitter_k: float = 3.51e-7,
    emitter_x: float = 0.5,
    pressure_compensating: bool = False,
    nominal_q: float = 1.11e-6,
) -> Network:
    """Build a single drip lateral: reservoir -> chain of emitter nodes.

    A textbook test case for the solver. Each segment between emitters is a
    short pipe; each node carries an emitter. `slope` (m/m) tilts the lateral
    (positive = uphill away from source). Defaults: 16 mm LDPE lateral, 0.5 m
    emitter spacing, turbulent emitter (x=0.5). The default emitter_k=3.51e-7
    gives q = k*sqrt(P) ~ 1.11e-6 m^3/s (= 4 L/h) at P = 10 m; nominal_q for
    the PC variant is likewise 4 L/h.
    """
    net = Network()
    net.add_reservoir(Reservoir(id="SRC", head=source_head, x=0.0,
                                y=source_elevation))
    prev = "SRC"
    for i in range(1, n_emitters + 1):
        nid = f"E{i}"
        elev = source_elevation + slope * spacing * i
        em = Emitter(
            k=emitter_k, x=emitter_x,
            pressure_compensating=pressure_compensating, nominal_q=nominal_q,
        )
        net.add_junction(Junction(id=nid, elevation=elev, demand=0.0,
                                  emitter=em, x=spacing * i, y=elev))
        net.add_pipe(Pipe(id=f"P{i}", start=prev, end=nid, length=spacing,
                          diameter=diameter, coeff=hw_c, model="HW"))
        prev = nid
    return net
