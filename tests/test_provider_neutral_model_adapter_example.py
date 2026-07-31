"""Tests for the independent provider-neutral model Adapter package skeleton."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from geotask_core import (
    RuntimeAdapter,
    load_runtime_descriptor,
    load_runtime_request,
    submit_runtime_request,
    validate_artifact_payload,
    validate_runtime_request_contract,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "examples" / "model_adapters" / "provider_neutral"
PACKAGE_SRC = PACKAGE_ROOT / "src"
EXAMPLES = PACKAGE_ROOT / "examples"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

from geotask_model_adapter_reference import (  # noqa: E402
    MODEL_RUNTIME_ID,
    MockStructuredModelProvider,
    ModelAdapterConfig,
    ModelAdapterContractError,
    ProviderNeutralModelRuntimeAdapter,
    StructuredModelInvocation,
    StructuredModelResult,
)


DESCRIPTOR_PATH = EXAMPLES / "model_runtime_descriptor.json"
REQUEST_PATH = EXAMPLES / "model_runtime_request.json"
OUTPUT_PATH = EXAMPLES / "mock_model_execution_result.json"


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _request_payload() -> dict[str, object]:
    return _json(REQUEST_PATH)


def _output_payload() -> dict[str, object]:
    return _json(OUTPUT_PATH)


def test_model_adapter_is_an_independent_package_skeleton() -> None:
    pyproject = (PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'name = "geotask-provider-neutral-model-adapter"' in pyproject
    assert 'version = "0.1.0"' in pyproject
    assert '"geotask-core>=0.4.0,<0.5.0"' in pyproject
    assert 'license-files = ["LICENSE"]' in pyproject
    assert '[tool.setuptools.packages.find]' in pyproject
    assert 'where = ["src"]' in pyproject
    assert 'include = ["geotask_model_adapter_reference*"]' in pyproject
    assert (PACKAGE_ROOT / "LICENSE").read_text(encoding="utf-8") == (
        ROOT / "LICENSE"
    ).read_text(encoding="utf-8")
    assert (PACKAGE_SRC / "geotask_model_adapter_reference" / "__init__.py").is_file()

    root_pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'include = ["geotask_core*"]' in root_pyproject


def test_model_adapter_examples_are_registered_and_descriptor_matches_code() -> None:
    descriptor_payload = _json(DESCRIPTOR_PATH)
    request_payload = _request_payload()
    output_payload = _output_payload()
    provider = MockStructuredModelProvider.completed(output_payload)
    adapter = ProviderNeutralModelRuntimeAdapter(provider)

    assert isinstance(adapter, RuntimeAdapter)
    assert adapter.describe().to_dict() == descriptor_payload
    descriptor = load_runtime_descriptor(descriptor_payload)
    request = load_runtime_request(request_payload)
    operation = validate_runtime_request_contract(descriptor, request)

    assert descriptor.runtime_id == MODEL_RUNTIME_ID
    assert descriptor.implementation_kind == "mock"
    assert descriptor.production_ready is False
    assert operation.operation_id == "geotask.runtime.execute-nonlocal"
    assert operation.input_artifact_ids == ("geotask.document",)
    assert operation.output_artifact_ids == ("geotask.execution-result",)
    assert operation.side_effect == "none"
    assert operation.requires_authorization is False
    assert validate_artifact_payload(
        "geotask.runtime-descriptor", descriptor_payload
    ).valid is True
    assert validate_artifact_payload(
        "geotask.runtime-request", request_payload
    ).valid is True
    assert validate_artifact_payload(
        "geotask.execution-result", output_payload
    ).valid is True


def test_mock_provider_completes_without_external_call_or_false_verification() -> None:
    output_payload = _output_payload()
    provider = MockStructuredModelProvider.completed(output_payload)
    adapter = ProviderNeutralModelRuntimeAdapter(provider)

    response = submit_runtime_request(adapter, _request_payload())

    assert response.state == "completed"
    assert response.side_effects_executed is False
    assert response.audit_ref is None
    assert [item.artifact_id for item in response.output_artifacts] == [
        "geotask.execution-result"
    ]
    result = response.output_artifacts[0].payload["geotask_result"]
    assert result["execution"]["mode"] == "model_only"
    assert result["checks"][0]["executor"] == "model"
    assert result["checks"][0]["deterministic"] is False
    assert result["checks"][0]["status"] == "computed"
    assert result["overall"]["assurance_level"] == "model_generated"
    assert provider.invocations and len(provider.invocations) == 1
    invocation = provider.invocations[0]
    assert isinstance(invocation, StructuredModelInvocation)
    assert invocation.model_ref == "mock://geotask-structured-result-v1"
    assert invocation.expected_output_artifact_id == "geotask.execution-result"
    assert invocation.authorization_ref is None
    assert invocation.metadata["model_options"]["temperature"] == 0


def test_invalid_input_and_request_contract_reject_before_provider_invocation() -> None:
    provider = MockStructuredModelProvider.completed(_output_payload())
    adapter = ProviderNeutralModelRuntimeAdapter(provider)

    invalid_input = _request_payload()
    del invalid_input["runtime_request"]["input_artifacts"][0]["payload"]["geotask"][
        "name"
    ]
    response = submit_runtime_request(adapter, invalid_input)
    assert response.state == "rejected"
    assert response.diagnostics[0].code == "invalid_model_input_artifact"
    assert provider.invocations == []

    wrong_output = _request_payload()
    wrong_output["runtime_request"]["expected_output_artifact_ids"] = [
        "geotask.control-evaluation"
    ]
    response = submit_runtime_request(adapter, wrong_output)
    assert response.state == "rejected"
    assert response.diagnostics[0].code == "model_runtime_request_contract_mismatch"
    assert provider.invocations == []

    local_execution = _request_payload()
    document = local_execution["runtime_request"]["input_artifacts"][0]["payload"]
    document["execution"]["mode"] = "local_only"
    document["execution"]["steps"][0]["executor"] = "local"
    assert validate_artifact_payload("geotask.document", document).valid is True
    response = submit_runtime_request(adapter, local_execution)
    assert response.state == "rejected"
    assert response.diagnostics[0].code == "unsupported_model_input_execution"
    assert provider.invocations == []

    credential_metadata = _request_payload()
    credential_key = "access_" + "token"
    credential_metadata["runtime_request"]["metadata"][credential_key] = (
        "[REDACTED_SECRET]"
    )
    response = submit_runtime_request(adapter, credential_metadata)
    assert response.state == "rejected"
    assert response.diagnostics[0].code == "credential_bearing_model_metadata"
    assert provider.invocations == []


def test_invalid_or_untruthful_provider_output_fails_closed() -> None:
    invalid_provider = MockStructuredModelProvider.completed({"geotask_result": {}})
    response = submit_runtime_request(
        ProviderNeutralModelRuntimeAdapter(invalid_provider),
        _request_payload(),
    )
    assert response.state == "failed"
    assert response.output_artifacts == ()
    assert response.diagnostics[0].code == "invalid_model_output_artifact"

    untruthful = _output_payload()
    untruthful["geotask_result"]["checks"][0]["status"] = "verified"
    untruthful["geotask_result"]["checks"][0]["assurance_level"] = (
        "local_deterministic"
    )
    untruthful["geotask_result"]["checks"][0]["deterministic"] = True
    untruthful["geotask_result"]["overall"]["status"] = "verified"
    untruthful["geotask_result"]["overall"]["assurance_level"] = (
        "local_deterministic"
    )
    assert validate_artifact_payload(
        "geotask.execution-result", untruthful
    ).valid is True

    response = submit_runtime_request(
        ProviderNeutralModelRuntimeAdapter(
            MockStructuredModelProvider.completed(untruthful)
        ),
        _request_payload(),
    )
    assert response.state == "failed"
    assert response.output_artifacts == ()
    assert response.diagnostics[0].code == "untruthful_model_output_claim"

    deceptive_summary = _output_payload()
    deceptive_summary["geotask_result"]["summary"]["verified"] = 1
    response = submit_runtime_request(
        ProviderNeutralModelRuntimeAdapter(
            MockStructuredModelProvider.completed(deceptive_summary)
        ),
        _request_payload(),
    )
    assert response.state == "failed"
    assert response.diagnostics[0].message == (
        "model Adapter output summary.verified must be zero"
    )


def test_provider_exception_is_generic_and_does_not_claim_runtime_state() -> None:
    class BrokenProvider:
        provider_id = "geotask.test.broken-provider"
        external_call = False
        requires_authorization = False
        audit_supported = False

        def invoke(self, _invocation: StructuredModelInvocation) -> StructuredModelResult:
            raise RuntimeError("[REDACTED_SECRET] provider-native failure")

    adapter = ProviderNeutralModelRuntimeAdapter(BrokenProvider())
    with pytest.raises(ModelAdapterContractError) as caught:
        submit_runtime_request(adapter, _request_payload())

    assert str(caught.value) == (
        "model provider failed without returning a structured result"
    )
    assert "[REDACTED_SECRET] provider-native failure" not in str(caught.value)


def test_external_provider_requires_opaque_authorization_and_preserves_audit_claim() -> None:
    class ExternalProvider:
        provider_id = "geotask.test.external-provider"
        external_call = True
        requires_authorization = True
        audit_supported = True

        def __init__(self) -> None:
            self.invocations: list[StructuredModelInvocation] = []

        def invoke(self, invocation: StructuredModelInvocation) -> StructuredModelResult:
            self.invocations.append(invocation)
            return StructuredModelResult.completed(
                _output_payload(),
                external_call_executed=True,
                audit_ref="audit://model-call-001",
            )

    provider = ExternalProvider()
    adapter = ProviderNeutralModelRuntimeAdapter(
        provider,
        ModelAdapterConfig(model_ref="provider://structured-model-v1"),
    )
    descriptor = adapter.describe()
    operation = descriptor.operations[0]

    assert descriptor.implementation_kind == "external"
    assert descriptor.external_side_effects_allowed is True
    assert descriptor.audit_supported is True
    assert operation.side_effect == "external_read"
    assert operation.requires_authorization is True

    missing_auth = _request_payload()
    response = submit_runtime_request(adapter, missing_auth)
    assert response.state == "rejected"
    assert provider.invocations == []

    authorized = _request_payload()
    authorized["runtime_request"]["authorization_ref"] = "opaque-auth-ref"
    response = submit_runtime_request(adapter, authorized)

    assert response.state == "completed"
    assert response.side_effects_executed is True
    assert response.audit_ref == "audit://model-call-001"
    assert len(provider.invocations) == 1
    assert provider.invocations[0].authorization_ref == "opaque-auth-ref"


def test_provider_claims_and_configuration_cannot_smuggle_credentials() -> None:
    with pytest.raises(ModelAdapterContractError, match="embedding credentials"):
        credential_marker = "api_" + "key=[REDACTED_SECRET]"
        ModelAdapterConfig(model_ref="provider://model?" + credential_marker)

    class ExternalWithoutAudit:
        provider_id = "geotask.test.external-without-audit"
        external_call = True
        requires_authorization = True
        audit_supported = False

        def invoke(self, _invocation: StructuredModelInvocation) -> StructuredModelResult:
            return StructuredModelResult.completed(_output_payload())

    with pytest.raises(ModelAdapterContractError, match="must support audit"):
        ProviderNeutralModelRuntimeAdapter(ExternalWithoutAudit())

    dishonest = StructuredModelResult.completed(
        _output_payload(),
        external_call_executed=True,
        audit_ref="audit://impossible",
    )
    adapter = ProviderNeutralModelRuntimeAdapter(
        MockStructuredModelProvider(dishonest)
    )
    with pytest.raises(ModelAdapterContractError, match="non-external provider"):
        submit_runtime_request(adapter, _request_payload())


def test_public_model_adapter_source_contains_no_network_or_provider_sdk() -> None:
    source_root = PACKAGE_SRC / "geotask_model_adapter_reference"
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(source_root.glob("*.py"))
    )

    assert "import requests" not in text
    assert "import httpx" not in text
    assert "from urllib" not in text
    assert "import openai" not in text
    assert "import anthropic" not in text
    assert "from geotask_runtime" not in text
    assert "import geotask_runtime" not in text
    assert "connector_credentials" not in text
    assert "token_budget" not in text
    assert "prompt_registry" not in text
