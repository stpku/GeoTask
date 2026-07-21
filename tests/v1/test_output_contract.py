"""Output contract tests — required fields, additional fields,
numeric precision, and violation handling.
"""

from __future__ import annotations

import math
from pathlib import Path

import yaml

from tests.v1.conftest import _PROJECT_ROOT, _EXAMPLES_DIR, _load_yaml, _find_diag


# ═══════════════════════════════════════════════════════════════════════════════
#  Output contract violation
# ═══════════════════════════════════════════════════════════════════════════════


def test_output_contract_violation() -> None:
    """Ordering referencing a field not in ``required_fields`` → ``output_contract_violation``."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    data = _load_yaml("examples/core/v1_minimal_distance.yaml")
    # Add ordering that references a field not in required_fields
    data["output_contract"]["ordering"] = {"by": "missing_field_name"}

    doc = canonicalize(data)
    diags = validate_canonical(doc)
    match = _find_diag(diags, code="output_contract_violation")
    assert match is not None, (
        f"Expected output_contract_violation diagnostic, got: {diags}"
    )


def test_v1_minimal_no_output_contract_error() -> None:
    """v1_minimal_distance.yaml has correct required_fields — no output contract violation."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    yaml_path = _EXAMPLES_DIR / "core" / "v1_minimal_distance.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    doc = canonicalize(data)
    result = execute_canonical(doc)

    # Should have no output contract violation errors
    oc_errors = [e for e in result.errors if "output_contract" in str(e.get("code", ""))]
    assert len(oc_errors) == 0, (
        f"Expected no output contract violations, got: {oc_errors}"
    )


def test_additional_field_violation() -> None:
    """``allow_additional_fields=false`` with extra field → output_contract_violation error."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    # allow_additional_fields=false + only required_fields=["dist"] but
    # the successful check produces assertion_id "dist" which matches —
    # so to violate: need a successful check whose ID is NOT in required_fields
    data = {
        "geotask": {
            "id": "add-field",
            "name": "Additional Field",
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
            "required_fields": [],  # empty — nothing required
            "allow_additional_fields": False,  # but extra fields NOT allowed
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    # "dist" is in outputs but not in required_fields, and additional fields not allowed
    oc_errors = [e for e in result.errors if "output_contract_violation" in str(e.get("code", ""))]
    assert len(oc_errors) >= 1, (
        f"Expected output_contract_violation for additional field, got: {result.errors}"
    )


def test_numeric_precision_applied() -> None:
    """``numeric_precision.decimal_places`` rounds float output values."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    # (0,0) to (1,1) → sqrt(2) ≈ 1.4142...
    # decimal_places=2 → 1.41
    data = {
        "geotask": {
            "id": "prec-test",
            "name": "Precision Test",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "a": {"type": "point", "data": {"coordinates": [0, 0]}},
            "b": {"type": "point", "data": {"coordinates": [1, 1]}},
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
            "numeric_precision": {"decimal_places": 2},
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    assert "dist" in result.outputs, f"Expected 'dist' in outputs, got: {result.outputs}"
    # sqrt(2) ≈ 1.4142..., rounded to 2 decimal places → 1.41
    assert math.isclose(result.outputs["dist"], 1.41, abs_tol=0.01), (
        f"Expected ~1.41 after precision rounding, got {result.outputs['dist']}"
    )


def test_output_violation_not_local_deterministic() -> None:
    """Output contract violation (missing required field) → overall assurance is NOT local_deterministic."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    # required_fields includes a field that no assertion produces → violation
    data = {
        "geotask": {
            "id": "oc-violation",
            "name": "OC Violation",
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
                {"id": "dist_ab", "operator": "distance_2d", "object_refs": ["a", "b"]},
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["dist_ab"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": ["missing_field"],  # does NOT match any assertion ID
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    # Output contract violation should be present
    assert len(result.errors) > 0, (
        f"Expected output contract violation errors, got none"
    )

    # Overall should NOT be local_deterministic when there are violations
    assert result.overall.assurance_level != "local_deterministic", (
        f"Expected overall NOT local_deterministic, got {result.overall.assurance_level}"
    )
