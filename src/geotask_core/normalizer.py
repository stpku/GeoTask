"""GeoTask Normalizer v0.2: Extract structured measurements from LLM output.

Enhanced from v0.1 with:
  - Improved distance & intersection extraction (Chinese + English)
  - Negative intersection detection (不相交, does not intersect)
  - Object reference mapping (CN ↔ EN)
  - Optional geotask_data for verification pipeline
  - Avoids confusing coordinates with final distances
  - operator_reference_missing detection

When geotask_data is provided, the verifier is invoked to produce
verified / contradicted / need_review statuses.
"""

import re

from geotask_core.result_schema import (
    STATUS_EXTRACTED,
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
        If geotask_data is provided, each measurement includes status,
        expected_value, and difference (for numeric values).
        If key fields are missing, conclusion includes need_review: true.
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
        review_reasons.append("operator_reference_missing")
    if not has_line_intersects and intersection_value is not None:
        if "operator_reference_missing" not in review_reasons:
            review_reasons.append("operator_reference_missing")

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

    # ── 7. Build conclusion ────────────────────────────────────────
    parts = []
    for m in measurements:
        unit_str = f" {m['unit']}" if m.get("unit") else ""
        val_str = str(m["value"]).lower() if isinstance(m["value"], bool) else m["value"]
        parts.append(f"{m['name']}={val_str}{unit_str}")
    summary = "; ".join(parts) if parts else "no measurements extracted"

    need_review = bool(review_reasons)

    conclusion = make_conclusion(
        summary=summary,
        external_data_used=False,
        overall_status="need_review" if need_review else "extracted",
        need_review=need_review,
        review_reasons=review_reasons,
    )

    result = make_geotask_result(
        measurements=measurements,
        conclusion=conclusion,
        verified_by=verified_by,
    )

    # ── 8. If geotask_data provided, run verifier ──────────────────
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
    # "144.22 米", "144.22m", "144.22 meter", "距离为 144.22", "distance = 144.22"
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
                # Sanity check: if the value looks like a coordinate (< 101) and
                # appears as part of coordinate syntax, skip it
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
    # If the matched text appears near coordinate pairs like [0, 0] or (120, 80)
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
    """Detect which objects are referenced in text, using CN→EN mapping.

    Args:
        text: The LLM output text.
        default_refs: Default English reference list if nothing detected.

    Returns:
        List of detected English object names, or default_refs if none found.
    """
    detected = list(default_refs)

    # Check Chinese object names
    for cn_name, en_name in CN_OBJECT_MAP.items():
        if cn_name in text and en_name not in detected:
            # Replace or add the English name
            pass  # Keep default_refs for now; mapping is informational

    # For v0.2, we keep the default refs since CN detection is fragile
    # Future versions may use smarter CN-to-EN object name resolution
    return detected
