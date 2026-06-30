"""Emitter (dripper / sprinkler) models for FarmTwin.

Two ways an emitter affects the hydraulic solve:

1. Non pressure-compensating (power law)  q = k * P^x , P = H - elevation.
   We solve this *exactly* inside the GGA by attaching a "virtual link" from the
   emitter node to a virtual fixed-head node at the node's ground elevation. The
   virtual link's head-loss law is the inverse of the emitter law:
       P = (q / k)^(1/x)  =>  h_L(q) = (1/k)^(1/x) * |q|^(1/x) * sign(q)
   so n_e = 1/x and r_e = k**(-1/x). When the GGA balances the network, the flow
   in the virtual link is exactly the emitter discharge.

2. Pressure compensating (PC): emitter delivers `nominal_q` over an operating
   pressure band. We model it as a fixed demand and afterwards check that the
   node pressure stayed within [p_min, p_max] (else we warn).
"""

from __future__ import annotations


def emitter_link_eval(k: float, x: float):
    """Return an evaluator f(Q) -> (headloss, gradient) for a non-PC emitter.

    Implements the inverted emitter law as a head-loss link.
    """
    n_e = 1.0 / x
    r_e = k ** (-1.0 / x)

    def f(flow):
        aq = abs(flow)
        headloss = r_e * flow * aq ** (n_e - 1.0) if aq > 0 else 0.0
        gradient = n_e * r_e * aq ** (n_e - 1.0) if aq > 0 else 1e-8
        return headloss, max(gradient, 1e-8)

    return f


def expand_emitters(net):
    """Build virtual fixed nodes and virtual links for non-PC emitters.

    Returns:
        extra_fixed: dict {virtual_node_id: fixed_head}
        extra_links: list of (link_id, start, end, evaluator)
        pc_demands:  dict {junction_id: extra_demand} for PC emitters
        pc_info:     dict {junction_id: (p_min, p_max, nominal_q)}
    """
    extra_fixed = {}
    extra_links = []
    pc_demands = {}
    pc_info = {}

    for jid, j in net.junctions.items():
        em = j.emitter
        if em is None:
            continue
        if em.pressure_compensating:
            pc_demands[jid] = pc_demands.get(jid, 0.0) + em.nominal_q
            pc_info[jid] = (em.p_min, em.p_max, em.nominal_q)
        else:
            vnode = f"__emit_{jid}"
            extra_fixed[vnode] = j.elevation  # virtual reservoir at ground
            extra_links.append((f"__emitlink_{jid}", jid, vnode, emitter_link_eval(em.k, em.x)))
    return extra_fixed, extra_links, pc_demands, pc_info


def emitter_flow(k: float, x: float, pressure: float) -> float:
    """Direct emitter discharge q = k * P^x for post-processing (P in m)."""
    if pressure <= 0:
        return 0.0
    return k * pressure**x
