"""Minimal GeoTask Core runner.

Executes spatial operations defined in a GeoTask document against
the declared objects. For v0.1-lite, the runner auto-detects
well-known object names and computes the corresponding operations.
"""

from geotask_core.ops import distance_2d, line_intersects_rect


def run_geotask(data: dict) -> dict:
    """Run spatial operations on a parsed GeoTask document.

    Auto-detects known object pairs:
      - (takeoff, school) -> distance_2d
      - (route, zone) -> line_intersects_rect

    Args:
        data: Parsed GeoTask dict (from parser.load_geotask).

    Returns:
        Dict with keys: measurements, conclusion, verified_by.
    """
    objects = data.get("objects", {})
    measurements = []
    verified_by = []

    # Auto-detect: takeoff -> school distance
    if "takeoff" in objects and "school" in objects:
        t = objects["takeoff"]
        s = objects["school"]
        if t.get("type") == "point" and s.get("type") == "point":
            val = round(distance_2d(t["xy"], s["xy"]), 2)
            measurements.append({
                "name": "takeoff_to_school_distance",
                "value": val,
                "unit": "meter",
                "object_refs": ["takeoff", "school"],
                "verified_by": "distance_2d",
            })
            verified_by.append({
                "operation": "distance_2d",
                "result": f"{val} meter",
            })

    # Auto-detect: route <-> zone intersection
    if "route" in objects and "zone" in objects:
        r = objects["route"]
        z = objects["zone"]
        if r.get("type") == "line" and z.get("type") == "rect":
            val = line_intersects_rect(r["points"], z["bbox"])
            measurements.append({
                "name": "route_intersects_zone",
                "value": val,
                "unit": None,
                "object_refs": ["route", "zone"],
                "verified_by": "line_intersects_rect",
            })
            verified_by.append({
                "operation": "line_intersects_rect",
                "result": str(val).lower(),
            })

    # Build summary
    parts = []
    for m in measurements:
        unit_str = f" {m['unit']}" if m.get("unit") else ""
        val_str = str(m["value"]).lower() if isinstance(m["value"], bool) else m["value"]
        parts.append(f"{m['name']}={val_str}{unit_str}")
    summary = "; ".join(parts) if parts else "no measurements computed"

    return {
        "measurements": measurements,
        "conclusion": {
            "summary": summary,
            "external_data_used": False,
        },
        "verified_by": verified_by,
    }


# Deprecated alias for backward compatibility
run_stir = run_geotask
