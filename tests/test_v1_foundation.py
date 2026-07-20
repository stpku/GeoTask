"""Comprehensive test suite for the v1.0 Foundation Slice.

Covers all critical v1.0 capabilities: canonicalization, validation, execution,
enum handling, ID validation, and legacy backward compatibility.

All tests are self-contained and use relative path resolution against the
project root (derived from this file's location).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest
import yaml

# ── Path setup ───────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

_EXAMPLES_DIR = _PROJECT_ROOT / "examples"


# ═══════════════════════════════════════════════════════════════════════════════
#  Helper utilities
# ═══════════════════════════════════════════════════════════════════════════════


def _load_yaml(rel_path: str) -> dict:
    """Load a YAML file relative to the project root."""
    full = _PROJECT_ROOT / rel_path
    with open(full, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _find_diag(diagnostics: list[dict], *, code: str = "", path_contains: str = "") -> dict | None:
    """Find the first diagnostic matching *code* and/or *path_contains*."""
    for d in diagnostics:
        if code and d.get("code") != code:
            continue
        if path_contains and path_contains not in d.get("path", ""):
            continue
        return d
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  1–3: Validation smoke tests
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
#  4–5: Canonicalization fundamentals
# ═══════════════════════════════════════════════════════════════════════════════


def test_legacy_to_canonical() -> None:
    """Load ``geotask_core_lite.yaml``, canonicalize — objects contain takeoff/school/route/zone."""
    from geotask_core.v1.canonicalizer import canonicalize

    data = _load_yaml("examples/geotask_core_lite.yaml")
    doc = canonicalize(data)

    assert "takeoff" in doc.objects
    assert "school" in doc.objects
    assert "route" in doc.objects
    assert "zone" in doc.objects
    assert doc.objects["takeoff"].type == "point"
    assert doc.objects["route"].type == "polyline"  # line → polyline mapping


def test_canonicalize_idempotent() -> None:
    """``canonicalize(canonicalize(doc).to_dict())`` produces the same CanonicalDocument."""
    from geotask_core.v1.canonicalizer import canonicalize, document_to_dict

    data = _load_yaml("examples/geotask_core_lite.yaml")
    first = canonicalize(data)
    roundtripped = canonicalize(document_to_dict(first))

    # Compare semantically — objects, metadata, operators
    assert first.metadata.id == roundtripped.metadata.id
    assert first.metadata.name == roundtripped.metadata.name
    assert sorted(first.objects.keys()) == sorted(roundtripped.objects.keys())
    assert first.operator_set == roundtripped.operator_set
    assert first.execution.mode == roundtripped.execution.mode
    assert first._source_schema_version == roundtripped._source_schema_version


# ═══════════════════════════════════════════════════════════════════════════════
#  6–8: Legacy field mapping
# ═══════════════════════════════════════════════════════════════════════════════


def test_xy_to_coordinates() -> None:
    """Legacy point with ``xy: [1, 2]`` converts to ``data["coordinates"]: [1, 2]``."""
    from geotask_core.v1.canonicalizer import canonicalize

    doc = canonicalize({
        "ops": {},
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {"p": {"type": "point", "xy": [1, 2]}},
        "task": {},
    })
    p = doc.objects["p"]
    assert p.data.get("coordinates") == [1, 2]
    assert "xy" not in p.data  # xy should be mapped away


def test_line_to_polyline() -> None:
    """Legacy ``line`` object type maps to ``polyline`` in canonical IR."""
    from geotask_core.v1.canonicalizer import canonicalize

    doc = canonicalize({
        "ops": {"line_intersects_rect": "check"},
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "route": {"type": "line", "points": [[0, 0], [10, 10]]},
            "zone": {"type": "rect", "bbox": [0, 0, 5, 5]},
        },
        "task": {},
    })
    assert doc.objects["route"].type == "polyline"
    assert doc.objects["zone"].type == "rect"


def test_top_level_assertions_to_tasks() -> None:
    """Document with top-level ``assertions`` → they become ``tasks[0].assertions``."""
    from geotask_core.v1.canonicalizer import canonicalize

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
            {"id": "dist_ab", "operator": "distance_2d", "object_refs": ["a", "b"]},
        ],
    })
    assert len(doc.tasks) >= 1
    task_assertions = doc.tasks[0].assertions
    assert len(task_assertions) >= 1
    assert task_assertions[0].id == "dist_ab"


# ═══════════════════════════════════════════════════════════════════════════════
#  9–10: Execution correctness
# ═══════════════════════════════════════════════════════════════════════════════


def test_same_operator_called_twice() -> None:
    """Task with two ``distance_2d`` assertions on different object pairs — both produce correct values."""
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
            {"id": "dist_ab", "operator": "distance_2d", "object_refs": ["a", "b"]},
            {"id": "dist_bc", "operator": "distance_2d", "object_refs": ["b", "c"]},
        ],
    })
    result = execute_canonical(doc)
    values = {chk.assertion_id: chk.value for chk in result.checks}

    assert math.isclose(values["dist_ab"], 5.0, rel_tol=1e-6)
    assert math.isclose(values["dist_bc"], 5.0, rel_tol=1e-6)


def test_object_order_independence() -> None:
    """Swapping object references in YAML yields the same execution result."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    doc_ab = canonicalize({
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
    res_ab = execute_canonical(doc_ab)

    doc_ba = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "a": {"type": "point", "xy": [3, 4]},
            "b": {"type": "point", "xy": [0, 0]},
        },
        "ops": {"distance_2d": "compute"},
        "task": {},
        "assertions": [
            {"id": "dist", "operator": "distance_2d", "object_refs": ["b", "a"]},
        ],
    })
    res_ba = execute_canonical(doc_ba)

    assert math.isclose(res_ab.checks[0].value, res_ba.checks[0].value, rel_tol=1e-6)


