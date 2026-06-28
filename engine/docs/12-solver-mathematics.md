# 12 — Solver Mathematics (deep dive per solver)

This document gives the governing equations, numerical schemes, and key references for
each KrishiFlow solver, and maps every part to a module in `engine/krishiflow`. It
builds on the method-selection rationale in
[10-numerical-methods-and-architecture.md](10-numerical-methods-and-architecture.md).

Contents: A0 live-parametrization principle · A1 GGA (network) · A2 MOC (transients) ·
A3 zero-inertia Saint-Venant (surface) · A4 Richards (soil) · A5 FAO-56/ASCE (ET) ·
A6 OpenFOAM component CFD · A7 pointer to the optimizer.

---

## A0. Design principle — everything is a live parameter (no frozen constants)

The solver and agronomy models are **deliberately over-parametrized**: every physical
coefficient and modeling assumption is an externally supplied, named, versioned
parameter — never a hard-coded constant. The parameters and assumptions are **expected
to keep changing with real-time data**, and each change makes predictions more
accurate. This is the intended behavior, not drift.

Each parameter carries a prior, a current estimate, an uncertainty, and a source tag:

```
param := { name, value, prior, uncertainty(sigma), source(lit|mfr|field), updated_at, version }
solvers/models take a ParameterSet, NOT literals  ->  any value can be overridden by real-time data
```

Parametrize at least the following (each updatable from the live data source shown):

| Module | Parameter(s) | Updated by (real-time data) |
| --- | --- | --- |
| GGA pipes (A1) | Hazen-Williams C / Darcy roughness e | flow + pressure residuals (aging) |
| Minor losses | K (bends/elbows/tees/valves/filters) | pressure across fittings / filter (clog) |
| Emitters | k, exponent x, PC band, clog factor | emitter/zone flow vs pressure |
| Pump | curve coeffs (a,b,c), efficiency | pump pressure/flow, power draw |
| Valves | Cv / loss vs position | valve position + dP |
| Demand / leak | nodal demand, background leakage | flow balance, night-flow |
| FAO-56 (A5) | Kcb, Ke (Kr, few, Kcmax), p (MAD), TAW/RAW | soil-moisture + ET residuals |
| FAO-56 inputs | ET0 input bias offsets | AWS vs forecast comparison |
| Richards (A4) | van Genuchten alpha, n, theta_r/s, Ks | soil-moisture profiles |
| Surface (A3) | Kostiakov-Lewis k, a, b ; Manning n | advance/recession + volume balance |
| Transient (A2) | wave celerity a ; unsteady-friction coeff | pressure-wave timing |
| Agronomy (F) | Kc curve, Ky, nutrient uptake, GDD stages | recorded yield + soil/leaf tests |

**Estimation path.** Only QC-passed data ([13-...](13-sensors-and-instrumentation.md) §B6)
feeds estimation; values become augmented states/parameters in the EKF/EnKF
([14-...](14-digital-twin-data-assimilation.md) §C1); estimates that pass
confidence/governance checks are promoted to the shared core as new priors. Bad/outlier
data is rejected before it can move any parameter.

**Module.** A planned `params.py` (ParameterSet + registry) that
[`solver.py`](../krishiflow/solver.py), [`fao56.py`](../krishiflow/fao56.py),
[`components.py`](../krishiflow/components.py) and
[`emitters.py`](../krishiflow/emitters.py) read from; the twin writes to it.

---

## A1. Pressurized network, steady — Global Gradient Algorithm (GGA)

Unknowns: link flows `Q` (size = links) and nodal heads `H` (size = junctions).
Graph form (Todini & Pilati 1988; Todini & Rossman 2013):

```
Energy:     A12 H + A10 H0 = -A11(Q) Q        (head-loss law per link)
Continuity: A21 Q = q                          (A21 = A12^T, q = demands)
A11 = diag( r|Q|^(n-1) + minor );  G = dHl/dQ = diag( n r|Q|^(n-1) + 2 m|Q| )
```

where `A12` is the node-incidence for unknown-head nodes, `A10` for fixed-head
(reservoir) nodes, `r` the resistance coefficient, `n` the head-loss exponent.

**Newton-Raphson two-step (sparse, symmetric positive-definite):**

```
(A21 G^-1 A12) H = A21 G^-1 (A11 Q + A10 H0) + (q - A21 Q)
Q <- Q - G^-1 (A11 Q + A10 H0 + A12 H)
```

The system matrix `A21 G^-1 A12` is SPD — solve by sparse Cholesky. Iterate to
`||dQ||/||Q|| < tol`. Implemented in [`solver.py`](../krishiflow/solver.py); all link
types (pipes, pumps, valves, venturi, virtual emitter links) are handled uniformly by
an evaluator returning `(headloss, dheadloss/dQ)`.

**Head-loss laws** ([`headloss.py`](../krishiflow/headloss.py)):

- Hazen-Williams: `h_L = 10.67 L Q^1.852 / (C^1.852 D^4.87)`, `n = 1.852`. Empirical,
  water only; singular gradient as `Q -> 0`.
