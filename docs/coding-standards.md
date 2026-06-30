# FarmTwin — Coding Standards

**Version:** 1.0.0  
**Date:** 2026-06-29  
**Enforced by:** Ruff (Python), clang-tidy (C/C++), ESLint (JS/React Native)  
**Auto-fixed by:** AI code-review bot on every PR (see `.github/workflows/ci.yml`)

---

## Table of Contents

1. [Guiding Principles](#1-guiding-principles)
2. [Python Standards (FarmTwin, cloud, edge Python glue)](#2-python-standards)
3. [C Standards (solver cores — libFarmTwin, MOC, Richards, Surface)](#3-c-standards)
4. [C++ Standards (edge decision engine)](#4-c-standards-c)
5. [JavaScript / React Native Standards (Studio survey app, farmer PWA)](#5-javascript--react-native-standards)
6. [Test Code Standards](#6-test-code-standards)
7. [Documentation Standards](#7-documentation-standards)
8. [Git & Commit Standards](#8-git--commit-standards)
9. [Numeric / Scientific Code Standards](#9-numeric--scientific-code-standards)
10. [Security Standards](#10-security-standards)
11. [Tool Configuration Reference](#11-tool-configuration-reference)

---

## 1. Guiding Principles

These are the three rules that every other rule below serves:

**P1 — Physics first, style second.** A formula that matches a white-paper equation is more valuable than one that is "prettier." Prefer clarity of physics over code cleverness. Cite the reference when you write the equation.

**P2 — No frozen constants.** Every physical coefficient that appears in the engine must be a named, documented parameter in a ParameterSet — never a bare literal. This is the A0 principle from doc 12.

**P3 — Fail loudly, fail early.** Solvers must raise meaningful exceptions (not return NaN or silently produce garbage) when inputs are out of range, convergence fails, or QC gates reject data.

---

## 2. Python Standards

### 2.1 Linter / Formatter

Tool: **Ruff** (replaces flake8, isort, pyupgrade, pydocstyle in one binary).  
Config: `pyproject.toml` → `[tool.ruff]` section (see §11).

All Ruff rules enforced on CI; auto-fix applied by AI bot where `--fix` is safe. Remaining issues raised as PR comments asking the developer to resolve.

### 2.2 Style Rules

**Imports**
```python
# Standard library first, then third-party, then local — separated by blank lines.
# CORRECT
import math
import os
from pathlib import Path

import numpy as np
from scipy.sparse.linalg import spsolve

from FarmTwin.params import ParameterSet

# WRONG — mixed order, wildcard import
from FarmTwin.solver import *
import numpy as np, math
```

**Type annotations — required on all public functions**
```python
# CORRECT
def hazen_williams(
    flow_m3s: float,
    diameter_m: float,
    length_m: float,
    c_factor: float,
) -> float:
    """Return head loss [m] via Hazen-Williams (n=1.852).

    Reference: Rossman (2000) EPANET 2 Manual, eq. 3-1.
    """
    ...

# WRONG — no types, no docstring
def hw(q, d, l, c):
    ...
```

**Maximum line length:** 100 characters.

**No bare `except`:**
```python
# CORRECT
try:
    result = solver.solve(network)
except ConvergenceError as exc:
    raise SolverError(f"GGA did not converge after {exc.iterations} iterations") from exc

# WRONG
try:
    result = solver.solve(network)
except:
    pass
```

**f-strings over `.format()` and `%`:**
```python
# CORRECT
raise ValueError(f"Pipe diameter {diameter_m:.4f} m outside catalogue range [0.01, 0.5] m")

# WRONG
raise ValueError("Pipe diameter %.4f m outside range" % diameter_m)
```

**Constants must be named and live in `params.py` or a module-level `__all__`-excluded `_CONST` block:**
```python
# CORRECT — named, documented
GRAVITY_MS2: float = 9.81          # gravitational acceleration [m/s²]
WATER_DENSITY_KGM3: float = 1000.0 # water density at 20°C [kg/m³]

# WRONG — bare literal
h_loss = 10.67 * length / (120**1.852 * 0.05**4.87)  # magic numbers
```

**Physical equations must cite the white-paper reference in the docstring or inline comment:**
```python
def penman_monteith_et0(
    t_mean_c: float,
    rn_mjm2d: float,
    ...
) -> float:
    """Compute FAO-56 Penman-Monteith reference ET₀ [mm/day].

    Implements eq. 6 from:
      Allen et al. (1998) FAO Irrigation & Drainage Paper 56, Chapter 2.
      ASCE-EWRI (2005) Standardized Reference ET, eq. 1 (Cn=900, Cd=0.34).
    """
    # eq. 6: ET0 = [0.408·Δ·(Rn-G) + γ·(900/(T+273))·u2·(es-ea)] / [Δ + γ·(1+0.34·u2)]
    ...
```

### 2.3 Naming Conventions

| Entity | Convention | Example |
|---|---|---|
| Module | `snake_case` | `head_loss.py` |
| Class | `PascalCase` | `GGASolver`, `ParameterSet` |
| Function / method | `snake_case` | `solve_network()` |
| Variable | `snake_case` | `head_loss_m` |
| Physical variable | `snake_case` with unit suffix | `flow_m3s`, `pressure_pa`, `length_m` |
| Constant | `UPPER_SNAKE_CASE` | `GRAVITY_MS2` |
| Private | leading underscore | `_assemble_a11()` |
| Test function | `test_<what>_<condition>` | `test_hazen_williams_zero_flow_returns_zero` |

**Unit suffixes are mandatory** on all physical variables:

| Quantity | Suffix | Example |
|---|---|---|
| metres | `_m` | `diameter_m` |
| m³/s | `_m3s` | `flow_m3s` |
| L/h | `_lh` | `emitter_flow_lh` |
| Pascals | `_pa` | `pressure_pa` |
| kPa | `_kpa` | `inlet_pressure_kpa` |
| mm/day | `_mmd` | `et0_mmd` |
| m head | `_mh` | `head_loss_mh` |
| °C | `_c` | `temp_c` |
| MJ/m²/day | `_mjm2d` | `rn_mjm2d` |

### 2.4 Complexity Limits

| Metric | Limit | Ruff rule |
|---|---|---|
| Cyclomatic complexity | ≤ 10 per function | `C901` |
| Lines per function | ≤ 60 | `PLR0915` |
| Arguments per function | ≤ 8 | `PLR0913` |
| Nesting depth | ≤ 4 | `C901` |

Scientific kernels (GGA inner loop, Modified Picard) may exceed line-count with documented justification in the PR.

### 2.5 Docstring Format — Google style

```python
def van_genuchten_theta(
    psi_m: float,
    alpha: float,
    n: float,
    theta_r: float,
    theta_s: float,
) -> float:
    """Compute volumetric water content θ from matric head ψ.

    Uses the van Genuchten (1980) retention curve.
    Reference: van Genuchten (1980) SSSAJ 44(5):892-898, eq. 3.

    Args:
        psi_m: Matric head [m], negative for unsaturated (suction).
        alpha: van Genuchten α parameter [1/m].
        n: van Genuchten n parameter [-], n > 1.
        theta_r: Residual volumetric water content [m³/m³].
        theta_s: Saturated volumetric water content [m³/m³].

    Returns:
        Volumetric water content θ [m³/m³].

    Raises:
        ValueError: If n ≤ 1 or alpha ≤ 0 or theta_r ≥ theta_s.
    """
```

---

## 3. C Standards

Applied to: `libFarmTwin` (GGA C core), MOC transient, zero-inertia surface, Richards solver.

### 3.1 Linter

Tool: **clang-tidy** with checks: `clang-diagnostic-*, cppcoreguidelines-*, readability-*, performance-*, bugprone-*`.  
Formatter: **clang-format** (style: `{BasedOnStyle: LLVM, IndentWidth: 4, ColumnLimit: 100}`).

### 3.2 Style Rules

**C standard:** C11 (`-std=c11`). No compiler extensions unless guarded by `#ifdef`.

**Naming:**

| Entity | Convention | Example |
|---|---|---|
| File | `snake_case.c` / `.h` | `gga_solver.c` |
| Function | `module_verb_noun` | `gga_solve_network()` |
| Struct | `PascalCase` + `_t` typedef | `typedef struct GgaNetwork GgaNetwork_t;` |
| Enum | `UPPER_SNAKE_CASE` | `LINK_TYPE_PIPE` |
| Macro constant | `FARMTWIN_UPPER` | `FARMTWIN_GRAVITY_MS2` |
| Local variable | `snake_case` + unit suffix | `head_loss_mh` |
| Parameter | same as local | `flow_m3s` |

**No global mutable state.** All solver state lives in an explicitly passed context struct.

**Every public function must validate its inputs and return an error code:**
```c
typedef enum {
    FARMTWIN_OK = 0,
    FARMTWIN_ERR_NULL_PTR,
    FARMTWIN_ERR_CONVERGENCE,
    FARMTWIN_ERR_SINGULAR,
    FARMTWIN_ERR_OUT_OF_RANGE,
} FarmTwinError;

/**
 * Compute Hazen-Williams head loss.
 *
 * Reference: Rossman (2000) EPANET 2 Manual, eq. 3-1.
 *
 * @param flow_m3s   Volumetric flow rate [m³/s]; may be negative.
 * @param diameter_m Pipe internal diameter [m]; must be > 0.
 * @param length_m   Pipe length [m]; must be > 0.
 * @param c_factor   Hazen-Williams C coefficient [-]; must be > 0.
 * @param[out] head_loss_mh Head loss [m]; sign follows flow direction.
 * @return FARMTWIN_OK on success, error code otherwise.
 */
FarmTwinError gga_hazen_williams(
    double flow_m3s,
    double diameter_m,
    double length_m,
    double c_factor,
    double *head_loss_mh);
```

**No dynamic allocation in the hot solver loop.** Pre-allocate all working arrays in the context struct during `*_create()`. Use arena allocators for temporary scratch.

**Memory ownership is explicit:** every `*_create()` has a matching `*_destroy()`. No raw `malloc/free` outside these pairs.

**Convergence failures must set a descriptive error string, not just an error code:**
```c
if (iter >= max_iterations) {
    snprintf(ctx->error_msg, FARMTWIN_ERR_MSG_LEN,
             "GGA did not converge after %d iterations; "
             "max |dQ|/|Q| = %.3e (tol = %.3e)",
             max_iterations, residual, ctx->params.convergence_tol);
    return FARMTWIN_ERR_CONVERGENCE;
}
```

**Physical constants as `static const double`:**
```c
static const double GRAVITY_MS2      = 9.81;
static const double WATER_DENSITY    = 1000.0;
static const double HW_EXPONENT      = 1.852;   /* Hazen-Williams n */
static const double ZERO_FLOW_EPS    = 1.0e-6;  /* Elhay-Simpson regularization threshold [m³/s] */
```

**Cite the equation in the comment above the implementation:**
```c
/* GGA two-step Newton-Raphson update (Todini & Pilati 1988, eq. 11-12):
 *   A21 G^-1 A12 H = A21 G^-1 (A11 Q + A10 H0) + (q - A21 Q)
 *   Q <- Q - G^-1 (A11 Q + A10 H0 + A12 H)
 */
```

### 3.3 Compilation Flags (mandatory)

```makefile
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Wshadow -Wdouble-promotion \
         -Wformat=2 -Wnull-dereference -fstack-protector-strong \
         -D_FORTIFY_SOURCE=2
# Release: add -O2 -DNDEBUG
# Debug:   add -g -fsanitize=address,undefined
```

---

## 4. C++ Standards (Edge Decision Engine)

Applied to: `engine/edge/` C++17 runtime.

Standard: **C++17** (`-std=c++17`). Linter: **clang-tidy** with `modernize-*` checks. Formatter: **clang-format** same config as C.

Additional rules beyond C:

- Prefer `std::unique_ptr` / `std::shared_ptr` over raw pointers.
- Use `[[nodiscard]]` on all functions returning error codes or results.
- RAII for all resources — no manual `delete` outside destructors.
- Use `std::optional<T>` for functions that may have no result rather than sentinel values.
- No exceptions in the real-time decision loop; use `std::expected<T,E>` (C++23) or a Result type.
- Mark every thread-safe function `// THREAD-SAFE`; every non-thread-safe function `// NOT THREAD-SAFE`.

---

## 5. JavaScript / React Native Standards

Applied to: `studio-app/` (React Native survey app), `cloud/dashboard/` (farmer PWA).

Linter: **ESLint** with `eslint-config-airbnb` + `eslint-plugin-react` + `typescript-eslint`.  
Formatter: **Prettier** (`printWidth: 100, singleQuote: true, trailingComma: 'all'`).

**TypeScript required** — no plain `.js` files in `studio-app/` or `dashboard/`.

**Naming:**

| Entity | Convention | Example |
|---|---|---|
| Component | `PascalCase` | `ZoneMoistureBar` |
| Hook | `use` + `PascalCase` | `useFarmStatus` |
| File | `kebab-case` | `zone-moisture-bar.tsx` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_ZONES` |
| API response type | `PascalCase` + `Dto` | `FarmStatusDto` |

**No `any` types.** Use `unknown` + type guard if the type is genuinely unknown.

**All user-facing strings must go through the i18n system** (`i18next`) — no hardcoded English strings in JSX:
```tsx
// CORRECT
<Text>{t('farm.status.irrigating', { zone: 2, remaining: '40 min' })}</Text>

// WRONG
<Text>Irrigating Zone 2 — 40 min remaining</Text>
```

**Accessibility:** every interactive element must have an `accessibilityLabel` prop.

---

## 6. Test Code Standards

### 6.1 TDD Workflow Switch

The TDD mode is controlled by the environment variable `FARMTWIN_TDD_MODE`:

```bash
# Enable TDD mode — tests run FIRST; product code is expected to fail initially
export FARMTWIN_TDD_MODE=on

# Disable TDD mode — tests and product code run together (integration/regression mode)
export FARMTWIN_TDD_MODE=off   # default
```

In CI, the `test-tdd` job always runs with `FARMTWIN_TDD_MODE=on` and **expects test failures** in the `tdd-stubs` branch. The `test-regression` job always runs with `FARMTWIN_TDD_MODE=off` and **expects all tests to pass** on `master`. See `.github/workflows/ci.yml`.

The TDD switch is also respected by `conftest.py`:
```python
# In conftest.py
TDD_MODE = os.getenv("FARMTWIN_TDD_MODE", "off").lower() == "on"
```

### 6.2 Python Test Rules (pytest)

- Test file: `tests/test_<module>.py`
- Test class: `Test<ClassOrBehaviour>` (optional; prefer module-level functions for simple cases)
- Test function: `test_<what>_<given_condition>_<expected_result>`

```python
# CORRECT naming
def test_hazen_williams_zero_flow_returns_zero():
    assert head_loss(flow_m3s=0.0, ...) == pytest.approx(0.0, abs=1e-12)

def test_gga_two_reservoir_matches_analytic():
    """Validation: H_J = 90.0 m (see engine/tests/test_solver.py)."""
```

- **Each test must document its reference** (white paper, analytic formula, or regression baseline) in the docstring.
- **Numeric tolerances must be justified:** `pytest.approx(x, rel=1e-4)` not `== x`.
- **No test may depend on another test's side effects.** Every test is independent.
- **Parameterize instead of copying:**
```python
@pytest.mark.parametrize("c_factor,expected_mh", [
    (150, 3.21),
    (100, 5.47),
    (80,  8.14),
])
def test_hazen_williams_c_factor_sweep(c_factor, expected_mh):
    ...
```

### 6.3 C Test Rules (Unity framework)

- Test file: `tests/c/test_<module>.c`
- Test function: `test_<module>_<behaviour>(void)`
- Every test that checks a solver result must print the expected vs actual value on failure.

---

## 7. Documentation Standards

- Every public API (Python function, C function, REST endpoint) must have a docstring/Doxygen comment before merge.
- Every solver equation in code must cite its reference (author, year, equation number).
- New design decisions must be recorded in the relevant `engine/docs/` markdown file and the changelog.
- The `requirements.md` is the single source of truth — code that contradicts it requires an approved PR updating `requirements.md` first.

---

## 8. Git & Commit Standards

**Branch naming:**
```
feature/<ticket>-short-description
fix/<ticket>-short-description
tdd/<ticket>-failing-tests-for-<module>
```

**Commit messages — Conventional Commits format:**
```
<type>(<scope>): <short description>

[optional body — what and why, not how]

[optional footer: Fixes #123, Refs doc-12]
```

Types: `feat`, `fix`, `test`, `docs`, `refactor`, `perf`, `ci`, `chore`.  
Scope: `solver`, `fao56`, `richards`, `surface`, `moc`, `iot`, `studio`, `cloud`, `schema`.

Examples:
```
feat(solver): add Elhay-Simpson zero-flow regularization to GGA

Fixes singular gradient matrix at near-zero flows in drip laterals.
Refs: Elhay & Simpson (2011) doi:10.1061/(ASCE)HY.1943-7900.0000411

test(fao56): add TDD stubs for dual crop coefficient Ke soil balance

All assertions intentionally fail until fao56.py Ke path is implemented.
FARMTWIN_TDD_MODE=on required to run.
```

**No force-push to `master` or `develop`.** All changes via PR.  
**PR must pass all CI checks** before merge. AI bot auto-fixes Ruff/clang-format issues; remaining failures block the merge.

---

## 9. Numeric / Scientific Code Standards

These rules are specific to the physics engine and have no equivalent in general software standards.

**N1 — Mass conservation check after every solver run.**  
The GGA post-processor must verify that total inflow = total outflow ± ε (default 0.1 L/h). Fail loudly if not.

**N2 — Dimensional consistency.**  
All internal computations use SI (m, m³/s, Pa, K, s). Conversions happen only at input (pre-processor) and output (post-processor). Never convert mid-calculation.

**N3 — Regularization must be documented and switchable.**  
Elhay-Simpson Q → 0 regularization, Celia mass-lumping, and any other numerical stabilizations must be:  
(a) documented with the reference,  
(b) controlled by a named parameter in ParameterSet,  
(c) tested both ON and OFF.

**N4 — Convergence criteria must be explicit and logged.**  
Every iterative solver (GGA, Modified Picard, EnKF) must log the final residual norm and number of iterations at `DEBUG` level. Never silently accept a non-converged result.

**N5 — Validation against published analytic or benchmark results.**  
Every solver module must include at least one test against a known analytic result or a published benchmark (EPANET test networks, HYDRUS-1D test problems, WinSRFR benchmarks). The reference for the expected value must be cited in the test docstring.

**N6 — No implicit unit conversion in function signatures.**  
If a function takes `flow_m3s` and internally needs L/h, do the conversion inside with a named constant — never pass a pre-converted value from the call site without a comment.

---

## 10. Security Standards

**S1 — No secrets in code.** API keys, passwords, LoRaWAN AppKeys, and MQTT credentials are loaded from environment variables or a secrets manager (AWS Secrets Manager / HashiCorp Vault). Never committed to git. CI uses `FARMTWIN_*` environment variable names; see `.env.example`.

**S2 — All external inputs validated at ingestion.** The B6 QC gate applies to sensor data. JSON schema validation (jsonschema) applies to all network topology, survey, and configuration inputs. Reject and log; never propagate invalid data to solvers.

**S3 — LoRaWAN per-device AES-128 OTAA keys; MQTT TLS 1.3.** No plain-text IoT communication outside the lab.

**S4 — Signed OTA firmware.** Edge controller and field node firmware images are signed with a project-specific ED25519 key; the bootloader verifies before flash.

---

## 11. Tool Configuration Reference

### pyproject.toml (Ruff + pytest)

```toml
[tool.ruff]
target-version = "py311"
line-length = 100
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "C90",  # mccabe complexity
    "PL",   # pylint
    "PT",   # flake8-pytest-style
    "SIM",  # flake8-simplify
    "D",    # pydocstyle
    "ANN",  # flake8-annotations
    "S",    # flake8-bandit (security)
]
ignore = [
    "D203",  # one-blank-line-before-class (conflicts with D211)
    "D212",  # multi-line-summary-first-line (conflicts with D213)
    "ANN101","ANN102",  # self/cls annotation not required
]
fixable = ["E", "W", "F", "I", "UP", "C4", "SIM"]

[tool.ruff.mccabe]
max-complexity = 10

[tool.ruff.pydocstyle]
convention = "google"

[tool.pytest.ini_options]
testpaths = ["engine/tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: unit tests (fast, no I/O)",
    "regression: regression tests against stored baselines",
    "tdd: TDD stubs — expected to fail until product code is written",
    "integration: integration tests (may use network/files)",
    "benchmark: performance benchmarks (slow)",
]
filterwarnings = ["error"]
```

### .clang-format

```yaml
---
BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
AllowShortFunctionsOnASingleLine: None
AllowShortIfStatementsOnASingleLine: Never
AlwaysBreakAfterReturnType: None
BreakBeforeBraces: Attach
SortIncludes: true
SpaceAfterCStyleCast: false
```

### .clang-tidy

```yaml
Checks: >-
  clang-diagnostic-*,
  cppcoreguidelines-*,
  readability-*,
  performance-*,
  bugprone-*,
  modernize-*,
  -readability-magic-numbers,
  -cppcoreguidelines-avoid-magic-numbers,
  -modernize-use-trailing-return-type
WarningsAsErrors: "*"
HeaderFilterRegex: ".*FarmTwin.*"
```

### .eslintrc.js (React Native / PWA)

```js
module.exports = {
  extends: [
    'airbnb',
    'airbnb/hooks',
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/recommended-requiring-type-checking',
    'prettier',
  ],
  rules: {
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/explicit-function-return-type': 'warn',
    'react/require-default-props': 'error',
    'import/order': ['error', { 'newlines-between': 'always' }],
  },
};
```

---

*End of coding-standards.md — version 1.0.0*
