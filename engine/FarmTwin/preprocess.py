"""Pre-processing for FarmTwin: JSON network I/O and a drip-lateral generator.

The JSON schema mirrors the data model so designs can be authored by hand, by
the FreeCAD workbench, or generated programmatically.

This module also implements the FarmTwin Survey (FTS) interchange format
(``docs/survey-schema.md``): loading an ``.fts.json`` document into a solver
network and validating it against the documented rules V01-V18, plus importers
for EPANET ``.inp`` and KoboToolbox survey payloads.
"""

from __future__ import annotations

import json
import re

from . import geo
from .components import PumpCurve, Venturi
from .network import (
    Emitter,
    Junction,
    Network,
    Pipe,
    Pump,
    Reservoir,
    Valve,
    VenturiLink,
)

# Pressure-head conversion: 1 kPa of water column = 1000 / (rho * g) metres.
_G = 9.80665
KPA_TO_M = 1000.0 / (1000.0 * _G)


def network_from_dict(d: dict) -> Network:
    net = Network()
    for r in d.get("reservoirs", []):
        net.add_reservoir(Reservoir(**r))
    for j in d.get("junctions", []):
        em = j.pop("emitter", None)
        junction = Junction(**j)
        if em:
            junction.emitter = Emitter(**em)
        net.add_junction(junction)
    for p in d.get("pipes", []):
        net.add_pipe(Pipe(**p))
    for p in d.get("pumps", []):
        curve = PumpCurve(**p.pop("curve"))
        net.add_pump(Pump(curve=curve, **p))
    for v in d.get("valves", []):
        net.add_valve(Valve(**v))
    for v in d.get("venturis", []):
        vent = Venturi(**v.pop("venturi"))
        net.add_venturi(VenturiLink(venturi=vent, **v))
    return net


def load_network(path: str) -> Network:
    with open(path, encoding="utf-8") as fh:
        return network_from_dict(json.load(fh))


def build_drip_lateral(
    *,
    source_head: float,
    source_elevation: float = 0.0,
    n_emitters: int = 20,
    spacing: float = 0.5,
    diameter: float = 0.016,
    hw_c: float = 150.0,
    slope: float = 0.0,
    emitter_k: float = 3.51e-7,
    emitter_x: float = 0.5,
    pressure_compensating: bool = False,
    nominal_q: float = 1.11e-6,
) -> Network:
    """Build a single drip lateral: reservoir -> chain of emitter nodes.

    A textbook test case for the solver. Each segment between emitters is a
    short pipe; each node carries an emitter. `slope` (m/m) tilts the lateral
    (positive = uphill away from source). Defaults: 16 mm LDPE lateral, 0.5 m
    emitter spacing, turbulent emitter (x=0.5). The default emitter_k=3.51e-7
    gives q = k*sqrt(P) ~ 1.11e-6 m^3/s (= 4 L/h) at P = 10 m; nominal_q for
    the PC variant is likewise 4 L/h.
    """
    net = Network()
    net.add_reservoir(Reservoir(id="SRC", head=source_head, x=0.0, y=source_elevation))
    prev = "SRC"
    for i in range(1, n_emitters + 1):
        nid = f"E{i}"
        elev = source_elevation + slope * spacing * i
        em = Emitter(
            k=emitter_k,
            x=emitter_x,
            pressure_compensating=pressure_compensating,
            nominal_q=nominal_q,
        )
        net.add_junction(
            Junction(id=nid, elevation=elev, demand=0.0, emitter=em, x=spacing * i, y=elev)
        )
        net.add_pipe(
            Pipe(
                id=f"P{i}",
                start=prev,
                end=nid,
                length=spacing,
                diameter=diameter,
                coeff=hw_c,
                model="HW",
            )
        )
        prev = nid
    return net


# ===========================================================================
# FarmTwin Survey (FTS) interchange format — see docs/survey-schema.md
# ===========================================================================

FTS_SCHEMA_VERSION = "1.0"

