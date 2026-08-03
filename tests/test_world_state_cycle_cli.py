"""High-level verify/recheck bundle command tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import geotask_core
import geotask_core.v1 as geotask_v1
from geotask_core.v1.world_state_cycle_cli import (
    WorldStateCycleCommandError,
    verify_incremental_recheck_bundle,
    verify_session_bundle,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
CORE = REPO_ROOT / "examples" / "core"

VERIFY_SESSION = CORE / "verification_session_uav_recheck.json"
VERIFY_STATE = CORE / "world_state_uav_separation_recheck.json"
VERIFY_OBSERVATION = CORE / "observation_uav_b_delay_recheck.json"
VERIFY_BINDINGS = {
    "task-gt16": CORE / "uav_route_crossing_temporal_separation.yaml",
    "result-gt16-initial": CORE / "verification_session_uav_execution_result.json",
    "transition-uav-recheck": CORE / "state_transition_uav_separation_recheck.json",
}

RECHECK_RESULT = CORE / "incremental_reevaluation_result_uav_recheck.json"
RECHECK_BINDINGS = {
    "base-world-state": CORE / "world_state_uav_separation_recheck.json",
    "successor-world-state": CORE / "world_state_uav_separation_successor.json",
    "impact-graph-uav-recheck": CORE / "impact_graph_uav_recheck.json",
    "correction-uav-recheck": CORE / "correction_request_uav_recheck.json",
    "discrepancy-uav-recheck": CORE / "discrepancy_report_uav_recheck.json",
    "result-gt16-reevaluation": CORE / "incremental_reevaluation_uav_execution_result.json",
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


def _binding_args(bindings: dict[str, Path]) -> list[str]:
    args: list[str] = []
    for ref_id, path in bindings.items():
        args.extend(["--bind", f"{ref_id}={path.relative_to(REPO_ROOT)}"])
    return args


def test_cycle_bundle_helpers_are_public_api() -> None:
    assert geotask_core.verify_session_bundle is verify_session_bundle
    assert geotask_core.verify_incremental_recheck_bundle is verify_incremental_recheck_bundle
    assert geotask_v1.verify_session_bundle is verify_session_bundle
    assert geotask_v1.verify_incremental_recheck_bundle is verify_incremental_recheck_bundle


def test_verify_session_bundle_validates_semantics_and_exact_bytes() -> None:
    payload = verify_session_bundle(
        VERIFY_SESSION,
        VERIFY_STATE,
        [VERIFY_OBSERVATION],
        VERIFY_BINDINGS,
    )

    body = payload["verification_bundle_check"]
    assert body["valid"] is True
    assert body["session_id"] == "fictional-uav-separation-verification-session"
    assert body["session_state"] == "blocked"
    assert body["world_state_revision"] == 2
    assert body["observation_refs"] == ["obs-uav-b-delay-002"]
    assert body["artifact_ref_count"] == 3
    assert body["semantic_validation_complete"] is True
    assert body["exact_bindings_verified"] is True
    assert body["task_executed_by_command"] is False
    assert body["recheck_executed_by_command"] is False
    assert body["action_executed_by_command"] is False


def test_verify_session_bundle_rejects_missing_and_extra_inputs() -> None:
    missing = dict(VERIFY_BINDINGS)
    missing.pop("transition-uav-recheck")
    with pytest.raises(WorldStateCycleCommandError, match="missing ref_id values"):
        verify_session_bundle(
            VERIFY_SESSION,
            VERIFY_STATE,
            [VERIFY_OBSERVATION],
            missing,
        )

    with pytest.raises(WorldStateCycleCommandError, match="not declared by the session"):
        verify_session_bundle(
            VERIFY_SESSION,
            VERIFY_STATE,
            [VERIFY_OBSERVATION, CORE / "observation_uav_delay.json"],
            VERIFY_BINDINGS,
        )


def test_verify_cli_json_is_machine_readable_and_read_only() -> None:
    result = _run_cli(
        "verify",
        str(VERIFY_SESSION.relative_to(REPO_ROOT)),
        "--state",
        str(VERIFY_STATE.relative_to(REPO_ROOT)),
        "--observation",
        str(VERIFY_OBSERVATION.relative_to(REPO_ROOT)),
        *_binding_args(VERIFY_BINDINGS),
        "--format",
        "json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    body = payload["verification_bundle_check"]
    assert body["valid"] is True
    assert body["exact_bindings_verified"] is True
    assert body["task_executed_by_command"] is False
    assert "Traceback" not in result.stderr


def test_verify_cli_rejects_duplicate_binding() -> None:
    args = [
        "verify",
        str(VERIFY_SESSION.relative_to(REPO_ROOT)),
        "--state",
        str(VERIFY_STATE.relative_to(REPO_ROOT)),
        "--observation",
        str(VERIFY_OBSERVATION.relative_to(REPO_ROOT)),
        *_binding_args(VERIFY_BINDINGS),
        "--bind",
        "task-gt16=examples/core/uav_route_crossing_temporal_separation.yaml",
    ]
    result = _run_cli(*args)

    assert result.returncode == 1
    assert "duplicates ref-id 'task-gt16'" in result.stderr
    assert "Traceback" not in result.stderr


def test_recheck_bundle_validates_complete_incremental_result() -> None:
    payload = verify_incremental_recheck_bundle(
        RECHECK_RESULT,
        RECHECK_BINDINGS,
    )

    body = payload["recheck_bundle_check"]
    assert body["valid"] is True
    assert body["result_id"] == "fictional-uav-separation-incremental-reevaluation"
    assert body["result_state"] == "completed"
    assert body["base_world_state"]["revision"] == 2
    assert body["successor_world_state"]["revision"] == 3
    assert body["impact_graph_id"] == "fictional-uav-separation-impact-graph"
    assert body["correction_request_count"] == 1
    assert body["discrepancy_report_count"] == 1
    assert body["execution_result_count"] == 1
    assert body["semantic_validation_complete"] is True
    assert body["exact_bindings_verified"] is True
    assert body["reevaluation_executed_by_command"] is False
    assert body["action_authorized_by_command"] is False
    assert body["action_executed_by_command"] is False


def test_recheck_bundle_rejects_wrong_exact_source() -> None:
    wrong = dict(RECHECK_BINDINGS)
    wrong["successor-world-state"] = CORE / "world_state_uav_separation_recheck.json"

    with pytest.raises((WorldStateCycleCommandError, ValueError), match="mismatch|does not match"):
        verify_incremental_recheck_bundle(RECHECK_RESULT, wrong)


def test_recheck_cli_json_is_machine_readable_and_non_executing() -> None:
    result = _run_cli(
        "recheck",
        str(RECHECK_RESULT.relative_to(REPO_ROOT)),
        *_binding_args(RECHECK_BINDINGS),
        "--format",
        "json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    body = payload["recheck_bundle_check"]
    assert body["valid"] is True
    assert body["result_state"] == "completed"
    assert body["exact_bindings_verified"] is True
    assert body["reevaluation_executed_by_command"] is False
    assert "Traceback" not in result.stderr


def test_cycle_command_help_states_non_execution_boundary() -> None:
    verify_help = _run_cli("verify", "--help")
    recheck_help = _run_cli("recheck", "--help")

    assert verify_help.returncode == 0
    assert "does not execute" in verify_help.stdout
    assert "--observation" in verify_help.stdout
    assert "--bind" in verify_help.stdout
    assert recheck_help.returncode == 0
    assert "does not execute reevaluation or actions" in recheck_help.stdout
    assert "--bind" in recheck_help.stdout
