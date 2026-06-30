"""Commissioning support for FarmTwin (R-POST-7).

Two responsibilities:

* **Device onboarding** — register field sensors/valves into the FTS document
  from a scanned LoRaWAN ``DevEUI`` so the runtime can auto-map them
  (plug-and-play onboarding, ``R-IOT-3``).
* **Commissioning check** — compare *measured* pressures/flows at the head and
  zone valves against the *designed* values and produce a pass/fail sign-off
  against the design's tolerance band, proving the install matches the design.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Default acceptance band: measured value must be within +/- this fraction of
# the designed value to pass commissioning.
DEFAULT_TOLERANCE_FRAC = 0.10


def register_sensor_from_deveui(
    *,
    fts: dict,
    dev_eui: str,
    sensor_type: str,
    zone_id: str | None,
    location: dict,
) -> dict:
    """Register a field sensor into an FTS document from a scanned DevEUI.

    Args:
        fts: The FTS document to update (modified in place and returned).
        dev_eui: The LoRaWAN ``DevEUI`` read from the device QR code.
        sensor_type: Sensor category (e.g. ``"soil_moisture"``).
        zone_id: Zone the sensor belongs to, or ``None`` for network-wide.
        location: ``{"lat", "lon", "elevation_m"}`` placement.

    Returns:
        The updated FTS document with the new sensor appended to ``sensors``.
    """
    sensors = fts.setdefault("sensors", [])
    sensor_id = f"S{len(sensors) + 1:02d}"
    sensors.append(
        {
            "id": sensor_id,
            "type": sensor_type,
            "zone_id": zone_id,
            "location": location,
            "lora_dev_eui": dev_eui,
            "installation_date": None,
            "notes": "auto-registered from DevEUI scan",
        }
    )
    return fts


@dataclass
class CommissioningPoint:
    """A single measured-vs-designed commissioning comparison."""

    location: str
    quantity: str  # "pressure" or "flow"
    designed: float
    measured: float
    tolerance_frac: float = DEFAULT_TOLERANCE_FRAC

    @property
    def error_frac(self) -> float:
        """Relative error of measured vs designed (0 if designed is 0)."""
        if self.designed == 0.0:
            return 0.0 if self.measured == 0.0 else 1.0
        return (self.measured - self.designed) / self.designed

    @property
    def passed(self) -> bool:
        """True if the measurement is within the acceptance band."""
        return abs(self.error_frac) <= self.tolerance_frac


@dataclass
class CommissioningReport:
    """Aggregate commissioning result with a pass/fail sign-off."""

    points: list[CommissioningPoint] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True only if every comparison point is within tolerance."""
        return all(p.passed for p in self.points)

    def summary(self) -> dict:
        """Return a machine-readable summary of the sign-off."""
        return {
            "passed": self.passed,
            "n_points": len(self.points),
            "n_failed": sum(1 for p in self.points if not p.passed),
            "points": [
                {
                    "location": p.location,
                    "quantity": p.quantity,
                    "designed": p.designed,
                    "measured": p.measured,
                    "error_frac": p.error_frac,
                    "passed": p.passed,
                }
                for p in self.points
            ],
        }


def commission_check(
    designed: dict[str, float],
    measured: dict[str, float],
    *,
    quantity: str = "pressure",
    tolerance_frac: float = DEFAULT_TOLERANCE_FRAC,
) -> CommissioningReport:
    """Compare measured against designed values at matching locations.

    Args:
        designed: Designed value per location (e.g. head pressures in m).
        measured: Field-measured value per location.
        quantity: Label for the compared quantity (``"pressure"``/``"flow"``).
        tolerance_frac: Allowed relative deviation before a point fails.

    Returns:
        A :class:`CommissioningReport` with one point per shared location.
    """
    report = CommissioningReport()
    for location, design_value in designed.items():
        if location not in measured:
            continue
        report.points.append(
            CommissioningPoint(
                location=location,
                quantity=quantity,
                designed=design_value,
                measured=measured[location],
                tolerance_frac=tolerance_frac,
            )
        )
    return report
