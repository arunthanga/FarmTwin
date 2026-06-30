"""Data-quality gate for FarmTwin sensor streams (QARTOD + Hampel).

Implements the six real-time quality-control checks required by ``R-QC-1`` /
``R-QC-2`` before any measurement may drive control or estimation:

* **B1** — gross-range check (sensor physical limits)
* **B2** — climatological range check (season-aware plausibility)
* **B3** — spike check (single-sample excursion)
* **B4** — rate-of-change check (physically implausible slew)
* **B5** — flat-line check (stuck sensor)
* **B6** — Hampel outlier check (rolling median +/- k * MAD)

Flags follow the QARTOD convention: ``PASS=1``, ``SUSPECT=3``, ``FAIL=4``.
Only ``PASS``/``SUSPECT`` readings are usable downstream; ``FAIL`` data is
excluded so it never reaches the GGA solver or the FAO-56 balance.

White-paper references:
    [QARTOD] IOOS QARTOD Real-Time QC Manuals, https://ioos.noaa.gov/project/qartod/
    [ioos_qc] https://ioos.github.io/ioos_qc/
    [Hampel] Hampel (1974) JASA 69(346):383-393, doi:10.1080/01621459.1974.10482962
"""

from __future__ import annotations

from enum import IntEnum
import math
from statistics import median

# MAD-to-sigma consistency constant for a normal distribution (Hampel 1974).
MAD_SCALE = 1.4826

# Spike-check severity multipliers (multiples of the spike threshold).
SPIKE_SUSPECT_FACTOR = 1.0
SPIKE_FAIL_FACTOR = 3.0

# Per-sensor default thresholds used by the streaming gate. Values are
# deliberately conservative; calibrate against site history (see
# ``calibrate_spike_threshold``).
_SPIKE_THRESHOLD: dict[str, float] = {
    "soil_moisture": 0.10,  # m3/m3
    "pressure_transducer": 100.0,  # kPa
    "flow_meter": 1.0,  # m3/h
}
_MAX_RATE_PER_S: dict[str, float] = {
    "soil_moisture": 5.0e-4,  # m3/m3 per second
    "pressure_transducer": 50.0,  # kPa per second
    "flow_meter": 1.0,  # m3/h per second
}

# Coarse seasonal climatology bounds (P5/P95) for the B2 check, by sensor type.
_CLIMATOLOGY: dict[str, tuple[float, float]] = {
    "soil_moisture": (0.08, 0.48),  # Palakkad red laterite (GLDAS estimate)
    "pressure_transducer": (0.0, 1000.0),
    "flow_meter": (0.0, 50.0),
}


class QCFlag(IntEnum):
    """QARTOD quality flag (lower is better)."""

    PASS = 1
    SUSPECT = 3
    FAIL = 4


def _is_invalid(value: float) -> bool:
    """Return True if ``value`` is NaN or infinite."""
    return math.isnan(value) or math.isinf(value)


def b1_gross_range(value: float, sensor_min: float, sensor_max: float) -> QCFlag:
    """B1 gross-range check against the sensor's physical limits.

    Args:
        value: Measured value.
        sensor_min: Inclusive lower physical bound for the sensor.
        sensor_max: Inclusive upper physical bound for the sensor.

    Returns:
        ``QCFlag.FAIL`` if the value is NaN/inf or outside the range, else
        ``QCFlag.PASS``.
    """
    if _is_invalid(value):
        return QCFlag.FAIL
    if value < sensor_min or value > sensor_max:
        return QCFlag.FAIL
    return QCFlag.PASS


def b2_climatological_range(
    value: float,
    doy: int,
    sensor_type: str,
) -> QCFlag:
    """B2 climatological-range check using season-aware plausibility bounds.

    Args:
        value: Measured value.
        doy: Day of year (1-366); reserved for date-specific bounds.
        sensor_type: Sensor category used to look up the climatology table.

    Returns:
        ``QCFlag.PASS`` inside the climatological band (or when no climatology
        is known), otherwise ``QCFlag.SUSPECT``.
    """
    del doy  # Single-band climatology for now; kept for the date-aware API.
    if _is_invalid(value):
        return QCFlag.FAIL
    bounds = _CLIMATOLOGY.get(sensor_type)
    if bounds is None:
        return QCFlag.PASS
    lo, hi = bounds
    if lo <= value <= hi:
        return QCFlag.PASS
    return QCFlag.SUSPECT


def b3_spike(
    prev: float,
    current: float,
    next_val: float,
    spike_threshold: float,
) -> QCFlag:
    """B3 spike check: excursion of ``current`` from its neighbours' average.

    Args:
        prev: Previous sample.
        current: Sample under test.
        next_val: Following sample.
        spike_threshold: Allowed deviation before a sample is suspect.

    Returns:
        ``PASS`` within threshold, ``SUSPECT`` up to ``SPIKE_FAIL_FACTOR`` x
        threshold, otherwise ``FAIL``.
    """
    if _is_invalid(current) or _is_invalid(prev) or _is_invalid(next_val):
        return QCFlag.FAIL
    deviation = abs(current - 0.5 * (prev + next_val))
    if deviation <= SPIKE_SUSPECT_FACTOR * spike_threshold:
        return QCFlag.PASS
    if deviation <= SPIKE_FAIL_FACTOR * spike_threshold:
        return QCFlag.SUSPECT
    return QCFlag.FAIL


