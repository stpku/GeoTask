"""Fail-closed Agent-generated GeoTask preparation tests."""

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
from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.agent_generation import (
    AGENT_REVISION_REQUEST_VERSION,
    build_generated_document_revision_request,
    prepare_generated_document,
)


ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "examples" / "core" / "agent_generated_distance_draft.yaml"
BLOCKED_DRAFT = ROOT / "examples" / "core" / "agent_generated_distance_blocked.yaml"
REVISED_DRAFT = ROOT / "examples" / "core" / "agent_generated_distance_revised.yaml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


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


def _body(document: dict) -> dict:
    return prepare_generated_document(document).to_dict()[
        "agent_generation_preparation"
    ]


def test_generated_draft_is_mechanically_repaired_revalidated_and_executed() -> None:
    source = load_geotask(DRAFT)
    original = deepcopy(source)

    body = _body(source)

    assert body["state"] == "repaired"
    assert body["initial_validation"]["valid"] is False
    assert body["final_validation"] == {"valid": True, "diagnostics": []}
    assert body["revision_request"]["state"] == "not_required"
    assert body["revision_request"]["required_changes"] == []
    assert body["revision_request"]["next_action"] == "none"
    assert [item["code"] for item in body["repairs"]] == [
        "add_schema_version",
        "derive_name_from_id",
        "add_task_id",
        "add_assertion_id",
        "synchronize_operator_set",
        "add_local_execution",
        "add_fail_closed_output_contract",
    ]
    assert body["repair_policy"] == {
        "mechanical_only": True,
        "source_mutated": False,
        "domain_inference_used": False,
        "model_called": False,
        "non_local_execution_allowed": False,
    }

    prepared = body["prepared_document"]
    assert prepared["geotask"] == {
        "id": "agent-generated-distance-draft",
        "schema_version": "1.0",
        "name": "agent-generated-distance-draft",
    }
    assert prepared["tasks"][0]["id"] == "task_1"
    assert prepared["tasks"][0]["assertions"][0]["id"] == (
        "task_1_assertion_1"
    )
    assert prepared["operator_set"] == ["distance_2d"]
    assert prepared["execution"] == {"mode": "local_only", "steps": []}
    assert prepared["output_contract"] == {
        "format": "structured",
        "required_fields": [],
        "allow_model_inference": False,
    }
    assert validate_document(prepared) == []

    result = body["execution_result"]["geotask_result"]
    assert result["execution"]["status"] == "completed"
    assert result["checks"] == [
        {
            "assertion_id": "task_1_assertion_1",
            "operator": "distance_2d",
            "object_refs": ["start", "finish"],
            "executor": "local",
            "value": 5.0,
            "unit": "meter",
            "status": "verified",
            "assurance_level": "local_deterministic",
            "deterministic": True,
            "evidence_refs": [],
            "error": None,
        }
    ]
    assert body["summary"] == {
        "repair_count": 7,
        "initial_error_count": 4,
        "residual_error_count": 0,
        "task_executed": True,
        "execution_status": "completed",
        "overall_status": "verified",
        "check_count": 1,
    }
    assert source == original


def test_preparation_is_idempotent_after_first_repair() -> None:
    first = _body(load_geotask(DRAFT))
    second = _body(first["prepared_document"])

    assert second["state"] == "valid"
    assert second["repairs"] == []
    assert second["initial_validation"] == {"valid": True, "diagnostics": []}
    assert second["final_validation"] == {"valid": True, "diagnostics": []}
    assert second["summary"]["task_executed"] is True
    assert second["summary"]["overall_status"] == "verified"


def test_unknown_object_reference_remains_blocked_without_execution() -> None:
    source = load_geotask(DRAFT)
    source["tasks"][0]["assertions"][0]["object_refs"][1] = "missing"

    body = _body(source)

    assert body["state"] == "blocked"
    assert body["final_validation"]["valid"] is False
    assert body["execution_result"] is None
    assert body["summary"]["task_executed"] is False
    codes = {item["code"] for item in body["final_validation"]["diagnostics"]}
    assert "invalid_reference" in codes
    assert all(item["code"] != "repair_object_reference" for item in body["repairs"])


