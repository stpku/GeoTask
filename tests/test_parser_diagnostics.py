"""Structured validation diagnostics for GeoTask YAML."""

import os
import subprocess
import sys
from pathlib import Path

import yaml

from geotask_core.parser import validate_geotask, validate_geotask_diagnostics


REPO_ROOT = Path(__file__).resolve().parent.parent


def _base_doc() -> dict:
    return {
        "geotask": {"version": "0.2", "name": "diag test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter", "axes": {"x": "east", "y": "north"}},
        "objects": {},
        "ops": {},
        "task": {"questions": ["Validate this document."]},
    }


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_validate_geotask_diagnostics_missing_top_level_key():
    """Structured diagnostics include path, code, message, and suggested fix."""
    data = {"geotask": {"version": "0.2", "name": "bad", "goal": "test"}}

    diagnostics = validate_geotask_diagnostics(data)

    space_diag = next(d for d in diagnostics if d["path"] == "space")
    assert space_diag["code"] == "missing_field"
    assert "Missing top-level key" in space_diag["message"]
    assert "Add a 'space' section" in space_diag["suggested_fix"]


def test_validate_geotask_diagnostics_unknown_object_type():
    """Unknown object types get a precise object path and stable code."""
    data = _base_doc()
    data["objects"] = {"bad": {"type": "polygon", "coords": []}}

    diagnostics = validate_geotask_diagnostics(data)

    diag = diagnostics[0]
    assert diag["path"] == "objects.bad.type"
    assert diag["code"] == "unknown_object_type"
    assert "polygon" in diag["message"]
    assert "point" in diag["suggested_fix"]


def test_validate_geotask_diagnostics_invalid_interval():
    """Invalid intervals expose a stable invalid_interval diagnostic."""
    data = _base_doc()
    data["objects"] = {
        "window_a": {"type": "time", "interval": ["12:00", "10:00"]},
        "window_b": {"type": "time", "interval": ["09:00", "11:00"]},
    }

    diagnostics = validate_geotask_diagnostics(data)

    diag = diagnostics[0]
    assert diag["path"] == "objects.window_a.interval"
    assert diag["code"] == "invalid_interval"
    assert "start <= end" in diag["suggested_fix"]


def test_validate_geotask_diagnostics_unknown_top_level_field():
    """Unexpected top-level keys get an explicit unknown_field diagnostic."""
    data = _base_doc()
    data["mystery"] = {"value": 1}

    diagnostics = validate_geotask_diagnostics(data)

    diag = next(d for d in diagnostics if d["path"] == "mystery")
    assert diag["code"] == "unknown_field"
    assert "Unexpected top-level field" in diag["message"]
    assert "Remove 'mystery'" in diag["suggested_fix"]


def test_validate_geotask_diagnostics_unknown_operator():
    """Unsupported ops entries surface a stable invalid_operator diagnostic."""
    data = _base_doc()
    data["ops"] = {"geo_distance": "unsupported op"}

    diagnostics = validate_geotask_diagnostics(data)

    diag = next(d for d in diagnostics if d["path"] == "ops.geo_distance")
    assert diag["code"] == "invalid_operator"
    assert "geo_distance" in diag["message"]
    assert "distance_2d" in diag["suggested_fix"]


def test_validate_geotask_diagnostics_unknown_object_field():
    """Unexpected object fields get a path-level unknown_field diagnostic."""
    data = _base_doc()
    data["objects"] = {"point_a": {"type": "point", "xy": [0, 0], "color": "red"}}

    diagnostics = validate_geotask_diagnostics(data)

    diag = next(d for d in diagnostics if d["path"] == "objects.point_a.color")
    assert diag["code"] == "unknown_field"
    assert "Unexpected field 'color'" in diag["message"]
    assert "Remove 'color'" in diag["suggested_fix"]


def test_validate_geotask_diagnostics_valid_assertions_and_expected_results():
    """Minimal public-safe assertions/expected_results sections validate cleanly."""
    data = _base_doc()
    data["objects"] = {
        "takeoff": {"type": "point", "xy": [0, 0]},
        "school": {"type": "point", "xy": [120, 80]},
    }
    data["ops"] = {"distance_2d": ""}
    data["assertions"] = [
        {
            "id": "distance_check",
            "operator": "distance_2d",
            "object_refs": ["takeoff", "school"],
        }
    ]
    data["expected_results"] = [
        {
            "name": "takeoff_to_school_distance",
            "value": 144.22,
        }
    ]

    diagnostics = validate_geotask_diagnostics(data)

    assert diagnostics == []


def test_validate_geotask_diagnostics_assertion_invalid_reference():
    """Assertion object refs must point to known objects."""
    data = _base_doc()
    data["objects"] = {"takeoff": {"type": "point", "xy": [0, 0]}}
    data["ops"] = {"distance_2d": ""}
    data["assertions"] = [
        {
            "id": "distance_check",
            "operator": "distance_2d",
            "object_refs": ["takeoff", "school"],
        }
    ]

    diagnostics = validate_geotask_diagnostics(data)

    diag = next(d for d in diagnostics if d["path"] == "assertions[0].object_refs[1]")
    assert diag["code"] == "invalid_reference"
    assert "school" in diag["message"]
    assert "known object ids" in diag["suggested_fix"]


def test_validate_geotask_diagnostics_assertion_invalid_operator():
    """Assertion operators must be registered Core operators."""
    data = _base_doc()
    data["objects"] = {"takeoff": {"type": "point", "xy": [0, 0]}}
    data["assertions"] = [
        {
            "id": "bad_check",
            "operator": "geo_distance",
            "object_refs": ["takeoff"],
        }
    ]

    diagnostics = validate_geotask_diagnostics(data)

    diag = next(d for d in diagnostics if d["path"] == "assertions[0].operator")
    assert diag["code"] == "invalid_operator"
    assert "geo_distance" in diag["message"]
    assert "distance_2d" in diag["suggested_fix"]


def test_validate_geotask_diagnostics_expected_results_missing_value():
    """Expected result entries require both a name and a value."""
    data = _base_doc()
    data["expected_results"] = [{"name": "takeoff_to_school_distance"}]

    diagnostics = validate_geotask_diagnostics(data)

    diag = next(d for d in diagnostics if d["path"] == "expected_results[0].value")
    assert diag["code"] == "missing_field"
    assert "value" in diag["message"]


def test_validate_geotask_remains_string_list_compatible():
    """Legacy validate_geotask API still returns strings with familiar fragments."""
    data = _base_doc()
    data["objects"] = {"point_a": {"type": "point"}}

    errors = validate_geotask(data)

    assert errors
    assert all(isinstance(error, str) for error in errors)
    assert any("missing" in error.lower() and ("xy" in error.lower() or "coordinates" in error.lower()) for error in errors)
    assert any("objects.point_a.xy" in error or "objects.point_a.coordinates" in error for error in errors)


def test_cli_validate_failure_prints_structured_diagnostics(tmp_path):
    """CLI validate failure includes path/code/suggested fix and no traceback."""
    data = _base_doc()
    data["objects"] = {"bad": {"type": "polygon", "coords": []}}
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    result = _run_cli("validate", str(path))
    combined = result.stdout + result.stderr

    assert result.returncode != 0
    assert "objects.bad.type" in combined
    assert "unknown_object_type" in combined
    assert "Suggested fix" in combined
    assert "Traceback" not in combined
