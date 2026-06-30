"""Network data model for FarmTwin.

A network is a graph of nodes (junctions, reservoirs) and links (pipes).
Emitters are attached to junctions and are expanded into virtual links by the
solver (see emitters.py). Units are SI throughout.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Junction:
    """A node with unknown head. demand is base withdrawal (m^3/s, >0 = out)."""

    id: str
    elevation: float = 0.0  # m
    demand: float = 0.0  # m^3/s (fixed/base demand)
    emitter: Emitter | None = None
    x: float = 0.0
    y: float = 0.0


@dataclass
class Reservoir:
    """A fixed-head boundary node (source). head = total head (m)."""

    id: str
    head: float  # total head (m), = water-surface elevation
    x: float = 0.0
    y: float = 0.0


@dataclass
class Pipe:
    """A link carrying flow from `start` node to `end` node.

    `fittings` is a list of fitting names (see components.K_LIBRARY) whose K
    values are summed into the minor loss; `minor_loss` adds any extra K.
    """

    id: str
    start: str
    end: str
    length: float  # m
    diameter: float  # m
    coeff: float  # HW: C (dimensionless); DW: roughness eps (m)
    minor_loss: float = 0.0  # extra minor-loss K (beyond `fittings`)
    fittings: list = field(default_factory=list)  # e.g. ["tee_run", "elbow_45"]
    model: str = "HW"  # "HW" or "DW"


@dataclass
class Pump:
    """A link that adds head from `start` to `end`, defined by a pump curve.

    `curve` is a components.PumpCurve. `status` may be "OPEN" or "CLOSED".
    """

    id: str
    start: str
    end: str
    curve: object  # components.PumpCurve
    status: str = "OPEN"


@dataclass
class Valve:
    """An in-line valve link.

    type: "TCV" (throttle / ball / gate via K), with status OPEN/CLOSED.
    PRV/PSV/FCV are reserved for the next increment.
    diameter is needed to convert K -> minor-loss coefficient.
    """

    id: str
    start: str
    end: str
    diameter: float
    k: float = 0.05  # minor-loss K at the current opening
    type: str = "TCV"
    status: str = "OPEN"


@dataclass
class VenturiLink:
    """A venturi fertigation injector placed in-line as a loss element."""

    id: str
    start: str
    end: str
    venturi: object  # components.Venturi
    status: str = "OPEN"


@dataclass
class Emitter:
    """Pressure-dependent outlet at a junction.

    Non-PC (power law): q = k * P^x, where P = pressure head = H - elevation.
    PC (pressure compensating): delivers `nominal_q` while P in [p_min, p_max].
    """

    k: float  # discharge coefficient (SI units consistent)
    x: float = 0.5  # emitter exponent (0.5 turbulent .. 1.0 laminar)
    pressure_compensating: bool = False
    nominal_q: float = 0.0  # m^3/s, used when pressure_compensating
    p_min: float = 5.0  # m, PC operating band lower bound
    p_max: float = 40.0  # m, PC operating band upper bound


@dataclass
class Network:
    junctions: dict = field(default_factory=dict)
    reservoirs: dict = field(default_factory=dict)
    pipes: dict = field(default_factory=dict)
    pumps: dict = field(default_factory=dict)
    valves: dict = field(default_factory=dict)
    venturis: dict = field(default_factory=dict)

    # ---- builders ----
    def add_junction(self, j: Junction) -> Junction:
        self.junctions[j.id] = j
        return j

    def add_reservoir(self, r: Reservoir) -> Reservoir:
        self.reservoirs[r.id] = r
        return r

    def _check_ends(self, link) -> None:
        if link.start not in self.node_ids or link.end not in self.node_ids:
            raise ValueError(f"Link {link.id}: endpoints must exist as nodes")

    def add_pipe(self, p: Pipe) -> Pipe:
        self._check_ends(p)
        self.pipes[p.id] = p
        return p

    def add_pump(self, p: Pump) -> Pump:
        self._check_ends(p)
        self.pumps[p.id] = p
        return p

    def add_valve(self, v: Valve) -> Valve:
        self._check_ends(v)
        self.valves[v.id] = v
        return v

    def add_venturi(self, v: VenturiLink) -> VenturiLink:
        self._check_ends(v)
        self.venturis[v.id] = v
        return v

    def active_links(self):
        """Yield (id, kind, link) for all non-CLOSED links."""
        for pid, p in self.pipes.items():
            yield pid, "pipe", p
        for pid, p in self.pumps.items():
            if getattr(p, "status", "OPEN") != "CLOSED":
                yield pid, "pump", p
        for vid, v in self.valves.items():
            if getattr(v, "status", "OPEN") != "CLOSED":
                yield vid, "valve", v
        for vid, v in self.venturis.items():
            if getattr(v, "status", "OPEN") != "CLOSED":
                yield vid, "venturi", v

    # ---- views ----
    @property
    def node_ids(self) -> set:
        return set(self.junctions) | set(self.reservoirs)

    def node_elevation(self, node_id: str) -> float:
        if node_id in self.junctions:
            return self.junctions[node_id].elevation
        return self.reservoirs[node_id].head

    def validate(self) -> None:
        if not self.reservoirs:
            raise ValueError("Network needs at least one reservoir (fixed head)")
        for p in self.pipes.values():
            if p.diameter <= 0 or p.length <= 0:
                raise ValueError(f"Pipe {p.id}: length and diameter must be > 0")
