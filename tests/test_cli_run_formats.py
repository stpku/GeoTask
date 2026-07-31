"""CLI tests for compatibility YAML and canonical v1 JSON run output."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from geotask_core.v1.result import GeotaskResult


REPO_ROOT = Path(__file__).resolve().parent.parent
GT19 = REPO_ROOT / "examples" / "core" / "uav_arrival_ground_clearance_release.yaml"
OBJECT_EXTENSIONS = REPO_ROOT / "examples" / "core" / "v1_polygon_multi_polyline.yaml"


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


def test_run_help_documents_formats_and_output() -> None:
    result = _run_cli("run", "--help")

    assert result.returncode == 0
    assert "--format yaml|v1-json" in result.stdout
    assert "--output" in result.stdout
    assert "GeotaskResult.to_dict()" in result.stdout


def test_run_docs_and_public_manifest_cover_v1_pipeline() -> None:
    docs = (REPO_ROOT / "docs" / "cli_usage.md").read_text(encoding="utf-8")
    manifest = (REPO_ROOT / ".release" / "public-manifest.yaml").read_text(
        encoding="utf-8"
    )

    assert "--format v1-json" in docs
    assert "--output execution-result.json" in docs
    assert "control evaluate task.yaml" in docs
    assert "tests/test_cli_run_formats.py" in manifest


def test_default_run_keeps_compatibility_yaml() -> None:
    result = _run_cli("run", str(GT19))

    assert result.returncode == 0
    assert result.stdout.startswith(f"[run] {GT19}\n")
    payload = yaml.safe_load(result.stdout.split("\n", 1)[1])
    assert "measurements" in payload
    assert "conclusion" in payload
    assert "geotask_result" not in payload


def test_run_v1_json_emits_clean_canonical_result() -> None:
    result = _run_cli("run", str(GT19), "--format", "v1-json")

    assert result.returncode == 0
    assert result.stderr == ""
    assert "[run]" not in result.stdout
    payload = json.loads(result.stdout)
    restored = GeotaskResult.from_dict(payload)
    result_data = payload["geotask_result"]
    assert result_data["schema_version"] == "1.0"
    assert result_data["task_id"] == "gt19-uav-arrival-ground-clearance-release"
    assert result_data["summary"]["total_checks"] == 4
    assert len(result_data["checks"]) == 4
    assert restored.to_dict() == payload


def test_run_v1_json_executes_polygon_and_multi_polyline_example() -> None:
    result = _run_cli(
        "run",
        str(OBJECT_EXTENSIONS),
        "--format",
        "v1-json",
        "--compact",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)["geotask_result"]
    assert payload["task_id"] == "polygon-multi-polyline-v1"
    assert payload["outputs"] == {
        "point_contained": True,
        "route_intersects": True,
    }
    assert {check["operator"] for check in payload["checks"]} == {
        "point_in_polygon",
        "multi_polyline_intersects_rect",
    }
    assert payload["overall"]["status"] == "verified"


def test_run_v1_json_compact_is_single_line() -> None:
    result = _run_cli(
        "run",
        str(GT19),
        "--format",
        "v1-json",
        "--compact",
    )

    assert result.returncode == 0
    assert result.stdout.count("\n") == 1
    assert "\n  " not in result.stdout
    assert json.loads(result.stdout)["geotask_result"]["schema_version"] == "1.0"


def test_run_output_file_keeps_stdout_clean(tmp_path: Path) -> None:
    output_path = tmp_path / "execution-result.json"

    result = _run_cli(
        "run",
        str(GT19),
        "--format",
        "v1-json",
        "--output",
        str(output_path),
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["geotask_result"]["task_id"] == (
        "gt19-uav-arrival-ground-clearance-release"
    )


def test_run_yaml_output_file_has_no_status_prefix(tmp_path: Path) -> None:
    output_path = tmp_path / "compat-result.yaml"

    result = _run_cli(
        "run",
        str(GT19),
        "--format",
        "yaml",
        "--output",
        str(output_path),
    )

    assert result.returncode == 0
    assert result.stdout == ""
    payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert "measurements" in payload
    assert "geotask_result" not in payload


def test_run_to_control_evaluate_forms_complete_cli_pipeline(tmp_path: Path) -> None:
    result_path = tmp_path / "execution-result.json"
    state_path = tmp_path / "control-state.yaml"
    state_path.write_text(
        "ground_zone_clear: false\nclearance_evidence_age_seconds: 8\n",
        encoding="utf-8",
    )

    run_result = _run_cli(
        "run",
        str(GT19),
        "--format",
        "v1-json",
        "--output",
        str(result_path),
    )
    control_result = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(result_path),
        "--state",
        str(state_path),
    )

    assert run_result.returncode == 0
    assert control_result.returncode == 0
    control = json.loads(control_result.stdout)["control_evaluation"]
    assert control["state"] == "blocked"
    assert control["blocked_outputs"] == [
        "automatic_drop_authorization",
        "payload_release_command",
    ]
    assert control["eligible_outputs"] == []
    assert control["action_executed"] is False


def test_run_rejects_invalid_options_without_traceback() -> None:
    cases = (
        ("--format", "xml"),
        ("--compact",),
        ("--format", "v1-json", "--format", "v1-json"),
        ("--output", "a.json", "--output", "b.json"),
        ("--unknown",),
    )

    for args in cases:
        result = _run_cli("run", str(GT19), *args)
        assert result.returncode != 0
        assert "run_failed" in result.stderr
        assert "Traceback" not in result.stderr


def test_run_refuses_to_overwrite_input_file() -> None:
    original = GT19.read_text(encoding="utf-8")

    result = _run_cli(
        "run",
        str(GT19),
        "--format",
        "v1-json",
        "--output",
        str(GT19),
    )

    assert result.returncode != 0
    assert "must not overwrite an input file" in result.stderr
    assert "Traceback" not in result.stderr
    assert GT19.read_text(encoding="utf-8") == original


def test_run_missing_or_invalid_task_has_no_traceback(tmp_path: Path) -> None:
    missing = _run_cli(
        "run",
        str(tmp_path / "missing.yaml"),
        "--format",
        "v1-json",
    )
    invalid_path = tmp_path / "invalid.yaml"
    invalid_path.write_text("geotask: [unterminated", encoding="utf-8")
    invalid = _run_cli("run", str(invalid_path), "--format", "v1-json")

    for result in (missing, invalid):
        assert result.returncode != 0
        assert "run_failed" in result.stderr
        assert "Traceback" not in result.stderr


def test_run_v1_path_uses_canonical_executor_only_when_requested() -> None:
    source = (REPO_ROOT / "src" / "geotask_core" / "cli.py").read_text(
        encoding="utf-8"
    )
    command_source = source.split("def cmd_run", 1)[1].split(
        "def cmd_normalize", 1
    )[0]

    assert 'if output_format == "v1-json"' in command_source
    assert "execute_canonical(canonicalize(data))" in command_source
    assert "result.to_dict()" in command_source
    assert "run_geotask(data)" in command_source