# ═══════════════════════════════════════════════════════════════════════════════
#  11–13: Error handling — references, arity, types
# ═══════════════════════════════════════════════════════════════════════════════


def test_invalid_reference() -> None:
    """Assertion referencing a non-existent object → status is ``invalid_reference``."""
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
    check = result.checks[0]
    assert check.status == "invalid_reference"
    assert check.error is not None
    assert check.error["code"] == "invalid_reference"


def test_arity_mismatch() -> None:
    """``distance_2d`` with 3 ``object_refs`` → error with ``arity_mismatch``."""
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
    check = result.checks[0]
    assert check.status == "invalid_operator"
    assert check.error is not None
    assert check.error["code"] == "arity_mismatch"


def test_object_type_mismatch() -> None:
    """``distance_2d`` with point + rect → error with ``object_type_mismatch``."""
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
    check = result.checks[0]
    assert check.status == "invalid_operator"
    assert check.error is not None
    assert check.error["code"] == "object_type_mismatch"


# ═══════════════════════════════════════════════════════════════════════════════
#  14–15: Validation — duplicate IDs and cycles
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
#  16: Polyline segment handling
# ═══════════════════════════════════════════════════════════════════════════════


def test_polyline_all_segments() -> None:
    """Polyline with 3+ points — ``point_to_line_distance_2d`` checks all segments.

    Point [12, 5] to polyline [[0,0], [10,0], [10,10]]:
    - Segment 1 ([0,0]→[10,0]): projection t=1.0 → [10,0] → distance sqrt(29) ≈ 5.385
    - Segment 2 ([10,0]→[10,10]): projection t=0.5 → [10,5] → distance 2.0
    Minimum = 2.0 (closest segment is the second one).
    """
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    doc = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "query_pt": {"type": "point", "xy": [12, 5]},
            "poly": {"type": "line", "points": [[0, 0], [10, 0], [10, 10]]},
        },
        "ops": {"point_to_line_distance_2d": "distance from point to polyline"},
        "task": {},
        "assertions": [
            {"id": "ptl", "operator": "point_to_line_distance_2d",
             "object_refs": ["query_pt", "poly"]},
        ],
    })
    result = execute_canonical(doc)
    check = result.checks[0]

    # Correct multi-segment distance: minimum is 2.0 (second segment)
    assert math.isclose(check.value, 2.0, rel_tol=1e-6), (
        f"Expected min-segment distance 2.0, got {check.value:.4f}"
    )
    assert check.status == "verified"


# ═══════════════════════════════════════════════════════════════════════════════
#  17–18: Assurance levels
# ═══════════════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════════════
#  19: Output contract validation
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


# ═══════════════════════════════════════════════════════════════════════════════
#  20–21: CLI / runner backward compatibility
# ═══════════════════════════════════════════════════════════════════════════════