- Darcy-Weisbach: `h_L = f (L/D) (8 Q^2 / (pi^2 g D^4))`, with `f` by Swamee-Jain
  `f = 0.25 / [log10( e/(3.7D) + 5.74/Re^0.9 )]^2`. Physically correct across regimes.

**Deep topics to specify:**

- Darcy gradient including `df/dQ` (we currently freeze `f` per iteration — acceptable,
  but the exact gradient quadratically converges).
- Zero-flow singularity of Hazen-Williams: regularize per Elhay & Simpson (2011) so `G`
  stays invertible.
- Control valves (PRV/PSV/FCV): status logic (active/open/closed) toggled between
  iterations.
- Extended-period simulation (tanks): non-null `A22` (unsteady GGA, Giustolisi &
  Todini 2010).

**Live parameters (A0):** `C` / `e`, minor-loss `K`, pump curve coeffs, valve `Cv`,
nodal demand and background leakage.

**Refs:** Todini & Pilati (1988); Todini & Rossman (2013) *J. Hydraul. Eng.*; Rossman
EPANET 2 manual (2000); Elhay & Simpson (2011) doi:10.1061/(ASCE)HY.1943-7900.0000411;
Giustolisi & Todini (2010) doi:10.2166/hydro.2010.164.

---

## A2. Transients / water hammer — Method of Characteristics (MOC)

Hyperbolic 1-D mass + momentum, wave celerity `a`:

```
dH/dt + (a^2 / gA) dQ/dx = 0
dQ/dt + gA dH/dx + f Q|Q| / (2 d A) = 0
```

MOC converts the PDEs to ODEs along the characteristic lines `dx/dt = ±a`, integrated
as the compatibility equations:

```
C+:  H_P = C_P - B Q_P
C-:  H_P = C_M + B Q_P        B = a / (gA)
C_P = H_A + B Q_A - R Q_A|Q_A| ;  C_M = H_B - B Q_B + R Q_B|Q_B|
```

**Numerics:** fixed grid with the Courant condition `Cr = a dt/dx <= 1`; interior nodes
by interpolation; boundary devices (valve closure law, pump trip with inertia,
air/relief valve, surge tank) as device equations combined with one characteristic.
Add unsteady-friction (Brunone) for accurate damping.

**Use:** a planned `transient.py` reusing the network topology from
[`network.py`](../krishiflow/network.py); sizes air/relief valves, pump-trip
protection, and informs the pump<->valve sequencing interlocks in the controller
([18-...](18-iot-control-architecture.md)).

**Live parameters (A0):** wave celerity `a` (pipe material/age), unsteady-friction
coefficient.

**Refs:** Wylie & Streeter (1993) *Fluid Transients in Systems*; Chaudhry *Applied
Hydraulic Transients*; "Numerical Approaches to Water Hammer Modelling", *Water* 2021,
13(11), 1597.

---

## A3. Surface irrigation (WinSRFR-class) — zero-inertia Saint-Venant

1-D open-channel continuity + momentum with an infiltration sink `z`:

```
dA/dt + dQ/dx + dz/dt = 0
dQ/dt + d(Q^2/A)/dx + gA(dh/dx - S0 + Sf) = 0
```

**Zero-inertia** drops the two acceleration terms (valid at low Froude number — all
practical fields); kinematic-wave additionally drops `dh/dx`. Discretize with the
**Preissmann four-point implicit scheme**; couple to **Kostiakov-Lewis** infiltration
`z = k t^a + b t`.

**Phases / hard parts to specify:** advance, storage, depletion, recession; volume-
balance parameter estimation; computational-incident handling (the tricky part per
SRFR 5).

**Use:** a planned `surface.py`; serves paddy / open-field crops in the Palakkad belt.

**Live parameters (A0):** Kostiakov-Lewis `k, a, b`; Manning `n`.

**Refs:** Strelkoff & Katopodes (1977) *J. Irrig. Drain. Div.* 103(3); Bautista,
Clemmens, Strelkoff, Schlegel (2009) WinSRFR, *Agric. Water Manage.* 96(7),
doi:10.1016/j.agwat.2009.03.007; Bautista et al. SRFR 5,
doi:10.1061/(ASCE)IR.1943-4774.0000938; Lyn & Goodwin (1987) Preissmann stability.

---

## A4. Soil water (root-zone twin) — Richards equation, mixed form

Mixed-form unsaturated flow with root-uptake sink `S`:

```
dtheta/dt - d/dz[ K(psi) (dpsi/dz + 1) ] + S(z,t) = 0
```

with van Genuchten-Mualem retention/conductivity:

```
Se = (theta - theta_r)/(theta_s - theta_r) = [1 + |alpha psi|^n]^(-m),  m = 1 - 1/n
K(Se) = Ks Se^L [1 - (1 - Se^(1/m))^m]^2
```

**Numerics:** the **Celia (1990) mass-conservative Modified Picard** iteration with a
lumped (diagonal) time matrix — the head-based form loses mass and must be avoided.
1-D vertical FV/FE per zone; root-distribution sink; FAO-56 supplies the top boundary
flux.

