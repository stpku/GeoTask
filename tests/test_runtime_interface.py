"""Public Runtime Interface Profile and fail-closed reference adapter tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.v1.artifact_validation import validate_artifact_payload
from geotask_core.v1.runtime_interface import (
    EXECUTE_ACTION_OPERATION_ID,
    REFERENCE_RUNTIME_ID,
    RUNTIME_DESCRIPTOR_ARTIFACT_ID,
    RUNTIME_DESCRIPTOR_SCHEMA_ID,
    RUNTIME_INTERFACE_PROFILE_ID,
    RUNTIME_INTERFACE_PROFILE_VERSION,
    RUNTIME_REQUEST_ARTIFACT_ID,
    RUNTIME_REQUEST_SCHEMA_ID,
    RUNTIME_RESPONSE_ARTIFACT_ID,
    RUNTIME_RESPONSE_SCHEMA_ID,
    VALIDATE_ARTIFACT_OPERATION_ID,
    FailClosedMockRuntime,
    RuntimeAdapter,
    RuntimeArtifact,
    RuntimeDiagnostic,
    RuntimeInterfaceFormatError,
    RuntimeResponse,
    load_runtime_descriptor,
    load_runtime_request,
    load_runtime_response,
    reference_runtime_descriptor,
    runtime_interface_profile_payload,
    submit_runtime_request,
    validate_runtime_request_contract,
    validate_runtime_response_contract,
)


ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR_EXAMPLE = ROOT / "examples" / "core" / "runtime_reference_descriptor.json"
REQUEST_EXAMPLE = ROOT / "examples" / "core" / "runtime_validate_artifact_request.json"
RUNTIME_SCHEMAS = (
    ROOT / "schemas" / "geotask-runtime-descriptor-v0.1.schema.json",
    ROOT / "schemas" / "geotask-runtime-request-v0.1.schema.json",
    ROOT / "schemas" / "geotask-runtime-response-v0.1.schema.json",
)


def _request_payload() -> dict[str, object]:
    return json.loads(REQUEST_EXAMPLE.read_text(encoding="utf-8"))


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


class _StaticResponseRuntime:
    def __init__(self, response: RuntimeResponse):
        self.response = response
        self.submit_called = False

    def describe(self):
        return reference_runtime_descriptor()

    def submit(self, request):
        self.submit_called = True
        return self.response


def test_runtime_profile_and_reference_descriptor_are_fail_closed() -> None:
    profile = runtime_interface_profile_payload()["runtime_interface_profile"]
    descriptor = load_runtime_descriptor(reference_runtime_descriptor().to_dict())

    assert profile["profile_id"] == RUNTIME_INTERFACE_PROFILE_ID
    assert profile["profile_version"] == RUNTIME_INTERFACE_PROFILE_VERSION == "0.1"
    assert profile["artifact_ids"] == [
        RUNTIME_DESCRIPTOR_ARTIFACT_ID,
        RUNTIME_REQUEST_ARTIFACT_ID,
        RUNTIME_RESPONSE_ARTIFACT_ID,
    ]
    assert profile["offline_discovery"]["submits_request"] is False
    assert profile["offline_discovery"]["executes_side_effects"] is False
    assert profile["exchange_validation"]["request_contract_preflight_available"] is True
    assert profile["exchange_validation"]["input_cardinality_enforced"] is True
    assert profile["exchange_validation"]["response_bound_to_descriptor_and_request"] is True
    assert profile["exchange_validation"]["invalid_request_must_be_rejected"] is True
    assert profile["exchange_validation"]["completed_outputs_must_match_request"] is True
    assert profile["private_implementation_excluded"] is True
    assert profile["core_imports_runtime"] is False
    assert profile["credentials_in_core"] is False
    assert profile["model_calls_in_reference_runtime"] is False
    assert profile["external_side_effects_in_reference_runtime"] is False

    assert descriptor.runtime_id == REFERENCE_RUNTIME_ID
    assert descriptor.implementation_kind == "mock"
    assert descriptor.production_ready is False
    assert descriptor.audit_supported is False
    assert descriptor.credentials_managed_externally is True
    assert descriptor.external_side_effects_allowed is False
    assert [item.operation_id for item in descriptor.operations] == [
        VALIDATE_ARTIFACT_OPERATION_ID
    ]
    assert descriptor.operations[0].side_effect == "none"
    assert descriptor.operations[0].requires_authorization is False
    assert descriptor.operations[0].min_input_artifacts == 1
    assert descriptor.operations[0].max_input_artifacts == 1


def test_reference_runtime_implements_public_protocol() -> None:
    runtime = FailClosedMockRuntime()

    assert isinstance(runtime, RuntimeAdapter)
    assert load_runtime_descriptor(runtime.describe().to_dict()).runtime_id == (
        REFERENCE_RUNTIME_ID
    )


def test_runtime_request_roundtrip_and_read_only_validation_complete() -> None:
    request_payload = _request_payload()
    request = load_runtime_request(request_payload)
    response = submit_runtime_request(FailClosedMockRuntime(), request_payload)
    response_payload = response.to_dict()
    body = response_payload["runtime_response"]

    assert request.runtime_id == REFERENCE_RUNTIME_ID
    assert request.operation_id == VALIDATE_ARTIFACT_OPERATION_ID
    assert len(request.input_artifacts) == 1
    assert request.authorization_ref is None

    assert body["state"] == "completed"
    assert body["side_effects_executed"] is False
    assert body["audit_ref"] is None
    assert body["retryable"] is False
    assert body["diagnostics"] == []
    assert [item["artifact_id"] for item in body["output_artifacts"]] == [
        "geotask.artifact-validation-report"
    ]
    validation = body["output_artifacts"][0]["payload"]["artifact_validation"]
    assert validation["artifact_id"] == "geotask.document"
    assert validation["valid"] is True
    assert validation["schema_verified"] is True

    assert validate_artifact_payload(
        RUNTIME_REQUEST_ARTIFACT_ID, request_payload
    ).valid is True
    assert validate_artifact_payload(
        RUNTIME_RESPONSE_ARTIFACT_ID, response_payload
    ).valid is True
    nested_validation = validate_artifact_payload(
        "geotask.artifact-validation-report",
        body["output_artifacts"][0]["payload"],
    )
    assert nested_validation.valid is True


def test_request_contract_validation_matches_descriptor_without_submission() -> None:
    descriptor = reference_runtime_descriptor()
    request = load_runtime_request(_request_payload())

    operation = validate_runtime_request_contract(descriptor, request)

    assert operation.operation_id == VALIDATE_ARTIFACT_OPERATION_ID
    assert operation.accepts_any_registered_artifact is True
    assert operation.output_artifact_ids == (
        "geotask.artifact-validation-report",
    )


def test_request_contract_validation_rejects_unadvertised_or_mismatched_requests() -> None:
    descriptor = reference_runtime_descriptor()

    private_operation = _request_payload()
    private_operation["runtime_request"]["operation_id"] = EXECUTE_ACTION_OPERATION_ID
    with pytest.raises(RuntimeInterfaceFormatError, match="not advertised"):
        validate_runtime_request_contract(
            descriptor, load_runtime_request(private_operation)
        )

    wrong_output = _request_payload()
    wrong_output["runtime_request"]["expected_output_artifact_ids"] = [
        "geotask.execution-result"
    ]
    with pytest.raises(RuntimeInterfaceFormatError, match="exactly match"):
        validate_runtime_request_contract(descriptor, load_runtime_request(wrong_output))

    unnecessary_auth = _request_payload()
    unnecessary_auth["runtime_request"]["authorization_ref"] = "opaque-auth-ref"
    with pytest.raises(RuntimeInterfaceFormatError, match="must be null"):
        validate_runtime_request_contract(
            descriptor, load_runtime_request(unnecessary_auth)
        )

    too_many_inputs = _request_payload()
    too_many_inputs["runtime_request"]["input_artifacts"].append(
        dict(too_many_inputs["runtime_request"]["input_artifacts"][0])
    )
    with pytest.raises(RuntimeInterfaceFormatError, match="advertised maximum 1"):
        validate_runtime_request_contract(
            descriptor, load_runtime_request(too_many_inputs)
        )


def test_runtime_response_contract_accepts_valid_exchange() -> None:
    descriptor = reference_runtime_descriptor()
    request = load_runtime_request(_request_payload())
    response = FailClosedMockRuntime().submit(request)

    operation = validate_runtime_response_contract(descriptor, request, response)

    assert operation is not None
    assert operation.operation_id == VALIDATE_ARTIFACT_OPERATION_ID


def test_submit_rejects_completed_response_missing_expected_output() -> None:
    request = load_runtime_request(_request_payload())
    adapter = _StaticResponseRuntime(
        RuntimeResponse(
            request_id=request.request_id,
            runtime_id=REFERENCE_RUNTIME_ID,
            operation_id=request.operation_id,
            state="completed",
            output_artifacts=(),
            diagnostics=(),
            audit_ref=None,
            side_effects_executed=False,
            retryable=False,
            next_poll_after_ms=None,
        )
    )

    with pytest.raises(RuntimeInterfaceFormatError, match="exactly match"):
        submit_runtime_request(adapter, _request_payload())

    assert adapter.submit_called is True


def test_submit_rejects_async_acceptance_for_synchronous_operation() -> None:
    request = load_runtime_request(_request_payload())
    adapter = _StaticResponseRuntime(
        RuntimeResponse(
            request_id=request.request_id,
            runtime_id=REFERENCE_RUNTIME_ID,
            operation_id=request.operation_id,
            state="accepted",
            output_artifacts=(),
            diagnostics=(),
            audit_ref=None,
            side_effects_executed=False,
            retryable=True,
            next_poll_after_ms=1000,
        )
    )

    with pytest.raises(RuntimeInterfaceFormatError, match="synchronous"):
        submit_runtime_request(adapter, _request_payload())


def test_submit_rejects_side_effect_claim_for_read_only_operation() -> None:
    request = load_runtime_request(_request_payload())
    valid_output = FailClosedMockRuntime().submit(request).output_artifacts[0]
    adapter = _StaticResponseRuntime(
        RuntimeResponse(
            request_id=request.request_id,
            runtime_id=REFERENCE_RUNTIME_ID,
            operation_id=request.operation_id,
            state="completed",
            output_artifacts=(valid_output,),
            diagnostics=(),
            audit_ref="audit://unexpected",
            side_effects_executed=True,
            retryable=False,
            next_poll_after_ms=None,
        )
    )

    with pytest.raises(RuntimeInterfaceFormatError, match="side_effect 'none'"):
        submit_runtime_request(adapter, _request_payload())


def test_submit_requires_invalid_request_to_be_rejected() -> None:
    request_payload = _request_payload()
    request_payload["runtime_request"]["expected_output_artifact_ids"] = [
        "geotask.execution-result"
    ]
    request = load_runtime_request(request_payload)
    adapter = _StaticResponseRuntime(
        RuntimeResponse(
            request_id=request.request_id,
            runtime_id=REFERENCE_RUNTIME_ID,
            operation_id=request.operation_id,
            state="completed",
            output_artifacts=(
                RuntimeArtifact(
                    artifact_id="geotask.execution-result",
                    payload={},
                ),
            ),
            diagnostics=(),
            audit_ref=None,
            side_effects_executed=False,
            retryable=False,
            next_poll_after_ms=None,
        )
    )

    with pytest.raises(RuntimeInterfaceFormatError, match="must produce a rejected"):
        submit_runtime_request(adapter, request_payload)


def test_invalid_target_is_reported_without_failing_runtime_contract() -> None:
    request_payload = _request_payload()
    request_payload["runtime_request"]["input_artifacts"][0]["payload"] = {
        "geotask": {}
    }

    response = submit_runtime_request(FailClosedMockRuntime(), request_payload)
    body = response.to_dict()["runtime_response"]
    validation = body["output_artifacts"][0]["payload"]["artifact_validation"]

    assert body["state"] == "completed"
    assert body["side_effects_executed"] is False
    assert validation["valid"] is False
    assert validation["diagnostics"]
    assert validate_artifact_payload(
        RUNTIME_RESPONSE_ARTIFACT_ID, response.to_dict()
    ).valid is True


def test_private_operation_is_rejected_without_side_effects() -> None:
    request_payload = _request_payload()
    request_payload["runtime_request"]["operation_id"] = EXECUTE_ACTION_OPERATION_ID

    response = submit_runtime_request(FailClosedMockRuntime(), request_payload)
    body = response.to_dict()["runtime_response"]

    assert body["state"] == "rejected"
    assert body["output_artifacts"] == []
    assert body["side_effects_executed"] is False
    assert body["audit_ref"] is None
    assert body["retryable"] is False
    assert body["diagnostics"][0]["code"] == "unsupported_runtime_operation"
    assert validate_artifact_payload(
        RUNTIME_RESPONSE_ARTIFACT_ID, response.to_dict()
    ).valid is True


def test_reference_runtime_rejects_wrong_runtime_and_authorization() -> None:
    wrong_runtime = _request_payload()
    wrong_runtime["runtime_request"]["runtime_id"] = "geotask.external.runtime"
    response = submit_runtime_request(FailClosedMockRuntime(), wrong_runtime)
    assert response.state == "rejected"
    assert response.diagnostics[0].code == "runtime_id_mismatch"

    unauthorized = _request_payload()
    unauthorized["runtime_request"]["authorization_ref"] = "opaque-auth-ref"
    response = submit_runtime_request(FailClosedMockRuntime(), unauthorized)
    assert response.state == "rejected"
    assert response.diagnostics[0].code == "unexpected_authorization_reference"


def test_runtime_strict_loaders_reject_unknown_and_inconsistent_fields() -> None:
    descriptor = reference_runtime_descriptor().to_dict()
    descriptor["runtime_descriptor"]["private_router"] = "not-public"
    with pytest.raises(RuntimeInterfaceFormatError, match="unknown field"):
        load_runtime_descriptor(descriptor)

    invalid_cardinality = reference_runtime_descriptor().to_dict()
    invalid_cardinality["runtime_descriptor"]["operations"][0][
        "min_input_artifacts"
    ] = 2
    invalid_cardinality["runtime_descriptor"]["operations"][0][
        "max_input_artifacts"
    ] = 1
    with pytest.raises(RuntimeInterfaceFormatError, match="greater than or equal"):
        load_runtime_descriptor(invalid_cardinality)

    request_payload = _request_payload()
    request_payload["runtime_request"]["input_artifacts"][0]["artifact_id"] = (
        "geotask.unknown"
    )
    with pytest.raises(RuntimeInterfaceFormatError, match="unknown GeoTask artifact"):
        load_runtime_request(request_payload)

    response_payload = submit_runtime_request(
        FailClosedMockRuntime(), _request_payload()
    ).to_dict()
    response_payload["runtime_response"]["state"] = "rejected"
    response_payload["runtime_response"]["side_effects_executed"] = True
    with pytest.raises(RuntimeInterfaceFormatError, match="requires at least one error"):
        load_runtime_response(response_payload)

    response_payload = submit_runtime_request(
        FailClosedMockRuntime(), _request_payload()
    ).to_dict()
    response_payload["runtime_response"]["side_effects_executed"] = True
    with pytest.raises(RuntimeInterfaceFormatError, match="requires audit_ref"):
        load_runtime_response(response_payload)


def test_runtime_artifacts_match_public_json_schemas() -> None:
    request_payload = _request_payload()
    response_payload = submit_runtime_request(
        FailClosedMockRuntime(), request_payload
    ).to_dict()
    payloads = (
        reference_runtime_descriptor().to_dict(),
        request_payload,
        response_payload,
    )
    expected_ids = (
        RUNTIME_DESCRIPTOR_SCHEMA_ID,
        RUNTIME_REQUEST_SCHEMA_ID,
        RUNTIME_RESPONSE_SCHEMA_ID,
    )

    for path, payload, expected_id in zip(
        RUNTIME_SCHEMAS, payloads, expected_ids, strict=True
    ):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["$id"] == expected_id
        assert list(Draft202012Validator(schema).iter_errors(payload)) == []


def test_public_runtime_module_excludes_private_implementation_dependencies() -> None:
    path = ROOT / "src" / "geotask_core" / "v1" / "runtime_interface.py"
    text = path.read_text(encoding="utf-8")

    assert "from geotask_runtime" not in text
    assert "import geotask_runtime" not in text
    assert "geotask_domain_packs" not in text
    assert "model_router" not in text
    assert "encoding_registry" not in text
    assert "token_budget" not in text
    assert "connector_credentials" not in text
    assert "FailClosedMockRuntime" in text
    assert "external_side_effects_allowed=False" in text


def test_runtime_public_namespaces_export_contract() -> None:
    import geotask_core
    import geotask_core.v1 as v1

    for namespace in (geotask_core, v1):
        assert namespace.RUNTIME_INTERFACE_PROFILE_ID == RUNTIME_INTERFACE_PROFILE_ID
        assert namespace.RUNTIME_INTERFACE_PROFILE_VERSION == "0.1"
        assert namespace.RuntimeAdapter is RuntimeAdapter
        assert namespace.FailClosedMockRuntime is FailClosedMockRuntime
        assert namespace.load_runtime_descriptor is load_runtime_descriptor
        assert namespace.load_runtime_request is load_runtime_request
        assert namespace.load_runtime_response is load_runtime_response
        assert namespace.validate_runtime_request_contract is (
            validate_runtime_request_contract
        )
        assert namespace.validate_runtime_response_contract is (
            validate_runtime_response_contract
        )
        assert namespace.submit_runtime_request is submit_runtime_request


def test_reference_descriptor_example_matches_public_descriptor() -> None:
    example = json.loads(DESCRIPTOR_EXAMPLE.read_text(encoding="utf-8"))

    assert load_runtime_descriptor(example).to_dict() == reference_runtime_descriptor().to_dict()
    assert validate_artifact_payload(RUNTIME_DESCRIPTOR_ARTIFACT_ID, example).valid is True


def test_runtime_cli_inspect_and_mock_are_machine_readable(tmp_path: Path) -> None:
    descriptor_result = _run_cli("runtime", "inspect", "--format", "json")
    profile_result = _run_cli(
        "runtime", "inspect", "--profile", "--format", "json"
    )
    output_path = tmp_path / "runtime-response.json"
    mock_result = _run_cli(
        "runtime",
        "mock",
        str(REQUEST_EXAMPLE),
        "--output",
        str(output_path),
    )

    assert descriptor_result.returncode == 0
    assert descriptor_result.stderr == ""
    assert json.loads(descriptor_result.stdout)["runtime_descriptor"]["runtime_id"] == (
        REFERENCE_RUNTIME_ID
    )
    assert profile_result.returncode == 0
    assert json.loads(profile_result.stdout)["runtime_interface_profile"][
        "private_implementation_excluded"
    ] is True
    assert mock_result.returncode == 0
    assert mock_result.stdout == ""
    body = json.loads(output_path.read_text(encoding="utf-8"))["runtime_response"]
    assert body["state"] == "completed"
    assert body["side_effects_executed"] is False


def test_runtime_cli_discovers_descriptor_and_checks_request_without_submission() -> None:
    inspect_result = _run_cli(
        "runtime",
        "inspect",
        str(DESCRIPTOR_EXAMPLE),
        "--format",
        "json",
    )
    check_result = _run_cli(
        "runtime",
        "check",
        str(DESCRIPTOR_EXAMPLE),
        str(REQUEST_EXAMPLE),
        "--format",
        "json",
    )

    assert inspect_result.returncode == 0
    assert inspect_result.stderr == ""
    descriptor = json.loads(inspect_result.stdout)["runtime_descriptor"]
    assert descriptor["runtime_id"] == REFERENCE_RUNTIME_ID
    assert descriptor["operations"][0]["operation_id"] == VALIDATE_ARTIFACT_OPERATION_ID

    assert check_result.returncode == 0
    assert check_result.stderr == ""
    check = json.loads(check_result.stdout)["runtime_contract_check"]
    assert check["valid"] is True
    assert check["runtime_id"] == REFERENCE_RUNTIME_ID
    assert check["request_id"] == "validate-minimal-distance"
    assert check["operation_id"] == VALIDATE_ARTIFACT_OPERATION_ID
    assert check["submitted"] is False
    assert check["side_effects_executed"] is False


def test_runtime_cli_check_rejects_contract_mismatch_before_submission(tmp_path: Path) -> None:
    request_payload = _request_payload()
    request_payload["runtime_request"]["expected_output_artifact_ids"] = [
        "geotask.execution-result"
    ]
    request_path = tmp_path / "mismatched-runtime-request.json"
    request_path.write_text(json.dumps(request_payload), encoding="utf-8")

    result = _run_cli(
        "runtime",
        "check",
        str(DESCRIPTOR_EXAMPLE),
        str(request_path),
        "--format",
        "json",
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "runtime_failed" in result.stderr
    assert "exactly match" in result.stderr
    assert "Traceback" not in result.stderr


def test_runtime_cli_rejects_private_operation_with_exit_two(tmp_path: Path) -> None:
    request_payload = _request_payload()
    request_payload["runtime_request"]["operation_id"] = EXECUTE_ACTION_OPERATION_ID
    request_path = tmp_path / "private-action-request.json"
    request_path.write_text(json.dumps(request_payload), encoding="utf-8")

    result = _run_cli("runtime", "mock", str(request_path), "--compact")

    assert result.returncode == 2
    assert result.stderr == ""
    body = json.loads(result.stdout)["runtime_response"]
    assert body["state"] == "rejected"
    assert body["side_effects_executed"] is False
    assert body["diagnostics"][0]["code"] == "unsupported_runtime_operation"


def test_runtime_cli_never_overwrites_request_input() -> None:
    result = _run_cli(
        "runtime",
        "mock",
        str(REQUEST_EXAMPLE),
        "--output",
        str(REQUEST_EXAMPLE),
    )

    assert result.returncode == 1
    assert "runtime_failed" in result.stderr
    assert "must not overwrite an input file" in result.stderr
    assert "Traceback" not in result.stderr


def test_runtime_cli_help_is_explicit_about_private_boundary() -> None:
    top = _run_cli("--help")
    runtime = _run_cli("runtime", "--help")

    assert top.returncode == 0
    assert "runtime" in top.stdout
    assert runtime.returncode == 0
    assert "runtime inspect" in runtime.stdout
    assert "runtime check" in runtime.stdout
    assert "runtime mock" in runtime.stdout
    assert "never calls a model" in runtime.stdout
    assert "executes actions" in runtime.stdout
