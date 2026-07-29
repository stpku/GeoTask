"""Result serialization tests — to_dict(), property projections,
and geotask_result key structure.
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from tests.v1.conftest import _PROJECT_ROOT, _load_yaml


def test_v1_result_has_legacy_projections() -> None:
    """``GeotaskResult`` includes ``measurements``, ``conclusion``, ``verified_by`` legacy fields."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = _load_yaml("examples/core/v1_minimal_distance.yaml")
    doc = canonicalize(data)
    result = execute_canonical(doc)

    assert len(result.measurements) >= 1
    assert "summary" in result.conclusion
    assert len(result.verified_by) >= 1


def test_v1_cli_output_contains_geotask_result() -> None:
    """Execute a v1 doc via execute_canonical — result.to_dict() contains 'geotask_result' key."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "result-key-test",
            "name": "Result Key Test",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "a": {"type": "point", "data": {"coordinates": [0, 0]}},
            "b": {"type": "point", "data": {"coordinates": [3, 4]}},
        },
        "operator_set": ["distance_2d"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {"id": "dist", "operator": "distance_2d", "object_refs": ["a", "b"]},
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["dist"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": ["dist"],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)
    d = result.to_dict()
    assert "geotask_result" in d, f"Expected 'geotask_result' key, got keys: {list(d.keys())}"
    assert d["geotask_result"]["schema_version"] == "1.0"


def test_result_to_dict() -> None:
    """GeotaskResult.to_dict() has correct structure with all expected keys."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "dict-test",
            "name": "Dict Test",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "a": {"type": "point", "data": {"coordinates": [0, 0]}},
            "b": {"type": "point", "data": {"coordinates": [3, 4]}},
        },
        "operator_set": ["distance_2d"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {"id": "dist", "operator": "distance_2d", "object_refs": ["a", "b"]},
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["dist"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": ["dist"],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)
    d = result.to_dict()

    gt_result = d["geotask_result"]
    assert gt_result["schema_version"] == "1.0"
    assert "task_id" in gt_result
    assert "execution" in gt_result
    assert "checks" in gt_result
    assert "outputs" in gt_result
    assert "summary" in gt_result
    assert "overall" in gt_result
    assert "warnings" in gt_result
    assert "errors" in gt_result

    assert gt_result["execution"]["mode"] == "local_only"
    assert len(gt_result["checks"]) == 1
    assert gt_result["checks"][0]["assertion_id"] == "dist"
    assert gt_result["summary"]["total_checks"] == 1
    assert gt_result["summary"]["verified"] == 1


def test_result_from_dict_roundtrips_canonical_shape() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical
    from geotask_core.v1.result import GeotaskResult

    data = _load_yaml("examples/core/v1_minimal_distance.yaml")
    original = execute_canonical(canonicalize(data))

    restored = GeotaskResult.from_dict(original.to_dict())

    assert restored.to_dict() == original.to_dict()
    assert restored.checks[0].assertion_id == original.checks[0].assertion_id
    assert restored.checks[0].deterministic is original.checks[0].deterministic


def test_result_from_dict_rejects_missing_unknown_and_wrong_types() -> None:
    from geotask_core.v1.result import GeotaskResult, ResultFormatError

    base = GeotaskResult(task_id="result-format-test").to_dict()

    missing = deepcopy(base)
    del missing["geotask_result"]["summary"]
    with pytest.raises(ResultFormatError, match="missing required field"):
        GeotaskResult.from_dict(missing)

    unknown = deepcopy(base)
    unknown["geotask_result"]["unexpected"] = True
    with pytest.raises(ResultFormatError, match="unknown field"):
        GeotaskResult.from_dict(unknown)

    wrong_type = deepcopy(base)
    wrong_type["geotask_result"]["checks"] = {}
    with pytest.raises(ResultFormatError, match="must be an array"):
        GeotaskResult.from_dict(wrong_type)

    negative = deepcopy(base)
    negative["geotask_result"]["summary"]["verified"] = -1
    with pytest.raises(ResultFormatError, match="negative count"):
        GeotaskResult.from_dict(negative)

    inconsistent = deepcopy(base)
    inconsistent["geotask_result"]["summary"]["total_checks"] = 1
    with pytest.raises(ResultFormatError, match="must equal the number of checks"):
        GeotaskResult.from_dict(inconsistent)


def test_result_from_dict_rejects_non_v1_schema() -> None:
    from geotask_core.v1.result import GeotaskResult, ResultFormatError

    payload = GeotaskResult(task_id="result-version-test").to_dict()
    payload["geotask_result"]["schema_version"] = "2.0"

    with pytest.raises(ResultFormatError, match="must be '1.0'"):
        GeotaskResult.from_dict(payload)
