"""Unified registered Artifact validation API and CLI tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import geotask_core.v1.artifact_validation as artifact_validation_module
from geotask_core.parser import load_geotask
from geotask_core.v1.artifact_validation import (
    ARTIFACT_VALIDATION_REPORT_VERSION,
    ARTIFACT_VALIDATION_SCHEMA_ID,
    ARTIFACT_VALIDATION_SCHEMA_VERSION,
    ArtifactValidationFormatError,
    ArtifactValidationReport,
    load_artifact_validation_report,
    validate_artifact_file,
    validate_artifact_payload,
)
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.control_evaluation import evaluate_control_profile
from geotask_core.v1.executor import execute_canonical


ROOT = Path(__file__).resolve().parents[1]
GT19 = ROOT / "examples" / "core" / "uav_arrival_ground_clearance_release.yaml"
ARTIFACT_VALIDATION_SCHEMA_PATH = (
    ROOT / "schemas" / "geotask-artifact-validation-v1.0.schema.json"
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


def _execution_payload() -> dict:
    document = canonicalize(load_geotask(GT19))
    return execute_canonical(document).to_dict()


def _control_payload() -> dict:
    document = canonicalize(load_geotask(GT19))
    result = execute_canonical(document)
    return evaluate_control_profile(
        document,
        result,
        {
            "ground_zone_clear": False,
            "clearance_evidence_age_seconds": 8,
        },
    ).to_dict()


def _validation_report_payload() -> dict:
    return validate_artifact_payload(
        "geotask.execution-result",
        _execution_payload(),
        file="execution-result.json",
    ).to_dict()


def _write_json(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def test_unified_api_validates_all_registered_artifact_types() -> None:
    document = validate_artifact_file("geotask.document", GT19)
    execution = validate_artifact_payload(
        "geotask.execution-result",
        _execution_payload(),
        file="execution-result.json",
    )
    control = validate_artifact_payload(
        "geotask.control-evaluation",
        _control_payload(),
        file="control-evaluation.json",
    )
    validation_report = validate_artifact_payload(
        "geotask.artifact-validation-report",
        execution.to_dict(),
        file="artifact-validation.json",
    )

    assert isinstance(document, ArtifactValidationReport)
    assert ARTIFACT_VALIDATION_REPORT_VERSION == "1.0"
    for report in (document, execution, control, validation_report):
        payload = report.to_dict()["artifact_validation"]
        assert report.valid is True
        assert payload["report_version"] == "1.0"
        assert payload["schema_verified"] is True
        assert payload["diagnostics"] == []

    document_body = document.to_dict()["artifact_validation"]
    assert document_body["artifact_id"] == "geotask.document"
    assert document_body["summary"]["document_name"] == (
        "GT19 UAV Arrival Ground Clearance Release"
    )
    assert document_body["summary"]["object_count"] > 0

    execution_body = execution.to_dict()["artifact_validation"]
    assert execution_body["summary"]["task_id"] == (
        "gt19-uav-arrival-ground-clearance-release"
    )
    assert execution_body["summary"]["check_count"] == 4

    control_body = control.to_dict()["artifact_validation"]
    assert control_body["summary"]["task_id"] == (
        "gt19-uav-arrival-ground-clearance-release"
    )
    assert control_body["summary"]["evaluation_count"] == 1

    validation_body = validation_report.to_dict()["artifact_validation"]
    assert validation_body["artifact_id"] == "geotask.artifact-validation-report"
    assert validation_body["summary"] == {
        "validated_artifact_id": "geotask.execution-result",
        "validated_artifact_valid": True,
        "diagnostic_count": 0,
    }


def test_artifact_validation_report_schema_and_strict_loader_roundtrip() -> None:
    schema = json.loads(ARTIFACT_VALIDATION_SCHEMA_PATH.read_text(encoding="utf-8"))
    payload = _validation_report_payload()

    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == ARTIFACT_VALIDATION_SCHEMA_ID
    assert ARTIFACT_VALIDATION_SCHEMA_VERSION == "1.0"
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []

    loaded = load_artifact_validation_report(payload)
    assert loaded.to_dict() == payload
    assert loaded.descriptor.artifact_id == "geotask.execution-result"
    assert loaded.valid is True
    assert loaded.schema_verified is True


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda p: p["artifact_validation"].__setitem__(
                "artifact_kind", "wrong_kind"
            ),
            "artifact_kind must match Registry value",
        ),
        (
            lambda p: p["artifact_validation"].__setitem__(
                "schema_id", "https://example.invalid/wrong.schema.json"
            ),
            "schema_id must match Registry value",
        ),
        (
            lambda p: p["artifact_validation"].__setitem__(
                "schema_verified", False
            ),
            "valid cannot be true when schema_verified is false",
        ),
        (
            lambda p: p["artifact_validation"].__setitem__(
                "diagnostics",
                [
                    {
                        "code": "invented_error",
                        "path": "",
                        "message": "failure",
                        "severity": "error",
                        "suggested_fix": "fix it",
                    }
                ],
            ),
            "valid cannot be true with error diagnostics",
        ),
        (
            lambda p: p["artifact_validation"].__setitem__(
                "summary", {"nested": {"not": "scalar"}}
            ),
            "must be a JSON scalar",
        ),
        (
            lambda p: p["artifact_validation"].__setitem__("unexpected", True),
            "contains unknown field",
        ),
    ],
)
def test_strict_report_loader_rejects_registry_and_cross_field_inconsistencies(
    mutator,
    message: str,
) -> None:
    payload = deepcopy(_validation_report_payload())
    mutator(payload)

    with pytest.raises(ArtifactValidationFormatError, match=message):
        load_artifact_validation_report(payload)


def test_invalid_target_report_is_still_a_valid_report_artifact() -> None:
    invalid_target_report = validate_artifact_payload(
        "geotask.execution-result",
        {},
        file="invalid-result.json",
    )
    assert invalid_target_report.valid is False

    report_validation = validate_artifact_payload(
        "geotask.artifact-validation-report",
        invalid_target_report.to_dict(),
        file="artifact-validation.json",
    )
    body = report_validation.to_dict()["artifact_validation"]

    assert report_validation.valid is True
    assert body["summary"]["validated_artifact_id"] == "geotask.execution-result"
    assert body["summary"]["validated_artifact_valid"] is False
    assert body["summary"]["diagnostic_count"] == 1
    assert body["diagnostics"] == []


def test_unified_api_reports_invalid_payloads_and_files(tmp_path: Path) -> None:
    invalid_document = tmp_path / "invalid.yaml"
    invalid_document.write_text("geotask:\n  name: broken\n", encoding="utf-8")
    malformed_result = tmp_path / "malformed.json"
    malformed_result.write_text("{not-json", encoding="utf-8")

    document_report = validate_artifact_file("geotask.document", invalid_document)
    result_report = validate_artifact_file(
        "geotask.execution-result", malformed_result
    )
    mapping_report = validate_artifact_payload(  # type: ignore[arg-type]
        "geotask.control-evaluation",
        [],
    )

    assert document_report.valid is False
    document_body = document_report.to_dict()["artifact_validation"]
    assert document_body["schema_verified"] is True
    assert document_body["summary"]["error_count"] > 0
    assert document_body["diagnostics"]

    assert result_report.valid is False
    result_body = result_report.to_dict()["artifact_validation"]
    assert result_body["diagnostics"][0]["code"] == "invalid_artifact_file"
    assert "invalid JSON" in result_body["diagnostics"][0]["message"]

    assert mapping_report.valid is False
    assert mapping_report.to_dict()["artifact_validation"]["diagnostics"][0][
        "code"
    ] == "invalid_artifact_file"

    with pytest.raises(KeyError, match="unknown GeoTask artifact"):
        validate_artifact_file("geotask.unknown", invalid_document)


def test_unified_api_fails_closed_when_schema_bundle_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        artifact_validation_module,
        "verify_schema_bundle",
        lambda artifact_id=None: {
            "schema_bundle_verification": {
                "valid": False,
                "diagnostics": [
                    {
                        "code": "invalid_bundled_schema",
                        "message": "digest mismatch",
                    }
                ],
            }
        },
    )

    report = validate_artifact_payload("geotask.execution-result", {})
    body = report.to_dict()["artifact_validation"]

    assert report.valid is False
    assert body["schema_verified"] is False
    assert body["summary"] == {}
    assert body["diagnostics"][0]["code"] == "invalid_bundled_schema"
    assert "digest mismatch" in body["diagnostics"][0]["message"]


def test_artifact_validate_cli_supports_all_registered_artifacts(
    tmp_path: Path,
) -> None:
    result_path = _write_json(tmp_path, "execution-result.json", _execution_payload())
    control_path = _write_json(tmp_path, "control-evaluation.json", _control_payload())
    validation_path = _write_json(
        tmp_path,
        "artifact-validation.json",
        _validation_report_payload(),
    )
    cases = (
        ("geotask.document", GT19, "object_count"),
        ("geotask.execution-result", result_path, "check_count"),
        ("geotask.control-evaluation", control_path, "evaluation_count"),
        (
            "geotask.artifact-validation-report",
            validation_path,
            "validated_artifact_id",
        ),
    )

    for artifact_id, path, summary_key in cases:
        result = _run_cli(
            "artifact",
            "validate",
            artifact_id,
            str(path),
            "--format",
            "json",
        )
        assert result.returncode == 0
        assert result.stderr == ""
        body = json.loads(result.stdout)["artifact_validation"]
        assert body["valid"] is True
        assert body["artifact_id"] == artifact_id
        assert body["schema_verified"] is True
        assert summary_key in body["summary"]


def test_artifact_validation_report_cli_rejects_inconsistent_report(
    tmp_path: Path,
) -> None:
    payload = _validation_report_payload()
    payload["artifact_validation"]["schema_id"] = (
        "https://example.invalid/wrong.schema.json"
    )
    path = _write_json(tmp_path, "invalid-artifact-validation.json", payload)

    result = _run_cli(
        "artifact",
        "validate",
        "geotask.artifact-validation-report",
        str(path),
        "--format",
        "json",
    )

    assert result.returncode != 0
    assert result.stderr == ""
    body = json.loads(result.stdout)["artifact_validation"]
    assert body["artifact_id"] == "geotask.artifact-validation-report"
    assert body["valid"] is False
    assert body["schema_verified"] is True
    assert body["diagnostics"][0]["code"] == (
        "invalid_artifact_validation_report"
    )
    assert "schema_id must match Registry value" in body["diagnostics"][0][
        "message"
    ]
    assert "Traceback" not in result.stdout


def test_artifact_validate_cli_text_and_invalid_json_contract(tmp_path: Path) -> None:
    text_result = _run_cli(
        "artifact",
        "validate",
        "geotask.document",
        str(GT19),
    )
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")
    invalid_result = _run_cli(
        "artifact",
        "validate",
        "geotask.execution-result",
        str(malformed),
        "--format",
        "json",
    )

    assert text_result.returncode == 0
    assert text_result.stderr == ""
    assert "Artifact valid:" in text_result.stdout
    assert "Artifact: geotask.document" in text_result.stdout
    assert "Schema verified: true" in text_result.stdout

    assert invalid_result.returncode != 0
    assert invalid_result.stderr == ""
    invalid_body = json.loads(invalid_result.stdout)["artifact_validation"]
    assert invalid_body["valid"] is False
    assert invalid_body["artifact_id"] == "geotask.execution-result"
    assert invalid_body["diagnostics"][0]["code"] == "invalid_artifact_file"
    assert "Traceback" not in invalid_result.stdout


def test_artifact_validate_help_and_invalid_options_are_stable() -> None:
    top = _run_cli("--help")
    direct = _run_cli("artifact", "--help")
    nested = _run_cli("artifact", "validate", "--help")

    assert top.returncode == 0
    assert "artifact" in top.stdout
    for result in (direct, nested):
        assert result.returncode == 0
        assert result.stderr == ""
        assert "artifact validate <artifact-id> <file>" in result.stdout
        assert "--format text|json" in result.stdout
        assert "without executing" in result.stdout

    cases = (
        ("artifact", "unknown"),
        ("artifact", "validate"),
        ("artifact", "validate", "geotask.document"),
        (
            "artifact",
            "validate",
            "geotask.unknown",
            "artifact.json",
        ),
        (
            "artifact",
            "validate",
            "geotask.document",
            "artifact.yaml",
            "--format",
        ),
        (
            "artifact",
            "validate",
            "geotask.document",
            "artifact.yaml",
            "--format",
            "yaml",
        ),
        (
            "artifact",
            "validate",
            "geotask.document",
            "artifact.yaml",
            "--format",
            "json",
            "--format",
            "text",
        ),
        (
            "artifact",
            "validate",
            "geotask.document",
            "artifact.yaml",
            "--unknown",
        ),
    )
    for args in cases:
        result = _run_cli(*args)
        assert result.returncode != 0
        assert "artifact_validate_failed" in result.stderr
        assert "Traceback" not in result.stderr


def test_unified_validator_is_read_only() -> None:
    source = (
        ROOT / "src" / "geotask_core" / "v1" / "artifact_validation.py"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "execute_canonical",
        "run_geotask",
        "evaluate_control_profile",
        "next_action(",
        "subprocess",
    ):
        assert forbidden not in source
    assert "validate_document" in source
    assert "validate_versioned_payload" in source
    assert "verify_schema_bundle" in source
