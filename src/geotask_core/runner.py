"""Minimal GeoTask Core runner v0.3 → v1.0 bridge.

Executes spatial operations defined in a GeoTask document against
the declared objects. Enhanced with:
  - Generic operator auto-detection from ops section
  - Support for 6 operators (distance_2d, line_intersects_rect,
    point_to_line_distance_2d, rect_contains_point, time_overlap,
    altitude_overlap)
  - Object-type-based auto-pairing (not name-based)
  - v1.0 assertion-driven execution for documents with explicit
    assertions or execution sections.

For legacy documents without assertions, the original auto-detection
logic runs unchanged. For v1.0 documents (with assertions or execution),
the document is canonicalized and executed via the v1.0 pipeline.
"""

from geotask_core.ops import (
    distance_2d,
    line_intersects_rect,
    point_to_line_distance_2d,
    rect_contains_point,
    time_overlap,
    altitude_overlap,
)
from geotask_core.compat.legacy_result import v1_result_to_legacy


def run_geotask(data: dict) -> dict:
    """Run spatial operations on a parsed GeoTask document.

    When the document has an explicit 'assertions' or 'execution' section,
    delegates to the v1.0 canonicalize → validate → execute pipeline.
    Otherwise, uses legacy auto-detection (backward compatible).

    Args:
        data: Parsed GeoTask dict (from parser.load_geotask).

    Returns:
        Dict with keys: measurements, conclusion, verified_by.
    """
    # ── v1.0 path: explicit assertions or execution section ──────────
    if data.get("assertions") or data.get("execution"):
        return _run_v1(data)

    # ── Legacy path: auto-detection from ops section ─────────────────
    return _run_legacy(data)


def _run_v1(data: dict) -> dict:
    """Execute via v1.0 unified validation → canonicalize → execute pipeline.

    Validation errors with severity="error" block execution.
    Returns v1.0 ``GeotaskResult.to_dict()`` format.
    """
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical, GeotaskResult
    from geotask_core.parser import validate_document

    # ── Unified validation ──────────────────────────────────────────
    all_diags = validate_document(data)
    errors = [d for d in all_diags if d.get("severity", "error") == "error"]

    if errors:
        # Build a failed result with diagnostics in result.errors
        result = GeotaskResult(
            task_id=data.get("geotask", {}).get("name", "unknown"),
        )
        result.execution.status = "failed"
        result.overall.status = "unverifiable"
        result.overall.assurance_level = "unverified"
        for d in errors:
            result.errors.append({
                "path": d.get("path", ""),
                "code": d.get("code", ""),
                "message": d.get("message", ""),
            })
        for d in [d for d in all_diags if d.get("severity") == "warning"]:
            result.warnings.append(
                f"{d.get('path', '')}: {d.get('code', '')}: {d.get('message', '')}"
            )
        return v1_result_to_legacy(result)

    # ── Execute ─────────────────────────────────────────────────────
    doc = canonicalize(data)
    result = execute_canonical(doc)

    # Attach any warnings from validation
    for d in all_diags:
        if d.get("severity") == "warning":
            warning = (
                f"{d.get('path', '')}: {d.get('code', '')}: "
                f"{d.get('message', '')}"
            )
            if warning not in result.warnings:
                result.warnings.append(warning)

    return v1_result_to_legacy(result)


