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
    commissioning,
    components,
    emitters,
    fao56,
    headloss,
    network,
    params,
    postprocess,
    preprocess,
    quality,
    richards,
    solver,
    surface,
    transient,
)
from .assimilation import (
    AssimilationResult,
    CalibrationTarget,
    HydraulicTwin,
    Observation,
)
from .components import (
    K_LIBRARY,
    MOTOR_CATALOG_HP,
    PumpCurve,
    Venturi,
    k_of,
    select_motor_hp,
    sum_k,
)
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
from .params import LiveParameter, ParameterSet
from .solver import SolveResult, solve

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
    # Implemented domain submodules
    "agronomy",
    "assimilation",
    "commissioning",
    "components",
    "emitters",
    "fao56",
    "headloss",
    "network",
    "params",
    "postprocess",
    "preprocess",
    "quality",
    "richards",
    "solver",
    "surface",
    "transient",
]

__version__ = "0.2.0"
