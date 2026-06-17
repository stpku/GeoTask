"""GeoTask Normalizer v0.1: Extract structured measurements from LLM output.

This module takes unstructured natural language output from GPT / DeepSeek
and attempts to extract spatial measurements into a structured format
compatible with the runner output schema.

It is deliberately simple -- production-grade normalization should live
outside GeoTask Core.
"""

import re


def normalize_model_output(text: str) -> dict:
    """Extract structured measurements from LLM natural language output.

    Supports:
      - Distance values (144.22, 144.22 米, 144.22m, 144.22 meter)
      - Intersection detection (相交, intersects)
      - Operator references (distance_2d, line_intersects_rect)

    Args:
        text: Raw LLM output text.

    Returns:
        Dict with keys: measurements, conclusion, verified_by.
        If key fields are missing, conclusion includes need_review: true.
    """
    measurements = []
    verified_by = []
    review_reasons = []

    # --- Extract distance value ---
    # Patterns: "144.22 米", "144.22m", "144.22 meter", "≈ 144.22", "144.22"
    distance_patterns = [
        r"([\d]+\.?\d*)\s*(?:米|meter|mètres|m)(?!\w)",  # 144.22 米 / meter / m
        r"(?:≈|about|approximately|约)\s*([\d]+\.?\d*)",  # ≈ 144.22
    ]
    distance_value = None
    for pat in distance_patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            try:
                distance_value = float(match.group(1))
            except ValueError:
                pass
            break

    # Fallback: look for "sqrt(...) ≈ 144.22"
    if distance_value is None:
        match = re.search(r"sqrt\([^)]+\)\s*≈?\s*([\d]+\.?\d*)", text)
        if match:
            try:
                distance_value = float(match.group(1))
            except ValueError:
                pass

    # --- Extract intersection ---
    # Chinese: 相交, 存在相交, 判定为相交
    # English: intersects, intersection exists, is determined to intersect
    intersection_value = None
    if re.search(r"相交|存在相交|判定.*相交", text):
        intersection_value = True
    elif re.search(r"intersects|intersection\s+exists|cross.*rect|overlap.*rect", text, re.IGNORECASE):
        intersection_value = True
    elif re.search(r"(不相交|no\s+intersect|does\s+not\s+intersect)", text, re.IGNORECASE):
        intersection_value = False

    # --- Detect operator references ---
    used_distance_2d = "distance_2d" in text.lower() or "distance 2d" in text.lower() or "sqrt((x1" in text
    used_line_intersects = "line_intersects_rect" in text.lower()

    # --- Build measurements ---
    if distance_value is not None:
        measurements.append({
            "name": "takeoff_to_school_distance",
            "value": distance_value,
            "unit": "meter",
            "object_refs": ["takeoff", "school"],
            "verified_by": "distance_2d",
        })
        verified_by.append({
            "operation": "distance_2d",
            "result": f"{distance_value} meter",
        })
    else:
        review_reasons.append("distance_value_not_found")

    if intersection_value is not None:
        measurements.append({
            "name": "route_intersects_zone",
            "value": intersection_value,
            "unit": None,
            "object_refs": ["route", "zone"],
            "verified_by": "line_intersects_rect",
        })
        verified_by.append({
            "operation": "line_intersects_rect",
            "result": str(intersection_value).lower(),
        })
    else:
        review_reasons.append("intersection_value_not_found")

    # Check operator detection
    if used_distance_2d:
        if not any(v.get("operation") == "distance_2d" for v in verified_by):
            verified_by.append({
                "operation": "distance_2d",
                "result": "mentioned but value not extracted",
            })
    else:
        review_reasons.append("distance_2d_not_detected")

    if used_line_intersects:
        if not any(v.get("operation") == "line_intersects_rect" for v in verified_by):
            verified_by.append({
                "operation": "line_intersects_rect",
                "result": "mentioned but value not extracted",
            })
    else:
        review_reasons.append("line_intersects_rect_not_detected")

    # --- Build conclusion ---
    parts = []
    for m in measurements:
        unit_str = f" {m['unit']}" if m.get("unit") else ""
        val_str = str(m["value"]).lower() if isinstance(m["value"], bool) else m["value"]
        parts.append(f"{m['name']}={val_str}{unit_str}")
    summary = "; ".join(parts) if parts else "no measurements extracted"

    conclusion = {
        "summary": summary,
        "external_data_used": False,
    }

    if review_reasons:
        conclusion["need_review"] = True
        conclusion["review_reasons"] = review_reasons

    return {
        "measurements": measurements,
        "conclusion": conclusion,
        "verified_by": verified_by,
    }
