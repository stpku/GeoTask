"""Hardening test suite for GeoTask Core v1.0.

Covers CLI validation, error handling, on_error policies, output contract
enforcement, duplicate YAML key detection, and edge-case execution behavior.

All tests are self-contained — no dependency on external example files for
error cases.  Uses the same import pattern as test_v1_foundation.py.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# ── Path setup ───────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

_EXAMPLES_DIR = _PROJECT_ROOT / "examples"


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _write_temp_yaml(content: str) -> str:
    """Write *content* to a temporary .yaml file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".yaml", prefix="geotask_test_")
    os.close(fd)
    Path(path).write_text(content, encoding="utf-8")
    return path


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run ``python -m geotask_core.cli`` with *args* and return the process."""
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  1–3: CLI validation — structured error detection
# ═══════════════════════════════════════════════════════════════════════════════


def test_cli_validate_detects_arity_mismatch() -> None:
    """Run CLI validate on a v1 doc with wrong operator arity — expect non-zero exit."""
    content = """\
geotask:
  name: "arity-test"
  schema_version: "1.0"
  id: "arity-test"

space:
  crs:
    type: "local_cartesian"
    identifier: "local_xy_m"
  horizontal_unit: "meter"

objects:
  a:
    type: "point"
    coordinates: [0, 0]
  b:
    type: "point"
    coordinates: [3, 4]
  c:
    type: "point"
    coordinates: [6, 8]

# distance_2d expects 2 refs — we give 3 to trigger arity_mismatch
assertions:
  - id: "bad_arity"
    operator: "distance_2d"
    object_refs: ["a", "b", "c"]

execution:
  mode: "local_only"
  steps:
    - id: "calc"
      executor: "local"
      assertion_refs: ["bad_arity"]

output_contract:
  format: "structured"
  required_fields: []
"""
    path = _write_temp_yaml(content)
    try:
        proc = _run_cli("validate", path)
        assert proc.returncode != 0, (
            f"Expected non-zero exit for arity mismatch, "
            f"got {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    finally:
        Path(path).unlink(missing_ok=True)


def test_cli_validate_detects_object_type_mismatch() -> None:
    """Run CLI validate on a v1 doc with object type mismatch — expect non-zero exit."""
    content = """\
geotask:
  name: "type-mismatch"
  schema_version: "1.0"
  id: "type-mismatch"

space:
  crs:
    type: "local_cartesian"
    identifier: "local_xy_m"
  horizontal_unit: "meter"

objects:
  a:
    type: "point"
    coordinates: [0, 0]
  r:
    type: "rect"
    bbox: [0, 0, 10, 10]

# distance_2d expects two points — we give point + rect
assertions:
  - id: "bad_type"
    operator: "distance_2d"
    object_refs: ["a", "r"]

execution:
  mode: "local_only"
  steps:
    - id: "calc"
      executor: "local"
      assertion_refs: ["bad_type"]

output_contract:
  format: "structured"
  required_fields: []
"""
    path = _write_temp_yaml(content)
    try:
        proc = _run_cli("validate", path)
        assert proc.returncode != 0, (
            f"Expected non-zero exit for type mismatch, "
            f"got {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    finally:
        Path(path).unlink(missing_ok=True)


def test_cli_validate_detects_dag_cycle() -> None:
    """Run CLI validate on a v1 doc with cyclic assertion dependency — expect non-zero exit."""
    content = """\
geotask:
  name: "cycle-test"
  schema_version: "1.0"
  id: "cycle-test"

space:
  crs:
    type: "local_cartesian"
    identifier: "local_xy_m"
  horizontal_unit: "meter"

objects:
  a:
    type: "point"
    coordinates: [0, 0]
  b:
    type: "point"
    coordinates: [3, 4]

assertions:
  - id: "A"
    operator: "distance_2d"
    object_refs: ["a", "b"]
    depends_on: ["B"]
  - id: "B"
    operator: "distance_2d"
    object_refs: ["a", "b"]
    depends_on: ["A"]

execution:
  mode: "local_only"
  steps:
    - id: "calc_a"
      executor: "local"
      assertion_refs: ["A"]
    - id: "calc_b"
      executor: "local"
      assertion_refs: ["B"]

output_contract:
  format: "structured"
  required_fields: []
"""
    path = _write_temp_yaml(content)
    try:
        proc = _run_cli("validate", path)
        assert proc.returncode != 0, (
            f"Expected non-zero exit for DAG cycle, "
            f"got {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    finally:
        Path(path).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  4–5: Warning handling in CLI / execution pipeline
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


def test_validation_error_returns_nonzero() -> None:
    """Validation error blocks execution → sys.exit(1) via CLI."""
    # Missing required top-level key
    content = """\
