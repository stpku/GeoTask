"""Control Evaluation Result strict loading and CLI validation tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.parser import load_geotask
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.control_evaluation import (
    CONTROL_EVALUATION_SCHEMA_ID,
    CONTROL_EVALUATION_SCHEMA_VERSION,
    ControlEvaluationFormatError,
    evaluate_control_profile,
    load_control_evaluation,
)
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.serialized_validation import (
    CONTROL_EVALUATION_VALIDATION_CONTRACT,
    EXECUTION_RESULT_VALIDATION_CONTRACT,
    validate_versioned_payload,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = (
    REPO_ROOT / "schemas" / "geotask-control-evaluation-v1.0.schema.json"
)
GT19 = REPO_ROOT / "examples" / "core" / "uav_arrival_ground_clearance_release.yaml"
MINIMAL = REPO_ROOT / "examples" / "core" / "v1_minimal_distance.yaml"


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


def _control_payload(*, blocked: bool = True) -> dict:
    document = canonicalize(load_geotask(GT19))
    execution_result = execute_canonical(document)
    return evaluate_control_profile(
        document,
        execution_result,
        {
            "ground_zone_clear": not blocked,
            "clearance_evidence_age_seconds": 8,
        },
    ).to_dict()


def _not_applicable_payload() -> dict:
    document = canonicalize(load_geotask(MINIMAL))
    return evaluate_control_profile(document, execute_canonical(document)).to_dict()


def _write_payload(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "control-evaluation.json"
    path.write_text(
        json.dumps(payload or _control_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_control_evaluation_schema_constants_and_strict_roundtrip() -> None:
    payload = _control_payload()
    schema = _schema()

    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == CONTROL_EVALUATION_SCHEMA_ID
    assert CONTROL_EVALUATION_SCHEMA_VERSION == "1.0"
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []

    loaded = load_control_evaluation(payload)
    assert loaded.to_dict() == payload
    assert loaded.task_id == "gt19-uav-arrival-ground-clearance-release"
    assert loaded.state == "blocked"
    assert len(loaded.evaluations) == 1
    assert loaded.action_executed is False


def test_not_applicable_control_result_roundtrips_with_empty_profile() -> None:
    payload = _not_applicable_payload()

    loaded = load_control_evaluation(payload)

    assert loaded.state == "not_applicable"
    assert loaded.profile_id == ""
    assert loaded.profile_version == ""
    assert loaded.evaluations == ()
    assert loaded.to_dict() == payload


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda p: p["control_evaluation"].__setitem__("action_executed", True),
            "action_executed must be false",
        ),
        (
            lambda p: p["control_evaluation"]["evaluations"][0].__setitem__(
                "action_executed", True
            ),
            "action_executed must be false",
        ),
        (
            lambda p: p["control_evaluation"].__setitem__("state", "satisfied"),
            "state must be 'blocked'",
        ),
        (
            lambda p: p["control_evaluation"].__setitem__(
                "blocked_outputs", ["different_output"]
            ),
            "blocked_outputs must aggregate evaluations",
        ),
        (
            lambda p: p["control_evaluation"]["control_context"]["entries"][
                "ground_zone_clear"
            ].__setitem__("value", True),
            "must equal",
        ),
        (
            lambda p: p["control_evaluation"]["evaluations"][0].__setitem__(
                "state", "unknown"
            ),
            "state must be 'blocked'",
        ),
        (
            lambda p: p["control_evaluation"]["evaluations"][0].__setitem__(
                "referenced_identifiers", []
            ),
            "must match expression identifiers",
        ),
        (
            lambda p: p["control_evaluation"]["evaluations"][0].__setitem__(
                "unknown_identifiers", ["invented_state"]
            ),
            "must match unresolved context identifiers",
        ),
        (
            lambda p: p["control_evaluation"]["evaluations"][0].__setitem__(
                "expression", "unsafe_call()"
            ),
            "expression is invalid",
        ),
    ],
)
def test_strict_loader_rejects_semantic_inconsistencies(mutator, message: str) -> None:
    payload = deepcopy(_control_payload())
    mutator(payload)

    with pytest.raises(ControlEvaluationFormatError, match=message):
        load_control_evaluation(payload)


def test_public_manifest_requires_validation_framework_assets() -> None:
    manifest = (REPO_ROOT / ".release" / "public-manifest.yaml").read_text(
        encoding="utf-8"
    )

    for path in (
        "src/geotask_core/v1/serialized_validation.py",
        "docs/spec/geotask-versioned-payload-validation-v1.0.md",
        "tests/test_control_validation_cli.py",
    ):
        assert path in manifest


def test_public_namespaces_export_validation_framework() -> None:
    import geotask_core
    import geotask_core.v1 as v1

    for namespace in (geotask_core, v1):
        assert namespace.CONTROL_EVALUATION_SCHEMA_ID == CONTROL_EVALUATION_SCHEMA_ID
        assert namespace.CONTROL_EVALUATION_SCHEMA_VERSION == "1.0"
        assert namespace.load_control_evaluation is load_control_evaluation
        assert namespace.validate_versioned_payload is validate_versioned_payload
        assert namespace.CONTROL_EVALUATION_VALIDATION_CONTRACT is (
            CONTROL_EVALUATION_VALIDATION_CONTRACT
        )
        assert namespace.EXECUTION_RESULT_VALIDATION_CONTRACT is (
            EXECUTION_RESULT_VALIDATION_CONTRACT
        )


def test_shared_validation_framework_handles_both_artifact_contracts() -> None:
    control_report, control_loaded = validate_versioned_payload(
        _control_payload(),
        CONTROL_EVALUATION_VALIDATION_CONTRACT,
        file="control.json",
    )

    document = canonicalize(load_geotask(GT19))
    result_payload = execute_canonical(document).to_dict()
    result_report, result_loaded = validate_versioned_payload(
        result_payload,
        EXECUTION_RESULT_VALIDATION_CONTRACT,
        file="result.json",
    )

    assert control_report.to_dict()["control_validation"]["evaluation_count"] == 1
    assert control_loaded is not None
    assert result_report.to_dict()["result_validation"]["check_count"] == 4
    assert result_loaded is not None
    assert control_report.contract.schema_id == CONTROL_EVALUATION_SCHEMA_ID


def test_control_validate_help_lists_validate_and_nonexecuting_boundary() -> None:
    results = (
        _run_cli("control", "--help"),
        _run_cli("control", "validate", "--help"),
    )

    for result in results:
        assert result.returncode == 0
        assert "control validate" in result.stdout
        assert "Control Evaluation Result v1.0" in result.stdout
        assert "execut" in result.stdout.lower()


def test_complete_cli_pipeline_ends_with_control_validation(tmp_path: Path) -> None:
    execution_path = tmp_path / "execution-result.json"
    state_path = tmp_path / "control-state.yaml"
    control_path = tmp_path / "control-evaluation.json"
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
        str(execution_path),
    )
    result_validation = _run_cli(
        "result", "validate", str(execution_path), "--format", "json"
    )
    control_evaluation = _run_cli(
        "control",
        "evaluate",
        str(GT19),
        "--result",
        str(execution_path),
        "--state",
        str(state_path),
        "--output",
        str(control_path),
    )
    control_validation = _run_cli(
        "control", "validate", str(control_path), "--format", "json"
    )

    for result in (
        run_result,
        result_validation,
        control_evaluation,
        control_validation,
    ):
        assert result.returncode == 0
        assert result.stderr == ""
    assert json.loads(result_validation.stdout)["result_validation"]["valid"] is True
    report = json.loads(control_validation.stdout)["control_validation"]
    assert report["valid"] is True
    assert report["evaluation_count"] == 1
    assert report["task_id"] == "gt19-uav-arrival-ground-clearance-release"


def test_control_validate_valid_text_report(tmp_path: Path) -> None:
    path = _write_payload(tmp_path)

    result = _run_cli("control", "validate", str(path))

    assert result.returncode == 0
    assert result.stderr == ""
    assert "Control evaluation valid:" in result.stdout
    assert CONTROL_EVALUATION_SCHEMA_ID in result.stdout
    assert "gt19-uav-arrival-ground-clearance-release" in result.stdout
    assert "Evaluations: 1" in result.stdout


def test_control_validate_valid_json_report(tmp_path: Path) -> None:
    path = _write_payload(tmp_path)

    result = _run_cli(
        "control",
        "validate",
        str(path),
        "--format",
        "json",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    report = json.loads(result.stdout)["control_validation"]
    assert report == {
        "valid": True,
        "schema_id": CONTROL_EVALUATION_SCHEMA_ID,
        "schema_version": "1.0",
        "file": str(path),
        "task_id": "gt19-uav-arrival-ground-clearance-release",
        "evaluation_count": 1,
        "diagnostics": [],
    }


def test_control_validate_invalid_json_report_is_machine_readable(
    tmp_path: Path,
) -> None:
    payload = _control_payload()
    payload["control_evaluation"]["action_executed"] = True
    path = _write_payload(tmp_path, payload)

    result = _run_cli(
        "control",
        "validate",
        str(path),
        "--format",
        "json",
    )

    assert result.returncode != 0
    assert result.stderr == ""
    report = json.loads(result.stdout)["control_validation"]
    assert report["valid"] is False
    assert report["schema_id"] == CONTROL_EVALUATION_SCHEMA_ID
    assert report["evaluation_count"] == 0
    assert report["diagnostics"][0]["code"] == "invalid_control_evaluation"
    assert "action_executed must be false" in report["diagnostics"][0]["message"]


def test_control_validate_malformed_and_duplicate_json_have_no_traceback(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"control_evaluation": {}, "control_evaluation": {}}',
        encoding="utf-8",
    )

    for path in (malformed, duplicate):
        result = _run_cli(
            "control",
            "validate",
            str(path),
            "--format",
            "json",
        )
        assert result.returncode != 0
        assert result.stderr == ""
        report = json.loads(result.stdout)["control_validation"]
        assert report["valid"] is False
        assert "invalid JSON" in report["diagnostics"][0]["message"]
        assert "Traceback" not in result.stdout


def test_control_validate_rejects_invalid_options() -> None:
    cases = (
        ("control", "validate"),
        ("control", "validate", "control.json", "--format", "yaml"),
        (
            "control",
            "validate",
            "control.json",
            "--format",
            "json",
            "--format",
            "json",
        ),
        ("control", "validate", "control.json", "--unknown"),
        ("control", "unknown"),
    )

    for args in cases:
        result = _run_cli(*args)
        assert result.returncode != 0
        assert "Traceback" not in result.stderr


def test_control_validate_command_never_evaluates_or_executes() -> None:
    source = (REPO_ROOT / "src" / "geotask_core" / "cli.py").read_text(
        encoding="utf-8"
    )
    command_source = source.split("def _cmd_control_validate", 1)[1].split(
        "def cmd_control", 1
    )[0]
    framework_source = (
        REPO_ROOT / "src" / "geotask_core" / "v1" / "serialized_validation.py"
    ).read_text(encoding="utf-8")

    assert "evaluate_control_profile" not in command_source
    assert "execute_canonical" not in command_source
    assert "next_action(" not in command_source
    assert "CONTROL_EVALUATION_VALIDATION_CONTRACT" in command_source
    assert "loader=load_control_evaluation" in framework_source