def _run_legacy(data: dict) -> dict:
    """Legacy auto-detection runner (unchanged from v0.3)."""
    objects = data.get("objects", {})
    ops_list = data.get("ops", {})
    measurements = []
    verified_by = []

    # Group objects by type
    points = {k: v for k, v in objects.items() if v.get("type") == "point"}
    lines = {k: v for k, v in objects.items() if v.get("type") == "line"}
    rects = {k: v for k, v in objects.items() if v.get("type") == "rect"}

    # Auto-detect based on ops section
    has_distance = any("distance_2d" in str(k) for k in ops_list)
    has_intersect = any("line_intersects_rect" in str(k) for k in ops_list)
    has_ptl = any("point_to_line_distance" in str(k) for k in ops_list)
    has_contains = any("rect_contains_point" in str(k) for k in ops_list)
    has_time = any("time_overlap" in str(k) for k in ops_list)
    has_alt = any("altitude_overlap" in str(k) for k in ops_list)

    # ── distance_2d: point → point ────────────────────────────────────
    if has_distance and len(points) >= 2:
        pt_names = list(points.keys())
        a, b = pt_names[0], pt_names[1]
        val = round(distance_2d(points[a]["xy"], points[b]["xy"]), 2)
        measurements.append({
            "name": f"{a}_to_{b}_distance",
            "value": val, "unit": "meter",
            "object_refs": [a, b], "verified_by": "distance_2d",
        })
        verified_by.append({"operation": "distance_2d", "result": f"{val} meter"})

    # ── line_intersects_rect: line ↔ rect ─────────────────────────────
    if has_intersect and lines and rects:
        l_name = list(lines.keys())[0]
        r_name = list(rects.keys())[0]
        val = line_intersects_rect(lines[l_name]["points"], rects[r_name]["bbox"])
        measurements.append({
            "name": f"{l_name}_intersects_{r_name}",
            "value": val, "unit": None,
            "object_refs": [l_name, r_name],
            "verified_by": "line_intersects_rect",
        })
        verified_by.append({
            "operation": "line_intersects_rect",
            "result": str(val).lower(),
        })

    # ── point_to_line_distance_2d: point ⟂ line ────────────────────────
    if has_ptl and points and lines:
        p_name = list(points.keys())[0]
        l_name = list(lines.keys())[0]
        val = round(
            point_to_line_distance_2d(
                points[p_name]["xy"], lines[l_name]["points"]
            ), 2,
        )
        measurements.append({
            "name": f"{p_name}_to_{l_name}_distance",
            "value": val, "unit": "meter",
            "object_refs": [p_name, l_name],
            "verified_by": "point_to_line_distance_2d",
        })
        verified_by.append({
            "operation": "point_to_line_distance_2d",
            "result": f"{val} meter",
        })

    # ── rect_contains_point: rect ∋ point ──────────────────────────────
    if has_contains and rects and points:
        r_name = list(rects.keys())[0]
        p_name = list(points.keys())[0]
        val = rect_contains_point(rects[r_name]["bbox"], points[p_name]["xy"])
        measurements.append({
            "name": f"{r_name}_contains_{p_name}",
            "value": val, "unit": None,
            "object_refs": [r_name, p_name],
            "verified_by": "rect_contains_point",
        })
        verified_by.append({
            "operation": "rect_contains_point",
            "result": str(val).lower(),
        })

    # ── time_overlap: time intervals ──────────────────────────────────
    if has_time:
        time_objects = {
            k: v for k, v in objects.items() if v.get("type") == "time"
        }
        if len(time_objects) >= 2:
            t_names = list(time_objects.keys())
            a, b = t_names[0], t_names[1]
            val = time_overlap(
                time_objects[a]["interval"], time_objects[b]["interval"]
            )
            measurements.append({
                "name": f"{a}_{b}_overlap",
                "value": val, "unit": None,
                "object_refs": [a, b], "verified_by": "time_overlap",
            })
            verified_by.append({
                "operation": "time_overlap",
                "result": str(val).lower(),
            })

    # ── altitude_overlap: altitude ranges ─────────────────────────────
    if has_alt:
        alt_objects = {
            k: v for k, v in objects.items() if v.get("type") == "altitude"
        }
        if len(alt_objects) >= 2:
            a_names = list(alt_objects.keys())
            a, b = a_names[0], a_names[1]
            val = altitude_overlap(
                alt_objects[a]["range"], alt_objects[b]["range"]
            )
            measurements.append({
                "name": f"{a}_{b}_overlap",
                "value": val, "unit": None,
                "object_refs": [a, b], "verified_by": "altitude_overlap",
            })
            verified_by.append({
                "operation": "altitude_overlap",
                "result": str(val).lower(),
            })

    # Build summary
    parts = []
    for m in measurements:
        unit_str = f" {m['unit']}" if m.get("unit") else ""
        val_str = (
            str(m["value"]).lower() if isinstance(m["value"], bool)
            else m["value"]
        )
        parts.append(f"{m['name']}={val_str}{unit_str}")
    summary = "; ".join(parts) if parts else "no measurements computed"

    return {
        "measurements": measurements,
        "conclusion": {"summary": summary, "external_data_used": False},
        "verified_by": verified_by,
    }


# Deprecated alias for backward compatibility
run_stir = run_geotask
