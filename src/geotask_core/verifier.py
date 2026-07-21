"""GeoTask Verifier v0.3: verify normalized model output against local ops.

Enhanced from v0.2 with:
  - Invalid operator / invalid reference detection
  - Unit mismatch detection in review reasons
  - Unified status priority (invalid_op > invalid_ref > contradicted > need_review)
  - Backward compatible with v0.1/v0.2
"""

from geotask_core.runner import run_geotask
from geotask_core.operator_registry import operator_names
from geotask_core.result_schema import (
    STATUS_VERIFIED,
    STATUS_CONTRADICTED,
    STATUS_NEED_REVIEW,
    STATUS_NEED_DATA,
    STATUS_EXTRACTED,
    STATUS_INVALID_OPERATOR,
    STATUS_INVALID_REFERENCE,
    REASON_OPERATOR_REFERENCE_MISSING,
    REASON_VALUE_NOT_FOUND,
    REASON_OBJECT_REFERENCE_MISSING,
    REASON_INVALID_OPERATOR,
    REASON_INVALID_REFERENCE,
    REASON_UNIT_MISMATCH,
    REASON_UNSUPPORTED_OPERATOR,
    make_measurement,
    make_conclusion,
    make_verified_by,
    make_geotask_result,
    compute_overall_status,
)

SUPPORTED_OPERATORS = operator_names()


def verify_normalized_result(
    normalized: dict,
    geotask_data: dict,
    tolerance: float = 0.05,
) -> dict:
    """Verify normalized model output against local GeoTask deterministic results.

    Args:
        normalized: Output from normalizer.normalize_model_output().
        geotask_data: Parsed GeoTask dict (from parser.load_geotask).
        tolerance: Absolute tolerance for float comparison (default 0.05).

    Returns:
        Unified GeoTask Result dict with status-aware measurements,
        conclusion, and verified_by.
    """
    # Run local deterministic computation
    core_result = run_geotask(geotask_data)
    known_objects = set(geotask_data.get("objects", {}).keys())

    core_measurements = {m["name"]: m for m in core_result.get("measurements", [])}
    norm_measurements = {m["name"]: m for m in normalized.get("measurements", [])}

    all_names = set(core_measurements.keys()) | set(norm_measurements.keys())

    verified_measurements = []
    verified_by_list = []

    # Inherit review reasons from normalizer
    norm_conclusion = normalized.get("conclusion", {})
    review_reasons = list(norm_conclusion.get("review_reasons", []))

    for name in sorted(all_names):
        norm_m = norm_measurements.get(name)
        core_m = core_measurements.get(name)

        norm_val = norm_m["value"] if norm_m else None
        norm_op = norm_m.get("verified_by", "") if norm_m else ""

        # ── Check operator validity ──────────────────────────────────
        if norm_op and norm_op not in SUPPORTED_OPERATORS:
            # Unknown operator
            if REASON_INVALID_OPERATOR not in review_reasons:
                review_reasons.append(REASON_INVALID_OPERATOR)

        # ── Check object references ──────────────────────────────────
        obj_refs = norm_m.get("object_refs", []) if norm_m else []
        for ref in obj_refs:
            if ref and known_objects and ref not in known_objects:
                if REASON_INVALID_REFERENCE not in review_reasons:
                    review_reasons.append(REASON_INVALID_REFERENCE)

        core_val = core_m["value"] if core_m else None
        is_numeric = isinstance(core_val, (int, float)) and not isinstance(core_val, bool)
        is_bool = isinstance(core_val, bool)

        # ── Determine status ────────────────────────────────────────
        status = STATUS_NEED_REVIEW
        expected_value = core_val
        difference = None

        if norm_val is None:
            status = STATUS_NEED_REVIEW
            if REASON_VALUE_NOT_FOUND not in review_reasons:
                review_reasons.append(REASON_VALUE_NOT_FOUND)
        elif core_val is None:
            status = STATUS_NEED_REVIEW
        elif is_numeric:
            diff = abs(float(norm_val) - float(core_val))
            difference = round(diff, 2)
            if diff <= tolerance:
                status = STATUS_VERIFIED
            else:
                status = STATUS_CONTRADICTED
        elif is_bool:
            if _bool_equal(norm_val, core_val):
                status = STATUS_VERIFIED
            else:
                status = STATUS_CONTRADICTED
        else:
            if str(norm_val).lower() == str(core_val).lower():
                status = STATUS_VERIFIED
            else:
                status = STATUS_CONTRADICTED

        verified_measurements.append(
            make_measurement(
                name=name,
                value=norm_val,
                unit=norm_m.get("unit") if norm_m else core_m.get("unit") if core_m else None,
                object_refs=norm_m.get("object_refs", []) if norm_m else core_m.get("object_refs", []) if core_m else [],
                verified_by=norm_op,
                status=status,
                expected_value=expected_value,
                difference=difference,
            )
        )

    # ── Build verified_by ───────────────────────────────────────────
    for v in normalized.get("verified_by", []):
        op = v.get("operation", "")
        res = v.get("result", "")
        core_ops = [c.get("operation", "") for c in core_result.get("verified_by", [])]
        op_status = STATUS_VERIFIED if op in core_ops else STATUS_EXTRACTED
        verified_by_list.append(make_verified_by(operation=op, result=res, status=op_status))

    # ── Compute overall status ───────────────────────────────────────
    overall_status = compute_overall_status(verified_measurements)

    # Elevate to invalid_op/ref if detected in review reasons
    if REASON_INVALID_OPERATOR in review_reasons and overall_status != STATUS_CONTRADICTED:
        overall_status = STATUS_INVALID_OPERATOR
    if REASON_INVALID_REFERENCE in review_reasons and overall_status not in (STATUS_INVALID_OPERATOR, STATUS_CONTRADICTED):
        overall_status = STATUS_INVALID_REFERENCE

    need_review = (
        norm_conclusion.get("need_review", False)
        or overall_status == STATUS_NEED_REVIEW
        or any(m["status"] == STATUS_NEED_REVIEW for m in verified_measurements)
        or bool(review_reasons)
    )

    # Build summary
    parts = []
    for m in verified_measurements:
        unit_str = f" {m['unit']}" if m.get("unit") else ""
        val_str = str(m["value"]).lower() if isinstance(m["value"], bool) else m["value"]
        parts.append(f"{m['name']}={val_str}{unit_str} [{m['status']}]")
    summary = "; ".join(parts) if parts else "no measurements"

    conclusion = make_conclusion(
        summary=summary,
        external_data_used=norm_conclusion.get("external_data_used", False),
        overall_status=overall_status,
        need_review=need_review,
        review_reasons=review_reasons,
    )

    return make_geotask_result(
        measurements=verified_measurements,
        conclusion=conclusion,
        verified_by=verified_by_list,
    )


def _bool_equal(a, b) -> bool:
    """Compare two values as booleans, handling string coercion."""
    def _to_bool(v) -> bool | None:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "yes", "1")
        if isinstance(v, (int, float)):
            return bool(v)
        return None

    ba = _to_bool(a)
    bb = _to_bool(b)
    if ba is None or bb is None:
        return False
    return ba == bb
