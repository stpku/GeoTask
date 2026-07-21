"""Validation tests — missing fields, invalid operators, duplicate IDs,
DAG cycles, ID patterns, enum values, YAML key detection, and more.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from tests.v1.conftest import (
    _PROJECT_ROOT,
    _EXAMPLES_DIR,
    _load_yaml,
    _find_diag,
    _write_temp_yaml,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Validation smoke tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_v1_minimal_document_validates() -> None:
    """Load ``examples/core/v1_minimal_distance.yaml``, canonicalize, validate — expect 0 diagnostics."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    data = _load_yaml("examples/core/v1_minimal_distance.yaml")
    doc = canonicalize(data)
    diags = validate_canonical(doc)
    assert diags == [], f"Expected 0 diagnostics, got: {diags}"


def test_v1_missing_execution() -> None:
    """v1.0 document without ``execution`` top-level key → validate returns missing_field for execution."""
    from geotask_core.parser import validate_geotask_diagnostics

    data = {
        "geotask": {
            "id": "missing-exec", "name": "Missing Exec", "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "p": {"type": "point", "data": {"coordinates": [0, 0]}},
        },
        "tasks": [],
        "output_contract": {"format": "structured", "required_fields": []},
    }
    diags = validate_geotask_diagnostics(data)
    match = _find_diag(diags, code="missing_field", path_contains="execution")
    assert match is not None, f"Expected missing_field for 'execution', got: {diags}"


def test_v1_missing_output_contract() -> None:
    """v1.0 document without ``output_contract`` top-level key → validate returns missing_field."""
    from geotask_core.parser import validate_geotask_diagnostics

    data = {
        "geotask": {
            "id": "missing-oc", "name": "Missing OC", "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "p": {"type": "point", "data": {"coordinates": [0, 0]}},
        },
        "tasks": [],
        "execution": {"mode": "local_only", "steps": []},
    }
    diags = validate_geotask_diagnostics(data)
    match = _find_diag(diags, code="missing_field", path_contains="output_contract")
    assert match is not None, f"Expected missing_field for 'output_contract', got: {diags}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Validation — duplicate IDs and cycles
# ═══════════════════════════════════════════════════════════════════════════════


def test_duplicate_assertion_id() -> None:
    """Two assertions with the same id → ``duplicate_id`` diagnostic."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

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
            {"id": "same_id", "operator": "distance_2d", "object_refs": ["a", "b"]},
            {"id": "same_id", "operator": "distance_2d", "object_refs": ["a", "b"]},
        ],
    })
    diags = validate_canonical(doc)
    match = _find_diag(diags, code="duplicate_id", path_contains="same_id")
    assert match is not None, f"Expected duplicate_id diagnostic, got: {diags}"


def test_cyclic_dependency() -> None:
    """Assertion A depends_on B, B depends_on A → ``cyclic_dependency`` diagnostic."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

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
            {"id": "A", "operator": "distance_2d", "object_refs": ["a", "b"], "depends_on": ["B"]},
            {"id": "B", "operator": "distance_2d", "object_refs": ["a", "b"], "depends_on": ["A"]},
        ],
    })
    diags = validate_canonical(doc)
    match = _find_diag(diags, code="cyclic_dependency")
    assert match is not None, f"Expected cyclic_dependency diagnostic, got: {diags}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Error handling — invalid references, arity, types
# ═══════════════════════════════════════════════════════════════════════════════


