"""Commercial catalogs and a cost model for design optimization.

specifications.md §3.5 (Stage G). Provides a discrete pipe-diameter catalog
(the optimizer chooses from these), and a price model so designs can be scored
on capital cost and pumping energy. Prices are overridable defaults (indicative
INR); the FTS ``electricity_tariff_inr_kwh`` feeds the energy term.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_G = 9.80665


@dataclass(frozen=True)
class PipeSpec:
    """One commercial pipe size for a material."""

    material: str
    nominal_diameter_mm: float
    internal_diameter_m: float
    pressure_class: str
    hw_c: float
    inr_per_m: float


# Indicative commercial catalog (uPVC IS 4985 / HDPE PE100 IS 4984), internal
# diameters and prices are representative defaults — override per supplier.
PIPE_CATALOG: list[PipeSpec] = [
    # uPVC PN6
    PipeSpec("pvc_upvc", 32, 0.0288, "PN6", 150.0, 35.0),
    PipeSpec("pvc_upvc", 40, 0.0360, "PN6", 150.0, 52.0),
    PipeSpec("pvc_upvc", 50, 0.0451, "PN6", 150.0, 78.0),
    PipeSpec("pvc_upvc", 63, 0.0569, "PN6", 150.0, 120.0),
    PipeSpec("pvc_upvc", 75, 0.0677, "PN6", 150.0, 168.0),
    PipeSpec("pvc_upvc", 90, 0.0813, "PN6", 150.0, 240.0),
    PipeSpec("pvc_upvc", 110, 0.0993, "PN6", 150.0, 355.0),
    # HDPE PE100 PN6
    PipeSpec("hdpe_pe100", 40, 0.0353, "PN6", 150.0, 60.0),
    PipeSpec("hdpe_pe100", 50, 0.0441, "PN6", 150.0, 92.0),
    PipeSpec("hdpe_pe100", 63, 0.0556, "PN6", 150.0, 142.0),
    PipeSpec("hdpe_pe100", 75, 0.0662, "PN6", 150.0, 198.0),
    PipeSpec("hdpe_pe100", 90, 0.0794, "PN6", 150.0, 280.0),
    PipeSpec("hdpe_pe100", 110, 0.0970, "PN6", 150.0, 410.0),
]


def pipe_options(material: str) -> list[PipeSpec]:
    """Catalog entries for a material, ascending by diameter."""
    opts = [p for p in PIPE_CATALOG if p.material == material]
    if not opts:  # fall back to uPVC if the material isn't catalogued
        opts = [p for p in PIPE_CATALOG if p.material == "pvc_upvc"]
    return sorted(opts, key=lambda p: p.internal_diameter_m)


_PRICE_BY_KEY = {(p.material, p.nominal_diameter_mm): p.inr_per_m for p in PIPE_CATALOG}
_AVG_PRICE = sum(p.inr_per_m for p in PIPE_CATALOG) / len(PIPE_CATALOG)


@dataclass
class CostModel:
    """Unit prices for the capital + energy cost of a design (INR)."""

    fitting_inr: dict[str, float] = field(default_factory=dict)
    valve_inr_by_dn: dict[float, float] = field(default_factory=dict)
    pump_inr_by_hp: dict[float, float] = field(default_factory=dict)
    emitter_inr_each: float = 6.0
    default_valve_inr: float = 1800.0
    default_fitting_inr: float = 60.0
    energy_inr_per_kwh: float = 6.0
    season_days: int = 120

    def pump_price(self, hp: float | None) -> float:
        """Price of the nearest catalogued pump >= hp (0 if hp is None)."""
        if hp is None or not self.pump_inr_by_hp:
            return 0.0
        for size in sorted(self.pump_inr_by_hp):
            if size >= hp:
                return self.pump_inr_by_hp[size]
        return self.pump_inr_by_hp[max(self.pump_inr_by_hp)]


DEFAULT_COSTS = CostModel(
    fitting_inr={
        "elbow_90": 55.0,
        "elbow_90_threaded": 55.0,
        "elbow_45": 50.0,
        "tee_run": 70.0,
        "tee_branch": 80.0,
        "coupler": 30.0,
        "check_valve": 450.0,
    },
    valve_inr_by_dn={32: 900.0, 40: 1200.0, 50: 1800.0, 63: 2600.0, 75: 3800.0},
    pump_inr_by_hp={1: 9000, 2: 14000, 3: 19000, 5: 28000, 7.5: 42000, 10: 60000},
    emitter_inr_each=6.0,
    energy_inr_per_kwh=5.8,
    season_days=120,
)

_VALVE_NODE_TYPES = frozenset({"zone_valve", "prv", "psv", "fcv"})


def pipe_inr_per_m(material: str, nominal_diameter_mm: float | None) -> float:
    """Price per metre for a (material, DN); average fallback if unknown."""
    return _PRICE_BY_KEY.get((material, nominal_diameter_mm), _AVG_PRICE)


def capital_cost(fts: dict, costs: CostModel = DEFAULT_COSTS) -> float:
    """Total capital cost (INR) of an FTS design: pipes + fittings + valves +
    pump + emitters."""
    total = 0.0
    for link in fts.get("links", []):
        length = float(link.get("length_m", 0.0) or 0.0)
        total += length * pipe_inr_per_m(
            link.get("material", "pvc_upvc"), link.get("nominal_diameter_mm")
        )
        for fit in link.get("minor_losses") or []:
            name = fit.get("fitting", "")
            count = int(fit.get("count", 1) or 1)
            total += count * costs.fitting_inr.get(name, costs.default_fitting_inr)

    for node in fts.get("nodes", []):
        ntype = node.get("type")
        if ntype in _VALVE_NODE_TYPES:
            dn = (node.get("attributes") or {}).get("dn_mm")
            total += costs.valve_inr_by_dn.get(dn, costs.default_valve_inr)
        elif ntype == "pump":
            total += costs.pump_price((node.get("attributes") or {}).get("motor_hp"))

    from .preprocess import zone_emitter_count

    for zone in fts.get("zones", []):
        total += zone_emitter_count(zone) * costs.emitter_inr_each
    return total


def season_energy_cost(
    power_kw: float,
    hours_per_day: float,
    costs: CostModel = DEFAULT_COSTS,
) -> float:
    """Pumping energy cost over the season (INR) for a steady duty power."""
    kwh = power_kw * hours_per_day * costs.season_days
    return kwh * costs.energy_inr_per_kwh


def hydraulic_power_kw(flow_m3s: float, head_m: float, pump_eff: float = 0.7) -> float:
    """Shaft power (kW) for a duty point at a given pump efficiency."""
    return _G * 1000.0 * flow_m3s * head_m / 1000.0 / max(pump_eff, 1e-6)
