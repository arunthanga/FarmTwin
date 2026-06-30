# ADR-0001: Two-Product, One Shared Engine Architecture

**Date:** 2026-06-29  
**Status:** Accepted  
**Deciders:** Arun T. (FarmTwin founder)

## Context
FarmTwin needs two distinct user-facing products:
- **FarmTwin Studio** — offline design tool used once at install time
- **FarmTwin Runtime** — always-on operational system used daily by the farmer

Both need the same physics (GGA hydraulic solver, FAO-56 crop water, van Genuchten soil).

## Decision
Maintain a single versioned Python package (`engine/krishiflow`) shared by both products.
All physical coefficients are **live parameters** (A0 principle) — no constants frozen in solver loops.
Runtime continuously estimates and writes back calibrated parameters to the shared core.

## Consequences
- **Good:** Single source of physical truth; calibration improvements flow to both products.
- **Good:** Avoids solver drift between design and operational models.
- **Bad:** Both products must pin the same engine version; semver discipline required.
- **Mitigation:** `pyproject.toml` pins the engine; CI tests both products against it.