# Validation bounds (named to keep them out of magic-number comparisons).
_AREA_HA_MIN, _AREA_HA_MAX = 0.01, 500.0
_ELEV_MIN, _ELEV_MAX = -10.0, 3000.0
_DIAM_MIN, _DIAM_MAX = 0.005, 0.5
_LEN_MIN, _LEN_MAX = 0.1, 5000.0
_EMIT_FLOW_MIN, _EMIT_FLOW_MAX = 0.5, 200.0
_EMIT_PRESS_MIN, _EMIT_PRESS_MAX = 30.0, 600.0
_EU_MIN, _EU_MAX = 70.0, 100.0
_LAT_MIN, _LAT_MAX = -90.0, 90.0
_LON_MIN, _LON_MAX = -180.0, 180.0

_REQUIRED_TOP = (
    "schema_version",
    "survey_id",
    "farm_id",
    "created_at",
    "updated_at",
    "surveyed_by",
    "farm",
    "water_source",
    "nodes",
    "links",
    "zones",
)
_SOURCE_NODE_TYPES = frozenset({"reservoir", "pump"})
_SOIL_TYPES = frozenset(
    {
        "sandy",
        "sandy_loam",
        "loam",
        "clay_loam",
        "clay",
        "red_laterite",
        "black_cotton",
        "alluvial",
    }
)
_CROP_TYPES = frozenset(
    {
        "coconut",
        "paddy",
        "banana_nendran",
        "banana_robusta",
        "tomato",
        "okra",
        "capsicum",
        "tapioca",
        "areca",
        "pepper",
        "mango",
        "other",
    }
)
_WEATHER_SOURCES = frozenset(
    {
        "open_meteo",
        "open_meteo_era5",
        "nasa_power",
        "imd",
        "aws",
        "on_farm_aws",
        "gefs",
        "era5",
    }
)

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-" r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


class FTSValidationError(ValueError):
    """Raised when an FTS document fails validation and errors must propagate."""


def _err(rule: str, message: str) -> str:
    """Format a validation error string tagged with its rule ID."""
    return f"{rule}: {message}"


def _in_range(value: object, lo: float, hi: float) -> bool:
    """Return True if ``value`` is a number within the inclusive ``[lo, hi]``."""
    return isinstance(value, int | float) and lo <= float(value) <= hi


def _validate_top_level(doc: dict, errors: list[str]) -> None:
    """Check required top-level fields, schema version, and survey ID."""
    for field_name in _REQUIRED_TOP:
        if field_name not in doc:
            errors.append(_err("V00", f"missing required field '{field_name}'"))
    if doc.get("schema_version") not in (None, FTS_SCHEMA_VERSION):
        errors.append(_err("V01", "unsupported schema_version"))
    survey_id = doc.get("survey_id")
    if survey_id is not None and not _UUID_RE.match(str(survey_id)):
        errors.append(_err("V02", "invalid survey_id (must be UUID)"))
    phone = (
        doc.get("surveyed_by", {}).get("phone")
        if isinstance(doc.get("surveyed_by"), dict)
        else None
    )
    if phone is not None and not _E164_RE.match(str(phone)):
        errors.append(_err("V18", "surveyed_by.phone must be E.164 (+digits)"))


def _validate_farm(doc: dict, errors: list[str]) -> None:
    """Validate the farm block (area and soil type)."""
    farm = doc.get("farm")
    if not isinstance(farm, dict):
        return
    if "area_ha" in farm and not _in_range(farm["area_ha"], _AREA_HA_MIN, _AREA_HA_MAX):
        errors.append(_err("V03", "farm area out of range (0.01-500 ha)"))
    soil = farm.get("soil_type_primary")
    if soil is not None and soil not in _SOIL_TYPES:
        errors.append(_err("V16b", f"unknown soil type '{soil}'"))


def _validate_gps(label: str, loc: dict, errors: list[str]) -> None:
    """Validate a single ``{lat, lon, elevation_m}`` location object."""
    if "elevation_m" in loc and not _in_range(loc["elevation_m"], _ELEV_MIN, _ELEV_MAX):
        errors.append(_err("V04", f"{label} elevation out of range"))
    if "lat" in loc and not _in_range(loc["lat"], _LAT_MIN, _LAT_MAX):
        errors.append(_err("V15", f"{label} latitude out of range"))
    if "lon" in loc and not _in_range(loc["lon"], _LON_MIN, _LON_MAX):
        errors.append(_err("V15", f"{label} longitude out of range"))


