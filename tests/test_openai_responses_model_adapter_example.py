"""Contract tests for the independent OpenAI Responses model Adapter package."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from geotask_core import (
    load_runtime_descriptor,
    load_runtime_request,
    submit_runtime_request,
    validate_artifact_payload,
    validate_runtime_request_contract,
)


ROOT = Path(__file__).resolve().parents[1]
NEUTRAL_ROOT = ROOT / "examples" / "model_adapters" / "provider_neutral"
OPENAI_ROOT = ROOT / "examples" / "model_adapters" / "openai_responses"
for package_src in (NEUTRAL_ROOT / "src", OPENAI_ROOT / "src"):
    if str(package_src) not in sys.path:
        sys.path.insert(0, str(package_src))

from geotask_openai_responses_adapter import (  # noqa: E402
    OPENAI_AUTHORIZATION_REF,
    OPENAI_RUNTIME_ID,
    OpenAIProviderConfigurationError,
    OpenAIResponsesConfig,
    StaticOpenAIClientResolver,
    build_openai_responses_runtime_adapter,
)


DESCRIPTOR_PATH = OPENAI_ROOT / "examples" / "openai_runtime_descriptor.json"
REQUEST_PATH = OPENAI_ROOT / "examples" / "openai_runtime_request.json"
OUTPUT_PATH = (
    NEUTRAL_ROOT / "examples" / "mock_model_execution_result.json"
)


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _request_payload() -> dict[str, object]:
    return _json(REQUEST_PATH)


def _output_payload() -> dict[str, object]:
    return _json(OUTPUT_PATH)


def _envelope(payload: dict[str, object]) -> str:
    return json.dumps(
        {"artifact_json": json.dumps(payload, ensure_ascii=False, allow_nan=False)},
        ensure_ascii=False,
        allow_nan=False,
    )


class FakeResponses:
    def __init__(self, *, response: object | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(dict(kwargs))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


class FakeOpenAIClient:
    def __init__(self, responses: FakeResponses):
        self.responses = responses
        self.option_calls: list[dict[str, object]] = []

    def with_options(self, **kwargs: object) -> "FakeOpenAIClient":
        self.option_calls.append(dict(kwargs))
        return self


class RetryableProviderError(RuntimeError):
    status_code = 429
    request_id = "req_rate_limited"


class BrokenResolver:
    def resolve(self, _authorization_ref: str) -> object:
        raise RuntimeError("[REDACTED_PRIVATE_DATA] resolver detail")


def _completed_response(payload: dict[str, object] | None = None) -> object:
    return SimpleNamespace(
        status="completed",
        output_text=_envelope(payload or _output_payload()),
        id="resp_geotask_001",
        _request_id="req_geotask_001",
    )


def _adapter(
    responses: FakeResponses,
    *,
    authorization_ref: str = OPENAI_AUTHORIZATION_REF,
):
    client = FakeOpenAIClient(responses)
    resolver = StaticOpenAIClientResolver(authorization_ref, client)
    adapter = build_openai_responses_runtime_adapter(
        OpenAIResponsesConfig(model="gpt-test-2026-07-01"),
        resolver,
    )
    return adapter, client


def test_openai_package_metadata_and_examples_are_public_contracts() -> None:
    pyproject = (OPENAI_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "geotask-openai-responses-adapter"' in pyproject
    assert 'version = "0.1.0"' in pyproject
    assert '"geotask-provider-neutral-model-adapter>=0.1.0,<0.2.0"' in pyproject
    assert '"openai>=2.46.0,<3.0.0"' in pyproject
    assert 'include = ["geotask_openai_responses_adapter*"]' in pyproject
    manifest = (OPENAI_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include examples *.json *.py" in manifest
    assert (OPENAI_ROOT / "examples" / "installed_smoke.py").is_file()
    assert (OPENAI_ROOT / "LICENSE").read_text(encoding="utf-8") == (
        ROOT / "LICENSE"
    ).read_text(encoding="utf-8")

    descriptor_payload = _json(DESCRIPTOR_PATH)
    request_payload = _request_payload()
    assert validate_artifact_payload(
        "geotask.runtime-descriptor", descriptor_payload
    ).valid is True
    assert validate_artifact_payload(
        "geotask.runtime-request", request_payload
    ).valid is True
    descriptor = load_runtime_descriptor(descriptor_payload)
    request = load_runtime_request(request_payload)
    operation = validate_runtime_request_contract(descriptor, request)
    assert descriptor.runtime_id == OPENAI_RUNTIME_ID
    assert descriptor.implementation_kind == "external"
    assert descriptor.production_ready is False
    assert descriptor.audit_supported is True
    assert descriptor.external_side_effects_allowed is True
    assert operation.side_effect == "external_read"
    assert operation.requires_authorization is True


def test_runtime_descriptor_generated_by_code_matches_file() -> None:
    adapter, _client = _adapter(FakeResponses(response=_completed_response()))
    assert adapter.describe().to_dict() == _json(DESCRIPTOR_PATH)


def test_openai_provider_completes_one_strict_audited_call() -> None:
    responses = FakeResponses(response=_completed_response())
    adapter, client = _adapter(responses)

    response = submit_runtime_request(adapter, _request_payload())

    assert response.state == "completed"
    assert response.side_effects_executed is True
    assert response.audit_ref == (
        "openai://responses/req_geotask_001/resp_geotask_001"
    )
    assert [item.artifact_id for item in response.output_artifacts] == [
        "geotask.execution-result"
    ]
    assert client.option_calls == [{"max_retries": 0, "timeout": 60.0}]
    assert len(responses.calls) == 1
    call = responses.calls[0]
    assert call["model"] == "gpt-test-2026-07-01"
    assert call["store"] is False
    assert call["truncation"] == "disabled"
    assert call["max_output_tokens"] == 4096
    assert "tools" not in call
    assert "metadata" not in call
    assert "previous_response_id" not in call
    assert "authorization" not in json.dumps(call).lower()
    format_contract = call["text"]["format"]
    assert format_contract["type"] == "json_schema"
    assert format_contract["strict"] is True
    assert format_contract["schema"] == {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "artifact_json": {
                "type": "string",
                "description": (
                    "A complete serialized geotask.execution-result/1.0 JSON object."
                ),
            }
        },
        "required": ["artifact_json"],
    }
    assert '"execution":{"mode":"model_only"' in call["input"]


def test_wrong_authorization_reference_blocks_before_openai_call() -> None:
    responses = FakeResponses(response=_completed_response())
    adapter, _client = _adapter(responses)
    request = _request_payload()
    request["runtime_request"]["authorization_ref"] = "vault://wrong-reference"

    response = submit_runtime_request(adapter, request)

    assert response.state == "blocked"
    assert response.side_effects_executed is False
    assert response.audit_ref is None
    assert response.diagnostics[0].code == "openai_client_unavailable"
    assert responses.calls == []


def test_resolver_failure_is_generic_and_does_not_leak_details() -> None:
    adapter = build_openai_responses_runtime_adapter(
        OpenAIResponsesConfig(model="gpt-test-2026-07-01"),
        BrokenResolver(),
    )
    response = submit_runtime_request(adapter, _request_payload())
    serialized = json.dumps(response.to_dict())

    assert response.state == "blocked"
    assert response.diagnostics[0].code == "openai_client_resolver_failed"
    assert "REDACTED_PRIVATE_DATA" not in serialized


def test_retryable_openai_failure_preserves_external_call_and_audit() -> None:
    responses = FakeResponses(error=RetryableProviderError("[REDACTED_PRIVATE_DATA]"))
    adapter, client = _adapter(responses)

    response = submit_runtime_request(adapter, _request_payload())
    serialized = json.dumps(response.to_dict())

    assert response.state == "failed"
    assert response.retryable is True
    assert response.side_effects_executed is True
    assert response.audit_ref == (
        "openai://responses/req_rate_limited/unknown-response"
    )
    assert response.diagnostics[0].code == "openai_responses_call_failed"
    assert "REDACTED_PRIVATE_DATA" not in serialized
    assert client.option_calls == [{"max_retries": 0, "timeout": 60.0}]
    assert len(responses.calls) == 1


def test_incomplete_or_invalid_structured_response_fails_closed() -> None:
    incomplete = SimpleNamespace(
        status="incomplete",
        output_text="",
        id="resp_incomplete",
        _request_id="req_incomplete",
    )
    response = submit_runtime_request(
        _adapter(FakeResponses(response=incomplete))[0],
        _request_payload(),
    )
    assert response.state == "failed"
    assert response.retryable is True
    assert response.diagnostics[0].code == "openai_response_not_completed"

    duplicate_outer = SimpleNamespace(
        status="completed",
        output_text=(
            '{"artifact_json":"{}","artifact_json":"{}"}'
        ),
        id="resp_duplicate",
        _request_id="req_duplicate",
    )
    response = submit_runtime_request(
        _adapter(FakeResponses(response=duplicate_outer))[0],
        _request_payload(),
    )
    assert response.state == "failed"
    assert response.retryable is False
    assert response.diagnostics[0].code == "openai_structured_output_invalid"

    nonfinite_inner = SimpleNamespace(
        status="completed",
        output_text=json.dumps({"artifact_json": '{"value":NaN}'}),
        id="resp_nonfinite",
        _request_id="req_nonfinite",
    )
    response = submit_runtime_request(
        _adapter(FakeResponses(response=nonfinite_inner))[0],
        _request_payload(),
    )
    assert response.state == "failed"
    assert response.diagnostics[0].code == "openai_structured_output_invalid"


def test_openai_output_cannot_bypass_neutral_truthfulness_guard() -> None:
    deceptive = _output_payload()
    deceptive["geotask_result"]["checks"][0]["status"] = "verified"
    deceptive["geotask_result"]["checks"][0]["assurance_level"] = (
        "local_deterministic"
    )
    deceptive["geotask_result"]["checks"][0]["deterministic"] = True
    deceptive["geotask_result"]["summary"]["verified"] = 1
    deceptive["geotask_result"]["summary"]["need_review"] = 0
    deceptive["geotask_result"]["overall"]["status"] = "verified"
    deceptive["geotask_result"]["overall"]["assurance_level"] = (
        "local_deterministic"
    )
    assert validate_artifact_payload(
        "geotask.execution-result", deceptive
    ).valid is True

    response = submit_runtime_request(
        _adapter(FakeResponses(response=_completed_response(deceptive)))[0],
        _request_payload(),
    )

    assert response.state == "failed"
    assert response.output_artifacts == ()
    assert response.side_effects_executed is True
    assert response.diagnostics[0].code == "untruthful_model_output_claim"


def test_configuration_requires_explicit_pinned_model_by_default() -> None:
    with pytest.raises(OpenAIProviderConfigurationError, match="pinned snapshot"):
        OpenAIResponsesConfig(model="gpt-current-alias")

    config = OpenAIResponsesConfig(
        model="gpt-current-alias",
        require_pinned_model=False,
    )
    assert config.model == "gpt-current-alias"


def test_public_openai_package_never_reads_environment_or_builds_credentials() -> None:
    source_root = OPENAI_ROOT / "src" / "geotask_openai_responses_adapter"
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(source_root.glob("*.py"))
    )
    assert "os.environ" not in text
    assert "getenv(" not in text
    assert "Bearer " not in text
    assert "from geotask_runtime" not in text
    assert "import geotask_runtime" not in text
    assert "responses.create" in text
    assert "max_retries=0" in text
    assert "store=False" not in text
    assert '"store": False' in text
