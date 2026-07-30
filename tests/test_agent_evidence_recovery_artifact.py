"""Registered Agent evidence-recovery Artifact and Schema tests."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

import geotask_core
import geotask_core.v1 as geotask_v1
from geotask_core.parser import load_geotask
from geotask_core.v1.agent_artifacts import (
    AGENT_EVIDENCE_RECOVERY_SCHEMA_ID,
    AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION,
    AgentArtifactFormatError,
    load_agent_evidence_recovery_report,
)
from geotask_core.v1.agent_integration import recover_evidence_request
from geotask_core.v1.artifact_validation import validate_artifact_payload


ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "examples" / "core" / "evidence_request_plan.yaml"
EVIDENCE = ROOT / "examples" / "core" / "evidence_request_verified_state.yaml"
SCHEMA_PATHS = (
    ROOT / "schemas" / "geotask-agent-integration-v0.1.schema.json",
    ROOT / "schemas" / "geotask-result-v1.0.schema.json",
    ROOT / "schemas" / "geotask-control-evaluation-v1.0.schema.json",
)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _reports() -> dict[str, dict]:
    document = load_geotask(TASK)
    evidence = yaml.safe_load(EVIDENCE.read_text(encoding="utf-8"))
    return {
        "blocked": recover_evidence_request(document, {}).to_dict(),
        "recovered": recover_evidence_request(document, evidence).to_dict(),
    }


def test_recovery_schema_is_draft_2020_12_and_resolves_offline() -> None:
    schemas = [json.loads(path.read_text(encoding="utf-8")) for path in SCHEMA_PATHS]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )

    Draft202012Validator.check_schema(schemas[0])
    assert schemas[0]["$id"] == AGENT_EVIDENCE_RECOVERY_SCHEMA_ID
    assert schemas[0]["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    for payload in _reports().values():
        assert list(
            Draft202012Validator(schemas[0], registry=registry).iter_errors(payload)
        ) == []


def test_recovery_schema_identity_is_stable() -> None:
    assert AGENT_EVIDENCE_RECOVERY_SCHEMA_ID.endswith(
        "geotask-agent-integration-v0.1.schema.json"
    )
    assert AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION == "0.1"


def test_strict_loader_accepts_blocked_and_recovered_business_states() -> None:
    reports = _reports()

    blocked = load_agent_evidence_recovery_report(reports["blocked"])[
        "agent_integration"
    ]
    recovered = load_agent_evidence_recovery_report(reports["recovered"])[
        "agent_integration"
    ]

    assert blocked["state"] == "blocked"
    assert blocked["request"]["evidence_complete"] is False
    assert blocked["materialization"]["task_reexecuted"] is False
    assert blocked["resumed_execution"] is None
    assert blocked["final_control_evaluation"] is None
    assert blocked["diagnostics"]

    assert recovered["state"] == "recovered"
    assert recovered["request"]["evidence_complete"] is True
    assert recovered["materialization"]["task_reexecuted"] is True
    assert recovered["materialization"]["next_action_executed"] is False
    assert recovered["materialization"]["model_guess_used"] is False
    assert recovered["resumed_execution"] is not None
    assert recovered["final_control_evaluation"] is not None
    assert recovered["diagnostics"] == []


@pytest.mark.parametrize(
    ("state", "expected_complete", "expected_reexecuted"),
    [
        ("blocked", False, False),
        ("recovered", True, True),
    ],
)
def test_blocked_and_recovered_reports_are_valid_artifacts(
    state: str,
    expected_complete: bool,
    expected_reexecuted: bool,
) -> None:
    report = validate_artifact_payload(
        "geotask.agent-evidence-recovery",
        _reports()[state],
        file=f"{state}-recovery.json",
    ).to_dict()["artifact_validation"]

    assert report["valid"] is True
    assert report["schema_verified"] is True
    assert report["summary"]["report_state"] == state
    assert report["summary"]["evidence_complete"] is expected_complete
    assert report["summary"]["task_reexecuted"] is expected_reexecuted
    assert report["diagnostics"] == []


def test_loader_rejects_task_identity_drift() -> None:
    payload = _reports()["recovered"]
    payload["agent_integration"]["resumed_execution"]["geotask_result"][
        "task_id"
    ] = "different-task"

    with pytest.raises(AgentArtifactFormatError, match="task_id must match"):
        load_agent_evidence_recovery_report(payload)


def test_loader_rejects_automatic_action_or_model_claims() -> None:
    for field in ("next_action_executed", "model_guess_used"):
        payload = _reports()["recovered"]
        payload["agent_integration"]["materialization"][field] = True
        with pytest.raises(AgentArtifactFormatError, match=field):
            load_agent_evidence_recovery_report(payload)


def test_loader_rejects_recovered_report_without_reexecution() -> None:
    payload = _reports()["recovered"]
    body = payload["agent_integration"]
    body["resumed_execution"] = None
    body["final_control_evaluation"] = None

    with pytest.raises(AgentArtifactFormatError, match="requires resumed execution"):
        load_agent_evidence_recovery_report(payload)


def test_loader_rejects_blocked_report_without_diagnostics() -> None:
    payload = _reports()["blocked"]
    payload["agent_integration"]["diagnostics"] = []

    with pytest.raises(AgentArtifactFormatError, match="requires at least one diagnostic"):
        load_agent_evidence_recovery_report(payload)


def test_loader_rejects_summary_output_drift() -> None:
    payload = _reports()["recovered"]
    payload["agent_integration"]["summary"]["eligible_outputs"] = []

    with pytest.raises(AgentArtifactFormatError, match="eligible_outputs must match"):
        load_agent_evidence_recovery_report(payload)


def test_unified_validation_returns_normalized_invalid_report() -> None:
    payload = _reports()["recovered"]
    payload["agent_integration"]["materialization"]["model_guess_used"] = True

    report = validate_artifact_payload(
        "geotask.agent-evidence-recovery", payload
    ).to_dict()["artifact_validation"]

    assert report["valid"] is False
    assert report["schema_verified"] is True
    assert report["summary"] == {}
    assert report["diagnostics"][0]["code"] == "invalid_agent_report"
    assert "model_guess_used" in report["diagnostics"][0]["message"]


def test_cli_validates_generated_blocked_and_recovered_reports(tmp_path: Path) -> None:
    blocked_path = tmp_path / "blocked-recovery.json"
    recovered_path = tmp_path / "recovered-recovery.json"

    blocked_generate = _run_cli(
        "agent",
        "recover",
        str(TASK),
        "--evidence",
        str(tmp_path / "empty-evidence.yaml"),
        "--output",
        str(blocked_path),
        "--compact",
    )
    # The file must exist before invoking the command.
    assert blocked_generate.returncode != 0
    (tmp_path / "empty-evidence.yaml").write_text("{}\n", encoding="utf-8")
    blocked_generate = _run_cli(
        "agent",
        "recover",
        str(TASK),
        "--evidence",
        str(tmp_path / "empty-evidence.yaml"),
        "--output",
        str(blocked_path),
        "--compact",
    )
    recovered_generate = _run_cli(
        "agent",
        "recover",
        str(TASK),
        "--evidence",
        str(EVIDENCE),
        "--output",
        str(recovered_path),
        "--compact",
    )

    assert blocked_generate.returncode == 0
    assert recovered_generate.returncode == 0
    assert blocked_generate.stdout == ""
    assert recovered_generate.stdout == ""

    for path, expected_state in (
        (blocked_path, "blocked"),
        (recovered_path, "recovered"),
    ):
        result = _run_cli(
            "artifact",
            "validate",
            "geotask.agent-evidence-recovery",
            str(path),
            "--format",
            "json",
        )
        assert result.returncode == 0
        assert result.stderr == ""
        body = json.loads(result.stdout)["artifact_validation"]
        assert body["valid"] is True
        assert body["schema_verified"] is True
        assert body["summary"]["report_state"] == expected_state


def test_recovery_validation_report_self_validates() -> None:
    validation = validate_artifact_payload(
        "geotask.agent-evidence-recovery",
        _reports()["blocked"],
        file="blocked-recovery.json",
    )
    outer = validate_artifact_payload(
        "geotask.artifact-validation-report",
        validation.to_dict(),
        file="recovery-validation.json",
    ).to_dict()["artifact_validation"]

    assert outer["valid"] is True
    assert outer["schema_verified"] is True
    assert outer["summary"] == {
        "validated_artifact_id": "geotask.agent-evidence-recovery",
        "validated_artifact_valid": True,
        "diagnostic_count": 0,
    }


def test_schema_export_and_exact_registry_lookup_are_available() -> None:
    schema_result = _run_cli(
        "schema", "export", "geotask.agent-evidence-recovery", "--compact"
    )
    registry_result = _run_cli(
        "inspect",
        "schemas",
        "geotask.agent-evidence-recovery",
        "--format",
        "json",
    )

    assert schema_result.returncode == 0
    assert json.loads(schema_result.stdout)["$id"] == AGENT_EVIDENCE_RECOVERY_SCHEMA_ID
    descriptor = json.loads(registry_result.stdout)["artifact_registry"]["artifacts"][0]
    assert descriptor["artifact_id"] == "geotask.agent-evidence-recovery"
    assert descriptor["wrapper_key"] == "agent_integration"


def test_recovery_loader_is_exported_from_public_namespaces() -> None:
    for namespace in (geotask_core, geotask_v1):
        assert namespace.AGENT_EVIDENCE_RECOVERY_SCHEMA_ID == (
            AGENT_EVIDENCE_RECOVERY_SCHEMA_ID
        )
        assert namespace.AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION == "0.1"
        assert namespace.load_agent_evidence_recovery_report is (
            load_agent_evidence_recovery_report
        )