def _validate_nodes(doc: dict, errors: list[str]) -> None:
    """Validate node locations and the presence of a water source."""
    nodes = doc.get("nodes") or []
    for node in nodes:
        loc = node.get("location")
        if isinstance(loc, dict):
            _validate_gps(f"node {node.get('id')}", loc, errors)
    if not any(n.get("type") in _SOURCE_NODE_TYPES for n in nodes):
        errors.append(_err("V05", "no water source node (reservoir or pump)"))


def _validate_links(doc: dict, errors: list[str]) -> None:
    """Validate link references, diameters, and lengths."""
    node_ids = {n.get("id") for n in (doc.get("nodes") or [])}
    for link in doc.get("links") or []:
        for end in ("from_node", "to_node"):
            ref = link.get(end)
            if ref is not None and ref not in node_ids:
                errors.append(_err("V06", f"dangling link {link.get('id')} -> {ref}"))
        if "internal_diameter_m" in link and not _in_range(
            link["internal_diameter_m"], _DIAM_MIN, _DIAM_MAX
        ):
            errors.append(_err("V08", f"link {link.get('id')} diameter out of range"))
        if "length_m" in link and not _in_range(link["length_m"], _LEN_MIN, _LEN_MAX):
            errors.append(_err("V09", f"link {link.get('id')} length out of range"))


def _validate_zones(doc: dict, errors: list[str]) -> None:
    """Validate zones, crop types, and emitter layout limits."""
    zones = doc.get("zones")
    if not zones:
        errors.append(_err("V12", "no irrigation zones defined"))
        return
    for zone in zones:
        crop = (zone.get("crop") or {}).get("type")
        if crop is not None and crop not in _CROP_TYPES:
            errors.append(_err("V16", f"unknown crop type '{crop}'"))
        layout = zone.get("emitter_layout") or {}
        if "flow_rate_lh" in layout and not _in_range(
            layout["flow_rate_lh"], _EMIT_FLOW_MIN, _EMIT_FLOW_MAX
        ):
            errors.append(_err("V10", "emitter flow_rate out of range (0.5-200 L/h)"))
        if "operating_pressure_kpa" in layout and not _in_range(
            layout["operating_pressure_kpa"], _EMIT_PRESS_MIN, _EMIT_PRESS_MAX
        ):
            errors.append(_err("V11", "emitter pressure out of range (30-600 kPa)"))


def _validate_misc(doc: dict, errors: list[str]) -> None:
    """Validate weather source and design constraints."""
    weather = doc.get("weather") or {}
    src = weather.get("preferred_source")
    if src is not None and src not in _WEATHER_SOURCES:
        errors.append(_err("V14", f"unknown weather source '{src}'"))
    dc = doc.get("design_constraints") or {}
    if "min_eu_pct" in dc and not _in_range(dc["min_eu_pct"], _EU_MIN, _EU_MAX):
        errors.append(_err("V13", "min_eu_pct out of range (70-100)"))


def _validate_connectivity(doc: dict, errors: list[str]) -> None:
    """V07: every node must be reachable from a source via the link graph."""
    nodes = doc.get("nodes") or []
    node_ids = {n.get("id") for n in nodes}
    sources = {n.get("id") for n in nodes if n.get("type") in _SOURCE_NODE_TYPES}
    if not sources:
        return  # V05 already reported; connectivity is undefined without a source.
    adjacency: dict[str, set] = {nid: set() for nid in node_ids}
    for link in doc.get("links") or []:
        a, b = link.get("from_node"), link.get("to_node")
        if a in adjacency and b in adjacency:
            adjacency[a].add(b)
            adjacency[b].add(a)
    seen: set = set(sources)
    stack = list(sources)
    while stack:
        cur = stack.pop()
        for nbr in adjacency.get(cur, ()):
            if nbr not in seen:
                seen.add(nbr)
                stack.append(nbr)
    for nid in node_ids - seen:
        errors.append(_err("V07", f"disconnected node '{nid}' (unreachable)"))


