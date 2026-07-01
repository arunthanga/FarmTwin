"""Candidate evaluation for design optimization (specifications.md §3.4, §3.7).

Builds the operating scenarios from an FTS design (honouring simultaneous-zone
scheduling), runs the GGA solver per scenario, and turns the result into a
constraint verdict + objective vector (capital cost, season pumping energy,
emission uniformity, yield proxy) for the optimizer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from . import catalog
from .fao56 import zone_design_flow
from .postprocess import emitter_discharges, pipe_velocity, pump_report, uniformity
from .preprocess import KPA_TO_M, fts_to_network
from .solver import solve


@dataclass
class ZoneScenario:
    """One simultaneously-irrigated block of zones (an operating case)."""

    name: str
    active_zones: list[str]
    zone_flows: dict[str, float]  # zone id -> design flow (m^3/s)
    hours_per_day: float


def _window_hours(dc: dict) -> float:
    """Irrigation window length in hours (default 4 h)."""
    start = dc.get("irrigation_window_start")
    end = dc.get("irrigation_window_end")
    try:
        sh, sm = (int(x) for x in str(start).split(":"))
        eh, em = (int(x) for x in str(end).split(":"))
        hours = (eh + em / 60.0) - (sh + sm / 60.0)
        return hours if hours > 0 else 4.0
    except (ValueError, AttributeError):
        return 4.0


def build_scenarios(fts: dict, *, efficiency: float = 0.9) -> list[ZoneScenario]:
    """Build operating scenarios honouring ``max_simultaneous_zones``.

    Zones are sized for the peak ET and the per-block watering time, then grouped
    (largest demand first) into blocks the controller would run sequentially. The
    design must satisfy every block.
    """
    zones = fts.get("zones") or []
    if not zones:
        return []
    dc = fts.get("design_constraints") or {}
    weather = fts.get("weather") or {}
    et0_peak = float(weather.get("design_eto_mm_day_peak", 5.8) or 5.8)
    n = len(zones)
    max_sim = int(dc.get("max_simultaneous_zones", n) or n)
    max_sim = max(1, min(max_sim, n))
    n_blocks = math.ceil(n / max_sim)
    hours_per_block = _window_hours(dc) / n_blocks

    flows = {
        z["id"]: zone_design_flow(
            z, et0_peak_mm_day=et0_peak, hours_per_day=hours_per_block, efficiency=efficiency
        )
        for z in zones
    }
    ordered = sorted(zones, key=lambda z: flows[z["id"]], reverse=True)
    scenarios: list[ZoneScenario] = []
    for b in range(n_blocks):
        block = ordered[b * max_sim : (b + 1) * max_sim]
        if not block:
            continue
        ids = [z["id"] for z in block]
        scenarios.append(
            ZoneScenario(
                name=f"block{b + 1}",
                active_zones=ids,
                zone_flows={zid: flows[zid] for zid in ids},
                hours_per_day=hours_per_block,
            )
        )
    return scenarios


@dataclass
class DesignConstraints:
    """Hydraulic + budget limits a feasible design must satisfy."""

    p_min_m: float = 7.0
    p_max_m: float = 35.0
    v_max_ms: float = 2.0
    min_eu_pct: float = 80.0
    budget_inr: float = math.inf

    @classmethod
    def from_fts(cls, fts: dict) -> DesignConstraints:
        dc = fts.get("design_constraints") or {}
        return cls(
            p_min_m=float(dc.get("min_emitter_pressure_kpa", 70.0) or 70.0) * KPA_TO_M,
            p_max_m=float(dc.get("max_emitter_pressure_kpa", 350.0) or 350.0) * KPA_TO_M,
            v_max_ms=float(dc.get("max_velocity_ms", 2.0) or 2.0),
            min_eu_pct=float(dc.get("min_eu_pct", 80.0) or 80.0),
            budget_inr=float(dc.get("budget_inr", math.inf) or math.inf),
        )


@dataclass
class DesignObjectives:
    """The objective vector (all framed so *lower is better* except eu/yield)."""

    capital_inr: float
    energy_inr: float
    eu_pct: float
    yield_rel: float = 1.0


@dataclass
class DesignReport:
    objectives: DesignObjectives
    feasible: bool
    violations: list[str] = field(default_factory=list)


def _zone_valve_nodes(fts: dict) -> dict[str, str]:
    return {z["id"]: z.get("valve_node") for z in fts.get("zones") or []}


def observability_score(fts: dict) -> dict:
    """Twin-readiness of a design's instrumentation (specifications.md §4 P4.13).

    A design is observable enough for the digital twin when system flow is
    metered and each zone has at least one state sensor. Returns the sensor
    tallies, the fraction of zones covered, and a 0–1 ``score`` the optimizer can
    use as a tie-break so the chosen design is twin-ready.
    """
    sensors = fts.get("sensors") or []
    zones = fts.get("zones") or []
    n_flow = sum(1 for s in sensors if s.get("type") == "flow_meter")
    n_pressure = sum(1 for s in sensors if s.get("type") == "pressure_transducer")
    n_moisture = sum(1 for s in sensors if s.get("type") == "soil_moisture")
    covered = {s.get("zone_id") for s in sensors if s.get("zone_id")}
    zones_covered = sum(1 for z in zones if z.get("id") in covered)
    zone_coverage = zones_covered / len(zones) if zones else 0.0
    score = 0.5 * min(n_flow, 1) + 0.5 * zone_coverage
    return {
        "n_flow_meters": n_flow,
        "n_pressure_transducers": n_pressure,
        "n_soil_moisture": n_moisture,
        "zones_covered": zones_covered,
        "zone_coverage": zone_coverage,
        "score": min(1.0, score),
    }


def evaluate(
    fts: dict,
    *,
    scenarios: list[ZoneScenario] | None = None,
    constraints: DesignConstraints | None = None,
    costs: catalog.CostModel = catalog.DEFAULT_COSTS,
) -> DesignReport:
    """Score an FTS design: solve each scenario, check constraints, build objectives.

    Feasibility (pressure band, velocity cap, pump envelope, convergence, EU,
    budget) is taken as the worst case across the scheduled scenarios. The EU
    objective uses an all-zones-on reference solve so it varies smoothly with
    pipe sizing even when the schedule runs one zone at a time.
    """
    constraints = constraints or DesignConstraints.from_fts(fts)
    scenarios = scenarios if scenarios is not None else build_scenarios(fts)
    valve_nodes = _zone_valve_nodes(fts)
    violations: list[str] = []
    feasible = True
    energy_inr = 0.0

    for scn in scenarios:
        net = fts_to_network(fts, active_zones=scn.active_zones, zone_flows=scn.zone_flows)
        res = solve(net)
        if not res.converged:
            feasible = False
            violations.append(f"{scn.name}: solver did not converge")
            continue
        for zid in scn.active_zones:
            vnode = valve_nodes.get(zid)
            p = res.pressures.get(vnode)
            if p is None:
                continue
            if p < constraints.p_min_m:
                feasible = False
                violations.append(f"{scn.name}/{zid}: inlet {p:.1f} m < Pmin")
            elif p > constraints.p_max_m:
                feasible = False
                violations.append(f"{scn.name}/{zid}: inlet {p:.1f} m > Pmax")
        for pid, pipe in net.pipes.items():
            v = pipe_velocity(res.flows.get(pid, 0.0), pipe.diameter)
            if v > constraints.v_max_ms:
                feasible = False
                violations.append(f"{scn.name}/{pid}: velocity {v:.2f} m/s > Vmax")
        for row in pump_report(net, res):
            pump = net.pumps.get(row["pump"])
            eff = pump.curve.pump_eff if pump else 0.7
            q_m3s = row["Q_m3ph"] / 3600.0
            power_kw = catalog.hydraulic_power_kw(q_m3s, max(row["head_m"], 0.0), eff)
            energy_inr += catalog.season_energy_cost(power_kw, scn.hours_per_day, costs)
            if row["motor_hp"] is None:
                feasible = False
                violations.append(f"{scn.name}/{row['pump']}: duty exceeds 1-50 HP range")

    # EU reference: all zones energised, single solve.
    eu_pct = 100.0
    net_all = fts_to_network(fts)
    res_all = solve(net_all)
    disch = emitter_discharges(net_all, res_all)
    if disch:
        u = uniformity(disch)
        eu_pct = u.get("EU_pct", 100.0)
    if eu_pct < constraints.min_eu_pct:
        feasible = False
        violations.append(f"EU {eu_pct:.1f}% < min {constraints.min_eu_pct:.1f}%")

    capital_inr = catalog.capital_cost(fts, costs)
    if capital_inr > constraints.budget_inr:
        feasible = False
        violations.append(f"capital INR {capital_inr:.0f} > budget {constraints.budget_inr:.0f}")

    return DesignReport(
        objectives=DesignObjectives(
            capital_inr=capital_inr,
            energy_inr=energy_inr,
            eu_pct=eu_pct,
            yield_rel=eu_pct / 100.0,
        ),
        feasible=feasible,
        violations=violations,
    )