def test_invalid_reference() -> None:
    """Assertion referencing a non-existent object → execution blocked with errors."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    doc = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "a": {"type": "point", "xy": [0, 0]},
        },
        "ops": {"distance_2d": "compute"},
        "task": {},
        "assertions": [
            {"id": "bad_ref", "operator": "distance_2d", "object_refs": ["a", "ghost"]},
        ],
    })
    result = execute_canonical(doc)
    assert result.execution.status == "failed"
    assert result.overall.assurance_level == "unverified"
    assert len(result.errors) >= 1


def test_arity_mismatch() -> None:
    """``distance_2d`` with 3 ``object_refs`` → execution blocked with errors."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    doc = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "a": {"type": "point", "xy": [0, 0]},
            "b": {"type": "point", "xy": [3, 4]},
            "c": {"type": "point", "xy": [6, 8]},
        },
        "ops": {"distance_2d": "compute"},
        "task": {},
        "assertions": [
            {"id": "arity3", "operator": "distance_2d", "object_refs": ["a", "b", "c"]},
        ],
    })
    result = execute_canonical(doc)
    assert result.execution.status == "failed"
    assert result.overall.assurance_level == "unverified"
    assert len(result.errors) >= 1


def test_object_type_mismatch() -> None:
    """``distance_2d`` with point + rect → execution blocked with errors."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    doc = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "a": {"type": "point", "xy": [0, 0]},
            "r": {"type": "rect", "bbox": [0, 0, 10, 10]},
        },
        "ops": {"distance_2d": "compute"},
        "task": {},
        "assertions": [
            {"id": "bad_type", "operator": "distance_2d", "object_refs": ["a", "r"]},
        ],
    })
    result = execute_canonical(doc)
    assert result.execution.status == "failed"
    assert result.overall.assurance_level == "unverified"
    assert len(result.errors) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
#  Enum correctness
# ═══════════════════════════════════════════════════════════════════════════════


def test_enums_all_values() -> None:
    """Verify all v1.0 enums can be instantiated with their correct string/int values."""
    from geotask_core.v1.enums import (
        EncodingType,
        ExecutionMode,
        ExecutionStatus,
        ExecutorType,
        VerificationMode,
        AssuranceLevel,
        ClaimStatus,
        OnErrorPolicy,
        DiagnosticSeverity,
    )

    # String enums — verify values and identity
    assert EncodingType.natural_language.value == "natural_language"
    assert EncodingType.geotask_yaml.value == "geotask_yaml"
    assert EncodingType.geotask_json.value == "geotask_json"
    assert EncodingType.compact_dsl.value == "compact_dsl"

    assert ExecutionMode.model_only.value == "model_only"
    assert ExecutionMode.local_only.value == "local_only"
    assert ExecutionMode.hybrid.value == "hybrid"
    assert ExecutionMode.shadow_compare.value == "shadow_compare"

    assert ExecutionStatus.pending.value == "pending"
    assert ExecutionStatus.running.value == "running"
    assert ExecutionStatus.completed.value == "completed"
    assert ExecutionStatus.failed.value == "failed"
    assert ExecutionStatus.skipped.value == "skipped"

    assert ExecutorType.model.value == "model"
    assert ExecutorType.local.value == "local"
    assert ExecutorType.connector.value == "connector"
    assert ExecutorType.human.value == "human"

    assert VerificationMode.none.value == "none"
    assert VerificationMode.local_deterministic.value == "local_deterministic"
    assert VerificationMode.model_self_check.value == "model_self_check"
    assert VerificationMode.model_local_compare.value == "model_local_compare"
    assert VerificationMode.human_review.value == "human_review"

    # IntEnum — ordered levels
    assert AssuranceLevel.unverified.value == 0
    assert AssuranceLevel.model_generated.value == 1
    assert AssuranceLevel.model_self_checked.value == 2
    assert AssuranceLevel.local_deterministic.value == 3
    assert AssuranceLevel.model_local_agreement.value == 4
    assert AssuranceLevel.independent_cross_verified.value == 5
    assert AssuranceLevel.human_reviewed.value == 6

    assert ClaimStatus.proposed.value == "proposed"
    assert ClaimStatus.verified.value == "verified"
    assert ClaimStatus.contradicted.value == "contradicted"
    assert ClaimStatus.need_review.value == "need_review"
    assert ClaimStatus.invalid_reference.value == "invalid_reference"
    assert ClaimStatus.invalid_operator.value == "invalid_operator"
    assert ClaimStatus.execution_error.value == "execution_error"

    assert OnErrorPolicy.stop.value == "stop"
    assert OnErrorPolicy.skip.value == "skip"
    assert OnErrorPolicy.continue_.value == "continue"
    assert OnErrorPolicy.need_review.value == "need_review"
    assert OnErrorPolicy.fallback.value == "fallback"

    assert DiagnosticSeverity.error.value == "error"
    assert DiagnosticSeverity.warning.value == "warning"


# ═══════════════════════════════════════════════════════════════════════════════
#  ID validation
# ═══════════════════════════════════════════════════════════════════════════════


def test_is_valid_geotask_id() -> None:
    """Test various ID strings against ``is_valid_geotask_id``."""
    from geotask_core.v1.enums import is_valid_geotask_id

    # Valid IDs
    assert is_valid_geotask_id("a")
    assert is_valid_geotask_id("point_a")
    assert is_valid_geotask_id("takeoff")
    assert is_valid_geotask_id("my-object.id_123")
    assert is_valid_geotask_id("A" * 128)  # max length
    assert is_valid_geotask_id("Z")

    # Invalid IDs
    assert not is_valid_geotask_id("")                    # empty
    assert not is_valid_geotask_id("1starts_with_digit")  # starts with digit
    assert not is_valid_geotask_id("-dash_first")         # starts with dash
    assert not is_valid_geotask_id(".dot_first")          # starts with dot
    assert not is_valid_geotask_id("_underscore_first")   # starts with underscore
    assert not is_valid_geotask_id("has space")           # contains space
    assert not is_valid_geotask_id("has!bang")            # contains special char
    assert not is_valid_geotask_id("A" * 129)             # too long
    assert not is_valid_geotask_id("\u4f60\u597d")        # non-ASCII


# ═══════════════════════════════════════════════════════════════════════════════
#  Boolean rejection in coordinates
# ═══════════════════════════════════════════════════════════════════════════════


def test_bool_not_number() -> None:
    """Object coordinates must not accept boolean values (``True`` / ``False``) as numbers."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    doc = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "bad_point": {"type": "point", "xy": [True, 0]},
        },
        "ops": {},
        "task": {},
    })
    diags = validate_canonical(doc)
    # Expect invalid_coordinates because True is bool, not a finite number
    coord_issues = [d for d in diags if d.get("code") == "invalid_coordinates"]
    assert len(coord_issues) >= 1, (
        f"Expected invalid_coordinates diagnostic for boolean coordinate, got: {diags}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Operator registry check
# ═══════════════════════════════════════════════════════════════════════════════


def test_operator_registry_has_six_operators() -> None:
    """Default operator registry contains all 6 Core operators."""
    from geotask_core.v1.operator_contracts import default_registry

    names = default_registry.list_names()
    assert "distance_2d" in names
    assert "line_intersects_rect" in names
    assert "point_to_line_distance_2d" in names
    assert "rect_contains_point" in names
    assert "time_overlap" in names
    assert "altitude_overlap" in names
    assert len(names) == 6


# ═══════════════════════════════════════════════════════════════════════════════
#  Validator rejects invalid execution mode
# ═══════════════════════════════════════════════════════════════════════════════


def test_validator_rejects_invalid_execution_mode() -> None:
    """Validator flags invalid execution mode as ``unsupported_execution_mode``."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    data = _load_yaml("examples/core/v1_minimal_distance.yaml")
    data["execution"]["mode"] = "quantum_mode"
    doc = canonicalize(data)
    diags = validate_canonical(doc)

    match = _find_diag(diags, code="unsupported_execution_mode")
    assert match is not None, f"Expected unsupported_execution_mode, got: {diags}"


def test_validator_accepts_v1_native_schema() -> None:
    """Validator accepts a fully-formed v1.0 native document with no diagnostics."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    # Build a v1.0-native document (no legacy fields)
    data = {
        "geotask": {
            "id": "minimal-dist",
            "name": "Minimal v1.0 Distance",
            "description": "Compute distance",
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
            "family": "measurement",
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
            "required_fields": ["distance_value"],
        },
    }
    doc = canonicalize(data)
    diags = validate_canonical(doc)

    # Should have no errors (warnings are OK)
    errors = [d for d in diags if d.get("severity") == "error"]
    assert errors == [], f"Expected 0 errors, got: {errors}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Warning / error handling
# ═══════════════════════════════════════════════════════════════════════════════


def test_warning_does_not_block_cli() -> None:
    """Doc with only warnings (no errors) passes CLI validate with exit 0."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    # Build a valid v1 document — canonical validation produces only warnings
    data = {
        "geotask": {
            "id": "warning-test",
            "name": "Warning Test",
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
        # Add verification that produces a warning (unreachable assurance)
        "verification": {
            "mode": "none",
            "required_assurance": "human_reviewed",
        },
    }
    doc = canonicalize(data)
    diags = validate_canonical(doc)

    # Should have warnings but no errors
    errors = [d for d in diags if d.get("severity") == "error"]
    warnings = [d for d in diags if d.get("severity") == "warning"]
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"
    assert len(warnings) >= 1, f"Expected at least 1 warning, got: {warnings}"


def test_validation_errors_not_hidden_by_legacy() -> None:
    """v1 doc with invalid execution mode → result.errors is not empty."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "err-test",
            "name": "Error Test",
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
            "mode": "quantum_mode",  # invalid — blocking error
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)
    assert len(result.errors) > 0, (
        f"Expected non-empty errors for invalid execution mode, got: {result.errors}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Duplicate YAML key detection
# ═══════════════════════════════════════════════════════════════════════════════


def test_duplicate_top_level_yaml_key() -> None:
    """Duplicate top-level YAML key raises yaml.YAMLError from load_geotask."""
    from geotask_core.parser import load_geotask

    content = """\
geotask:
  name: "first"
  schema_version: "1.0"

space:
  crs:
    type: "local_cartesian"
    identifier: "local_xy_m"
  horizontal_unit: "meter"

objects:
  a:
    type: "point"
    coordinates: [0, 0]

# Duplicate top-level key — same indentation, different sibling
geotask:
  name: "second"
  schema_version: "1.0"

tasks:
  - id: "t1"
    assertions:
      - id: "dist"
        operator: "distance_2d"
        object_refs: ["a"]

execution:
  mode: "local_only"
  steps: []

output_contract:
  format: "structured"
  required_fields: []
"""
    path = _write_temp_yaml(content)
    try:
        with pytest.raises((yaml.YAMLError, yaml.constructor.ConstructorError)):
            load_geotask(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_duplicate_nested_yaml_key() -> None:
    """Duplicate nested YAML key inside a mapping raises yaml.YAMLError from load_geotask."""
    from geotask_core.parser import load_geotask

    content = """\
geotask:
  name: "test"
  name: "duplicated"       # duplicate key inside geotask mapping
  schema_version: "1.0"

space:
  crs:
    type: "local_cartesian"
    identifier: "local_xy_m"
  horizontal_unit: "meter"

objects:
  a:
    type: "point"
    coordinates: [0, 0]

tasks:
  - id: "t1"
    assertions:
      - id: "dist"
        operator: "distance_2d"
        object_refs: ["a"]

execution:
  mode: "local_only"
  steps: []

output_contract:
  format: "structured"
  required_fields: []
"""
    path = _write_temp_yaml(content)
    try:
        with pytest.raises((yaml.YAMLError, yaml.constructor.ConstructorError)):
            load_geotask(path)
    finally:
        Path(path).unlink(missing_ok=True)
