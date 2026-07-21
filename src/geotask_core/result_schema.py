"""GeoTask Result Schema v0.3 — lightweight constants and helpers.

No Pydantic, no ORM, no heavy frameworks.
Just status constants and builder functions for the unified GeoTask Result format.
"""

# ── Status constants ──────────────────────────────────────────────────

STATUS_VERIFIED = "verified"
STATUS_CONTRADICTED = "contradicted"
STATUS_NEED_REVIEW = "need_review"
STATUS_EXTRACTED = "extracted"
STATUS_NEED_DATA = "need_data"
STATUS_INVALID_OPERATOR = "invalid_operator"
STATUS_INVALID_REFERENCE = "invalid_reference"
STATUS_MODEL_INFERRED = "model_inferred"

# ── Review reason constants ───────────────────────────────────────────

REASON_OPERATOR_REFERENCE_MISSING = "operator_reference_missing"
REASON_VALUE_NOT_FOUND = "value_not_found"
REASON_OBJECT_REFERENCE_MISSING = "object_reference_missing"
REASON_INVALID_OPERATOR = "invalid_operator"
REASON_INVALID_REFERENCE = "invalid_reference"
REASON_UNIT_MISMATCH = "unit_mismatch"
REASON_UNSUPPORTED_OPERATOR = "unsupported_operator"
REASON_AMBIGUOUS_NEGATION = "ambiguous_negation"


# ── Builder functions ─────────────────────────────────────────────────

def make_measurement(
    name: str,
    value,
    unit: str | None = None,
    object_refs: list[str] | None = None,
    verified_by: str = "",
    status: str = STATUS_EXTRACTED,
    expected_value=None,
    difference: float | None = None,
) -> dict:
    """Build a measurement entry for the unified GeoTask Result."""
    entry: dict = {
        "name": name,
        "value": value,
        "unit": unit,
        "object_refs": object_refs or [],
        "verified_by": verified_by,
        "status": status,
    }
    if expected_value is not None:
        entry["expected_value"] = expected_value
    if difference is not None:
        entry["difference"] = round(difference, 2)
    return entry


def make_conclusion(
    summary: str = "",
    external_data_used: bool = False,
    overall_status: str = STATUS_NEED_REVIEW,
    need_review: bool = False,
    review_reasons: list[str] | None = None,
) -> dict:
    """Build a conclusion entry for the unified GeoTask Result."""
    return {
        "summary": summary,
        "external_data_used": external_data_used,
        "overall_status": overall_status,
        "need_review": need_review,
        "review_reasons": review_reasons or [],
    }


def make_verified_by(
    operation: str,
    result: str,
    status: str = STATUS_EXTRACTED,
) -> dict:
    """Build a verified_by entry."""
    return {
        "operation": operation,
        "result": result,
        "status": status,
    }


def make_geotask_result(
    measurements: list[dict],
    conclusion: dict,
    verified_by: list[dict],
) -> dict:
    """Build the complete GeoTask Result dict."""
    return {
        "measurements": measurements,
        "conclusion": conclusion,
        "verified_by": verified_by,
    }


def compute_overall_status(measurements: list[dict]) -> str:
    """Derive overall_status from individual measurement statuses.

    Priority (v0.3):
        invalid_operator > invalid_reference > contradicted > need_review > need_data > verified
    """
    if any(m.get("status") == STATUS_INVALID_OPERATOR for m in measurements):
        return STATUS_INVALID_OPERATOR
    if any(m.get("status") == STATUS_INVALID_REFERENCE for m in measurements):
        return STATUS_INVALID_REFERENCE
    if any(m.get("status") == STATUS_CONTRADICTED for m in measurements):
        return STATUS_CONTRADICTED
    if any(m.get("status") == STATUS_NEED_REVIEW for m in measurements):
        return STATUS_NEED_REVIEW
    if any(m.get("status") == STATUS_NEED_DATA for m in measurements):
        return STATUS_NEED_DATA
    return STATUS_VERIFIED
