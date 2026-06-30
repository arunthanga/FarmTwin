#!/usr/bin/env python3
"""Generate regression test baselines.

Run this script after any validated change to the solver to regenerate
the golden output files in engine/tests/baselines/.

Usage:
    cd <repo-root>
    python scripts/generate_baselines.py [--all | --solver | --fao56]
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

BASELINES_DIR = Path("engine/tests/baselines")


def generate_solver_baseline() -> None:
    """Generate pilot two-zone network GGA baseline."""
    print("Generating solver baseline...")
    # Placeholder — replace with actual solver call once implemented
    baseline = {
        "_note": "Regenerate with: python scripts/generate_baselines.py --solver",
        "system_flow_m3s": 0.00222,
        "min_eu_pct": 85.0,
        "pump_duty_q_m3s": 0.00222,
        "pump_duty_h_m": 25.6,
    }
    out = BASELINES_DIR / "pilot_two_zone_baseline.json"
    out.write_text(json.dumps(baseline, indent=2))
    print(f"  Written: {out}")


def generate_fao56_baseline() -> None:
    """Generate 30-day June Palakkad ET₀ baseline."""
    print("Generating FAO-56 baseline...")
    baseline = {
        "_note": "Regenerate with: python scripts/generate_baselines.py --fao56",
        "cumulative_et0_mm": 168.0,
        "dr_initial_mm": 40.0,
        "daily_inputs": []  # populated by NASA POWER fetch in production
    }
    out = BASELINES_DIR / "fao56_june_palakkad_baseline.json"
    out.write_text(json.dumps(baseline, indent=2))
    print(f"  Written: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate FarmTwin regression baselines")
    parser.add_argument("--all",    action="store_true", help="Generate all baselines")
    parser.add_argument("--solver", action="store_true", help="GGA solver baseline only")
    parser.add_argument("--fao56",  action="store_true", help="FAO-56 baseline only")
    args = parser.parse_args()

    if args.all or args.solver:
        generate_solver_baseline()
    if args.all or args.fao56:
        generate_fao56_baseline()
    if not any([args.all, args.solver, args.fao56]):
        print("Use --all, --solver, or --fao56. Run with -h for help.")


if __name__ == "__main__":
    main()
