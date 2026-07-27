from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "unverifiable_constraint.yaml"


def _three_valued_and(values: list[bool | None]) -> bool | None:
    if False in values:
        return False
    if all(value is True for value in values):
        return True
    return None


def test_gt07_example_preserves_unverifiable_required_condition() -> None:
    data = load_geotask(CASE)
    errors = [
        diagnostic
        for diagnostic in validate_document(data)
        if diagnostic.get("severity", "error") == "error"
    ]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    checks = {check.assertion_id: check for check in result.checks}

    assert checks["route_intersects_zone"].value is True
    assert checks["route_intersects_zone"].status == "verified"
    assert checks["altitude_conflict"].value is True
    assert checks["altitude_conflict"].status == "verified"

    temporal = checks["temporal_conflict"]
    assert temporal.value is None
    assert temporal.status == "unverifiable"
    assert temporal.assurance_level == "unverified"
    assert temporal.error is not None
    assert temporal.error["code"] == "unverifiable_condition"
    assert result.execution.status == "partial"


def test_gt07_three_valued_and_propagates_unknown() -> None:
    data = load_geotask(CASE)
    result = execute_canonical(canonicalize(data))
    values = {check.assertion_id: check.value for check in result.checks}

    full_conflict = _three_valued_and(
        [
            values["route_intersects_zone"],
            values["altitude_conflict"],
            values["temporal_conflict"],
        ]
    )

    rule = data["extensions"]["decision_rule"]
    assert rule["logic"] == "three_valued_and"
    assert rule["unknown_policy"] == "propagate"
    assert full_conflict is None
    assert rule["expected_status"] == "unverifiable"


def test_three_valued_and_false_dominates_unknown() -> None:
    assert _three_valued_and([True, False, None]) is False
    assert _three_valued_and([True, True, True]) is True
