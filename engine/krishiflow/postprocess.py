"""Post-processing for KrishiFlow: engineering report, uniformity metrics, plots.

Computes the quantities irrigation designers care about: nodal pressures, link
flows and velocities, emitter discharges, emission/distribution uniformity, and
pump duty point + required motor HP. Plots are optional (matplotlib).
"""

from __future__ import annotations

import math

from .components import select_motor_hp
from .emitters import emitter_flow


def pipe_velocity(flow, diameter):
    area = math.pi * diameter ** 2 / 4.0
    return abs(flow) / area if area > 0 else 0.0


def emitter_discharges(net, result):
    """Return {junction_id: q (m^3/s)} for every emitter node."""
    out = {}
    for nid, j in net.junctions.items():
        em = j.emitter
        if em is None:
            continue
        p = result.pressures[nid]
        if em.pressure_compensating:
            # delivers nominal flow while within band; degrade outside
            if p < em.p_min:
                out[nid] = em.k * max(p, 0.0) ** em.x  # falls off below band
            else:
                out[nid] = em.nominal_q
        else:
            out[nid] = emitter_flow(em.k, em.x, p)
    return out


def uniformity(discharges):
    """Return dict of uniformity metrics from a list/dict of emitter flows.

    DU_lq : low-quarter distribution uniformity (%) = mean(lowest 25%) / mean.
    CV    : coefficient of variation of emitter flow.
    EU    : statistical emission uniformity (%) = (1 - CV) * 100 (approx).
    """
    q = sorted(float(v) for v in (discharges.values()
               if isinstance(discharges, dict) else discharges))
    n = len(q)
    if n == 0:
        return {}
    mean = sum(q) / n
    if mean <= 0:
        return {"count": n, "q_mean": 0.0}
    nlq = max(1, n // 4)
    mean_lq = sum(q[:nlq]) / nlq
    var = sum((v - mean) ** 2 for v in q) / n
    cv = math.sqrt(var) / mean
    return {
        "count": n,
        "q_min": q[0],
        "q_max": q[-1],
        "q_mean": mean,
        "DU_lq_pct": 100.0 * mean_lq / mean,
        "CV": cv,
        "EU_pct": 100.0 * (1.0 - cv),
    }


def pump_report(net, result):
    """Return per-pump duty point and motor sizing."""
    rows = []
    for pid, pump in net.pumps.items():
        if getattr(pump, "status", "OPEN") == "CLOSED":
            continue
        q = abs(result.flows.get(pid, 0.0))
        gain = pump.curve.head_gain(q)
        hp = pump.curve.motor_hp(q, gain)
        try:
            catalog_hp, _ = select_motor_hp(hp)
            note = ""
        except ValueError as exc:
            catalog_hp, note = None, str(exc)
        rows.append({
            "pump": pid, "Q_m3ph": q * 3600.0, "head_m": gain,
            "required_hp": hp, "motor_hp": catalog_hp, "note": note,
        })
    return rows


def report(net, result) -> str:
    """Build a human-readable text report of the solved network."""
    L = []
    L.append("=" * 64)
    L.append("KrishiFlow hydraulic report")
    L.append("=" * 64)
    L.append(f"Converged: {result.converged}  "
             f"iterations: {result.iterations}  "
             f"max |dQ|: {result.max_residual:.2e} m3/s")
    L.append("")
    L.append("Node pressures (m):")
    for nid in sorted(net.junctions):
        L.append(f"  {nid:<10} P = {result.pressures[nid]:8.2f}   "
                 f"H = {result.heads[nid]:8.2f}")
    L.append("")
    L.append("Link flows & velocities:")
    for pid, pipe in net.pipes.items():
        q = result.flows.get(pid, 0.0)
        v = pipe_velocity(q, pipe.diameter)
        L.append(f"  pipe  {pid:<8} Q = {q*3600:8.3f} m3/h  V = {v:5.2f} m/s")
    for vid in net.valves:
        L.append(f"  valve {vid:<8} Q = {result.flows.get(vid,0)*3600:8.3f} m3/h")
    for vid in net.venturis:
        L.append(f"  vent. {vid:<8} Q = {result.flows.get(vid,0)*3600:8.3f} m3/h")

    pumps = pump_report(net, result)
    if pumps:
        L.append("")
        L.append("Pumps (duty point & motor sizing):")
        for r in pumps:
            hp = f"{r['motor_hp']} HP" if r['motor_hp'] else "OVER-RANGE"
            L.append(f"  {r['pump']:<8} Q = {r['Q_m3ph']:7.2f} m3/h  "
                     f"H = {r['head_m']:6.2f} m  req {r['required_hp']:5.2f} HP "
                     f"-> {hp} {r['note']}")

    disch = emitter_discharges(net, result)
    if disch:
        u = uniformity(disch)
        L.append("")
        L.append("Emitter performance:")
        L.append(f"  emitters: {u['count']}   "
                 f"q_avg = {u['q_mean']*1e6:.2f} L/h-ish (x3.6 -> L/h: "
                 f"{u['q_mean']*3.6e6:.2f})")
        L.append(f"  q_min = {u['q_min']*3.6e6:.2f} L/h   "
                 f"q_max = {u['q_max']*3.6e6:.2f} L/h")
        L.append(f"  DU(low-quarter) = {u['DU_lq_pct']:.1f}%   "
                 f"EU = {u['EU_pct']:.1f}%   CV = {u['CV']:.3f}")

    if result.pc_warnings:
        L.append("")
        L.append("WARNINGS:")
        for w in result.pc_warnings:
            L.append(f"  ! {w}")
    L.append("=" * 64)
    return "\n".join(L)


def plot_lateral_profile(net, result, path="lateral_profile.png"):
    """Plot pressure & emitter flow along an ordered E1..En lateral. Optional."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # matplotlib not installed -> skip gracefully
        return f"(plot skipped: {exc})"

    nodes = sorted((n for n in net.junctions if n.startswith("E")),
                   key=lambda s: int(s[1:]))
    if not nodes:
        nodes = sorted(net.junctions)
    xs = list(range(1, len(nodes) + 1))
    press = [result.pressures[n] for n in nodes]
    disch = emitter_discharges(net, result)
    flows = [disch.get(n, 0.0) * 3.6e6 for n in nodes]  # ~L/h scale

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(xs, press, "-o", color="#3b82f6", label="pressure (m)")
    ax1.set_xlabel("emitter # along lateral")
    ax1.set_ylabel("pressure head (m)", color="#3b82f6")
    ax2 = ax1.twinx()
    ax2.plot(xs, flows, "-s", color="#36c2a3", label="emitter flow")
    ax2.set_ylabel("emitter flow (rel.)", color="#36c2a3")
    ax1.set_title("KrishiFlow: pressure & emitter flow along lateral")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
