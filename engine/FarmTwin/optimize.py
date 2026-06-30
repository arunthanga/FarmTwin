"""Design optimizer for FarmTwin Studio (specifications.md §3.6-3.8).

Searches the discrete pipe-diameter design space and returns the **top 2-3**
ranked designs (lowest-cost / highest-uniformity / balanced) with a priced Bill
of Materials. Uses NSGA-II (``pymoo``) when the ``[pro]`` extra is installed to
propose candidate genomes; always includes a deterministic heuristic pool
(greedy least-cost + a uniform size ladder) so the core produces a design with
no optional dependency. All candidates are scored by :func:`evaluate.evaluate`.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from . import catalog
from .catalog import CostModel, PipeSpec
from .evaluate import DesignConstraints, DesignReport, evaluate
from .postprocess import pipe_velocity
from .preprocess import fts_to_network
from .solver import solve

# Link types whose diameter the optimizer is allowed to choose.
SIZABLE_TYPES = frozenset({"mainline", "submain", "main", "riser", "bypass"})
_CATALOG_MATERIALS = {p.material for p in catalog.PIPE_CATALOG}


@dataclass
class DecisionVariable:
    """A sizable link and its ordered (ascending diameter) catalog options."""

    link_id: str
    options: list[PipeSpec]


@dataclass
class RankedDesign:
    """A labelled recommendation."""

    label: str  # "lowest_cost" | "highest_uniformity" | "balanced"
    fts: dict
    report: DesignReport
    bom: dict


def _is_sizable(link: dict) -> bool:
    return link.get("type") in SIZABLE_TYPES or link.get("material") in _CATALOG_MATERIALS


def decision_space(fts: dict) -> list[DecisionVariable]:
    """Build the per-link diameter decision variables for an FTS design."""
    variables: list[DecisionVariable] = []
    for link in fts.get("links", []):
        if not _is_sizable(link):
            continue
        material = link.get("material")
        if material not in _CATALOG_MATERIALS:
            material = "pvc_upvc"
        variables.append(DecisionVariable(link["id"], catalog.pipe_options(material)))
    return variables


def apply_genome(fts: dict, variables: list[DecisionVariable], genome: list[int]) -> dict:
    """Return a deep copy of ``fts`` with each sizable link set to its choice."""
    design = copy.deepcopy(fts)
    links = {link["id"]: link for link in design.get("links", [])}
    for var, idx in zip(variables, genome, strict=True):
        spec = var.options[max(0, min(idx, len(var.options) - 1))]
        link = links.get(var.link_id)
        if link is None:
            continue
        link["material"] = spec.material
        link["nominal_diameter_mm"] = spec.nominal_diameter_mm
        link["internal_diameter_m"] = spec.internal_diameter_m
        link["hazen_williams_c"] = spec.hw_c
    return design


def _greedy_least_cost(
    fts: dict,
    variables: list[DecisionVariable],
    constraints: DesignConstraints,
    costs: CostModel,
    *,
    max_steps: int = 40,
) -> list[int]:
    """Start at the smallest sizes; upsize the worst (fastest) pipe until feasible."""
    genome = [0] * len(variables)
    for _ in range(max_steps):
        design = apply_genome(fts, variables, genome)
        if evaluate(design, constraints=constraints, costs=costs).feasible:
            return genome
        net = fts_to_network(design)
        res = solve(net)
        worst_i, worst_v = None, -1.0
        for i, var in enumerate(variables):
            if genome[i] >= len(var.options) - 1:
                continue
            pipe = net.pipes.get(var.link_id)
            if pipe is None:
                continue
            v = pipe_velocity(res.flows.get(var.link_id, 0.0), pipe.diameter)
            if v > worst_v:
                worst_v, worst_i = v, i
        if worst_i is None:  # nothing left to upsize
            break
        genome[worst_i] += 1
    return genome


def _ladder(variables: list[DecisionVariable]) -> list[list[int]]:
    """Uniform size levels: every link at option ``min(level, max)``."""
    max_opts = max((len(v.options) for v in variables), default=1)
    return [[min(level, len(v.options) - 1) for v in variables] for level in range(max_opts)]


def _pymoo_genomes(
    fts: dict,
    variables: list[DecisionVariable],
    constraints: DesignConstraints,
    costs: CostModel,
    *,
    pop: int,
    generations: int,
    seed: int,
) -> list[list[int]]:
    """NSGA-II proposals when pymoo is installed; [] otherwise (best-effort)."""
    try:
        import numpy as np
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.core.problem import Problem
        from pymoo.operators.crossover.sbx import SBX
        from pymoo.operators.mutation.pm import PM
        from pymoo.operators.repair.rounding import RoundingRepair
        from pymoo.operators.sampling.rnd import IntegerRandomSampling
        from pymoo.optimize import minimize as pymoo_minimize
    except ImportError:
        return []

    n_var = len(variables)
    xu = np.array([len(v.options) - 1 for v in variables])

    class _Problem(Problem):
        def __init__(self) -> None:
            super().__init__(n_var=n_var, n_obj=3, n_constr=1, xl=np.zeros(n_var), xu=xu)

        def _evaluate(self, X, out, *args, **kwargs):  # noqa: N803
            f, g = [], []
            for row in X:
                rep = evaluate(
                    apply_genome(fts, variables, [int(round(x)) for x in row]),
                    constraints=constraints,
                    costs=costs,
                )
                o = rep.objectives
                f.append([o.capital_inr, o.energy_inr, 100.0 - o.eu_pct])
                g.append([0.0 if rep.feasible else float(len(rep.violations))])
            out["F"] = np.array(f)
            out["G"] = np.array(g)

    try:
        result = pymoo_minimize(
            _Problem(),
            NSGA2(
                pop_size=pop,
                sampling=IntegerRandomSampling(),
                crossover=SBX(prob=0.9, eta=15, repair=RoundingRepair()),
                mutation=PM(eta=20, repair=RoundingRepair()),
                eliminate_duplicates=True,
            ),
            ("n_gen", generations),
            seed=seed,
            verbose=False,
        )
        x = result.X
        if x is None:
            return []
        rows = x if hasattr(x[0], "__len__") else [x]
        return [[int(round(v)) for v in row] for row in rows]
    except Exception:  # noqa: BLE001 - pymoo is best-effort; fall back to heuristics
        return []


def _rank(pool: list[tuple[tuple[int, ...], dict, DesignReport]]) -> list[RankedDesign]:
    """Pick lowest-cost / highest-uniformity / balanced (knee) from the pool."""
    feasible = [c for c in pool if c[2].feasible] or pool
    caps = [c[2].objectives.capital_inr for c in feasible]
    eus = [c[2].objectives.eu_pct for c in feasible]
    cmin, cmax = min(caps), max(caps)
    emin, emax = min(eus), max(eus)

    def knee(c) -> float:
        nc = (c[2].objectives.capital_inr - cmin) / (cmax - cmin) if cmax > cmin else 0.0
        ne = (emax - c[2].objectives.eu_pct) / (emax - emin) if emax > emin else 0.0
        return (nc**2 + ne**2) ** 0.5

    picks = {
        "lowest_cost": min(feasible, key=lambda c: c[2].objectives.capital_inr),
        "highest_uniformity": max(feasible, key=lambda c: c[2].objectives.eu_pct),
        "balanced": min(feasible, key=knee),
    }
    from .postprocess import priced_bom

    return [
        RankedDesign(label=label, fts=c[1], report=c[2], bom=priced_bom(c[1]))
        for label, c in picks.items()
    ]


def optimize_design(
    fts: dict,
    *,
    costs: CostModel = catalog.DEFAULT_COSTS,
    constraints: DesignConstraints | None = None,
    pop: int = 40,
    generations: int = 25,
    seed: int = 0,
) -> list[RankedDesign]:
    """Search pipe diameters and return the top 2-3 ranked, priced designs.

    Combines NSGA-II proposals (when ``pymoo`` is installed) with a deterministic
    heuristic pool, scores every unique candidate with :func:`evaluate.evaluate`,
    and labels the recommendations lowest-cost / highest-uniformity / balanced.
    """
    constraints = constraints or DesignConstraints.from_fts(fts)
    variables = decision_space(fts)
    if not variables:
        report = evaluate(fts, constraints=constraints, costs=costs)
        from .postprocess import priced_bom

        only = RankedDesign("balanced", copy.deepcopy(fts), report, priced_bom(fts, costs))
        return [only]

    genomes: set[tuple[int, ...]] = set()
    genomes.add(tuple(_greedy_least_cost(fts, variables, constraints, costs)))
    genomes.update(tuple(g) for g in _ladder(variables))
    genomes.update(
        tuple(g)
        for g in _pymoo_genomes(
            fts, variables, constraints, costs, pop=pop, generations=generations, seed=seed
        )
    )

    pool: list[tuple[tuple[int, ...], dict, DesignReport]] = []
    for genome in genomes:
        design = apply_genome(fts, variables, list(genome))
        pool.append((genome, design, evaluate(design, constraints=constraints, costs=costs)))
    return _rank(pool)
