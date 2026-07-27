from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "core" / "multi_constraint_conflict.yaml"


def test_gt06_example_validates_and_runs_three_core_assertions() -> None:
    data = load_geotask(CASE)
    errors = [d for d in validate_document(data) if d.get("severity", "error") == "error"]
    assert errors == []

    result = execute_canonical(canonicalize(data))
    values = {check.assertion_id: check.value for check in result.checks}

    assert values == {
        "route_intersects_zone": True,
        "altitude_conflict": True,
        "temporal_conflict": False,
    }
    assert all(check.status == "verified" for check in result.checks)


def test_gt06_explicit_and_rule_produces_no_full_conflict() -> None:
    data = load_geotask(CASE)
    result = execute_canonical(canonicalize(data))
    values = {check.assertion_id: bool(check.value) for check in result.checks}

    full_conflict = (
        values["route_intersects_zone"]
        and values["altitude_conflict"]
        and values["temporal_conflict"]
    )

    rule = data["extensions"]["decision_rule"]
    assert rule["expression"] == (
        "route_intersects_zone AND altitude_conflict AND temporal_conflict"
    )
    assert full_conflict is False
    assert full_conflict is rule["expected"]