def test_legacy_cli_keeps_working() -> None:
    """``run_geotask`` on legacy document (no assertions) returns old-style output."""
    from geotask_core.runner import run_geotask

    data = _load_yaml("examples/geotask_core_lite.yaml")
    result = run_geotask(data)

    assert "measurements" in result
    assert "conclusion" in result
    assert "verified_by" in result
    assert len(result["measurements"]) >= 2
    assert "144.22" in result["conclusion"]["summary"]
    assert result["conclusion"]["external_data_used"] == False


def test_v1_native_execution() -> None:
    """Load ``v1_minimal_distance.yaml`` via ``run_geotask`` — returns v1.0 ``to_dict()`` format."""
    from geotask_core.runner import run_geotask

    data = _load_yaml("examples/core/v1_minimal_distance.yaml")
    result = run_geotask(data)

    # run_geotask returns legacy format for backward compat
    assert result["measurements"], "expected measurements in result"
    m = result["measurements"][0]
    assert math.isclose(m["value"], 5.0, rel_tol=0.01)
    assert m["name"] == "ab_distance"
    assert m["verified_by"] == "distance_2d"


# ═══════════════════════════════════════════════════════════════════════════════
#  22: Enum correctness
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
#  23: ID validation
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
    assert not is_valid_geotask_id("你好")                 # non-ASCII


# ═══════════════════════════════════════════════════════════════════════════════
#  24: Canonical roundtrip
# ═══════════════════════════════════════════════════════════════════════════════


def test_canonicalize_roundtrip() -> None:
    """Legacy → canonical → document_to_dict → canonicalize → same canonical."""
    from geotask_core.v1.canonicalizer import canonicalize, document_to_dict

    data = _load_yaml("examples/geotask_core_lite.yaml")
    first = canonicalize(data)
    second = canonicalize(document_to_dict(first))

    # Check objects identical
    assert sorted(first.objects.keys()) == sorted(second.objects.keys())
    for obj_id in first.objects:
        o1 = first.objects[obj_id]
        o2 = second.objects[obj_id]
        assert o1.type == o2.type
        assert o1.data == o2.data

    # Check tasks have same assertions
    assert len(first.tasks) == len(second.tasks)
    for t1, t2 in zip(first.tasks, second.tasks):
        assert len(t1.assertions) == len(t2.assertions)
        for a1, a2 in zip(t1.assertions, t2.assertions):
            assert a1.id == a2.id
            assert a1.operator == a2.operator
            assert a1.object_refs == a2.object_refs

    # Check execution
    assert first.execution.mode == second.execution.mode
    assert len(first.execution.steps) == len(second.execution.steps)

    # Check metadata
    assert first.metadata.id == second.metadata.id
    assert first.metadata.name == second.metadata.name


# ═══════════════════════════════════════════════════════════════════════════════
#  25: Boolean rejection in coordinates
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
#  Bonus: Additional smoke tests for broader v1.0 coverage
# ═══════════════════════════════════════════════════════════════════════════════


def test_execution_summary_counts() -> None:
    """Execution result summary correctly counts verified vs invalid checks."""
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
            {"id": "valid", "operator": "distance_2d", "object_refs": ["a", "b"]},
            {"id": "invalid", "operator": "distance_2d", "object_refs": ["a", "ghost"]},
        ],
    })
    result = execute_canonical(doc)
    assert result.summary.total_checks == 2
    assert result.summary.verified == 1
    assert result.summary.invalid == 1


def test_depends_on_skip() -> None:
    """Assertion whose dependency fails is skipped."""
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
        # Use empty steps so executor uses task-based iteration (no step on_error break)
        "execution": {"mode": "local_only", "steps": []},
        "assertions": [
            {"id": "bad", "operator": "distance_2d", "object_refs": ["a", "ghost"], "on_error": "continue"},
            {"id": "dep", "operator": "distance_2d", "object_refs": ["a", "a"], "depends_on": ["bad"]},
        ],
    })
    result = execute_canonical(doc)
    dep_check = next((c for c in result.checks if c.assertion_id == "dep"), None)
    assert dep_check is not None, f"Expected 'dep' assertion in checks, got: {[c.assertion_id for c in result.checks]}"
    assert dep_check.status == "skipped"


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
