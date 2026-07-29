"""Machine-readable GeoTask result schema and CLI validation tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core import (
    GEOTASK_RESULT_SCHEMA_ID,
    GEOTASK_RESULT_SCHEMA_VERSION,
)
from geotask_core.parser import load_geotask
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.result import GeotaskResult, ResultFormatError


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "geotask-result-v1.0.schema.json"
GT19 = REPO_ROOT / "examples" / "core" / "uav_arrival_ground_clearance_release.yaml"


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


def _canonical_payload() -> dict:
    document = canonicalize(load_geotask(GT19))
    return execute_canonical(document).to_dict()


def _write_payload(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "execution-result.json"
    path.write_text(
        json.dumps(payload or _canonical_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_result_schema_is_valid_draft_2020_12_and_matches_public_constants() -> None:
    schema = _schema()

    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == GEOTASK_RESULT_SCHEMA_ID
    assert schema["properties"]["geotask_result"]["$ref"] == "#/$defs/geotaskResult"
    assert GEOTASK_RESULT_SCHEMA_VERSION == "1.0"


def test_canonical_result_passes_schema_and_python_loader() -> None:
    payload = _canonical_payload()
    validator = Draft202012Validator(_schema())

    assert list(validator.iter_errors(payload)) == []
    restored = GeotaskResult.from_dict(payload)
    assert restored.to_dict() == payload
    assert restored.task_id == "gt19-uav-arrival-ground-clearance-release"
    assert len(restored.checks) == 4


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda p: p["geotask_result"].__setitem__("unexpected", True),
            "unknown field",
        ),
        (
            lambda p: p["geotask_result"]["execution"].__setitem__(
                "status", "finished"
            ),
            "must be one of",
        ),
        (
            lambda p: p["geotask_result"]["checks"][0].__setitem__(
                "executor", "shell"
            ),
            "must be one of",
        ),
        (
            lambda p: p["geotask_result"]["checks"][0].__setitem__(
                "assurance_level", "certain"
            ),
            "must be one of",
        ),
        (
            lambda p: p["geotask_result"]["summary"].__setitem__(
                "verified", -1
            ),
            "negative count",
        ),
    ],
)
def test_schema_and_python_loader_reject_same_structural_invalidities(
    mutator,
    message: str,
) -> None:
    payload = deepcopy(_canonical_payload())
    mutator(payload)

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ResultFormatError, match=message):
        GeotaskResult.from_dict(payload)


def test_python_loader_adds_cross_field_check_count_invariant() -> None:
    payload = deepcopy(_canonical_payload())
    payload["geotask_result"]["summary"]["total_checks"] += 1

    # JSON Schema cannot express equality with the sibling checks array length.
    assert list(Draft202012Validator(_schema()).iter_errors(payload)) == []
    with pytest.raises(ResultFormatError, match="must equal the number of checks"):
        GeotaskResult.from_dict(payload)


def test_result_validate_help_and_top_level_help() -> None:
    top = _run_cli("--help")
    direct = _run_cli("result", "--help")
    nested = _run_cli("result", "validate", "--help")

    assert top.returncode == 0
    assert "result" in top.stdout
    for result in (direct, nested):
        assert result.returncode == 0
        assert "result validate" in result.stdout
        assert "--format text|json" in result.stdout
        assert "without executing" in result.stdout


def test_result_validate_valid_text_report(tmp_path: Path) -> None:
    result_path = _write_payload(tmp_path)

    result = _run_cli("result", "validate", str(result_path))

    assert result.returncode == 0
    assert result.stderr == ""
    assert "Result valid:" in result.stdout
    assert GEOTASK_RESULT_SCHEMA_ID in result.stdout
    assert "gt19-uav-arrival-ground-clearance-release" in result.stdout
    assert "Checks: 4" in result.stdout


def test_result_validate_valid_json_report(tmp_path: Path) -> None:
    result_path = _write_payload(tmp_path)

    result = _run_cli(
        "result",
        "validate",
        str(result_path),
        "--format",
        "json",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    report = json.loads(result.stdout)["result_validation"]
    assert report == {
        "valid": True,
        "schema_id": GEOTASK_RESULT_SCHEMA_ID,
        "schema_version": "1.0",
        "file": str(result_path),
        "task_id": "gt19-uav-arrival-ground-clearance-release",
        "check_count": 4,
        "diagnostics": [],
    }


def test_result_validate_invalid_json_report_is_machine_readable(
    tmp_path: Path,
) -> None:
    payload = _canonical_payload()
    payload["geotask_result"]["overall"]["status"] = "approved"
    result_path = _write_payload(tmp_path, payload)

    result = _run_cli(
        "result",
        "validate",
        str(result_path),
        "--format",
        "json",
    )

    assert result.returncode != 0
    assert result.stderr == ""
    report = json.loads(result.stdout)["result_validation"]
    assert report["valid"] is False
    assert report["schema_id"] == GEOTASK_RESULT_SCHEMA_ID
    assert report["task_id"] == ""
    assert report["diagnostics"][0]["code"] == "invalid_geotask_result"
    assert "must be one of" in report["diagnostics"][0]["message"]


def test_result_validate_malformed_json_still_returns_json_report(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "malformed.json"
    result_path.write_text("{not-json", encoding="utf-8")

    result = _run_cli(
        "result",
        "validate",
        str(result_path),
        "--format",
        "json",
    )

    assert result.returncode != 0
    assert result.stderr == ""
    report = json.loads(result.stdout)["result_validation"]
    assert report["valid"] is False
    assert "invalid JSON" in report["diagnostics"][0]["message"]
    assert "Traceback" not in result.stdout


def test_result_validate_invalid_text_uses_stderr_without_traceback(
    tmp_path: Path,
) -> None:
    payload = _canonical_payload()
    payload["geotask_result"]["summary"]["total_checks"] = 99
    result_path = _write_payload(tmp_path, payload)

    result = _run_cli("result", "validate", str(result_path))

    assert result.returncode != 0
    assert result.stdout == ""
    assert "Result INVALID" in result.stderr
    assert "must equal the number of checks" in result.stderr
    assert GEOTASK_RESULT_SCHEMA_ID in result.stderr
    assert "Traceback" not in result.stderr


def test_result_validate_rejects_invalid_options() -> None:
    cases = (
        ("result", "check", "result.json"),
        ("result", "validate"),
        ("result", "validate", "result.json", "--format", "yaml"),
        (
            "result",
            "validate",
            "result.json",
            "--format",
            "json",
            "--format",
            "json",
        ),
        ("result", "validate", "result.json", "--unknown"),
    )

    for args in cases:
        result = _run_cli(*args)
        assert result.returncode != 0
        assert "result_validate_failed" in result.stderr
        assert "Traceback" not in result.stderr


def test_result_validate_command_does_not_execute_task() -> None:
    source = (REPO_ROOT / "src" / "geotask_core" / "cli.py").read_text(
        encoding="utf-8"
    )
    command_source = source.split("def cmd_result", 1)[1].split(
        "def cmd_normalize", 1
    )[0]
    shared_source = source.split("def _validate_serialized_artifact", 1)[1].split(
        "def _parse_result_validate_args", 1
    )[0]
    framework_source = (
        REPO_ROOT / "src" / "geotask_core" / "v1" / "serialized_validation.py"
    ).read_text(encoding="utf-8")

    assert "execute_canonical" not in command_source
    assert "run_geotask" not in command_source
    assert "validate_versioned_payload" in shared_source
    assert "loader=GeotaskResult.from_dict" in framework_source