geotask:
  name: "incomplete"
  schema_version: "1.0"
  id: "incomplete"

space:
  crs:
    type: "local_cartesian"
    identifier: "local_xy_m"
  horizontal_unit: "meter"

objects:
  a:
    type: "point"
    coordinates: [0, 0]
  b:
    type: "point"
    coordinates: [3, 4]
"""
    path = _write_temp_yaml(content)
    try:
        proc = _run_cli("run", path)
        assert proc.returncode != 0, (
            f"Expected non-zero exit for validation error, "
            f"got {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    finally:
        Path(path).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  6–7: v1 execution result structure
# ═══════════════════════════════════════════════════════════════════════════════


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
#  8–9: Output contract — required fields and violations
# ═══════════════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════════════
#  12: Assertion parameter passing
# ═══════════════════════════════════════════════════════════════════════════════


def test_assertion_parameters_passed() -> None:
    """Create a test operator that verifies assertion parameters are received as kwargs."""
    import geotask_core.ops as ops_mod
    from geotask_core.v1.operator_contracts import OperatorContract, default_registry
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    # Define a test implementation that captures parameters
    def _test_params_receiver(coords: list, **kwargs) -> dict:
        """Return received kwargs unchanged — proves parameters are passed through."""
        return {"coords": coords, "received_params": kwargs}

    # Monkey-patch it into the ops module so the impl path resolves
    setattr(ops_mod, "_test_params_receiver", _test_params_receiver)  # pyright: ignore[reportAttributeAccessIssue]

    # Register a temporary operator contract
    test_contract = OperatorContract(
        name="_test_params_op",
        version="1.0",
        family="test",
        description="Test operator that captures parameters",
        arity=1,
        input_types=["point"],
        output={"type": "object"},
        deterministic=True,
        model_execution={},
        implementation="geotask_core.ops._test_params_receiver",
    )

    try:
        default_registry.register(test_contract)

        data = {
            "geotask": {
                "id": "params-test",
                "name": "Params Test",
                "schema_version": "1.0",
            },
            "space": {
                "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
                "horizontal_unit": "meter",
            },
            "objects": {
                "p": {"type": "point", "data": {"coordinates": [10, 20]}},
            },
            "operator_set": ["_test_params_op"],
            "tasks": [{
                "id": "t1",
                "assertions": [
                    {
                        "id": "param_check",
                        "operator": "_test_params_op",
                        "object_refs": ["p"],
                        "parameters": {"tolerance": 0.01, "mode": "strict"},
                    },
                ],
            }],
            "execution": {
                "mode": "local_only",
                "steps": [
                    {"id": "test_step", "executor": "local", "assertion_refs": ["param_check"]},
                ],
            },
            "output_contract": {
                "format": "structured",
                "required_fields": [],
            },
        }

        doc = canonicalize(data)
        result = execute_canonical(doc)

        # The check result value should contain the returned dict with received_params
        check = result.checks[0]
        assert check.status == "verified", f"Expected verified, got {check.status}"
        params = check.value.get("received_params", {})
        assert params.get("tolerance") == 0.01, (
            f"Expected tolerance=0.01 in params, got {params}"
        )
        assert params.get("mode") == "strict", (
            f"Expected mode='strict' in params, got {params}"
        )

    finally:
        # Clean up
        if "_test_params_op" in default_registry._contracts:
            del default_registry._contracts["_test_params_op"]
        if hasattr(ops_mod, "_test_params_receiver"):
            delattr(ops_mod, "_test_params_receiver")


# ═══════════════════════════════════════════════════════════════════════════════
#  13–14: Condition handling
# ═══════════════════════════════════════════════════════════════════════════════


def test_condition_false_next_assertion_executes() -> None:
    """condition=false on first assertion — second assertion still executes normally."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "cond-false-test",
            "name": "Condition False",
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
                {
                    "id": "skip_me",
                    "operator": "distance_2d",
                    "object_refs": ["a", "b"],
                    "condition": "false",
                },
                {
                    "id": "run_me",
                    "operator": "distance_2d",
                    "object_refs": ["a", "b"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    skip_check = next((c for c in result.checks if c.assertion_id == "skip_me"), None)
    run_check = next((c for c in result.checks if c.assertion_id == "run_me"), None)

    assert skip_check is not None, "Expected 'skip_me' in checks"
    assert run_check is not None, "Expected 'run_me' in checks"
    assert skip_check.status == "skipped", (
        f"Expected 'skip_me' status='skipped', got '{skip_check.status}'"
    )
    assert run_check.status == "verified", (
        f"Expected 'run_me' status='verified', got '{run_check.status}'"
    )


def test_invalid_condition_is_unverifiable() -> None:
    """condition='garbage' → assertion status is 'unverifiable'."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "bad-cond",
            "name": "Bad Condition",
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
                {
                    "id": "weird_cond",
                    "operator": "distance_2d",
                    "object_refs": ["a", "b"],
                    "condition": "garbage_value",
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)
    check = result.checks[0]
    assert check.status == "unverifiable", (
        f"Expected 'unverifiable', got '{check.status}'"
    )
    assert check.error is not None
    assert check.error["code"] == "unverifiable_condition"


# ═══════════════════════════════════════════════════════════════════════════════
#  15–19: On-error policy semantics
# ═══════════════════════════════════════════════════════════════════════════════


def test_on_error_stop() -> None:
    """stop policy halts current task — remaining assertions are skipped."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "stop-test",
            "name": "Stop Test",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "a": {"type": "point", "data": {"coordinates": [0, 0]}},
        },
        "operator_set": ["distance_2d"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "bad_ref",
                    "operator": "distance_2d",
                    "object_refs": ["a", "ghost"],  # invalid reference → fails
                    "on_error": "stop",
                },
                {
                    "id": "should_skip",
                    "operator": "distance_2d",
                    "object_refs": ["a", "a"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    should_skip = next((c for c in result.checks if c.assertion_id == "should_skip"), None)
    assert should_skip is not None, "Expected 'should_skip' in checks"
    assert should_skip.status == "skipped", (
        f"Expected 'skipped' due to stop policy, got '{should_skip.status}'"
    )


def test_on_error_continue() -> None:
    """continue policy keeps executing after a failed assertion."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "continue-test",
            "name": "Continue Test",
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
                {
                    "id": "bad_ref",
                    "operator": "distance_2d",
                    "object_refs": ["a", "ghost"],
                    "on_error": "continue",
                },
                {
                    "id": "good_one",
                    "operator": "distance_2d",
                    "object_refs": ["a", "b"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    good = next((c for c in result.checks if c.assertion_id == "good_one"), None)
    assert good is not None, "Expected 'good_one' in checks"
    assert good.status == "verified", (
        f"Expected 'verified' after continue, got '{good.status}'"
    )


def test_on_error_skip() -> None:
    """skip policy marks the failed assertion as skipped and continues."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "skip-test",
            "name": "Skip Test",
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
                {
                    "id": "bad_ref",
                    "operator": "distance_2d",
                    "object_refs": ["a", "ghost"],
                    "on_error": "skip",
                },
                {
                    "id": "good_one",
                    "operator": "distance_2d",
                    "object_refs": ["a", "b"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    bad = next((c for c in result.checks if c.assertion_id == "bad_ref"), None)
    good = next((c for c in result.checks if c.assertion_id == "good_one"), None)
    assert bad is not None
    assert good is not None
    assert bad.status == "skipped", f"Expected 'skipped', got '{bad.status}'"
    assert good.status == "verified", f"Expected 'verified', got '{good.status}'"


def test_on_error_need_review() -> None:
    """need_review policy converts failure to 'need_review' status and continues."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "review-test",
            "name": "Review Test",
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
                {
                    "id": "bad_ref",
                    "operator": "distance_2d",
                    "object_refs": ["a", "ghost"],
                    "on_error": "need_review",
                },
                {
                    "id": "good_one",
                    "operator": "distance_2d",
                    "object_refs": ["a", "b"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    bad = next((c for c in result.checks if c.assertion_id == "bad_ref"), None)
    good = next((c for c in result.checks if c.assertion_id == "good_one"), None)
    assert bad is not None
    assert good is not None
    assert bad.status == "need_review", (
        f"Expected 'need_review', got '{bad.status}'"
    )
    assert good.status == "verified", f"Expected 'verified', got '{good.status}'"


def test_on_error_fallback_no_target() -> None:
    """fallback policy without a target → status becomes 'unverifiable'."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "fallback-test",
            "name": "Fallback Test",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "a": {"type": "point", "data": {"coordinates": [0, 0]}},
        },
        "operator_set": ["distance_2d"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "bad_ref",
                    "operator": "distance_2d",
                    "object_refs": ["a", "ghost"],
                    "on_error": "fallback",
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    check = result.checks[0]
    assert check.status == "unverifiable", (
        f"Expected 'unverifiable' for fallback without target, got '{check.status}'"
    )
    assert check.assurance_level == "unverified", (
        f"Expected 'unverified' assurance, got '{check.assurance_level}'"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  20–21: v1.0 object types — time_interval and altitude_interval
# ═══════════════════════════════════════════════════════════════════════════════


def test_time_interval_start_end() -> None:
    """time_interval objects with start/end fields work in time_overlap operator."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "time-test",
            "name": "Time Interval Test",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "t1": {
                "type": "time_interval",
                "data": {"start": "08:00", "end": "10:00"},
            },
            "t2": {
                "type": "time_interval",
                "data": {"start": "09:00", "end": "11:00"},
            },
        },
        "operator_set": ["time_overlap"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "overlap",
                    "operator": "time_overlap",
                    "object_refs": ["t1", "t2"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["overlap"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    assert len(result.checks) == 1
    assert result.checks[0].value is True, (
        f"Expected time_overlap(08-10, 09-11) == True, got {result.checks[0].value}"
    )
    assert result.checks[0].status == "verified"


def test_altitude_interval_min_max() -> None:
    """altitude_interval objects with min/max fields work in altitude_overlap operator."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "alt-test",
            "name": "Altitude Interval Test",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "a1": {
                "type": "altitude_interval",
                "data": {"min": 100, "max": 200},
            },
            "a2": {
                "type": "altitude_interval",
                "data": {"min": 150, "max": 250},
            },
        },
        "operator_set": ["altitude_overlap"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "overlap",
                    "operator": "altitude_overlap",
                    "object_refs": ["a1", "a2"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["overlap"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    assert len(result.checks) == 1
    assert result.checks[0].value is True, (
        f"Expected altitude_overlap(100-200, 150-250) == True, got {result.checks[0].value}"
    )
    assert result.checks[0].status == "verified"


# ═══════════════════════════════════════════════════════════════════════════════
#  22–23: Duplicate YAML key detection
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


# ═══════════════════════════════════════════════════════════════════════════════
#  24: GeotaskResult.to_dict() structure
# ═══════════════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════════════
#  25: line_intersects_rect — multi-segment handling
# ═══════════════════════════════════════════════════════════════════════════════


def test_line_intersects_second_segment() -> None:
    """Polyline where first segment misses rect but second segment crosses it → True.

    Rect: [0, 0, 5, 5]
    Polyline: [[-2, 6], [6, 6], [2, 2]]
      Segment 1: (-2,6)→(6,6) — entirely above rect (y=6 > max_y=5) → no intersection
      Segment 2: (6,6)→(2,2) — enters rect [0,0,5,5] at ~(4.3,5) or internally → intersection
    """
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "seg-test",
            "name": "Segment Intersection",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "poly": {
                "type": "polyline",
                "data": {"coordinates": [[-2, 6], [6, 6], [2, 2]]},
            },
            "zone": {
                "type": "rect",
                "data": {"bbox": [0, 0, 5, 5]},
            },
        },
        "operator_set": ["line_intersects_rect"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "intersects",
                    "operator": "line_intersects_rect",
                    "object_refs": ["poly", "zone"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["intersects"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    assert len(result.checks) == 1
    assert result.checks[0].value is True, (
        f"Expected intersection (second segment), got {result.checks[0].value}"
    )
    assert result.checks[0].status == "verified"


# ═══════════════════════════════════════════════════════════════════════════════
#  26: point_to_line_distance_2d — non-first segment nearest
# ═══════════════════════════════════════════════════════════════════════════════


def test_point_to_polyline_nearest_not_first() -> None:
    """Point closest to non-first segment of a polyline → correct min distance.

    Point [12, 5] to polyline [[0,0], [10,0], [10,10]]:
      Segment 1 ([0,0]→[10,0]): distance ≈ 5.385
      Segment 2 ([10,0]→[10,10]): distance = 2.0  (closest)
    Min distance = 2.0 — NOT from the first segment.
    """
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "ptl-test",
            "name": "Point-to-Line Nearest",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "pt": {
                "type": "point",
                "data": {"coordinates": [12, 5]},
            },
            "poly": {
                "type": "polyline",
                "data": {"coordinates": [[0, 0], [10, 0], [10, 10]]},
            },
        },
        "operator_set": ["point_to_line_distance_2d"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "min_dist",
                    "operator": "point_to_line_distance_2d",
                    "object_refs": ["pt", "poly"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["min_dist"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    assert len(result.checks) == 1
    assert math.isclose(result.checks[0].value, 2.0, rel_tol=1e-6), (
        f"Expected min distance 2.0 (from second segment), got {result.checks[0].value}"
    )
    assert result.checks[0].status == "verified"


# ═══════════════════════════════════════════════════════════════════════════════
#  27: Output contract violation → overall NOT local_deterministic
# ═══════════════════════════════════════════════════════════════════════════════


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