def validate_fts_json(doc: dict) -> list[str]:
    """Validate an FTS document against rules V01-V18.

    Args:
        doc: A parsed FTS JSON document.

    Returns:
        A list of human-readable error strings (each tagged with its rule ID).
        An empty list means the document is valid.
    """
    errors: list[str] = []
    _validate_top_level(doc, errors)
    _validate_farm(doc, errors)
    _validate_nodes(doc, errors)
    _validate_links(doc, errors)
    _validate_zones(doc, errors)
    _validate_misc(doc, errors)
    _validate_connectivity(doc, errors)
    return errors


def load_fts_json(doc: dict) -> dict:
    """Convert an FTS document into a solver-ready network dict.

    Node and link identifiers (and pipe lengths) are preserved so a design can
    round-trip Studio -> Runtime without loss.

    Args:
        doc: A parsed (and ideally validated) FTS JSON document.

    Returns:
        A dict ``{"nodes": [...], "links": [...]}`` consumable by the solver
        layer; each link carries its ``length_m`` and diameter.
    """
    nodes = []
    for node in doc.get("nodes", []):
        loc = node.get("location") or {}
        nodes.append(
            {
                "id": node["id"],
                "type": node.get("type", "junction"),
                "elevation_m": loc.get("elevation_m", 0.0),
                "attributes": node.get("attributes", {}),
            }
        )
    links = []
    for link in doc.get("links", []):
        links.append(
            {
                "id": link["id"],
                "from_node": link.get("from_node"),
                "to_node": link.get("to_node"),
                "type": link.get("type", "pipe"),
                "length_m": link.get("length_m"),
                "diameter_m": link.get("internal_diameter_m"),
                "c_factor": link.get("hazen_williams_c"),
            }
        )
    return {"nodes": nodes, "links": links}


def load_fts_file(path: str) -> dict:
    """Load an ``.fts.json`` file and return the solver-ready network dict."""
    with open(path, encoding="utf-8") as fh:
        return load_fts_json(json.load(fh))


# ===========================================================================
# FTS -> solvable Network bridge (specifications.md §3.2, Stage D)
# ===========================================================================


def zone_emitter_count(zone: dict) -> int:
    """Number of emitters in a zone (plants x emitters/plant, area fallback)."""
    layout = zone.get("emitter_layout") or {}
    crop = zone.get("crop") or {}
    epp = int(layout.get("emitters_per_plant", 1) or 1)
    plants = crop.get("plant_count")
    if plants is None:
        area = float(zone.get("area_m2", 0.0) or 0.0)
        rs = crop.get("row_spacing_m")
        ps = crop.get("plant_spacing_m")
        plants = area / (float(rs) * float(ps)) if rs and ps else 0.0
    return max(1, int(round(float(plants) * epp)))


def zone_nominal_flow_m3s(zone: dict) -> float:
    """Nominal zone flow (m^3/s) from emitter count x rated emitter flow."""
    layout = zone.get("emitter_layout") or {}
    flow_lh = float(layout.get("flow_rate_lh", 4.0) or 4.0)
    return zone_emitter_count(zone) * flow_lh / 1000.0 / 3600.0


