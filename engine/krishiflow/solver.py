"""Global Gradient Algorithm (GGA) steady-state hydraulic solver for FarmTwin.

Solves the coupled mass-conservation and head-loss equations for a pressurized
pipe network using Todini & Pilati's GGA (the EPANET core method). Every link
(pipe, pump, valve, venturi, virtual emitter link) is treated uniformly through
an evaluator returning (headloss, gradient) for the current flow.

Derivation (orientation: link goes start -> end; positive Q flows start->end):
    Energy:     A12 @ Hu + A10 @ H0 = hL(Q)
    Continuity: A12^T @ Q = demand
where A is the incidence matrix with A[k, start]=+1, A[k, end]=-1.

Newton/GGA iteration with G = diag(dhL/dQ):
    M = A12^T G^-1 A12                       (sparse SPD)
    M Hu = demand - A12^T Q + A12^T G^-1 (hL - A10 H0)
    Q   <- Q - G^-1 (hL - A10 H0 - A12 Hu)
Iterate until the max flow change is below tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import components as comp
from .emitters import expand_emitters


@dataclass
class SolveResult:
    heads: dict          # node_id -> total head H (m)
    pressures: dict      # junction_id -> pressure head P = H - elevation (m)
    flows: dict          # link_id -> flow (m^3/s), + means start->end
    iterations: int
    converged: bool
    max_residual: float
    pc_warnings: list     # PC emitters outside their pressure band


def _link_evaluator(kind, link):
    """Return f(Q) -> (headloss, gradient) for a real network link."""
    if kind == "pipe":
        total_k = float(link.minor_loss) + comp.sum_k(*link.fittings)

        def f(flow, link=link, total_k=total_k):
            return comp.pipe_headloss_gradient(
                flow, link.length, link.diameter, link.coeff, link.model, total_k
            )
        return f
    if kind == "pump":
        return lambda flow, link=link: link.curve.headloss_gradient(flow)
    if kind == "valve":
        m = comp.minor_loss_m(link.k, link.diameter)

        def f(flow, m=m):
            aq = abs(flow)
            return m * flow * aq, max(2.0 * m * aq, 1e-8)
        return f
    if kind == "venturi":
        return lambda flow, link=link: link.venturi.headloss_gradient(flow)
    raise ValueError(f"Unknown link kind: {kind}")


def solve(net, *, tol=1e-8, max_iter=200, damping=1.0):
    """Solve the network. Returns a SolveResult.

    tol      convergence tolerance on max |dQ| (m^3/s)
    max_iter iteration cap
    damping  under-relaxation factor in (0, 1] for difficult networks
    """
    net.validate()

    # ---- assemble fixed (known-head) and unknown nodes ----
    extra_fixed, emit_links, pc_demands, pc_info = expand_emitters(net)

    fixed_head = {rid: r.head for rid, r in net.reservoirs.items()}
    fixed_head.update(extra_fixed)

    unknown = list(net.junctions.keys())
    uidx = {nid: i for i, nid in enumerate(unknown)}
    nn = len(unknown)

    # ---- assemble link list with evaluators ----
    links = []  # (id, start, end, evaluator)
    for lid, kind, link in net.active_links():
        links.append((lid, link.start, link.end, _link_evaluator(kind, link)))
    for lid, s, e, f in emit_links:
        links.append((lid, s, e, f))
    nl = len(links)
    if nl == 0:
        raise ValueError("Network has no active links to solve")

    # incidence (only unknown-node columns matter for A12; fixed via A10 term)
    starts = [s for _, s, _, _ in links]
    ends = [e for _, _, e, _ in links]

    # demand vector for unknown nodes (base demand + PC emitter nominal flow)
    demand = np.zeros(nn)
    for nid, j in net.junctions.items():
        demand[uidx[nid]] += j.demand
    for nid, q in pc_demands.items():
        demand[uidx[nid]] += q

    # ---- initial flow guess ----
    Q = np.full(nl, 1e-3)

    converged = False
    max_res = np.inf
    it = 0
    for it in range(1, max_iter + 1):
        hL = np.empty(nl)
        ginv = np.empty(nl)
        for k, (_, _, _, f) in enumerate(links):
            h, g = f(Q[k])
            hL[k] = h
            ginv[k] = 1.0 / g

        # build M = A12^T G^-1 A12 and RHS.
        # Continuity sign convention: A12^T Q = -demand (net link outflow from a
        # node balances its withdrawal), so the RHS starts from -demand.
        M = np.zeros((nn, nn))
        rhs = -demand.copy()
        # A12^T Q  and  A12^T G^-1 (hL - A10 H0)
        a10h0 = np.zeros(nl)
        for k in range(nl):
            s, e = starts[k], ends[k]
            si = uidx.get(s)
            ei = uidx.get(e)
            # A10 H0 term: contribution of fixed-head endpoints
            if si is None:
                a10h0[k] += fixed_head[s]      # +1 incidence at start
            if ei is None:
                a10h0[k] -= fixed_head[e]       # -1 incidence at end
            # M assembly (incidence products); unknown endpoints only
            gi = ginv[k]
            if si is not None:
                M[si, si] += gi
                rhs[si] -= Q[k]                 # -A12^T Q
                rhs[si] += gi * (hL[k] - a10h0[k])  # +A12^T G^-1(hL - A10H0)
            if ei is not None:
                M[ei, ei] += gi
                rhs[ei] += Q[k]
                rhs[ei] -= gi * (hL[k] - a10h0[k])
            if si is not None and ei is not None:
                M[si, ei] -= gi
                M[ei, si] -= gi

        # solve for unknown heads
        try:
            Hu = np.linalg.solve(M, rhs)
        except np.linalg.LinAlgError:
            Hu = np.linalg.lstsq(M, rhs, rcond=None)[0]

        # update flows: Q <- Q - G^-1 (hL - A10 H0 - A12 Hu)
        newQ = Q.copy()
        for k in range(nl):
            s, e = starts[k], ends[k]
            a12hu = 0.0
            si, ei = uidx.get(s), uidx.get(e)
            if si is not None:
                a12hu += Hu[si]
            if ei is not None:
                a12hu -= Hu[ei]
            newQ[k] = Q[k] - ginv[k] * (hL[k] - a10h0[k] - a12hu)

        newQ = Q + damping * (newQ - Q)
        max_res = float(np.max(np.abs(newQ - Q)))
        Q = newQ
        if max_res < tol:
            converged = True
            break

    # ---- assemble results ----
    heads = dict(fixed_head)
    for nid in unknown:
        heads[nid] = float(Hu[uidx[nid]])

    pressures = {}
    for nid, j in net.junctions.items():
        pressures[nid] = heads[nid] - j.elevation

    flows = {}
    for k, (lid, _, _, _) in enumerate(links):
        if not lid.startswith("__emitlink_"):
            flows[lid] = float(Q[k])

    # PC emitter band check
    pc_warnings = []
    for nid, (p_min, p_max, q_nom) in pc_info.items():
        p = pressures[nid]
        if p < p_min or p > p_max:
            pc_warnings.append(
                f"PC emitter at {nid}: pressure {p:.1f} m outside "
                f"[{p_min:.1f}, {p_max:.1f}] m operating band"
            )

    return SolveResult(
        heads=heads, pressures=pressures, flows=flows, iterations=it,
        converged=converged, max_residual=max_res, pc_warnings=pc_warnings,
    )
