"""FarmTwin: an open hydraulic + agronomy simulation engine for irrigation.

Core: a 1-D pressurized-network solver (Global Gradient Algorithm) with a
component library (pipes, pumps/motors, valves, fittings, venturi, emitters),
a FAO-56 agronomy layer, and pre/post-processing for irrigation design and
digital-twin operation.
"""

from .network import (
    Network, Junction, Reservoir, Pipe, Pump, Valve, VenturiLink, Emitter,
)
from .components import (
    PumpCurve, Venturi, K_LIBRARY, k_of, sum_k, select_motor_hp,
    MOTOR_CATALOG_HP,
)
from .solver import solve, SolveResult

__all__ = [
    "Network", "Junction", "Reservoir", "Pipe", "Pump", "Valve", "VenturiLink",
    "Emitter", "PumpCurve", "Venturi", "K_LIBRARY", "k_of", "sum_k",
    "select_motor_hp", "MOTOR_CATALOG_HP", "solve", "SolveResult",
]

__version__ = "0.1.0"
