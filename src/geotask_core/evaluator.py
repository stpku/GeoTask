"""GeoTask Eval v0.1: Compare GeoTask Core ground truth with LLM normalized output.

This module provides a simple evaluator that:
1. Compares deterministic GeoTask Core results with normalized LLM outputs
2. Applies a fixed 100-point scoring rubric
3. Produces a machine-readable score dict with errors and warnings

Design principle: keep it simple. No heavy frameworks, no external APIs.
"""

import math
from typing import Optional


def evaluate_model_output(
    core_result: dict,
    normalized_output: dict,
    tolerance: float = 0.01,
) -> dict:
    """Evaluate normalized LLM output against GeoTask Core ground truth.

    Args:
        core_result: Output from runner.run_geotask() -- treated as ground truth.
        normalized_output: Output from normalizer.normalize_model_output().
        tolerance: Absolute tolerance for float comparison (default 0.01).

    Returns:
        A score dict with keys: score, details, warnings, errors.

    Score dict structure:
        score:
            total: int                # 0-100
            distance_match: bool
            intersection_match: bool
            operator_match: bool
            external_data_used_match: bool
        details:
            expected_distance: float | null
            actual_distance: float | null
            expected_intersection: bool | null
            actual_intersection: bool | null
            expected_operations: list[str]
            actual_operations: list[str]
        warnings: list[str]
        errors: list[str]
    """
    core_measurements = core_result.get("measurements", [])
    norm_measurements = normalized_output.get("measurements", [])

    # Index both sides by measurement name
    core_by_name: dict[str, dict] = {m["name"]: m for m in core_measurements if m.get("name")}
    norm_by_name: dict[str, dict] = {m["name"]: m for m in norm_measurements if m.get("name")}

    # Extract expected operations from core verified_by
    expected_ops = [v.get("operation", "") for v in core_result.get("verified_by", [])]

    # Extract actual operations from normalized verified_by
    actual_ops = [v.get("operation", "") for v in normalized_output.get("verified_by", [])]

    # ── Initialize result containers ──
    warnings: list[str] = []
    errors: list[str] = []

    score = {
        "total": 0,
        "distance_match": False,
        "intersection_match": False,
        "operator_match": False,
        "external_data_used_match": False,
    }

    details = {
        "expected_distance": None,
        "actual_distance": None,
        "expected_intersection": None,
        "actual_intersection": None,
        "expected_operations": expected_ops,
        "actual_operations": actual_ops,
    }

    # ── 1. Distance comparison (40 pts) ──
    core_dist = core_by_name.get("takeoff_to_school_distance")
    norm_dist = norm_by_name.get("takeoff_to_school_distance")

    if core_dist:
        details["expected_distance"] = core_dist.get("value")
    if norm_dist:
        details["actual_distance"] = norm_dist.get("value")

    if core_dist is None:
        # No distance measurement in core → skip, don't count as error
        pass
    elif norm_dist is None:
        errors.append("distance_value_missing")
    else:
        exp_val = core_dist.get("value")
        act_val = norm_dist.get("value")
        if _float_close(exp_val, act_val, tolerance):
            score["distance_match"] = True
            score["total"] += 40
        else:
            errors.append("distance_value_mismatch")

    # ── 2. Intersection comparison (40 pts) ──
    core_int = core_by_name.get("route_intersects_zone")
    norm_int = norm_by_name.get("route_intersects_zone")

    if core_int:
        details["expected_intersection"] = core_int.get("value")
    if norm_int:
        details["actual_intersection"] = norm_int.get("value")

    if core_int is None:
        pass
    elif norm_int is None:
        errors.append("intersection_value_missing")
    else:
        if _bool_match(core_int.get("value"), norm_int.get("value")):
            score["intersection_match"] = True
            score["total"] += 40
        else:
            errors.append("intersection_value_mismatch")

    # ── 3. Operator comparison (15 pts) ──
    if _ops_contain(expected_ops, actual_ops):
        score["operator_match"] = True
        score["total"] += 15
    else:
        errors.append("operator_missing")

    # ── 4. external_data_used comparison (5 pts) ──
    core_conclusion = core_result.get("conclusion", {})
    norm_conclusion = normalized_output.get("conclusion", {})

    core_ext = core_conclusion.get("external_data_used", False)
    norm_ext = norm_conclusion.get("external_data_used")

    if norm_ext is None:
        # Missing in normalized output → assume false, give warning
        warnings.append("external_data_used_missing_assumed_false")
        norm_ext = False

    if core_ext == norm_ext:
        score["external_data_used_match"] = True
        score["total"] += 5
    else:
        errors.append("external_data_used_mismatch")

    return {
        "score": score,
        "details": details,
        "warnings": warnings,
        "errors": errors,
    }


def _float_close(a, b, tolerance: float) -> bool:
    """Check if two numeric values are close within absolute tolerance."""
    if a is None or b is None:
        return False
    if isinstance(a, bool) or isinstance(b, bool):
        return False
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return False
    return math.isclose(float(a), float(b), abs_tol=tolerance)


def _bool_match(a, b) -> bool:
    """Check if two values match as booleans, handling string coercion."""
    if a is None or b is None:
        return False
    # Normalize to python bool
    def _to_bool(v) -> Optional[bool]:
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


def _ops_contain(expected: list[str], actual: list[str]) -> bool:
    """Check that all expected operations are present in actual operations."""
    actual_norm = {_norm_op(o) for o in actual if o}
    for op in expected:
        if not op:
            continue
        if _norm_op(op) not in actual_norm:
            return False
    return True


def _norm_op(op: str) -> str:
    """Normalize an operator name for comparison."""
    return op.strip().lower().replace(" ", "_").replace("-", "_")