def fts_to_network(
    fts: dict,
    *,
    active_zones: list[str] | None = None,
    zone_flows: dict[str, float] | None = None,
    source_head_m: float | None = None,
) -> Network:
    """Build a solver ``Network`` from an FTS survey/design document.

    Topology mapping (specifications.md §3.2):

    - a ``reservoir`` node becomes a fixed-head ``Reservoir`` (head from
      ``attributes.head_m``, else ``source_head_m``, else the water source);
    - a ``pump`` node is split into ``<id>__in``/``<id>__out`` junctions joined
      by a ``Pump`` link whose curve comes from the node attributes; links into
      the pump attach to ``__in`` and links out attach to ``__out``;
    - every other node becomes a ``Junction`` at its elevation;
    - each link becomes a ``Pipe`` with its diameter / Hazen-Williams C and the
      summed ``minor_losses`` K;
    - each active zone is represented by a non-PC ``Emitter`` at its
      ``valve_node`` whose ``k`` delivers the zone design flow at the layout's
      operating pressure, so inter-zone uniformity (EU/DU) emerges from the
      solved pressures.

    Args:
        fts: FTS document (ideally validated and length-filled, see ``geo``).
        active_zones: zone IDs to energise (default: all zones).
        zone_flows: optional per-zone design flow (m^3/s) overriding the nominal
            emitter-count estimate (supplied by the demand model in Phase 2).
        source_head_m: optional explicit source head (m).

    Returns:
        A :class:`~FarmTwin.network.Network` ready for :func:`FarmTwin.solver.solve`.
    """
    nodes = {n["id"]: n for n in fts.get("nodes", [])}
    water_source = fts.get("water_source") or {}
    net = Network()

    def elevation_of(nid: str) -> float:
        loc = nodes[nid].get("location") or {}
        return float(loc.get("elevation_m", 0.0) or 0.0)

    pump_split: dict[str, tuple[str, str]] = {}
    for nid, node in nodes.items():
        ntype = node.get("type", "junction")
        elev = elevation_of(nid)
        if ntype == "reservoir":
            attrs = node.get("attributes") or {}
            head = attrs.get("head_m")
            if head is None:
                head = source_head_m
            if head is None:
                head = geo.source_head_m(water_source) if water_source else elev
            net.add_reservoir(Reservoir(id=nid, head=float(head)))
        elif ntype == "pump":
            in_id, out_id = f"{nid}__in", f"{nid}__out"
            net.add_junction(Junction(id=in_id, elevation=elev))
            net.add_junction(Junction(id=out_id, elevation=elev))
            curve = PumpCurve.from_fts(node.get("attributes") or {})
            net.add_pump(Pump(id=f"PUMP_{nid}", start=in_id, end=out_id, curve=curve))
            pump_split[nid] = (in_id, out_id)
        else:
            net.add_junction(Junction(id=nid, elevation=elev))

    for link in fts.get("links", []):
        start = link.get("from_node")
        end = link.get("to_node")
        if start in pump_split:
            start = pump_split[start][1]  # leaving a pump -> discharge node
        if end in pump_split:
            end = pump_split[end][0]  # entering a pump -> suction node
        diameter = link.get("internal_diameter_m")
        length = link.get("length_m")
        if diameter is None or length is None:
            raise FTSValidationError(
                f"link {link.get('id')} needs internal_diameter_m and length_m "
                f"(run geo.fill_link_lengths first)"
            )
        total_k = sum(
            float(f.get("k", 0.0)) * float(f.get("count", 1) or 1)
            for f in (link.get("minor_losses") or [])
        )
        net.add_pipe(
            Pipe(
                id=link["id"],
                start=start,
                end=end,
                length=float(length),
                diameter=float(diameter),
                coeff=float(link.get("hazen_williams_c", 140.0) or 140.0),
                minor_loss=total_k,
                model="HW",
            )
        )

    active = set(active_zones) if active_zones is not None else None
    for zone in fts.get("zones", []):
        zid = zone.get("id")
        if active is not None and zid not in active:
            continue
        vnode = zone.get("valve_node")
        if vnode not in net.junctions:
            continue
        q = (zone_flows or {}).get(zid)
        if q is None:
            q = zone_nominal_flow_m3s(zone)
        layout = zone.get("emitter_layout") or {}
        p_op_m = float(layout.get("operating_pressure_kpa", 100.0) or 100.0) * KPA_TO_M
        x = 0.5  # turbulent power-law emitter exponent (network-level zone proxy)
        k = q / (p_op_m**x) if p_op_m > 0 else 0.0
        net.junctions[vnode].emitter = Emitter(k=k, x=x)

    return net


def epanet_backend_available() -> bool:
    """Return True if the optional WNTR (EPANET) backend is importable."""
    try:
        import wntr  # noqa: F401
    except ImportError:
        return False
    return True


