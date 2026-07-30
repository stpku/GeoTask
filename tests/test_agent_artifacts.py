"""Registered Agent report Artifact and Schema tests."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

import geotask_core
import geotask_core.v1 as geotask_v1
from geotask_core.parser import load_geotask
from geotask_core.v1.agent_artifacts import (
    AGENT_GENERATION_PREPARATION_SCHEMA_ID,
    AGENT_GENERATION_PREPARATION_SCHEMA_VERSION,
    AGENT_REVISION_RETRY_SCHEMA_ID,
    AGENT_REVISION_RETRY_SCHEMA_VERSION,
    AGENT_REVISION_VERIFICATION_SCHEMA_ID,
    AGENT_REVISION_VERIFICATION_SCHEMA_VERSION,
    AgentArtifactFormatError,
    load_agent_generation_preparation_report,
    load_agent_revision_retry_report,
    load_agent_revision_verification_report,
)
from geotask_core.v1.agent_generation import (
    prepare_generated_document,
    retry_generated_document,
)
from geotask_core.v1.artifact_validation import validate_artifact_payload


ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "examples" / "core" / "agent_generated_distance_draft.yaml"
BLOCKED = ROOT / "examples" / "core" / "agent_generated_distance_blocked.yaml"
REVISED = ROOT / "examples" / "core" / "agent_generated_distance_revised.yaml"
SCHEMA_PATHS = (
    ROOT / "schemas" / "geotask-agent-generation-preparation-v0.1.schema.json",
    ROOT / "schemas" / "geotask-agent-revision-verification-v0.1.schema.json",
    ROOT / "schemas" / "geotask-agent-revision-retry-v0.1.schema.json",
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
    repaired_preparation = prepare_generated_document(load_geotask(DRAFT)).to_dict()
    preparation = prepare_generated_document(load_geotask(BLOCKED)).to_dict()
    revised = load_geotask(REVISED)
    valid_preparation = prepare_generated_document(revised).to_dict()
    accepted = retry_generated_document(preparation, revised).to_dict()
    tampered = deepcopy(revised)
    tampered["objects"]["finish"]["coordinates"] = [6, 8]
    rejected = retry_generated_document(preparation, tampered).to_dict()
    verification = {
        "agent_revision_verification": accepted["agent_revision_retry"][
            "revision_verification"
        ]
    }
    return {
        "repaired_preparation": repaired_preparation,
        "preparation": preparation,
        "valid_preparation": valid_preparation,
        "verification": verification,
        "accepted_retry": accepted,
        "rejected_retry": rejected,
    }


def test_agent_artifact_schemas_are_draft_2020_12_and_resolve_offline() -> None:
    schemas = [json.loads(path.read_text(encoding="utf-8")) for path in SCHEMA_PATHS]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    reports = _reports()
    samples = (
        (schemas[0], reports["repaired_preparation"]),
        (schemas[0], reports["preparation"]),
        (schemas[0], reports["valid_preparation"]),
        (schemas[1], reports["verification"]),
        (schemas[2], reports["accepted_retry"]),
        (schemas[2], reports["rejected_retry"]),
    )

    for schema in schemas:
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    for schema, payload in samples:
        assert list(Draft202012Validator(schema, registry=registry).iter_errors(payload)) == []


def test_agent_schema_ids_and_versions_are_stable() -> None:
    assert AGENT_GENERATION_PREPARATION_SCHEMA_ID.endswith(
        "geotask-agent-generation-preparation-v0.1.schema.json"
    )
    assert AGENT_REVISION_VERIFICATION_SCHEMA_ID.endswith(
        "geotask-agent-revision-verification-v0.1.schema.json"
    )
    assert AGENT_REVISION_RETRY_SCHEMA_ID.endswith(
        "geotask-agent-revision-retry-v0.1.schema.json"
    )
    assert AGENT_GENERATION_PREPARATION_SCHEMA_VERSION == "0.1"
    assert AGENT_REVISION_VERIFICATION_SCHEMA_VERSION == "0.1"
    assert AGENT_REVISION_RETRY_SCHEMA_VERSION == "0.1"


def test_strict_loaders_accept_all_supported_business_states() -> None:
    reports = _reports()

    assert load_agent_generation_preparation_report(reports["repaired_preparation"])[
        "agent_generation_preparation"
    ]["state"] == "repaired"
    assert load_agent_generation_preparation_report(reports["preparation"])[
        "agent_generation_preparation"
    ]["state"] == "blocked"
    assert load_agent_generation_preparation_report(reports["valid_preparation"])[
        "agent_generation_preparation"
    ]["state"] == "valid"
    assert load_agent_revision_verification_report(reports["verification"])[
        "agent_revision_verification"
    ]["state"] == "accepted"
    rejected_verification = {
        "agent_revision_verification": reports["rejected_retry"][
            "agent_revision_retry"
        ]["revision_verification"]
    }
    assert load_agent_revision_verification_report(rejected_verification)[
        "agent_revision_verification"
    ]["state"] == "rejected"
    assert load_agent_revision_retry_report(reports["accepted_retry"])[
        "agent_revision_retry"
    ]["state"] == "accepted"
    assert load_agent_revision_retry_report(reports["rejected_retry"])[
        "agent_revision_retry"
    ]["state"] == "rejected"


@pytest.mark.parametrize(
    ("artifact_id", "report_key", "expected_state"),
    [
        (
            "geotask.agent-generation-preparation",
            "repaired_preparation",
            "repaired",
        ),
        ("geotask.agent-generation-preparation", "preparation", "blocked"),
        ("geotask.agent-generation-preparation", "valid_preparation", "valid"),
        ("geotask.agent-revision-verification", "verification", "accepted"),
        ("geotask.agent-revision-retry", "accepted_retry", "accepted"),
        ("geotask.agent-revision-retry", "rejected_retry", "rejected"),
    ],
)
def test_supported_business_states_are_valid_artifacts(
    artifact_id: str,
    report_key: str,
    expected_state: str,
) -> None:
    report = validate_artifact_payload(artifact_id, _reports()[report_key])
    body = report.to_dict()["artifact_validation"]

    assert body["valid"] is True
    assert body["schema_verified"] is True
    assert body["summary"]["report_state"] == expected_state
    assert body["diagnostics"] == []


def test_preparation_loader_rejects_false_execution_claim() -> None:
    payload = _reports()["preparation"]
    payload["agent_generation_preparation"]["summary"]["task_executed"] = True

    with pytest.raises(AgentArtifactFormatError, match="blocked state"):
        load_agent_generation_preparation_report(payload)


def test_verification_loader_rejects_inconsistent_violation_count() -> None:
    payload = _reports()["rejected_retry"]
    verification = {
        "agent_revision_verification": payload["agent_revision_retry"][
            "revision_verification"
        ]
    }
    verification["agent_revision_verification"]["summary"]["violation_count"] = 0

    with pytest.raises(AgentArtifactFormatError, match="violation_count"):
        load_agent_revision_verification_report(verification)


def test_retry_loader_rejects_rejected_report_with_preparation() -> None:
    reports = _reports()
    payload = reports["rejected_retry"]
    payload["agent_revision_retry"]["preparation"] = reports["accepted_retry"][
        "agent_revision_retry"
    ]["preparation"]

    with pytest.raises(AgentArtifactFormatError, match="rejected state"):
        load_agent_revision_retry_report(payload)


def test_agent_artifact_validation_returns_normalized_invalid_report() -> None:
    payload = _reports()["rejected_retry"]
    payload["agent_revision_retry"]["revision_verification"]["summary"][
        "violation_count"
    ] = 0

    report = validate_artifact_payload("geotask.agent-revision-retry", payload)
    body = report.to_dict()["artifact_validation"]

    assert body["valid"] is False
    assert body["schema_verified"] is True
    assert body["summary"] == {}
    assert body["diagnostics"][0]["code"] == "invalid_agent_report"
    assert "violation_count" in body["diagnostics"][0]["message"]


def test_agent_artifact_cli_validates_all_three_report_types(tmp_path: Path) -> None:
    reports = _reports()
    files = {
        "geotask.agent-generation-preparation": reports["preparation"],
        "geotask.agent-revision-verification": reports["verification"],
        "geotask.agent-revision-retry": reports["accepted_retry"],
    }

    for artifact_id, payload in files.items():
        path = tmp_path / f"{artifact_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        result = _run_cli("artifact", "validate", artifact_id, str(path), "--format", "json")
        assert result.returncode == 0
        assert result.stderr == ""
        body = json.loads(result.stdout)["artifact_validation"]
        assert body["artifact_id"] == artifact_id
        assert body["valid"] is True
        assert body["schema_verified"] is True


def test_agent_artifact_validation_report_self_validates() -> None:
    validation = validate_artifact_payload(
        "geotask.agent-revision-retry",
        _reports()["rejected_retry"],
        file="rejected-retry.json",
    )
    outer = validate_artifact_payload(
        "geotask.artifact-validation-report",
        validation.to_dict(),
        file="agent-artifact-validation.json",
    ).to_dict()["artifact_validation"]

    assert outer["valid"] is True
    assert outer["schema_verified"] is True
    assert outer["summary"] == {
        "validated_artifact_id": "geotask.agent-revision-retry",
        "validated_artifact_valid": True,
        "diagnostic_count": 0,
    }


def test_agent_artifact_cli_emits_json_before_nonzero_exit(tmp_path: Path) -> None:
    payload = _reports()["accepted_retry"]
    payload["agent_revision_retry"]["summary"]["task_executed"] = False
    path = tmp_path / "invalid-retry.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = _run_cli(
        "artifact",
        "validate",
        "geotask.agent-revision-retry",
        str(path),
        "--format",
        "json",
    )

    assert result.returncode == 1
    assert result.stderr == ""
    body = json.loads(result.stdout)["artifact_validation"]
    assert body["valid"] is False
    assert body["diagnostics"][0]["code"] == "invalid_agent_report"
    assert "Traceback" not in result.stdout


def test_agent_artifact_loaders_are_exported_from_public_namespaces() -> None:
    for namespace in (geotask_core, geotask_v1):
        assert namespace.AgentArtifactFormatError is AgentArtifactFormatError
        assert (
            namespace.load_agent_generation_preparation_report
            is load_agent_generation_preparation_report
        )
        assert (
            namespace.load_agent_revision_verification_report
            is load_agent_revision_verification_report
        )
        assert namespace.load_agent_revision_retry_report is load_agent_revision_retry_report
        assert namespace.AGENT_GENERATION_PREPARATION_SCHEMA_VERSION == "0.1"
        assert namespace.AGENT_REVISION_VERIFICATION_SCHEMA_VERSION == "0.1"
        assert namespace.AGENT_REVISION_RETRY_SCHEMA_VERSION == "0.1"
