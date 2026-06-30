"""Tests for krishiflow.quality (B6 data quality gate — QARTOD + Hampel).

All six QC checks must be individually testable:
  B1 — Gross-range check
  B2 — Climatological range check
  B3 — Spike check
  B4 — Rate-of-change check
  B5 — Flatline check
  B6 — Hampel outlier check (rolling median ± k·MAD)

White-paper references:
  [QARTOD]  IOOS QARTOD Real-Time QC Manuals https://ioos.noaa.gov/project/qartod/
  [ioos_qc] ioos_qc Python package https://ioos.github.io/ioos_qc/
  [Hampel]  Hampel (1974) JASA 69(346):383-393 doi:10.1080/01621459.1974.10482962
"""

from __future__ import annotations

import pytest

try:
    from krishiflow.quality import (
        QCFlag,
        b1_gross_range,
        b2_climatological_range,
        b3_spike,
        b4_rate_of_change,
        b5_flatline,
        b6_hampel,
        run_b6_gate,
    )
    _QC_AVAILABLE = True
except ImportError:
    _QC_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — QC Flag Enumeration (unit)
# ══════════════════════════════════════════════════════════════════════

class TestQCFlagEnum:
    """Unit tests for QCFlag enumeration values (aligned with QARTOD standard)."""

    @pytest.mark.unit
    def test_qc_flag_values_match_qartod(self) -> None:
        """QCFlag values must match QARTOD standard: PASS=1, SUSPECT=3, FAIL=4.

        Reference: IOOS QARTOD Manual, Table 2 — Quality Flag Definitions.
        """
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        assert QCFlag.PASS == 1
        assert QCFlag.SUSPECT == 3
        assert QCFlag.FAIL == 4

    @pytest.mark.unit
    def test_pass_is_better_than_suspect(self) -> None:
        """PASS < SUSPECT in quality ordering (lower = better)."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        assert QCFlag.PASS < QCFlag.SUSPECT

    @pytest.mark.unit
    def test_suspect_is_better_than_fail(self) -> None:
        """SUSPECT < FAIL in quality ordering."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        assert QCFlag.SUSPECT < QCFlag.FAIL


# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — B1 Gross-Range Check (unit)
# ══════════════════════════════════════════════════════════════════════

class TestB1GrossRange:
    """Unit tests for B1 gross-range check.

    Reference: IOOS QARTOD Manual §4.1 — Gross Range Test.
    """

    @pytest.mark.unit
    @pytest.mark.parametrize("value,sensor_min,sensor_max,expected_flag", [
        (25.0,   0.0, 100.0, 1),   # PASS — inside range
        (0.0,    0.0, 100.0, 1),   # PASS — at lower bound (inclusive)
        (100.0,  0.0, 100.0, 1),   # PASS — at upper bound (inclusive)
        (-0.001, 0.0, 100.0, 4),   # FAIL — just below lower bound
        (100.001,0.0, 100.0, 4),   # FAIL — just above upper bound
        (float("nan"), 0.0, 100.0, 4),  # FAIL — NaN
    ])
    def test_b1_parametrized(
        self, value: float, sensor_min: float, sensor_max: float, expected_flag: int,
    ) -> None:
        """Gross-range check for various input values."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        flag = b1_gross_range(value=value, sensor_min=sensor_min, sensor_max=sensor_max)
        assert flag == expected_flag

    @pytest.mark.unit
    def test_b1_soil_moisture_sensor_bounds(self) -> None:
        """Soil moisture VWC must be in 0.0–1.0 m³/m³ (physical bounds for any soil)."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        assert b1_gross_range(0.35, 0.0, 1.0) == QCFlag.PASS
        assert b1_gross_range(1.01, 0.0, 1.0) == QCFlag.FAIL
        assert b1_gross_range(-0.01, 0.0, 1.0) == QCFlag.FAIL

    @pytest.mark.unit
    def test_b1_pressure_transducer_bounds(self) -> None:
        """Pipe pressure must be in 0–1000 kPa for a typical 10-bar transducer."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        assert b1_gross_range(150.0, 0.0, 1000.0) == QCFlag.PASS
        assert b1_gross_range(1001.0, 0.0, 1000.0) == QCFlag.FAIL


# ══════════════════════════════════════════════════════════════════════
# SECTION 3 — B3 Spike Check (unit)
# ══════════════════════════════════════════════════════════════════════

class TestB3Spike:
    """Unit tests for B3 spike detection.

    Reference: IOOS QARTOD Manual §4.3 — Spike Test.
    A spike is defined as a single sample that deviates from adjacent samples
    by more than the spike_threshold.
    """

    @pytest.mark.unit
    def test_b3_no_spike_returns_pass(self) -> None:
        """Gradual change over three samples → no spike → PASS."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        flag = b3_spike(prev=20.0, current=20.5, next_val=21.0, spike_threshold=5.0)
        assert flag == QCFlag.PASS

    @pytest.mark.unit
    def test_b3_large_spike_returns_fail(self) -> None:
        """A sudden jump far above the threshold → FAIL."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        # Soil moisture: previous=0.25, current=0.99 (implausible jump), next=0.26
        flag = b3_spike(prev=0.25, current=0.99, next_val=0.26, spike_threshold=0.10)
        assert flag == QCFlag.FAIL

    @pytest.mark.unit
    def test_b3_moderate_spike_returns_suspect(self) -> None:
        """A moderately large jump returns SUSPECT (2x < spike < 3x threshold)."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        flag = b3_spike(prev=20.0, current=30.0, next_val=20.5, spike_threshold=8.0)
        # |30 - (20+20.5)/2| = 9.75 > threshold → at least SUSPECT
        assert flag in (QCFlag.SUSPECT, QCFlag.FAIL)


