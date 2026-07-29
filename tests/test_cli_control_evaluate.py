"""CLI tests for non-executing control-profile evaluation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from geotask_core.parser import load_geotask
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical


REPO_ROOT = Path(__file__).resolve().parent.parent
GT19 = REPO_ROOT / "examples" / "core" / "uav_arrival_ground_clearance_release.yaml"
CONTROL_SCHEMA = (
    REPO_ROOT / "schemas" / "geotask-control-evaluation-v1.0.schema.json"
)


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


def _write_execution_result(tmp_path: Path) -> tuple[Path, dict]:
    document = canonicalize(load_geotask(GT19))
    result = execute_canonical(document)
    payload = result.to_dict()
    path = tmp_path / "execution-result.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path, payload


def _blocked_state() -> dict:
    return {
        "ground_zone_clear": False,
        "clearance_evidence_age_seconds": 8,
    }


def _satisfied_state() -> dict:
    return {
        "ground_zone_clear": True,
        "clearance_evidence_age_seconds": 8,
    }


def test_top_level_help_lists_control_command() -> None:
    result = _run_cli("--help")

    assert result.returncode == 0
    assert "control" in result.stdout


def test_control_help_documents_non_executing_contract() -> None:
    results = (
        _run_cli("control", "--help"),
        _run_cli("control", "evaluate", "--help"),
    )

    for result in results:
        assert result.returncode == 0
        assert "control evaluate" in result.stdout
        assert "--result" in result.stdout
        assert "--state" in result.stdout
        assert "never executes next_action" in result.stdout


def test_control_evaluate_emits_schema_valid_blocked_json(tmp_path: Path) -> None:
    result_path, _ = _write_execution_result(tmp_path)
    state_path = tmp_path / "state.yaml"
    state_path.write_text(
        yaml.safe_dump(_blocked_state(), sort_keys=False),
        encoding="utf-8",
    )

    result = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
        "--state",
        str(state_path),
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    control = payload["control_evaluation"]
    assert control["state"] == "blocked"
    assert control["gate_satisfied"] is False
    assert control["blocked_outputs"] == [
        "automatic_drop_authorization",
        "payload_release_command",
    ]
    assert control["eligible_outputs"] == []
    assert control["action_executed"] is False
    assert all(item["action_executed"] is False for item in control["evaluations"])

    schema = json.loads(CONTROL_SCHEMA.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []


def test_control_evaluate_accepts_json_state_and_compact_stdout(tmp_path: Path) -> None:
    result_path, _ = _write_execution_result(tmp_path)
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(_satisfied_state(), ensure_ascii=False),
        encoding="utf-8",
    )

    result = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
        "--state",
        str(state_path),
        "--compact",
    )

    assert result.returncode == 0
    assert "\n  " not in result.stdout
    payload = json.loads(result.stdout)
    control = payload["control_evaluation"]
    assert control["state"] == "satisfied"
    assert control["gate_satisfied"] is True
    assert control["blocked_outputs"] == []
    assert control["eligible_outputs"] == [
        "automatic_drop_authorization",
        "payload_release_command",
    ]
    assert control["action_executed"] is False


def test_control_evaluate_output_file_keeps_stdout_clean(tmp_path: Path) -> None:
    result_path, _ = _write_execution_result(tmp_path)
    state_path = tmp_path / "state.yaml"
    state_path.write_text(
        yaml.safe_dump(_blocked_state(), sort_keys=False),
        encoding="utf-8",
    )
    output_path = tmp_path / "control-result.json"

    result = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
        "--state",
        str(state_path),
        "--output",
        str(output_path),
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["control_evaluation"]["state"] == "blocked"
    assert payload["control_evaluation"]["action_executed"] is False


def test_control_evaluate_without_state_preserves_unknowns(tmp_path: Path) -> None:
    result_path, _ = _write_execution_result(tmp_path)

    result = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
    )

    assert result.returncode == 0
    control = json.loads(result.stdout)["control_evaluation"]
    assert control["state"] == "unknown"
    assert control["gate_satisfied"] is None
    assert control["unknown_identifiers"] == [
        "clearance_evidence_age_seconds",
        "ground_zone_clear",
    ]
    assert control["blocked_outputs"] == [
        "automatic_drop_authorization",
        "payload_release_command",
    ]


def test_control_evaluate_requires_result_and_rejects_unknown_options() -> None:
    missing = _run_cli("control", "evaluate", str(GT19))
    unknown = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        "result.json",
        "--execute",
    )

    for result in (missing, unknown):
        assert result.returncode != 0
        assert "control_evaluate_failed" in result.stderr
        assert "Traceback" not in result.stderr
    assert "requires --result" in missing.stderr
    assert "unknown control evaluate option" in unknown.stderr


def test_control_evaluate_rejects_malformed_and_cross_task_results(
    tmp_path: Path,
) -> None:
    result_path, payload = _write_execution_result(tmp_path)

    malformed_path = tmp_path / "malformed.json"
    malformed_path.write_text("{not-json", encoding="utf-8")
    malformed = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(malformed_path),
    )

    mismatched_payload = deepcopy(payload)
    mismatched_payload["geotask_result"]["task_id"] = "another-task"
    mismatch_path = tmp_path / "mismatch.json"
    mismatch_path.write_text(json.dumps(mismatched_payload), encoding="utf-8")
    mismatch = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(mismatch_path),
    )

    for result in (malformed, mismatch):
        assert result.returncode != 0
        assert "control_evaluate_failed" in result.stderr
        assert "Traceback" not in result.stderr
    assert "invalid JSON" in malformed.stderr
    assert "does not match document id" in mismatch.stderr


def test_control_evaluate_rejects_non_mapping_state(tmp_path: Path) -> None:
    result_path, _ = _write_execution_result(tmp_path)
    state_path = tmp_path / "state.yaml"
    state_path.write_text("- one\n- two\n", encoding="utf-8")

    result = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
        "--state",
        str(state_path),
    )

    assert result.returncode != 0
    assert "must contain an object or mapping" in result.stderr
    assert "Traceback" not in result.stderr


def test_control_evaluate_rejects_missing_or_invalid_task_files(
    tmp_path: Path,
) -> None:
    result_path, _ = _write_execution_result(tmp_path)

    missing = _run_cli(
        "control",
        "evaluate",
        str(tmp_path / "missing.yaml"),
        "--result",
        str(result_path),
    )

    invalid_task = tmp_path / "invalid.yaml"
    invalid_task.write_text("geotask: [unterminated", encoding="utf-8")
    malformed = _run_cli(
        "control",
        "evaluate",
        str(invalid_task),
        "--result",
        str(result_path),
    )

    for result in (missing, malformed):
        assert result.returncode != 0
        assert "control_evaluate_failed" in result.stderr
        assert "Traceback" not in result.stderr
    assert "GeoTask file not found" in missing.stderr
    assert "while parsing" in malformed.stderr or "expected" in malformed.stderr


def test_control_evaluate_rejects_duplicate_state_keys(tmp_path: Path) -> None:
    result_path, _ = _write_execution_result(tmp_path)

    duplicate_json = tmp_path / "duplicate-state.json"
    duplicate_json.write_text(
        '{"ground_zone_clear": false, "ground_zone_clear": true}',
        encoding="utf-8",
    )
    json_error = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
        "--state",
        str(duplicate_json),
    )

    duplicate_yaml = tmp_path / "duplicate-state.yaml"
    duplicate_yaml.write_text(
        "ground_zone_clear: false\nground_zone_clear: true\n",
        encoding="utf-8",
    )
    yaml_error = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
        "--state",
        str(duplicate_yaml),
    )

    assert json_error.returncode != 0
    assert "duplicate JSON key" in json_error.stderr
    assert "Traceback" not in json_error.stderr
    assert yaml_error.returncode != 0
    assert "duplicate key" in yaml_error.stderr
    assert "Traceback" not in yaml_error.stderr


def test_control_evaluate_rejects_duplicate_result_keys(tmp_path: Path) -> None:
    result_path, payload = _write_execution_result(tmp_path)
    canonical = json.dumps(payload, ensure_ascii=False)
    duplicate = canonical.replace(
        '"schema_version": "1.0"',
        '"schema_version": "1.0", "schema_version": "1.0"',
        1,
    )
    result_path.write_text(duplicate, encoding="utf-8")

    result = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
    )

    assert result.returncode != 0
    assert "duplicate JSON key" in result.stderr
    assert "Traceback" not in result.stderr


def test_control_evaluate_refuses_to_overwrite_input_files(tmp_path: Path) -> None:
    result_path, _ = _write_execution_result(tmp_path)
    state_path = tmp_path / "state.yaml"
    state_path.write_text(
        yaml.safe_dump(_blocked_state(), sort_keys=False),
        encoding="utf-8",
    )
    original_result = result_path.read_text(encoding="utf-8")
    original_state = state_path.read_text(encoding="utf-8")

    result_collision = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
        "--state",
        str(state_path),
        "--output",
        str(result_path),
    )
    state_collision = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
        "--state",
        str(state_path),
        "--output",
        str(state_path),
    )

    for result in (result_collision, state_collision):
        assert result.returncode != 0
        assert "must not overwrite" in result.stderr
        assert "Traceback" not in result.stderr
    assert result_path.read_text(encoding="utf-8") == original_result
    assert state_path.read_text(encoding="utf-8") == original_state


def test_control_evaluate_rejects_nonfinite_json_values(tmp_path: Path) -> None:
    result_path, payload = _write_execution_result(tmp_path)

    nonfinite_result = deepcopy(payload)
    nonfinite_result["geotask_result"]["outputs"]["unsafe"] = float("nan")
    nonfinite_result_path = tmp_path / "nonfinite-result.json"
    nonfinite_result_path.write_text(
        json.dumps(nonfinite_result, allow_nan=True),
        encoding="utf-8",
    )
    result_error = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(nonfinite_result_path),
    )

    nonfinite_state_path = tmp_path / "nonfinite-state.json"
    nonfinite_state_path.write_text('{"ground_zone_clear": NaN}', encoding="utf-8")
    state_error = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
        "--state",
        str(nonfinite_state_path),
    )

    for result in (result_error, state_error):
        assert result.returncode != 0
        assert "non-finite JSON number" in result.stderr
        assert "Traceback" not in result.stderr


def test_control_command_source_does_not_execute_canonical_or_next_action() -> None:
    source = (REPO_ROOT / "src" / "geotask_core" / "cli.py").read_text(
        encoding="utf-8"
    )
    command_source = source.split("def cmd_control", 1)[1].split(
        "def print_result", 1
    )[0]

    assert "execute_canonical" not in command_source
    assert "next_action(" not in command_source
    assert "evaluate_control_profile" in command_source