**Use:** a planned `richards.py`; the high-fidelity upgrade to the bucket model in
[`fao56.py`](../krishiflow/fao56.py); produces the soil-moisture state the twin
assimilates sensor data into. Validate against HYDRUS.

**Live parameters (A0):** `alpha, n, theta_r, theta_s, Ks`.

**Refs:** Richards (1931); Celia, Bouloutas & Zarba (1990) *WRR* 26(7),
doi:10.1029/WR026i007p01483; van Genuchten (1980) *SSSAJ*; Simunek et al. HYDRUS.

---

## A5. Reference ET & crop water — FAO-56 + ASCE standardized

**Reference ET (Penman-Monteith, already implemented in
[`fao56.py`](../krishiflow/fao56.py)):**

```
ET0 = [ 0.408 D (Rn - G) + g (900/(T+273)) u2 (es - ea) ] / [ D + g (1 + 0.34 u2) ]
```

`D` = slope of vapour-pressure curve, `g` = psychrometric constant, `Rn` = net
radiation, `u2` = 2-m wind, `(es - ea)` = vapour-pressure deficit. The **ASCE-EWRI
(2005)** standardized form fixes `Cn/Cd` constants for grass (ETos) / alfalfa (ETrs).

**Crop water (dual crop coefficient):**

```
ETc = (Kcb + Ke) ET0       (Ke from a daily soil-evaporation balance: Kr, few, Kc max)
ETc_adj = (Ks Kcb + Ke) ET0   (Ks = water-stress coefficient from root-zone depletion)
```

**Root-zone water balance (bucket):** `Dr,i = Dr,i-1 - (P - RO) - I - CR + ETc + DP`,
with `RAW = p * TAW`, `Ks = (TAW - Dr)/((1-p) TAW)` for `Dr > RAW`.

**Inputs** are sourced per the instrument -> public-data fallback mapping in
[17-weather-data-integration.md](17-weather-data-integration.md). Crop coefficients,
root depth and MAD come from the agronomy layer ([21-agronomy-layer.md](21-agronomy-layer.md))
and advance by growth stage in real time.

**Live parameters (A0):** `Kcb, Ke (Kr, few, Kcmax), p, TAW/RAW`, ET0 input bias.

**Refs:** Allen, Pereira, Raes & Smith (1998) FAO Irrigation & Drainage Paper 56;
ASCE-EWRI (2005) doi:10.1061/9780784408056; Thorp (2022) pyfao56 *SoftwareX* (cross-
check); NASA POWER for daily ETo (*Agronomy* 2021, 11(10), 2077).

---

## A6. Component CFD (offline) — OpenFOAM FVM + FSI

3-D RANS (k-epsilon / RSM) or LES of emitter labyrinths to derive the `q = k H^x` curve
and exponent (ISO 9261), turbulent dissipation and anti-clog wall-shear maps; venturi
injector dH and suction; tee/manifold K-values. Pressure-compensating emitters need
fluid-structure interaction (diaphragm deformation) via OpenFOAM + CalculiX/deal.II
coupled with **preCICE**.

**Crucial scoping:** these simulations run **offline on HPC**; outputs are cached as the
K-library and emitter curves consumed by [`components.py`](../krishiflow/components.py) /
[`emitters.py`](../krishiflow/emitters.py) — **never per-design**. Field-scale network
solves stay 1-D (A1).

**Refs:** Li et al. (2008) labyrinth CFD + particle tracking, *Irrig. Sci.* 26(5),
doi:10.1007/s00271-008-0108-1; Lequette et al. (2024) SKE/RSM/LES comparison;
"Performance of Emitters... CFD", *Water* 2025, 17(5), 689; PC-emitter diaphragm FSI,
*Irrig. & Drain.* doi:10.1002/ird.2601; preCICE (OpenFOAM coupling).

---

## A7. Design optimization

The Design Studio's multi-objective optimizer (NSGA-II over cost/energy vs uniformity
vs yield/profit) is specified separately in
[20-design-optimization.md](20-design-optimization.md). It scores each candidate by
running the A1 solver + A5 FAO-56 + agronomy (Part F).

---

## Module map (summary)

| Solver | Equation | Scheme | Module |
| --- | --- | --- | --- |
| Network (steady) | mass+energy | GGA / Newton-Raphson | `solver.py`, `headloss.py` |
| Transient | Saint-Venant (full) | MOC | `transient.py` (planned) |
| Surface | Saint-Venant (zero-inertia) | Preissmann + Kostiakov-Lewis | `surface.py` (planned) |
| Soil | Richards (mixed) | Celia Modified Picard FV/FE | `richards.py` (planned) |
| ET / crop water | Penman-Monteith + dual Kc | daily balance | `fao56.py` |
| Component | 3-D RANS/LES + FSI | OpenFOAM FVM (offline) | feeds `components.py`/`emitters.py` |
| Parameters | — | ParameterSet registry | `params.py` (planned) |