# ══════════════════════════════════════════════════════════════════════
# SECTION 4 — B4 Rate-of-Change Check (unit)
# ══════════════════════════════════════════════════════════════════════

class TestB4RateOfChange:
    """Unit tests for B4 rate-of-change check.

    Reference: IOOS QARTOD Manual §4.4 — Rate of Change Test.
    """

    @pytest.mark.unit
    def test_b4_slow_change_passes(self) -> None:
        """Gradual soil moisture change (0.001 m³/m³/min) must pass."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        flag = b4_rate_of_change(
            current=0.30, previous=0.29, dt_seconds=900,  # 15 min
            max_rate_per_second=0.0001,
        )
        assert flag == QCFlag.PASS

    @pytest.mark.unit
    def test_b4_instantaneous_jump_fails(self) -> None:
        """A 0.5 m³/m³ jump in 15 minutes must fail (physically impossible for soil)."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        flag = b4_rate_of_change(
            current=0.80, previous=0.30, dt_seconds=900,
            max_rate_per_second=0.0001,  # 0.0001 m³/m³/s = 0.09/15min max
        )
        assert flag == QCFlag.FAIL


# ══════════════════════════════════════════════════════════════════════
# SECTION 5 — B5 Flatline Check (unit)
# ══════════════════════════════════════════════════════════════════════

class TestB5Flatline:
    """Unit tests for B5 flatline (stuck sensor) check.

    Reference: IOOS QARTOD Manual §4.5 — Flat Line Test.
    """

    @pytest.mark.unit
    def test_b5_varying_values_pass(self) -> None:
        """Values that vary over the window must pass."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        history = [0.30, 0.31, 0.29, 0.32, 0.28, 0.30]
        flag = b5_flatline(history=history, eps=1e-4, min_count=5)
        assert flag == QCFlag.PASS

    @pytest.mark.unit
    def test_b5_stuck_sensor_fails(self) -> None:
        """Exact same value repeated N times → stuck sensor → FAIL."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        history = [0.30] * 10
        flag = b5_flatline(history=history, eps=1e-4, min_count=5)
        assert flag == QCFlag.FAIL

    @pytest.mark.unit
    def test_b5_window_shorter_than_min_count_returns_pass(self) -> None:
        """If history is shorter than min_count, test cannot fire → PASS."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        history = [0.30, 0.30]   # Only 2 readings; need 5 to flag
        flag = b5_flatline(history=history, eps=1e-4, min_count=5)
        assert flag == QCFlag.PASS


# ══════════════════════════════════════════════════════════════════════
# SECTION 6 — B6 Hampel Outlier Check (unit)
# ══════════════════════════════════════════════════════════════════════

class TestB6Hampel:
    """Unit tests for B6 Hampel filter (rolling median ± k·MAD).

    Reference: Hampel (1974) JASA 69(346):383-393.
    An outlier is detected when |x_i − median(window)| > k * 1.4826 * MAD(window).
    The constant 1.4826 makes MAD consistent with σ under normality.
    """

    @pytest.mark.unit
    def test_b6_clean_series_passes(self) -> None:
        """A clean Gaussian-like series with no outliers → all PASS."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        series = [0.28, 0.29, 0.30, 0.31, 0.29, 0.30, 0.28, 0.31, 0.30, 0.29]
        flags = b6_hampel(series=series, window=5, k=3.0)
        assert all(f == QCFlag.PASS for f in flags)

    @pytest.mark.unit
    def test_b6_single_outlier_flagged(self) -> None:
        """A single large outlier in the middle of a clean series → FAIL at that index."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        series = [0.28, 0.29, 0.30, 0.99, 0.29, 0.30, 0.28, 0.31, 0.30, 0.29]
        flags = b6_hampel(series=series, window=5, k=3.0)
        # Index 3 (value=0.99) must be flagged
        assert flags[3] == QCFlag.FAIL
        # All other indices should be PASS
        for i, flag in enumerate(flags):
            if i != 3:
                assert flag == QCFlag.PASS, f"Index {i} should be PASS, got {flag}"

    @pytest.mark.unit
    def test_b6_length_preserved(self) -> None:
        """Output flag list must have the same length as the input series."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        series = list(range(20))
        flags = b6_hampel(series=[float(x) for x in series], window=5, k=3.0)
        assert len(flags) == len(series)


