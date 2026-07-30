"""Agent Integration Profile and GT08 evidence-recovery tests."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import yaml

import geotask_core
import geotask_core.v1 as geotask_v1
from geotask_core.parser import load_geotask
from geotask_core.v1.agent_integration import (
    AGENT_INTEGRATION_PROFILE_ID,
    AGENT_INTEGRATION_PROFILE_VERSION,
    agent_integration_profile_payload,
    list_agent_tool_descriptors,
    recover_evidence_request,
)


ROOT = Path(__file__).resolve().parents[1]
GT08 = ROOT / "examples" / "core" / "evidence_request_plan.yaml"
VERIFIED_STATE = (
    ROOT / "examples" / "core" / "evidence_request_verified_state.yaml"
)
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _evidence() -> dict:
    return yaml.safe_load(VERIFIED_STATE.read_text(encoding="utf-8"))


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


def _check(payload: dict, assertion_id: str) -> dict:
    checks = payload["geotask_result"]["checks"]
    return next(item for item in checks if item["assertion_id"] == assertion_id)


def _control_block(payload: dict, block: str) -> dict:
    evaluations = payload["control_evaluation"]["evaluations"]
    return next(item for item in evaluations if item["block"] == block)


def test_agent_profile_exposes_four_model_neutral_tools() -> None:
    payload = agent_integration_profile_payload()["agent_integration_profile"]
    descriptors = list_agent_tool_descriptors()

    assert payload["id"] == AGENT_INTEGRATION_PROFILE_ID
    assert payload["version"] == AGENT_INTEGRATION_PROFILE_VERSION
    assert payload["status"] == "preview"
    assert [item.name for item in descriptors] == [
        "inspect_artifacts",
        "validate_artifact",
        "execute_task",
        "evaluate_control",
    ]
    assert payload["required_sequence"] == [item.name for item in descriptors]
    preparation = payload["generated_document_preparation"]
    assert preparation["helper"] == "geotask agent prepare <generated.yaml>"
    assert preparation["repair_policy"] == "mechanical_only"
    assert preparation["domain_inference_used"] is False
    assert preparation["model_called"] is False
    assert "infer object_refs" in preparation["forbidden_repairs"]
    revision = preparation["revision_request"]
    assert revision["version"] == "0.1"
    assert revision["candidate_values_are_inventory_only"] is True
    assert revision["selected_value"] is None
    assert revision["automatic_revision_applied"] is False
    assert revision["retry_command"] == (
        "geotask agent retry <blocked-report.json> <revised.yaml>"
    )
    verification = preparation["revision_verification"]
    assert verification["version"] == "0.1"
    assert verification["requested_paths_only"] is True
    assert verification["revision_request_recomputed"] is True
    assert verification["coordinates_immutable_unless_requested"] is True
    assert verification["task_executed_before_acceptance"] is False
    assert verification["output_option"] == (
        "--verification-output <revision-verification.json>"
    )
    report_artifacts = preparation["report_artifacts"]
    assert [item["artifact_id"] for item in report_artifacts] == [
        "geotask.agent-generation-preparation",
        "geotask.agent-revision-verification",
        "geotask.agent-revision-retry",
    ]
    assert all(item["schema_version"] == "0.1" for item in report_artifacts)
    assert all(item["schema_id"].startswith("https://") for item in report_artifacts)
    assert preparation["artifact_validity_is_distinct_from_business_state"] is True
    assert payload["evidence_recovery"]["model_guess_used"] is False
    assert payload["evidence_recovery"]["next_action_executed"] is False
    assert all("hosted model" not in item.purpose.lower() for item in descriptors)


def test_agent_profile_is_exported_from_root_and_v1_packages() -> None:
    assert geotask_core.AGENT_INTEGRATION_PROFILE_ID == AGENT_INTEGRATION_PROFILE_ID
    assert (
        geotask_v1.AGENT_INTEGRATION_PROFILE_VERSION
        == AGENT_INTEGRATION_PROFILE_VERSION
    )
    assert geotask_core.recover_evidence_request is recover_evidence_request
    assert geotask_v1.agent_integration_profile_payload is agent_integration_profile_payload


def test_gt08_recovery_reruns_trigger_after_verified_evidence() -> None:
    document = load_geotask(GT08)
    original = deepcopy(document)

    body = recover_evidence_request(document, _evidence()).to_dict()[
        "agent_integration"
    ]

    assert body["state"] == "recovered"
    assert body["request"]["id"] == "verify-restricted-schedule"
    assert body["request"]["missing_fields"] == []
    assert body["request"]["evidence_complete"] is True
    assert body["materialization"] == {
        "condition_identifier": "restricted_schedule_verified",
        "condition_value": True,
        "condition_rewritten_to_literal": True,
        "task_reexecuted": True,
        "next_action_executed": False,
        "model_guess_used": False,
    }

    initial = _check(body["initial_execution"], "temporal_conflict")
    resumed = _check(body["resumed_execution"], "temporal_conflict")
    assert initial["status"] == "unverifiable"
    assert initial["value"] is None
    assert resumed["status"] == "verified"
    assert resumed["value"] is True

    assert _control_block(
        body["initial_control_evaluation"], "evidence_request"
    )["state"] == "unknown"
    assert _control_block(
        body["resume_control_evaluation"], "evidence_request"
    )["state"] == "satisfied"
    assert _control_block(
        body["final_control_evaluation"], "decision_rule"
    )["value"] is True
    assert body["summary"] == {
        "decision_value": True,
        "blocked_outputs": [],
        "eligible_outputs": ["automatic_approval", "full_conflict"],
    }

    assert document == original
    assert document["tasks"][0]["assertions"][2]["condition"] == (
        "restricted_schedule_verified"
    )


def test_gt08_incomplete_evidence_remains_blocked_without_reexecution() -> None:
    evidence = _evidence()
    evidence.pop("source_reference")

    body = recover_evidence_request(load_geotask(GT08), evidence).to_dict()[
        "agent_integration"
    ]

    assert body["state"] == "blocked"
    assert body["request"]["missing_fields"] == ["source_reference"]
    assert body["request"]["evidence_complete"] is False
    assert body["materialization"]["task_reexecuted"] is False
    assert body["resumed_execution"] is None
    assert body["final_control_evaluation"] is None
    assert body["summary"]["decision_value"] is None
    assert body["summary"]["blocked_outputs"] == [
        "full_conflict",
        "automatic_approval",
    ]
    assert body["summary"]["eligible_outputs"] == []
    assert body["diagnostics"][0]["code"] == "missing_required_evidence"


def test_gt08_false_resume_condition_remains_blocked() -> None:
    evidence = _evidence()
    evidence["restricted_schedule_verified"] = False

    body = recover_evidence_request(load_geotask(GT08), evidence).to_dict()[
        "agent_integration"
    ]

    assert body["state"] == "blocked"
    assert body["request"]["missing_fields"] == []
    assert body["materialization"]["condition_value"] is False
    assert body["materialization"]["task_reexecuted"] is False
    assert {item["code"] for item in body["diagnostics"]} == {
        "resume_condition_not_verified",
        "resume_expression_not_satisfied",
    }


def test_agent_cli_inspect_emits_machine_readable_profile() -> None:
    result = _run_cli("agent", "inspect", "--format", "json")

    assert result.returncode == 0
    assert result.stderr == ""
    profile = json.loads(result.stdout)["agent_integration_profile"]
    assert profile["id"] == AGENT_INTEGRATION_PROFILE_ID
    assert [item["name"] for item in profile["tools"]] == [
        "inspect_artifacts",
        "validate_artifact",
        "execute_task",
        "evaluate_control",
    ]


def test_agent_cli_recovers_gt08_and_keeps_actions_unexecuted() -> None:
    result = _run_cli(
        "agent",
        "recover",
        str(GT08),
        "--evidence",
        str(VERIFIED_STATE),
        "--compact",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert "\n  " not in result.stdout
    body = json.loads(result.stdout)["agent_integration"]
    assert body["state"] == "recovered"
    assert body["summary"]["decision_value"] is True
    assert body["materialization"]["next_action_executed"] is False
    assert body["materialization"]["model_guess_used"] is False


def test_agent_cli_blocked_recovery_is_expected_output_not_command_failure(
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    evidence.pop("verified_at")
    evidence_path = tmp_path / "incomplete.yaml"
    evidence_path.write_text(
        yaml.safe_dump(evidence, sort_keys=False),
        encoding="utf-8",
    )

    result = _run_cli(
        "agent",
        "recover",
        str(GT08),
        "--evidence",
        str(evidence_path),
    )

    assert result.returncode == 0
    assert result.stderr == ""
    body = json.loads(result.stdout)["agent_integration"]
    assert body["state"] == "blocked"
    assert body["request"]["missing_fields"] == ["verified_at"]
    assert body["summary"]["eligible_outputs"] == []


def test_agent_cli_rejects_missing_evidence_argument_without_traceback() -> None:
    result = _run_cli("agent", "recover", str(GT08))

    assert result.returncode != 0
    assert "requires --evidence" in result.stderr
    assert "Traceback" not in result.stderr


def test_ci_smoke_installs_and_runs_agent_preview() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "geotask agent inspect --format json" in workflow
    assert "geotask agent recover examples/core/evidence_request_plan.yaml" in workflow
    assert "evidence_request_verified_state.yaml" in workflow
    assert 'report["state"] == "recovered"' in workflow
    assert 'report["materialization"]["next_action_executed"] is False' in workflow
    assert 'report["materialization"]["model_guess_used"] is False' in workflow