def test_missing_operator_and_object_binding_are_not_inferred() -> None:
    source = load_geotask(DRAFT)
    assertion = source["tasks"][0]["assertions"][0]
    assertion.pop("operator")
    assertion.pop("object_refs")

    body = _body(source)

    assert body["state"] == "blocked"
    assert body["summary"]["task_executed"] is False
    codes = {item["code"] for item in body["final_validation"]["diagnostics"]}
    assert "operator_inference_forbidden" in codes
    assert "object_binding_inference_forbidden" in codes


def test_non_local_execution_is_blocked_not_silently_rewritten() -> None:
    source = load_geotask(DRAFT)
    source["execution"] = {"mode": "hybrid", "steps": []}

    body = _body(source)

    assert body["state"] == "blocked"
    assert body["prepared_document"]["execution"]["mode"] == "hybrid"
    assert body["summary"]["task_executed"] is False
    assert "non_local_execution_forbidden" in {
        item["code"] for item in body["final_validation"]["diagnostics"]
    }


def test_output_contract_is_tightened_without_changing_task_semantics() -> None:
    source = load_geotask(DRAFT)
    source["output_contract"] = {
        "format": "structured",
        "required_fields": [],
        "allow_model_inference": True,
    }

    body = _body(source)

    assert body["state"] == "repaired"
    assert body["prepared_document"]["output_contract"][
        "allow_model_inference"
    ] is False
    assert "disable_model_inference" in {
        item["code"] for item in body["repairs"]
    }
    assert body["execution_result"]["geotask_result"]["checks"][0]["value"] == 5.0


def test_blocked_draft_emits_revision_request_without_selecting_candidates() -> None:
    body = _body(load_geotask(BLOCKED_DRAFT))

    assert body["state"] == "blocked"
    request = body["revision_request"]
    assert request["request_version"] == "0.1"
    assert request["state"] == "required"
    assert request["next_action"] == "revise_generated_document"
    assert request["revision_base"] == "prepared_document"
    assert len(request["revision_base_sha256"]) == 64
    assert request["retry_command"] == (
        "geotask agent retry <blocked-report.json> <revised.yaml>"
    )
    assert request["resume_when"] == "final_validation.valid == true"
    assert request["model_called"] is False
    assert request["automatic_revision_applied"] is False

    changes = {item["code"]: item for item in request["required_changes"]}
    operator = changes["invalid_operator"]
    assert operator["action"] == "select_registered_operator"
    assert "distance_2d" in operator["candidate_values"]
    assert operator["selected_value"] is None
    assert operator["automatic_change_allowed"] is False

    binding = changes["invalid_reference"]
    assert binding["action"] == "bind_explicit_objects"
    assert binding["candidate_values"] == ["finish", "start"]
    assert binding["selected_value"] is None
    assert binding["automatic_change_allowed"] is False
    assert body["summary"]["task_executed"] is False


def test_revision_request_fingerprint_is_deterministic_and_document_specific() -> None:
    first = _body(load_geotask(BLOCKED_DRAFT))["revision_request"]
    second = _body(load_geotask(BLOCKED_DRAFT))["revision_request"]
    changed = load_geotask(BLOCKED_DRAFT)
    changed["objects"]["finish"]["coordinates"] = [6, 8]
    third = _body(changed)["revision_request"]

    assert first["revision_base_sha256"] == second["revision_base_sha256"]
    assert first["revision_base_sha256"] != third["revision_base_sha256"]


def test_agent_revision_then_reprepare_executes_successfully() -> None:
    blocked = _body(load_geotask(BLOCKED_DRAFT))
    revised = _body(load_geotask(REVISED_DRAFT))

    assert blocked["revision_request"]["state"] == "required"
    assert revised["state"] == "valid"
    assert revised["repairs"] == []
    assert revised["revision_request"]["state"] == "not_required"
    assert revised["final_validation"] == {"valid": True, "diagnostics": []}
    check = revised["execution_result"]["geotask_result"]["checks"][0]
    assert check["operator"] == "distance_2d"
    assert check["object_refs"] == ["start", "finish"]
    assert check["value"] == 5.0
    assert check["status"] == "verified"


def test_non_local_document_revision_request_routes_to_authorized_runtime() -> None:
    source = load_geotask(DRAFT)
    source["execution"] = {"mode": "hybrid", "steps": []}

    request = _body(source)["revision_request"]

    assert request["state"] == "routing_required"
    assert request["next_action"] == "route_to_authorized_runtime"
    assert request["required_changes"] == [
        {
            "code": "non_local_execution_forbidden",
            "path": "execution.mode",
            "action": "route_to_authorized_runtime",
            "instruction": (
                "Route this document to an authorized Runtime, or explicitly revise "
                "execution.mode to local_only only when Core supports the full task."
            ),
            "candidate_values": ["local_only"],
            "selected_value": None,
            "automatic_change_allowed": False,
            "retryable": False,
            "requires_external_input": False,
        }
    ]


