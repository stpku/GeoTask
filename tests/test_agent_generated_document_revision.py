"""Fail-closed revision-diff verification for Agent-generated documents."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

import geotask_core
import geotask_core.v1 as geotask_v1
from geotask_core.parser import load_geotask
from geotask_core.v1.agent_generation import (
    AGENT_REVISION_RETRY_VERSION,
    AGENT_REVISION_VERIFICATION_VERSION,
    AgentGenerationError,
    prepare_generated_document,
    retry_generated_document,
    verify_generated_document_revision,
)


ROOT = Path(__file__).resolve().parents[1]
BLOCKED_DRAFT = ROOT / "examples" / "core" / "agent_generated_distance_blocked.yaml"
REVISED_DRAFT = ROOT / "examples" / "core" / "agent_generated_distance_revised.yaml"
DRAFT = ROOT / "examples" / "core" / "agent_generated_distance_draft.yaml"
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


def _blocked_report() -> dict:
    return prepare_generated_document(load_geotask(BLOCKED_DRAFT)).to_dict()


def _revised_document() -> dict:
    return load_geotask(REVISED_DRAFT)


def test_valid_revision_changes_only_requested_and_derived_paths() -> None:
    report = _blocked_report()
    revised = _revised_document()
    report_original = deepcopy(report)
    revised_original = deepcopy(revised)

    result = verify_generated_document_revision(report, revised)
    body = result.to_dict()["agent_revision_verification"]

    assert body["report_version"] == "0.1"
    assert body["state"] == "accepted"
    assert body["changed_paths"] == [
        "operator_set[0]",
        "tasks.task_1.assertions[0].object_refs[1]",
        "tasks.task_1.assertions[0].operator",
    ]
    assert body["violations"] == []
    assert body["summary"] == {
        "changed_path_count": 3,
        "resolved_change_count": 2,
        "violation_count": 0,
        "accepted": True,
    }
    assert body["policy"]["requested_paths_only"] is True
    assert body["policy"]["task_executed"] is False
    assert body["policy"]["model_called"] is False
    assert {item["path"] for item in body["allowed_paths"]} == {
        "tasks.task_1.assertions[0].operator",
        "tasks.task_1.assertions[0].object_refs[1]",
        "operator_set",
    }
    assert all(item["selected_by_core"] is False for item in body["resolved_changes"])
    assert report == report_original
    assert revised == revised_original


def test_retry_runs_only_after_revision_verification_accepts() -> None:
    body = retry_generated_document(
        _blocked_report(),
        _revised_document(),
    ).to_dict()["agent_revision_retry"]

    assert body["report_version"] == "0.1"
    assert body["state"] == "accepted"
    assert body["revision_verification"]["state"] == "accepted"
    assert body["summary"] == {
        "revision_accepted": True,
        "task_executed": True,
        "preparation_state": "valid",
        "overall_status": "verified",
    }
    check = body["preparation"]["execution_result"]["geotask_result"]["checks"][0]
    assert check["operator"] == "distance_2d"
    assert check["object_refs"] == ["start", "finish"]
    assert check["value"] == 5.0
    assert check["status"] == "verified"


@pytest.mark.parametrize(
    ("mutator", "expected_path"),
    [
        (
            lambda document: document["objects"]["finish"].update(
                {"coordinates": [6, 8]}
            ),
            "objects.finish.coordinates[0]",
        ),
        (
            lambda document: document.update(
                {"extensions": {"evidence": {"source_reference": "invented"}}}
            ),
            "extensions",
        ),
        (
            lambda document: document["geotask"].update({"name": "changed-name"}),
            "geotask.name",
        ),
        (
            lambda document: document["tasks"][0].update({"goal": "A different goal"}),
            "tasks.task_1.goal",
        ),
    ],
)
def test_unrequested_changes_are_rejected_before_execution(mutator, expected_path: str) -> None:
    revised = _revised_document()
    mutator(revised)

    body = retry_generated_document(
        _blocked_report(),
        revised,
    ).to_dict()["agent_revision_retry"]

    assert body["state"] == "rejected"
    assert body["preparation"] is None
    assert body["summary"]["task_executed"] is False
    violations = body["revision_verification"]["violations"]
    assert any(
        item["code"] == "unauthorized_revision_path"
        and item["path"] == expected_path
        for item in violations
    )


def test_operator_selection_must_come_from_candidate_inventory() -> None:
    revised = _revised_document()
    revised["tasks"][0]["assertions"][0]["operator"] = "buffer"
    revised["operator_set"] = ["buffer"]

    body = verify_generated_document_revision(
        _blocked_report(), revised
    ).to_dict()["agent_revision_verification"]

    assert body["state"] == "rejected"
    assert any(
        item["code"] == "revision_value_not_in_candidates"
        and item["path"] == "tasks.task_1.assertions[0].operator"
        for item in body["violations"]
    )


def test_object_binding_must_come_from_existing_object_inventory() -> None:
    revised = _revised_document()
    revised["tasks"][0]["assertions"][0]["object_refs"][1] = "other"

    body = verify_generated_document_revision(
        _blocked_report(), revised
    ).to_dict()["agent_revision_verification"]

    assert body["state"] == "rejected"
    assert any(
        item["code"] == "revision_value_not_in_candidates"
        and item["path"] == "tasks.task_1.assertions[0].object_refs[1]"
        for item in body["violations"]
    )


def test_operator_set_cannot_include_unrelated_operators() -> None:
    revised = _revised_document()
    revised["operator_set"].append("time_overlap")

    body = verify_generated_document_revision(
        _blocked_report(), revised
    ).to_dict()["agent_revision_verification"]

    assert body["state"] == "rejected"
    assert any(
        item["code"] == "revision_operator_set_mismatch"
        and item["path"] == "operator_set"
        for item in body["violations"]
    )


def test_each_required_change_must_be_resolved() -> None:
    revised = _revised_document()
    revised["tasks"][0]["assertions"][0]["object_refs"][1] = "destination"

    body = verify_generated_document_revision(
        _blocked_report(), revised
    ).to_dict()["agent_revision_verification"]

    assert body["state"] == "rejected"
    assert any(
        item["code"] == "required_revision_unchanged"
        and item["path"] == "tasks.task_1.assertions[0].object_refs[1]"
        for item in body["violations"]
    )


def test_tampered_revision_request_is_rejected_as_malformed() -> None:
    report = _blocked_report()
    body = report["agent_generation_preparation"]
    body["revision_request"]["required_changes"][0]["path"] = (
        "objects.finish.coordinates"
    )

    with pytest.raises(
        AgentGenerationError,
        match="does not match the blocked document diagnostics",
    ):
        verify_generated_document_revision(report, _revised_document())


def test_tampered_revision_base_fingerprint_is_rejected() -> None:
    report = _blocked_report()
    report["agent_generation_preparation"]["revision_request"][
        "revision_base_sha256"
    ] = "0" * 64

    with pytest.raises(
        AgentGenerationError,
        match="does not match the blocked document diagnostics",
    ):
        verify_generated_document_revision(report, _revised_document())


def test_non_local_request_cannot_be_retried_in_core() -> None:
    source = load_geotask(DRAFT)
    source["execution"] = {"mode": "hybrid", "steps": []}
    report = prepare_generated_document(source).to_dict()
    revised = deepcopy(report["agent_generation_preparation"]["prepared_document"])
    revised["execution"]["mode"] = "local_only"

    body = retry_generated_document(report, revised).to_dict()["agent_revision_retry"]

    assert body["state"] == "rejected"
    assert body["preparation"] is None
    codes = {
        item["code"] for item in body["revision_verification"]["violations"]
    }
    assert "revision_not_locally_retryable" in codes
    assert "non_retryable_revision_change" in codes


def test_revision_verification_exports_are_public() -> None:
    assert geotask_core.AGENT_REVISION_VERIFICATION_VERSION == "0.1"
    assert geotask_v1.AGENT_REVISION_VERIFICATION_VERSION == "0.1"
    assert geotask_core.AGENT_REVISION_RETRY_VERSION == "0.1"
    assert geotask_v1.AGENT_REVISION_RETRY_VERSION == "0.1"
    assert AGENT_REVISION_VERIFICATION_VERSION == "0.1"
    assert AGENT_REVISION_RETRY_VERSION == "0.1"
    assert (
        geotask_core.verify_generated_document_revision
        is verify_generated_document_revision
    )
    assert geotask_v1.retry_generated_document is retry_generated_document


def test_agent_retry_cli_accepts_revision_and_writes_prepared_document(
    tmp_path: Path,
) -> None:
    blocked_report = tmp_path / "blocked.json"
    retry_report = tmp_path / "retry.json"
    verification_output = tmp_path / "verification.json"
    prepared_output = tmp_path / "prepared.yaml"
    blocked_report.write_text(
        json.dumps(_blocked_report(), ensure_ascii=False),
        encoding="utf-8",
    )

    result = _run_cli(
        "agent",
        "retry",
        str(blocked_report),
        str(REVISED_DRAFT),
        "--output",
        str(retry_report),
        "--verification-output",
        str(verification_output),
        "--prepared-output",
        str(prepared_output),
        "--compact",
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    body = json.loads(retry_report.read_text(encoding="utf-8"))[
        "agent_revision_retry"
    ]
    verification = json.loads(verification_output.read_text(encoding="utf-8"))[
        "agent_revision_verification"
    ]
    prepared = yaml.safe_load(prepared_output.read_text(encoding="utf-8"))
    assert body["state"] == "accepted"
    assert body["revision_verification"]["state"] == "accepted"
    assert verification == body["revision_verification"]
    assert body["summary"]["task_executed"] is True
    assert prepared == body["preparation"]["prepared_document"]


def test_agent_retry_cli_rejects_coordinate_tampering_without_output_document(
    tmp_path: Path,
) -> None:
    blocked_report = tmp_path / "blocked.json"
    rejected_report = tmp_path / "rejected.json"
    verification_output = tmp_path / "rejected-verification.json"
    prepared_output = tmp_path / "must-not-exist.yaml"
    blocked_report.write_text(
        json.dumps(_blocked_report(), ensure_ascii=False),
        encoding="utf-8",
    )
    revised = _revised_document()
    revised["objects"]["finish"]["coordinates"] = [6, 8]
    revised_path = tmp_path / "tampered.yaml"
    revised_path.write_text(
        yaml.safe_dump(revised, sort_keys=False),
        encoding="utf-8",
    )

    result = _run_cli(
        "agent",
        "retry",
        str(blocked_report),
        str(revised_path),
        "--output",
        str(rejected_report),
        "--verification-output",
        str(verification_output),
        "--prepared-output",
        str(prepared_output),
        "--compact",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == ""
    body = json.loads(rejected_report.read_text(encoding="utf-8"))[
        "agent_revision_retry"
    ]
    verification = json.loads(verification_output.read_text(encoding="utf-8"))[
        "agent_revision_verification"
    ]
    assert body["state"] == "rejected"
    assert body["preparation"] is None
    assert verification == body["revision_verification"]
    assert verification["state"] == "rejected"
    assert body["summary"]["task_executed"] is False
    assert prepared_output.exists() is False


def test_agent_retry_cli_rejects_output_path_collisions(tmp_path: Path) -> None:
    blocked_report = tmp_path / "blocked.json"
    blocked_report.write_text(
        json.dumps(_blocked_report(), ensure_ascii=False),
        encoding="utf-8",
    )
    same = tmp_path / "same.json"

    result = _run_cli(
        "agent",
        "retry",
        str(blocked_report),
        str(REVISED_DRAFT),
        "--output",
        str(same),
        "--prepared-output",
        str(same),
    )

    assert result.returncode != 0
    assert "must be different files" in result.stderr
    assert "Traceback" not in result.stderr


def test_agent_retry_cli_requires_verification_output_file(tmp_path: Path) -> None:
    blocked_report = tmp_path / "blocked.json"
    blocked_report.write_text(
        json.dumps(_blocked_report(), ensure_ascii=False),
        encoding="utf-8",
    )

    result = _run_cli(
        "agent",
        "retry",
        str(blocked_report),
        str(REVISED_DRAFT),
        "--verification-output",
        "-",
    )

    assert result.returncode != 0
    assert "requires a file path" in result.stderr
    assert "Traceback" not in result.stderr


def test_ci_installed_smoke_enforces_revision_diff_guard() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "geotask agent retry blocked-preparation.json" in workflow
    assert "--verification-output revision-verification.json" in workflow
    assert "--prepared-output retried-prepared.yaml" in workflow
    assert "tampered-revision.yaml" in workflow
    assert 'test "$rejected_exit" -eq 2' in workflow
    assert "test ! -e must-not-exist.yaml" in workflow
    assert 'report["state"] == "accepted"' in workflow
    assert 'verification["state"] == "accepted"' in workflow
    assert 'report["state"] == "rejected"' in workflow
    assert 'item["code"] == "unauthorized_revision_path"' in workflow
    assert 'report["summary"]["task_executed"] is False' in workflow
