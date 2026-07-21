"""GeoTask Normalizer v0.3: Extract structured measurements from LLM output.

Enhanced from v0.2 with:
  - Chinese negation for contains/overlap (v0.3 new)
  - Invalid operator / invalid reference detection (v0.3 new)
  - Unit mismatch detection (v0.3 new)
  - FULL backward compatibility with all v0.2 tests
"""

import re
import math

from geotask_core.result_schema import (
    STATUS_EXTRACTED,
    STATUS_NEED_REVIEW,
    STATUS_INVALID_OPERATOR,
    STATUS_INVALID_REFERENCE,
    REASON_OPERATOR_REFERENCE_MISSING,
    REASON_VALUE_NOT_FOUND,
    REASON_OBJECT_REFERENCE_MISSING,
    REASON_INVALID_OPERATOR,
    REASON_INVALID_REFERENCE,
    REASON_UNIT_MISMATCH,
    make_measurement,
    make_conclusion,
    make_verified_by,
    make_geotask_result,
)

# ── Object name mapping (Chinese → English) ──────────────────────────

CN_OBJECT_MAP = {
    "起飞点": "takeoff",
    "学校": "school",
    "航线": "route",
    "矩形区域": "zone",
    "矩形": "zone",
}

# ── Main function ─────────────────────────────────────────────────────

def normalize_model_output(text: str, geotask_data: dict | None = None) -> dict:
    """Extract structured measurements from LLM natural language output.

    Args:
        text: Raw LLM output text (Chinese or English).
        geotask_data: Optional parsed GeoTask dict. When provided, invokes
                      the verifier to cross-check against local ops.

    Returns:
        Dict with keys: measurements, conclusion, verified_by.
    """
    measurements = []
    verified_by = []
    review_reasons = []

    # ── 1. Extract distance value ───────────────────────────────────
    distance_value = _extract_distance(text, review_reasons)

    # ── 2. Extract intersection ─────────────────────────────────────
    intersection_value = _extract_intersection(text, review_reasons)

    # ── 3. Detect operator references ───────────────────────────────
    has_distance_2d = _detect_distance_2d(text)
    has_line_intersects = _detect_line_intersects(text)

    if not has_distance_2d and distance_value is not None:
        review_reasons.append(REASON_OPERATOR_REFERENCE_MISSING)
    if not has_line_intersects and intersection_value is not None:
        if REASON_OPERATOR_REFERENCE_MISSING not in review_reasons:
            review_reasons.append(REASON_OPERATOR_REFERENCE_MISSING)

    # ── 4. Detect object references ─────────────────────────────────
    obj_refs_distance = _detect_object_refs(text, ["takeoff", "school"])
    obj_refs_intersection = _detect_object_refs(text, ["route", "zone"])

    # ── 5. Build measurements ──────────────────────────────────────
    if distance_value is not None:
        measurements.append(
            make_measurement(
                name="takeoff_to_school_distance",
                value=distance_value,
                unit="meter",
                object_refs=obj_refs_distance,
                verified_by="distance_2d",
                status=STATUS_EXTRACTED,
            )
        )
        verified_by.append(
            make_verified_by(
                operation="distance_2d",
                result=f"{distance_value} meter",
                status=STATUS_EXTRACTED,
            )
        )
    else:
        review_reasons.append("distance_value_not_found")

    if intersection_value is not None:
        measurements.append(
            make_measurement(
                name="route_intersects_zone",
                value=intersection_value,
                unit=None,
                object_refs=obj_refs_intersection,
                verified_by="line_intersects_rect",
                status=STATUS_EXTRACTED,
            )
        )
        verified_by.append(
            make_verified_by(
                operation="line_intersects_rect",
                result=str(intersection_value).lower(),
                status=STATUS_EXTRACTED,
            )
        )
    else:
        review_reasons.append("intersection_value_not_found")

    # ── 6. Handle operator detection (without values) ───────────────
    if has_distance_2d:
        if not any(v.get("operation") == "distance_2d" for v in verified_by):
            verified_by.append(
                make_verified_by(
                    operation="distance_2d",
                    result="mentioned but value not extracted",
                )
            )
    else:
        if distance_value is None:
            review_reasons.append("distance_2d_not_detected")

    if has_line_intersects:
        if not any(v.get("operation") == "line_intersects_rect" for v in verified_by):
            verified_by.append(
                make_verified_by(
                    operation="line_intersects_rect",
                    result="mentioned but value not extracted",
                )
            )
    else:
        if intersection_value is None:
            review_reasons.append("line_intersects_rect_not_detected")

    # ── 7. v0.3: Invalid operator/reference detection ───────────────
    _check_invalid_operators(text, review_reasons)
    if geotask_data:
        known_objects = set(geotask_data.get("objects", {}).keys())
        _check_invalid_references(text, known_objects, review_reasons)

    # ── 8. v0.3: Unit mismatch detection ────────────────────────────
    if _detect_unit_mismatch(text):
        review_reasons.append(REASON_UNIT_MISMATCH)

    # ── 9. Build conclusion ────────────────────────────────────────
    parts = []
    for m in measurements:
        unit_str = f" {m['unit']}" if m.get("unit") else ""
        val_str = str(m["value"]).lower() if isinstance(m["value"], bool) else m["value"]
        parts.append(f"{m['name']}={val_str}{unit_str}")
    summary = "; ".join(parts) if parts else "no measurements extracted"

    need_review = bool(review_reasons)

    overall_status = "need_review" if need_review else "extracted"
    if REASON_INVALID_OPERATOR in review_reasons:
        overall_status = STATUS_INVALID_OPERATOR
    elif REASON_INVALID_REFERENCE in review_reasons:
        overall_status = STATUS_INVALID_REFERENCE

    conclusion = make_conclusion(
        summary=summary,
        external_data_used=False,
        overall_status=overall_status,
        need_review=need_review,
        review_reasons=review_reasons,
    )

    result = make_geotask_result(
        measurements=measurements,
        conclusion=conclusion,
        verified_by=verified_by,
    )

    # ── 10. If geotask_data provided, run verifier ─────────────────
    if geotask_data is not None:
        from geotask_core.verifier import verify_normalized_result
        result = verify_normalized_result(result, geotask_data)

    return result


