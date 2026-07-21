"""CLI tests — validate, run, non-zero exit behavior, and v1 output format."""

from __future__ import annotations

from pathlib import Path

from tests.v1.conftest import _PROJECT_ROOT, _write_temp_yaml, _run_cli


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
