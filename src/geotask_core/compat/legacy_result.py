"""Legacy result conversion helper.

Converts v1.0 GeotaskResult objects into the legacy output format
(measurements, conclusion, verified_by) expected by v0.x consumers.
"""


def v1_result_to_legacy(result) -> dict:
    """Convert v1.0 GeotaskResult to legacy output format (measurements, conclusion, verified_by)."""
    # Use the pre-built legacy projections if available
    if result.measurements:
        return {
            "measurements": result.measurements,
            "conclusion": result.conclusion,
            "verified_by": result.verified_by,
        }

    # Fallback: build from checks
    measurements = []
    verified_by = []
    for check in result.checks:
        measurements.append({
            "name": check.assertion_id,
            "value": check.value,
            "unit": check.unit,
            "object_refs": check.object_refs,
            "verified_by": check.operator,
        })
        verified_by.append({
            "operation": check.operator,
            "result": str(check.value).lower()
            if isinstance(check.value, bool) else str(check.value or ""),
        })

    parts = []
    for m in measurements:
        unit_str = f" {m['unit']}" if m.get("unit") else ""
        val = m["value"]
        val_str = (
            str(val).lower() if isinstance(val, bool)
            else str(val) if val is not None else "N/A"
        )
        parts.append(f"{m['name']}={val_str}{unit_str}")

    return {
        "measurements": measurements,
        "conclusion": {
            "summary": "; ".join(parts) if parts else "no measurements computed",
            "external_data_used": False,
        },
        "verified_by": verified_by,
    }
