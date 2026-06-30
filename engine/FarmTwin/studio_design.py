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
from .catalog import DEFAULT_COSTS, CostModel
from .evaluate import DesignConstraints
from .optimize import RankedDesign, optimize_design
from .preprocess import FTSValidationError, validate_fts_json


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