def load_epanet_inp(path: str) -> dict:
    """Parse an EPANET 2.x ``.inp`` file into a network dict.

    Uses the open-source **WNTR** package (EPANET's C engine wrapped in Python)
    when it is installed for robust, fully-featured parsing; otherwise falls
    back to a built-in minimal parser covering the ``[JUNCTIONS]``,
    ``[RESERVOIRS]`` and ``[PIPES]`` sections. Either way the result lets
    existing designs from EPANET-compatible tools (IRRICAD/IrriPro) round-trip.

    Args:
        path: Path to an EPANET ``.inp`` file.

    Returns:
        A dict ``{"nodes": [...], "links": [...]}``.
    """
    if epanet_backend_available():
        try:
            return _load_epanet_inp_wntr(path)
        except Exception:  # noqa: BLE001 - any WNTR parse issue -> minimal fallback
            return _load_epanet_inp_minimal(path)
    return _load_epanet_inp_minimal(path)


def _load_epanet_inp_wntr(path: str) -> dict:
    """Parse an EPANET ``.inp`` via WNTR into the FarmTwin network dict."""
    import wntr

    wn = wntr.network.WaterNetworkModel(path)
    nodes: list[dict] = []
    for name, node in wn.nodes():
        node_type = type(node).__name__.replace("Node", "").lower()
        nodes.append(
            {
                "id": name,
                "type": "reservoir"
                if node_type == "reservoir"
                else ("reservoir" if node_type == "tank" else "junction"),
                "elevation_m": float(getattr(node, "elevation", 0.0) or 0.0),
            }
        )
    links: list[dict] = []
    for name, link in wn.links():
        if type(link).__name__ != "Pipe":
            continue
        links.append(
            {
                "id": name,
                "from_node": link.start_node_name,
                "to_node": link.end_node_name,
                "type": "pipe",
                "length_m": float(link.length),
                "diameter_m": float(link.diameter),
                "c_factor": float(link.roughness),
            }
        )
    return {"nodes": nodes, "links": links}


def _load_epanet_inp_minimal(path: str) -> dict:
    """Built-in fallback EPANET parser (JUNCTIONS/RESERVOIRS/PIPES only)."""
    nodes: list[dict] = []
    links: list[dict] = []
    section = None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split(";", 1)[0].strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].upper()
                continue
            parts = line.split()
            if section == "JUNCTIONS":
                nodes.append(
                    {
                        "id": parts[0],
                        "type": "junction",
                        "elevation_m": float(parts[1]) if len(parts) > 1 else 0.0,
                    }
                )
            elif section == "RESERVOIRS":
                nodes.append(
                    {
                        "id": parts[0],
                        "type": "reservoir",
                        "elevation_m": float(parts[1]) if len(parts) > 1 else 0.0,
                    }
                )
            elif section == "PIPES" and len(parts) >= 6:
                links.append(
                    {
                        "id": parts[0],
                        "from_node": parts[1],
                        "to_node": parts[2],
                        "type": "pipe",
                        "length_m": float(parts[3]),
                        "diameter_m": float(parts[4]) / 1000.0,  # EPANET mm -> m
                        "c_factor": float(parts[5]),
                    }
                )
    return {"nodes": nodes, "links": links}


def convert_kobo_to_fts(payload: dict) -> dict:
    """Convert a KoboToolbox/ODK survey submission into an FTS document.

    Only the fields a single-point Kobo form can capture are mapped; map-based
    geometry (nodes/links/zone polygons) is left empty for later enrichment.

    Args:
        payload: A KoboToolbox webhook submission.

    Returns:
        A partial FTS JSON document with ``schema_version == "1.0"``.
    """
    geo = payload.get("_geolocation") or [None, None]
    lat, lon = [*geo, None, None][:2]
    return {
        "schema_version": FTS_SCHEMA_VERSION,
        "survey_id": str(payload.get("_uuid", payload.get("_id", ""))),
        "sync_status": "synced",
        "farm": {
            "name": payload.get("farm_name"),
            "village": payload.get("village"),
            "area_ha": payload.get("farm_area_ha"),
        },
        "water_source": {
            "type": payload.get("source_type"),
            "location": {"lat": lat, "lon": lon},
        },
        "nodes": [],
        "links": [],
        "zones": [],
        "sensors": [],
    }
