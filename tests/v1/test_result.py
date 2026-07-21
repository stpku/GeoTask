"""Result serialization tests — to_dict(), property projections,
and geotask_result key structure.
"""

from __future__ import annotations

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
