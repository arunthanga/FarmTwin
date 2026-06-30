"""FarmTwin: an open hydraulic + agronomy simulation engine for irrigation.

Core: a 1-D pressurized-network solver (Global Gradient Algorithm) with a
component library (pipes, pumps/motors, valves, fittings, venturi, emitters),
a FAO-56 agronomy layer, and pre/post-processing for irrigation design and
digital-twin operation.
"""

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
from .solver import SolveResult, solve

__all__ = [
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
]

__version__ = "0.2.0"