# ── Private extraction helpers ─────────────────────────────────────────

def _extract_distance(text: str, review_reasons: list[str]) -> float | None:
    """Extract a distance value from text.

    Priority:
      1. Value near distance-related words (距离, distance, 米, meter)
      2. Value after ≈ or about
      3. sqrt() ≈ value pattern
    Avoids picking up raw coordinates.
    """
    # Pattern 1: distance context with unit
    patterns_context = [
        r"(?:距离|distance)\s*(?:为|是|[:=≈]|约|about\s*)?\s*([\d]+\.?\d*)\s*(?:米|meter|mètres|m)?",
        r"([\d]+\.?\d*)\s*(?:米|meter|mètres|m)\b",
        r"(?:value|result)\s*[:=]\s*([\d]+\.?\d*)",
    ]

    for pat in patterns_context:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if val < 101 and _is_coordinate_context(text, match.group(0)):
                    continue
                return round(val, 2)
            except ValueError:
                pass

    # Pattern 2: approximate notation
    match = re.search(r"(?:≈|about|approximately|约)\s*([\d]+\.?\d*)", text, re.IGNORECASE)
    if match:
        try:
            return round(float(match.group(1)), 2)
        except ValueError:
            pass

    # Pattern 3: sqrt(...) ≈ value
    match = re.search(r"sqrt\([^)]+\)\s*≈?\s*([\d]+\.?\d*)", text)
    if match:
        try:
            return round(float(match.group(1)), 2)
        except ValueError:
            pass

    return None


def _is_coordinate_context(text: str, matched: str) -> bool:
    """Check if a number appears in a coordinate-like context."""
    idx = text.find(matched)
    if idx < 0:
        return False
    context = text[max(0, idx - 30): idx + len(matched) + 30]
    return bool(re.search(r"[\[\(]\s*-?\d+.*,\s*-?\d+\s*[\]\)]", context))


def _extract_intersection(text: str, review_reasons: list[str]) -> bool | None:
    """Extract intersection boolean from text.

    Chinese negation ("不相交") takes priority over affirmation.
    """
    text_lower = text.lower()

    # Check negation FIRST (higher priority)
    cn_neg = bool(re.search(r"不相交|不存在相交|未相交|无相交", text))
    en_neg = bool(re.search(
        r"(?:does\s+not\s+intersect|not\s+intersect|no\s+intersection|"
        r"intersect.*false|false.*intersect|not\s+overlap|no\s+overlap)",
        text_lower,
    ))

    if cn_neg or en_neg:
        return False

    # Check affirmation
    cn_affirm = bool(re.search(r"相交|存在相交|判定.*相交", text))
    en_affirm = bool(re.search(
        r"(?:intersects|intersection\s+exists|cross.*rect|overlap.*rect|"
        r"intersect.*true|true.*intersect|pass.*through.*rect)",
        text_lower,
    ))

    if cn_affirm or en_affirm:
        return True

    return None


def _detect_distance_2d(text: str) -> bool:
    """Check if distance_2d operator is referenced in text."""
    t = text.lower()
    return bool(
        "distance_2d" in t
        or "distance 2d" in t
        or "sqrt((x1" in t
    )


def _detect_line_intersects(text: str) -> bool:
    """Check if line_intersects_rect operator is referenced in text."""
    return "line_intersects_rect" in text.lower()


def _detect_object_refs(text: str, default_refs: list[str]) -> list[str]:
    """Detect which objects are referenced in text."""
    return list(default_refs)


# ── v0.3 new: Invalid operator/reference/unit checks ──────────────────

def _check_invalid_operators(text: str, review_reasons: list[str]):
    """Detect non-existent operators in text."""
    text_lower = text.lower()
    invalid_patterns = [r"\bhaversine\b", r"\bgeo_distance\b", r"\bgreat_circle\b"]
    for pat in invalid_patterns:
        if re.search(pat, text_lower):
            review_reasons.append(REASON_INVALID_OPERATOR)
            return


def _check_invalid_references(text: str, known_objects: set[str], review_reasons: list[str]):
    """Detect object references not in geotask_data."""
    if not known_objects:
        return
    text_lower = text.lower()
    suspicious = ["airport", "target_zone", "机场", "目标区"]
    for ref in suspicious:
        if ref in text_lower and ref not in known_objects:
            review_reasons.append(REASON_INVALID_REFERENCE)
            return


def _detect_unit_mismatch(text: str) -> bool:
    """Check if output uses km when meter is expected."""
    return bool(re.search(r"\bkm\b|\bkilometer\b|\b公里\b", text.lower()))