def test_generation_preparation_is_exported_from_root_and_v1_packages() -> None:
    assert geotask_core.prepare_generated_document is prepare_generated_document
    assert geotask_v1.prepare_generated_document is prepare_generated_document
    assert (
        geotask_core.build_generated_document_revision_request
        is build_generated_document_revision_request
    )
    assert (
        geotask_v1.build_generated_document_revision_request
        is build_generated_document_revision_request
    )
    assert geotask_core.AGENT_GENERATION_REPORT_VERSION == "0.1"
    assert geotask_v1.AGENT_GENERATION_REPORT_VERSION == "0.1"
    assert geotask_core.AGENT_REVISION_REQUEST_VERSION == "0.1"
    assert geotask_v1.AGENT_REVISION_REQUEST_VERSION == "0.1"
    assert AGENT_REVISION_REQUEST_VERSION == "0.1"


def test_agent_prepare_cli_writes_report_and_repaired_document(tmp_path: Path) -> None:
    report_path = tmp_path / "preparation-report.json"
    repaired_path = tmp_path / "prepared.yaml"

    result = _run_cli(
        "agent",
        "prepare",
        str(DRAFT),
        "--output",
        str(report_path),
        "--repaired-output",
        str(repaired_path),
        "--compact",
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    body = json.loads(report_path.read_text(encoding="utf-8"))[
        "agent_generation_preparation"
    ]
    repaired = yaml.safe_load(repaired_path.read_text(encoding="utf-8"))
    assert body["state"] == "repaired"
    assert body["summary"]["overall_status"] == "verified"
    assert repaired == body["prepared_document"]
    assert validate_document(repaired) == []


def test_agent_prepare_cli_emits_blocked_report_and_nonzero_exit(
    tmp_path: Path,
) -> None:
    source = load_geotask(DRAFT)
    source["tasks"][0]["assertions"][0]["object_refs"] = ["start", "unknown"]
    blocked_path = tmp_path / "blocked.yaml"
    blocked_path.write_text(
        yaml.safe_dump(source, sort_keys=False),
        encoding="utf-8",
    )
    repaired_path = tmp_path / "must-not-exist.yaml"

    result = _run_cli(
        "agent",
        "prepare",
        str(blocked_path),
        "--repaired-output",
        str(repaired_path),
    )

    assert result.returncode == 2
    assert result.stderr == ""
    body = json.loads(result.stdout)["agent_generation_preparation"]
    assert body["state"] == "blocked"
    assert body["summary"]["task_executed"] is False
    assert body["revision_request"]["state"] == "required"
    assert body["revision_request"]["next_action"] == "revise_generated_document"
    assert repaired_path.exists() is False
    assert "Traceback" not in result.stdout


def test_agent_prepare_cli_rejects_output_path_collisions(tmp_path: Path) -> None:
    same = tmp_path / "same.json"
    result = _run_cli(
        "agent",
        "prepare",
        str(DRAFT),
        "--output",
        str(same),
        "--repaired-output",
        str(same),
    )

    assert result.returncode != 0
    assert "must be different files" in result.stderr
    assert "Traceback" not in result.stderr


def test_ci_installed_smoke_runs_generated_document_preparation() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "geotask agent prepare examples/core/agent_generated_distance_draft.yaml" in workflow
    assert "--repaired-output prepared-generated.yaml" in workflow
    assert "prepared-document-validation.json" in workflow
    assert "agent_generated_distance_blocked.yaml" in workflow
    assert "agent_generated_distance_revised.yaml" in workflow
    assert 'test "$blocked_exit" -eq 2' in workflow
    assert 'report["state"] == "repaired"' in workflow
    assert 'request["state"] == "required"' in workflow
    assert 'changes["invalid_operator"]["selected_value"] is None' in workflow
    assert 'changes["invalid_reference"]["selected_value"] is None' in workflow
    assert 'request["automatic_revision_applied"] is False' in workflow
    assert 'report["repair_policy"]["model_called"] is False' in workflow
    assert 'report["repair_policy"]["domain_inference_used"] is False' in workflow
    assert 'check["value"] == 5.0' in workflow
