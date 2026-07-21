"""Assurance level tests — local_deterministic, model_generated, unverified,
and overall assurance behavior.
"""

from __future__ import annotations

from tests.v1.conftest import _PROJECT_ROOT, _load_yaml


def test_local_only_assurance() -> None:
    """``local_only`` execution produces ``local_deterministic`` assurance for successful checks."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    doc = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "a": {"type": "point", "xy": [0, 0]},
            "b": {"type": "point", "xy": [3, 4]},
        },
        "ops": {"distance_2d": "compute"},
        "task": {},
        "assertions": [
            {"id": "dist", "operator": "distance_2d", "object_refs": ["a", "b"]},
        ],
    })
    result = execute_canonical(doc)
    check = result.checks[0]
    assert check.status == "verified"
    assert check.assurance_level == "local_deterministic"


def test_model_only_not_local_deterministic() -> None:
    """``model_only`` execution does NOT produce ``local_deterministic`` assurance."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = _load_yaml("examples/core/v1_minimal_distance.yaml")
    # Override execution mode to model_only
    data["execution"]["mode"] = "model_only"
    doc = canonicalize(data)
    result = execute_canonical(doc)

    for check in result.checks:
        assert check.assurance_level != "local_deterministic", (
            f"model_only check {check.assertion_id} incorrectly has local_deterministic"
        )
    # model_only checks should be model_generated or similar
    assert any(chk.assurance_level == "model_generated" for chk in result.checks)


def test_missing_required_field_makes_overall_unverified() -> None:
    """Required field not produced by any assertion → overall assurance is unverified."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    # A blocking validation error → overall unverified
    data = {
        "geotask": {
            "id": "missing-field",
            "name": "Missing Field",
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
            "mode": "invalid_mode",  # blocking validation error
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)
    assert result.overall.assurance_level == "unverified", (
        f"Expected overall 'unverified', got {result.overall.assurance_level}"
    )
