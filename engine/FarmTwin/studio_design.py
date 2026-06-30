"""FarmTwin Studio orchestration (specifications.md §3.10, Stage K).

One entry point that takes a field survey (GPS node locations + pump
specifications + crops + constraints) and returns the **best configurations of
pipes/valves/fittings** — the top 2-3 ranked, priced designs. This ties together
geometry (geo), validation (preprocess), the demand model + evaluation
(evaluate), and the optimizer (optimize).
"""

from __future__ import annotations

import copy

from . import geo
from .assimilation import CalibrationTarget, HydraulicTwin
from .catalog import DEFAULT_COSTS, CostModel
from .evaluate import DesignConstraints
from .optimize import RankedDesign, optimize_design
from .preprocess import FTSValidationError, fts_to_network, validate_fts_json


def design_from_fts(
    fts: dict,
    *,
    costs: CostModel = DEFAULT_COSTS,
    constraints: DesignConstraints | None = None,
    validate: bool = True,
) -> list[RankedDesign]:
    """Survey → optimized pipe/valve/fitting configurations.

    Steps: fill pipe lengths from GPS (B) → validate the survey (A) → search the
    diameter design space scoring each candidate with the GGA solver + FAO-56
    demand + cost model (C–H) → return the top 2-3 ranked, priced designs (I–J).

    Args:
        fts: an FTS survey/design document (GPS nodes, pump attributes, zones,
            ``design_constraints``).
        costs: price model for capital + energy scoring.
        constraints: hydraulic/budget limits (defaults derived from the FTS).
        validate: raise on FTS validation errors before optimizing.

    Returns:
        A list of :class:`~FarmTwin.optimize.RankedDesign` (lowest-cost /
        highest-uniformity / balanced), each with a solved feasibility report and
        a priced Bill of Materials.

    Raises:
        FTSValidationError: if ``validate`` and the survey fails validation.
    """
    fts = copy.deepcopy(fts)
    geo.fill_link_lengths(fts)
    if validate:
        errors = validate_fts_json(fts)
        if errors:
            raise FTSValidationError("; ".join(errors))
    return optimize_design(fts, costs=costs, constraints=constraints)


def design_twin_targets(
    net, *, prior_std: float = 20.0, lower: float = 50.0, upper: float = 160.0
) -> list[CalibrationTarget]:
    """Calibration targets (pipe Hazen-Williams C) for every pipe in a design."""
    return [
        CalibrationTarget.pipe_coeff(pid, prior_std=prior_std, lower=lower, upper=upper)
        for pid in net.pipes
    ]


def twin_from_design(fts: dict, *, prior_std: float = 20.0) -> HydraulicTwin:
    """Seed a :class:`~FarmTwin.assimilation.HydraulicTwin` from a chosen design.

    The Studio→Runtime bridge (specifications.md §4 P4.14): the as-built design's
    pipe roughness values become the twin's priors, so the Runtime starts from
    the design and refines roughness/clog from field sensors.
    """
    net = fts_to_network(fts)
    return HydraulicTwin(net, targets=design_twin_targets(net, prior_std=prior_std))
