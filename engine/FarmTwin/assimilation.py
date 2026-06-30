"""Digital-twin data assimilation for FarmTwin (R-TWIN-1..3).

Closes the calibration loop: take field measurements (pressures/flows from
sensors), run the GGA solver as the forward model, and use an **Extended Kalman
Filter** to re-estimate live network parameters (pipe roughness/C-factor,
junction demand, emitter discharge coefficient, ...). The estimates and their
uncertainty are then promoted to the shared core under governance
(``promote``), exactly the feedback loop described in
``engine/docs/14-digital-twin-data-assimilation.md``.

Design:
* The state ``x`` is the vector of calibrated parameters; the network object is
  the carrier (a :class:`CalibrationTarget` knows how to read/write one value).
* The observation model ``h(x)`` sets ``x`` into the network, calls
  :func:`FarmTwin.solver.solve`, and reads the predicted sensor quantities.
* ``H = dh/dx`` is obtained by finite differences (re-solving per parameter).
* QC fail-safe: observations flagged ``QCFlag.FAIL`` by the B6 gate are dropped
  before assimilation, and a chi-square innovation gate rejects whole updates
  whose mismatch is implausibly large (R-TWIN-2), so one bad reading cannot
  corrupt the calibrated state.

The filter is pure NumPy (no SciPy dependency); for the chi-square gate a
threshold can be supplied from ``scipy.stats.chi2.ppf`` if desired.

White papers: Evensen (2003) EnKF; Bar-Shalom et al. (2001) EKF + innovation
gating. See docs/requirements.md §4.12.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from .params import LiveParameter, ParameterSet
from .quality import QCFlag
from .solver import solve


@dataclass
class CalibrationTarget:
    """One tunable network parameter the twin estimates.

    ``get``/``set`` read and write the value on a network object; ``prior_std``
    seeds the initial state uncertainty; ``lower``/``upper`` bound the estimate.
    """

    name: str
    get: Callable[[object], float]
    set: Callable[[object, float], None]
    prior_std: float
    lower: float = 1.0e-9
    upper: float = 1.0e12

    @classmethod
    def pipe_coeff(
        cls, pipe_id: str, *, prior_std: float, lower: float = 1.0, upper: float = 200.0
    ) -> CalibrationTarget:
        """Calibrate a pipe's head-loss coefficient (HW C-factor or DW roughness)."""
        return cls(
            name=f"pipe[{pipe_id}].coeff",
            get=lambda net: net.pipes[pipe_id].coeff,
            set=lambda net, v: setattr(net.pipes[pipe_id], "coeff", v),
            prior_std=prior_std,
            lower=lower,
            upper=upper,
        )

    @classmethod
    def junction_demand(
        cls, junction_id: str, *, prior_std: float, lower: float = 0.0, upper: float = 1.0
    ) -> CalibrationTarget:
        """Calibrate a junction's base demand (m^3/s)."""
        return cls(
            name=f"junction[{junction_id}].demand",
            get=lambda net: net.junctions[junction_id].demand,
            set=lambda net, v: setattr(net.junctions[junction_id], "demand", v),
            prior_std=prior_std,
            lower=lower,
            upper=upper,
        )

    @classmethod
    def emitter_k(
        cls, junction_id: str, *, prior_std: float, lower: float = 1.0e-9, upper: float = 1.0
    ) -> CalibrationTarget:
        """Calibrate the discharge coefficient ``k`` of a junction's emitter."""
        return cls(
            name=f"emitter[{junction_id}].k",
            get=lambda net: net.junctions[junction_id].emitter.k,
            set=lambda net, v: setattr(net.junctions[junction_id].emitter, "k", v),
            prior_std=prior_std,
            lower=lower,
            upper=upper,
        )


@dataclass
class Observation:
    """A field measurement used to constrain the estimate.

    kind     "pressure" (junction pressure head, m) or "flow" (link flow, m^3/s)
    location node id (pressure) or link id (flow)
    value    measured value
    std      measurement standard deviation (sensor noise)
    flag     B6 QC flag; FAIL readings are dropped before assimilation
    """

    kind: str
    location: str
    value: float
    std: float = 1.0
    flag: QCFlag = QCFlag.PASS


