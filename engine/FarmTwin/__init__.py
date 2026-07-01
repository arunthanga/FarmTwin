"""FarmTwin: an open hydraulic + agronomy simulation engine for irrigation.

Core: a 1-D pressurized-network solver (Global Gradient Algorithm) with a
component library (pipes, pumps/motors, valves, fittings, venturi, emitters),
a FAO-56 agronomy layer, and pre/post-processing for irrigation design and
digital-twin operation.
"""

# Domain submodules — the implemented engine surface. Imported here so the
# public package API matches the implemented structure. Each only hard-imports
# NumPy at module load; SciPy/matplotlib/WNTR/TSNet are lazy-imported on use.
from . import (
    agronomy,
    assimilation,
    catalog,
    commissioning,
    components,
    emitters,
    evaluate,
    fao56,
    geo,
    headloss,
    network,
    optimize,
    params,
    postprocess,
    preprocess,
    quality,
    richards,
    solver,
    studio_design,
    surface,
    transient,
)
from .assimilation import (
    AssimilationResult,
    CalibrationTarget,
    HydraulicTwin,
    Observation,
)
from .catalog import DEFAULT_COSTS, PIPE_CATALOG, CostModel, PipeSpec
from .components import (
    K_LIBRARY,
    MOTOR_CATALOG_HP,
    PumpCurve,
    Venturi,
    k_of,
    select_motor_hp,
    sum_k,
)
from .evaluate import DesignConstraints, DesignObjectives, DesignReport, build_scenarios
from .network import (
    Emitter,
    Junction,
    Network,
    Pipe,
    Pump,
    Reservoir,
    Valve,
    VenturiLink,
)
from .optimize import RankedDesign, optimize_design
from .params import LiveParameter, ParameterSet
from .preprocess import fts_to_network
from .solver import SolveResult, solve
from .studio_design import design_from_fts, twin_from_design

__all__ = [
    # Hydraulic network model + solver (top-level convenience exports)
    "Network",
    "Junction",
    "Reservoir",
    "Pipe",
    "Pump",
    "Valve",
    "VenturiLink",
    "Emitter",
    "PumpCurve",
    "Venturi",
    "K_LIBRARY",
    "k_of",
    "sum_k",
    "select_motor_hp",
    "MOTOR_CATALOG_HP",
    "solve",
    "SolveResult",
    # Live parametrization + digital-twin assimilation
    "ParameterSet",
    "LiveParameter",
    "HydraulicTwin",
    "CalibrationTarget",
    "Observation",
    "AssimilationResult",
    # Studio design optimization (survey -> best pipe/valve/fitting config)
    "design_from_fts",
    "optimize_design",
    "fts_to_network",
    "build_scenarios",
    "twin_from_design",
    "RankedDesign",
    "DesignConstraints",
    "DesignObjectives",
    "DesignReport",
    "PipeSpec",
    "PIPE_CATALOG",
    "CostModel",
    "DEFAULT_COSTS",
    # Implemented domain submodules
    "agronomy",
    "assimilation",
    "catalog",
    "commissioning",
    "components",
    "emitters",
    "evaluate",
    "fao56",
    "geo",
    "headloss",
    "network",
    "optimize",
    "params",
    "postprocess",
    "preprocess",
    "quality",
    "richards",
    "solver",
    "studio_design",
    "surface",
    "transient",
]

__version__ = "0.2.0"
