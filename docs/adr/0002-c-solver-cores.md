# ADR-0002: Solver Cores Implemented in C

**Date:** 2026-06-29  
**Status:** Accepted  

## Context
The GGA solver inner loop (sparse Cholesky, repeated 5–20 Newton iterations) and Richards solver
(tridiagonal Modified Picard per zone per time step) must run on a Raspberry Pi 4 edge controller.
Python/NumPy has 3–5× overhead versus compiled C at this scale.

## Decision
Implement GGA, MOC transient, zero-inertia surface, and Richards as C11 libraries (`libkrishiflow.so`).
Expose via `cffi` Python bindings. Python callers (Studio, cloud twin) use the same `.so`.

## Consequences
- **Good:** GGA 500-node solve < 50 ms on RPi 4 (vs ~300 ms Python).
- **Good:** C library callable from C++ edge runtime without Python runtime overhead.
- **Bad:** C code harder to prototype; more CI infrastructure needed (clang-tidy, sanitizers).
- **Mitigation:** Python MVP version stays in `krishiflow/` as reference; C ports validated against it.
