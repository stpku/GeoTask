"""GeoTask Core installed self-diagnostic tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from geotask_core import doctor

ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _check_by_id(payload: dict, check_id: str) -> dict:
    checks = payload["geotask_core_doctor"]["checks"]
    return next(item for item in checks if item["id"] == check_id)


def test_doctor_run_passes_with_explicit_offline_boundaries() -> None:
    payload = doctor.run_doctor()
    body = payload["geotask_core_doctor"]

    assert body["schema_version"] == "0.1"
    assert body["state"] == "passed"
    assert body["valid"] is True
    assert body["summary"]["check_count"] == 10
    assert body["summary"]["failed"] == 0
    assert [item["id"] for item in body["checks"]] == [
        "package",
        "python_support",
        "schema_bundle",
        "artifact_registry",
        "operator_registry",
        "capability_registry",
        "reference_agent_bundle",
        "reference_agent_replay",
        "core_benchmark",
        "quality_benchmark",
    ]
    assert body["boundaries"] == {
        "registered_artifact": False,
        "new_schema_introduced": False,
        "new_operator_introduced": False,
        "network_used": False,
        "model_called": False,
        "external_truth_fetched": False,
        "production_system_accessed": False,
        "production_write_performed": False,
        "action_authorized": False,
        "action_executed": False,
        "core_benchmark_performance_enforced": False,
        "quality_benchmark_suite": "fixed",
    }
    assert _check_by_id(payload, "schema_bundle")["checked_count"] > 0
    assert _check_by_id(payload, "artifact_registry")["artifact_count"] > 0
    assert _check_by_id(payload, "operator_registry")["operator_count"] > 0
    assert _check_by_id(payload, "capability_registry")["capability_count"] == 9
    assert _check_by_id(payload, "reference_agent_replay")["action_executed"] is False
    assert _check_by_id(payload, "core_benchmark")["performance_enforced"] is False


def test_doctor_cli_json_text_help_and_output(tmp_path: Path) -> None:
    completed = _run_cli("inspect", "health", "--format", "json", "--compact")
    assert completed.returncode == 0, completed.stderr or completed.stdout
    body = json.loads(completed.stdout)["geotask_core_doctor"]
    assert body["valid"] is True
    assert body["summary"]["failed"] == 0

    text = _run_cli("inspect", "health")
    assert text.returncode == 0, text.stderr or text.stdout
    assert "GeoTask Core Doctor v0.1" in text.stdout
    assert "[PASS] schema_bundle" in text.stdout
    assert "not a registered GeoTask Artifact" in text.stdout

    help_result = _run_cli("inspect", "health", "--help")
    assert help_result.returncode == 0
    assert "Usage: geotask inspect health" in help_result.stdout
    assert "offline read-only" in help_result.stdout

    output = tmp_path / "doctor.json"
    written = _run_cli(
        "inspect", "health", "--format", "json", "--output", str(output)
    )
    assert written.returncode == 0, written.stderr or written.stdout
    assert written.stdout == ""
    assert json.loads(output.read_text(encoding="utf-8"))["geotask_core_doctor"]["valid"] is True


def test_doctor_schema_bundle_failure_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor,
        "verify_schema_bundle",
        lambda: {
            "schema_bundle_verification": {
                "valid": False,
                "bundle_version": "1.0",
                "checked_count": len(doctor.BUNDLED_SCHEMA_IDS),
                "diagnostics": [
                    {
                        "code": "invalid_bundled_schema",
                        "schema_id": "fixture",
                        "message": "digest mismatch",
                    }
                ],
            }
        },
    )

    payload = doctor.run_doctor()
    body = payload["geotask_core_doctor"]
    check = _check_by_id(payload, "schema_bundle")
    assert body["state"] == "failed"
    assert body["valid"] is False
    assert body["summary"]["failed"] == 1
    assert check["state"] == "failed"
    assert check["valid"] is False
    assert check["diagnostics"][0]["message"] == "digest mismatch"


def test_doctor_reference_agent_manifest_failure_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_manifest_failure(_root: Path) -> dict:
        raise doctor.ReferenceAgentActivationError(
            "installed Reference Agent activation bundle failed SHA-256 manifest verification"
        )

    monkeypatch.setattr(doctor, "verify_reference_agent_bundle", _raise_manifest_failure)

    payload = doctor.run_doctor()
    body = payload["geotask_core_doctor"]
    bundle_check = _check_by_id(payload, "reference_agent_bundle")
    replay_check = _check_by_id(payload, "reference_agent_replay")
    assert body["state"] == "failed"
    assert body["valid"] is False
    assert bundle_check["state"] == "failed"
    assert "SHA-256 manifest verification" in bundle_check["summary"]
    assert replay_check["valid"] is True


def test_doctor_check_exception_is_reported_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_registry_failure() -> dict:
        raise ValueError("registry fixture failure")

    monkeypatch.setattr(doctor, "artifact_registry_payload", _raise_registry_failure)
    payload = doctor.run_doctor()
    check = _check_by_id(payload, "artifact_registry")
    assert payload["geotask_core_doctor"]["valid"] is False
    assert check["state"] == "failed"
    assert check["diagnostics"] == [
        {
            "code": "doctor_check_failed",
            "message": "registry fixture failure",
            "exception_type": "ValueError",
        }
    ]
