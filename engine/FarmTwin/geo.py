"""Geospatial geometry for FarmTwin (specifications.md §3.1, Stage B).

Turns the GPS coordinates captured in an FTS survey into the geometry the
hydraulic solver needs: pipe segment lengths (great-circle, optionally including
the elevation drop) and the source's total head. All distances in metres;
coordinates are WGS84 decimal degrees (EPSG:4326), matching the FTS schema.
"""

from __future__ import annotations

from collections.abc import Callable
import math

# WGS84 mean radius (m); adequate for farm-scale segment lengths.
EARTH_RADIUS_M = 6_371_008.8


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in metres."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def segment_length_m(a: dict, b: dict, *, use_elevation: bool = True) -> float:
    """3-D length of a pipe between two ``{lat, lon, elevation_m}`` locations.

    Horizontal distance via haversine; the elevation difference is added in
    quadrature when ``use_elevation`` and both elevations are present.
    """
    horizontal = haversine_m(a["lat"], a["lon"], b["lat"], b["lon"])
    if use_elevation and a.get("elevation_m") is not None and b.get("elevation_m") is not None:
        dz = float(a["elevation_m"]) - float(b["elevation_m"])
        return math.hypot(horizontal, dz)
    return horizontal


def polyline_length_m(points: list[dict], *, use_elevation: bool = True) -> float:
    """Total length of a GPS-tracked route (list of location dicts)."""
    return sum(
        segment_length_m(points[i], points[i + 1], use_elevation=use_elevation)
        for i in range(len(points) - 1)
    )


def source_head_m(water_source: dict) -> float:
    """Derive the source's total head (m) for the solver reservoir node.

    Preference order: explicit ``sump_elevation_m`` (water surface of a sump);
    otherwise the source location elevation minus the dynamic (then static)
    water level for a well; otherwise the location elevation.
    """
    loc = water_source.get("location") or {}
    if water_source.get("sump_elevation_m") is not None:
        return float(water_source["sump_elevation_m"])
    elev = float(loc.get("elevation_m", 0.0) or 0.0)
    drawdown = water_source.get("dynamic_water_level_m")
    if drawdown is None:
        drawdown = water_source.get("static_water_level_m")
    return elev - float(drawdown) if drawdown is not None else elev


def elevation_lookup(lat: float, lon: float) -> float | None:
    """Pluggable DEM/SRTM elevation hook.

    Returns ``None`` by default (offline / no DEM bundled). The survey app is the
    primary source of ``elevation_m``; wire a real DEM provider here when one is
    available without making it a hard dependency.
    """
    del lat, lon
    return None


_GPS_SOURCES = frozenset({"gps_straight", "gps_track"})


def fill_link_lengths(
    fts: dict,
    *,
    overwrite_missing_only: bool = True,
    dem: Callable[[float, float], float | None] | None = None,
) -> dict:
    """Populate ``link.length_m`` from node GPS where appropriate (Stage B).

    Mutates and returns ``fts``. A link length is (re)computed from its endpoint
    node locations when the length is missing, or when ``overwrite_missing_only``
    is False and the link's ``length_source`` is a GPS source (``gps_straight`` /
    ``gps_track``) — measured (``manual``/``manual_tape``) lengths are preserved.
    Optionally fills missing node ``elevation_m`` from a ``dem`` callback.
    """
    node_loc: dict[str, dict] = {}
    for node in fts.get("nodes", []):
        loc = dict(node.get("location") or {})
        if loc.get("elevation_m") is None and dem is not None and "lat" in loc and "lon" in loc:
            elev = dem(loc["lat"], loc["lon"])
            if elev is not None:
                loc["elevation_m"] = elev
                node["location"] = loc
        node_loc[node.get("id")] = loc

    for link in fts.get("links", []):
        a = node_loc.get(link.get("from_node"))
        b = node_loc.get(link.get("to_node"))
        if not a or not b or "lat" not in a or "lat" not in b:
            continue
        has_length = link.get("length_m") is not None
        is_gps = link.get("length_source") in _GPS_SOURCES
        if has_length and (overwrite_missing_only or not is_gps):
            continue
        link["length_m"] = round(segment_length_m(a, b), 3)
        link.setdefault("length_source", "gps_straight")
    return fts