@dataclass
class AssimilationResult:
    """Outcome of one assimilation step."""

    values: dict[str, float]
    uncertainty: dict[str, float]  # std dev per parameter
    innovation: list[float]  # measured - predicted, for the used observations
    mahalanobis: float  # normalised innovation magnitude (for gating)
    accepted: bool  # False if gated out or no usable observations
    n_used: int  # number of observations that passed QC


@dataclass
class HydraulicTwin:
    """EKF that calibrates network parameters from sensor observations.

    Usage::

        twin = HydraulicTwin(net, [CalibrationTarget.pipe_coeff("P1", prior_std=20)])
        twin.assimilate([Observation("pressure", "J1", measured, std=0.05)])
        promoted = twin.promote()      # governed write-back of confident params
    """

    net: object
    targets: list[CalibrationTarget]
    params: ParameterSet | None = None
    process_std: float = 0.0  # per-step random-walk std (covariance inflation)
    fd_rel_step: float = 1.0e-4  # finite-difference relative step
    fd_abs_step: float = 1.0e-7  # finite-difference absolute floor
    innovation_gate: float | None = None  # reject update if mahalanobis^2 exceeds this
    max_inner: int = 25  # iterated-EKF (Gauss-Newton) relinearizations per update
    step_tol: float = 1.0e-9  # convergence tolerance on the parameter step

    x: np.ndarray = field(init=False)
    P: np.ndarray = field(init=False)
    prior: np.ndarray = field(init=False)
    _version: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.x = np.array([t.get(self.net) for t in self.targets], dtype=float)
        self.prior = self.x.copy()
        self.P = np.diag(np.array([t.prior_std for t in self.targets], dtype=float) ** 2)

    # ---- forward model & Jacobian -------------------------------------------
    def _apply(self, x: np.ndarray) -> None:
        for value, target in zip(x, self.targets, strict=True):
            target.set(self.net, float(value))

    def _predict_observations(self, x: np.ndarray, observations: list[Observation]) -> np.ndarray:
        """Set parameters, solve, and read the predicted sensor quantities."""
        self._apply(x)
        result = solve(self.net, params=self.params)
        out = np.empty(len(observations))
        for i, obs in enumerate(observations):
            if obs.kind == "pressure":
                out[i] = result.pressures[obs.location]
            elif obs.kind == "flow":
                out[i] = result.flows[obs.location]
            else:
                raise ValueError(f"Unknown observation kind: {obs.kind!r}")
        return out

    def _jacobian(
        self, x: np.ndarray, observations: list[Observation], h0: np.ndarray
    ) -> np.ndarray:
        h = np.empty((len(observations), len(x)))
        for j in range(len(x)):
            step = max(self.fd_rel_step * abs(x[j]), self.fd_abs_step)
            xp = x.copy()
            xp[j] += step
            h[:, j] = (self._predict_observations(xp, observations) - h0) / step
        return h

    # ---- EKF update ---------------------------------------------------------
    def assimilate(self, observations: list[Observation]) -> AssimilationResult:
        """Run one iterated-EKF (Gauss-Newton MAP) update against observations.

        FAIL-flagged observations are dropped (fail-safe). The update is the MAP
        estimate that balances the prior ``(x, P)`` against the measurements
        ``(z, R)``, found by re-linearizing the solver-based observation model to
        convergence — this avoids the recursive-EKF "freeze" where the covariance
        collapses before a nonlinear estimate has converged. If a chi-square gate
        is set and the *initial* normalised innovation exceeds it, the update is
        rejected and the state is left unchanged.
        """
        used = [o for o in observations if o.flag != QCFlag.FAIL]
        if not used:
            self._apply(self.x)  # keep the network consistent with current state
            return AssimilationResult(
                values=self._values(),
                uncertainty=self._uncertainty(),
                innovation=[],
                mahalanobis=0.0,
                accepted=False,
                n_used=0,
            )

        z = np.array([o.value for o in used], dtype=float)
        r_inv = np.linalg.pinv(np.diag(np.array([o.std for o in used], dtype=float) ** 2))

        x_prior = self.x.copy()
        p0 = self.P + np.eye(len(self.x)) * self.process_std**2  # optional inflation
        p0_inv = np.linalg.pinv(p0)

        # ---- gate on the initial innovation (one bad reading can't update) ----
        h0 = self._predict_observations(x_prior, used)
        jac0 = self._jacobian(x_prior, used, h0)
        innovation0 = z - h0
        s0 = jac0 @ p0 @ jac0.T + np.linalg.pinv(r_inv)
        mahalanobis = float(innovation0 @ np.linalg.pinv(s0) @ innovation0)
        if self.innovation_gate is not None and mahalanobis > self.innovation_gate:
            self._apply(self.x)
            return AssimilationResult(
                values=self._values(),
                uncertainty=self._uncertainty(),
                innovation=innovation0.tolist(),
                mahalanobis=mahalanobis,
                accepted=False,
                n_used=len(used),
            )

        # ---- iterated Gauss-Newton MAP estimate ----
        x = x_prior.copy()
        jac = jac0
        for _ in range(self.max_inner):
            h = self._predict_observations(x, used)
            jac = self._jacobian(x, used, h)
            normal = p0_inv + jac.T @ r_inv @ jac
            grad = jac.T @ r_inv @ (z - h) - p0_inv @ (x - x_prior)
            dx = np.linalg.solve(normal, grad)
            x = self._clamp(x + dx)
            if np.max(np.abs(dx)) < self.step_tol:
                break

        p_post = np.linalg.pinv(p0_inv + jac.T @ r_inv @ jac)
        self.P = 0.5 * (p_post + p_post.T)  # keep symmetric
        self.x = x
        self._apply(self.x)  # leave the network at the new estimate
        return AssimilationResult(
            values=self._values(),
            uncertainty=self._uncertainty(),
            innovation=innovation0.tolist(),
            mahalanobis=mahalanobis,
            accepted=True,
            n_used=len(used),
        )

    # ---- governed write-back ------------------------------------------------
    def promote(
        self, *, max_relative_uncertainty: float = 0.05, source: str = "field"
    ) -> dict[str, LiveParameter]:
        """Promote confident estimates to LiveParameters (R-TWIN-3 governance).

        Only parameters whose relative uncertainty is at or below
        ``max_relative_uncertainty`` are returned; each carries its prior,
        uncertainty, source and a bumped version stamp.
        """
        std = np.sqrt(np.clip(np.diag(self.P), 0.0, None))
        promoted: dict[str, LiveParameter] = {}
        for i, target in enumerate(self.targets):
            value = float(self.x[i])
            sigma = float(std[i])
            rel = sigma / abs(value) if value != 0.0 else np.inf
            if rel <= max_relative_uncertainty:
                self._version += 1
                promoted[target.name] = LiveParameter(
                    value=value,
                    prior=float(self.prior[i]),
                    uncertainty=sigma,
                    source=source,
                    version=self._version,
                    updated_at=LiveParameter.now_iso(),
                    lower=target.lower,
                    upper=target.upper,
                )
        return promoted

    # ---- helpers ------------------------------------------------------------
    def _clamp(self, x: np.ndarray) -> np.ndarray:
        lo = np.array([t.lower for t in self.targets])
        hi = np.array([t.upper for t in self.targets])
        return np.minimum(np.maximum(x, lo), hi)

    def _values(self) -> dict[str, float]:
        return {t.name: float(v) for t, v in zip(self.targets, self.x, strict=True)}

    def _uncertainty(self) -> dict[str, float]:
        std = np.sqrt(np.clip(np.diag(self.P), 0.0, None))
        return {t.name: float(s) for t, s in zip(self.targets, std, strict=True)}

    def state(self) -> dict[str, float]:
        """Current best estimate for each calibrated parameter."""
        return self._values()