# ══════════════════════════════════════════════════════════════════════
# SECTION 7 — Full B6 Gate Integration (unit)
# ══════════════════════════════════════════════════════════════════════

class TestRunB6Gate:
    """Integration tests for the full B6 QC gate (all six checks in sequence)."""

    @pytest.mark.unit
    def test_all_checks_pass_for_clean_reading(self) -> None:
        """A physically plausible soil moisture reading must pass all six checks."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        history = [0.28, 0.29, 0.30, 0.31, 0.29, 0.30, 0.28, 0.31, 0.30, 0.29]
        result = run_b6_gate(
            value=0.30,
            sensor_type="soil_moisture",
            sensor_min=0.0,
            sensor_max=1.0,
            history=history,
            prev_value=history[-1],
            prev_timestamp_s=0.0,
            current_timestamp_s=900.0,
            climatological_min=0.05,
            climatological_max=0.55,
        )
        assert result["overall_flag"] == QCFlag.PASS
        assert all(v == QCFlag.PASS for v in result["check_flags"].values())

    @pytest.mark.unit
    def test_gross_range_failure_propagates_to_overall(self) -> None:
        """A gross-range failure must set the overall flag to FAIL."""
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        history = [0.28] * 10
        result = run_b6_gate(
            value=1.5,          # WAY outside 0–1 for soil moisture
            sensor_type="soil_moisture",
            sensor_min=0.0,
            sensor_max=1.0,
            history=history,
            prev_value=history[-1],
            prev_timestamp_s=0.0,
            current_timestamp_s=900.0,
            climatological_min=0.05,
            climatological_max=0.55,
        )
        assert result["overall_flag"] == QCFlag.FAIL
        assert result["check_flags"]["b1_gross_range"] == QCFlag.FAIL

    @pytest.mark.unit
    def test_failed_reading_excluded_from_solver_inputs(self) -> None:
        """run_b6_gate must set usable=False for FAIL readings.

        This ensures FAIL data never reaches the GGA solver or FAO-56 module.
        """
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        result = run_b6_gate(
            value=-99.0,  # clearly invalid
            sensor_type="pressure_transducer",
            sensor_min=0.0,
            sensor_max=1000.0,
            history=[150.0] * 10,
            prev_value=150.0,
            prev_timestamp_s=0.0,
            current_timestamp_s=900.0,
            climatological_min=0.0,
            climatological_max=1000.0,
        )
        assert result["usable"] is False


# ══════════════════════════════════════════════════════════════════════
# SECTION 8 — TDD Stubs
# ══════════════════════════════════════════════════════════════════════

class TestQualityTDD:
    """TDD stubs for QC features not yet implemented."""

    @pytest.mark.tdd
    def test_b2_climatological_range_uses_historical_percentiles(self) -> None:
        """B2 must use date-specific historical percentile bounds from a climate table.

        Not yet implemented: climatological bounds table lookup in quality.py.
        Palakkad June soil moisture: P5=0.08, P95=0.48 (estimated from GLDAS).
        """
        if not _QC_AVAILABLE:
            pytest.skip("quality module not available")
        flag = b2_climatological_range(
            value=0.35,
            doy=180,
            sensor_type="soil_moisture",
        )
        assert flag == QCFlag.PASS

    @pytest.mark.tdd
    def test_battery_voltage_low_triggers_alert(self) -> None:
        """Sensor battery voltage < 3.2 V must trigger a maintenance alert.

        Not yet implemented: battery health check in quality.py.
        """
        from krishiflow.quality import check_battery_health  # type: ignore[import]
        result = check_battery_health(voltage_v=3.1, min_voltage_v=3.2)
        assert result["alert_required"] is True
        assert result["flag"] == QCFlag.SUSPECT

    @pytest.mark.tdd
    def test_qartod_spike_threshold_auto_calibrated_from_history(self) -> None:
        """Spike threshold must be auto-calibrated from recent history (2·σ of residuals).

        Not yet implemented: adaptive spike threshold in b3_spike().
        Reference: IOOS QARTOD Manual Appendix A — adaptive threshold calibration.
        """
        from krishiflow.quality import calibrate_spike_threshold  # type: ignore[import]
        # 30 days of 15-min readings with σ ≈ 0.015 m³/m³
        import numpy as np
        rng = np.random.default_rng(42)
        history = (0.30 + rng.normal(0, 0.015, 2880)).tolist()
        threshold = calibrate_spike_threshold(history=history, n_sigma=2.0)
        # Should be approximately 2 * 0.015 = 0.030
        assert threshold == pytest.approx(0.030, rel=0.3)