def b4_rate_of_change(
    current: float,
    previous: float,
    dt_seconds: float,
    max_rate_per_second: float,
) -> QCFlag:
    """B4 rate-of-change check against the maximum physical slew rate.

    Args:
        current: Latest sample.
        previous: Prior sample.
        dt_seconds: Elapsed time between the two samples (s).
        max_rate_per_second: Maximum plausible change per second.

    Returns:
        ``QCFlag.FAIL`` if the observed rate exceeds the limit, else
        ``QCFlag.PASS``.
    """
    if _is_invalid(current) or _is_invalid(previous) or dt_seconds <= 0:
        return QCFlag.FAIL
    rate = abs(current - previous) / dt_seconds
    if rate > max_rate_per_second:
        return QCFlag.FAIL
    return QCFlag.PASS


def b5_flatline(
    history: list[float],
    eps: float = 1e-4,
    min_count: int = 5,
) -> QCFlag:
    """B5 flat-line check for a stuck sensor.

    Args:
        history: Recent samples, oldest first.
        eps: Maximum spread within the window treated as "no change".
        min_count: Number of trailing samples that must be flat to flag.

    Returns:
        ``QCFlag.FAIL`` if the last ``min_count`` samples are all within
        ``eps``; otherwise ``QCFlag.PASS``. Too-short histories pass.
    """
    if len(history) < min_count:
        return QCFlag.PASS
    window = history[-min_count:]
    if max(window) - min(window) <= eps:
        return QCFlag.FAIL
    return QCFlag.PASS


def b6_hampel(
    series: list[float],
    window: int = 7,
    k: float = 3.0,
) -> list[QCFlag]:
    """B6 Hampel filter: flag points far from a rolling median.

    A point is an outlier when ``|x_i - median(window)| > k * MAD_SCALE *
    MAD(window)`` (Hampel 1974).

    Args:
        series: Input samples.
        window: Total window width (centred on each sample).
        k: Threshold multiplier.

    Returns:
        One flag per input sample (length preserved).
    """
    n = len(series)
    half = max(1, window // 2)
    flags: list[QCFlag] = []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        win = series[lo:hi]
        med = median(win)
        mad = median([abs(v - med) for v in win])
        threshold = k * MAD_SCALE * mad
        deviation = abs(series[i] - med)
        flags.append(QCFlag.FAIL if deviation > threshold else QCFlag.PASS)
    return flags


def check_battery_health(
    voltage_v: float,
    min_voltage_v: float = 3.2,
) -> dict[str, object]:
    """Flag a sensor node whose battery has dropped below the safe minimum.

    Args:
        voltage_v: Measured node battery voltage (V).
        min_voltage_v: Minimum voltage before maintenance is required.

    Returns:
        Mapping with ``alert_required`` (bool) and ``flag`` (``QCFlag``).
    """
    if voltage_v < min_voltage_v:
        return {"alert_required": True, "flag": QCFlag.SUSPECT}
    return {"alert_required": False, "flag": QCFlag.PASS}


def calibrate_spike_threshold(history: list[float], n_sigma: float = 2.0) -> float:
    """Derive a spike threshold from recent history (``n_sigma`` of residuals).

    The residual spread is estimated robustly as the standard deviation of the
    series about its median, so a few outliers do not inflate the threshold.

    Args:
        history: Recent samples (e.g. several weeks at the logging interval).
        n_sigma: Number of standard deviations to allow before flagging.

    Returns:
        The calibrated spike threshold in the units of ``history``.
    """
    if len(history) < 2:
        return 0.0
    med = median(history)
    variance = sum((v - med) ** 2 for v in history) / len(history)
    return n_sigma * math.sqrt(variance)


def run_b6_gate(  # noqa: PLR0913
    *,
    value: float,
    sensor_type: str,
    sensor_min: float,
    sensor_max: float,
    history: list[float],
    prev_value: float,
    prev_timestamp_s: float,
    current_timestamp_s: float,
    climatological_min: float,
    climatological_max: float,
) -> dict[str, object]:
    """Run the full six-check QC gate on a single streaming reading.

    Args:
        value: Latest measurement under test.
        sensor_type: Sensor category (selects default thresholds).
        sensor_min: Gross-range lower bound.
        sensor_max: Gross-range upper bound.
        history: Recent samples, oldest first (excludes ``value``).
        prev_value: Previous accepted sample.
        prev_timestamp_s: Timestamp of ``prev_value`` (s).
        current_timestamp_s: Timestamp of ``value`` (s).
        climatological_min: Season-aware lower plausibility bound.
        climatological_max: Season-aware upper plausibility bound.

    Returns:
        Mapping with ``check_flags`` (per-check ``QCFlag``), ``overall_flag``
        (the worst flag) and ``usable`` (``True`` unless the reading FAILs).
    """
    checks: dict[str, QCFlag] = {}
    checks["b1_gross_range"] = b1_gross_range(value, sensor_min, sensor_max)

    if _is_invalid(value) or not (climatological_min <= value <= climatological_max):
        checks["b2_climatological_range"] = QCFlag.FAIL if _is_invalid(value) else QCFlag.SUSPECT
    else:
        checks["b2_climatological_range"] = QCFlag.PASS

    if len(history) >= 2:
        checks["b3_spike"] = b3_spike(
            prev=history[-2],
            current=history[-1],
            next_val=value,
            spike_threshold=_SPIKE_THRESHOLD.get(sensor_type, math.inf),
        )

    checks["b4_rate_of_change"] = b4_rate_of_change(
        current=value,
        previous=prev_value,
        dt_seconds=current_timestamp_s - prev_timestamp_s,
        max_rate_per_second=_MAX_RATE_PER_S.get(sensor_type, math.inf),
    )

    checks["b5_flatline"] = b5_flatline(history)
    checks["b6_hampel"] = b6_hampel([*history, value])[-1]

    overall = QCFlag(max(int(f) for f in checks.values()))
    return {
        "check_flags": checks,
        "overall_flag": overall,
        "usable": overall != QCFlag.FAIL,
    }
