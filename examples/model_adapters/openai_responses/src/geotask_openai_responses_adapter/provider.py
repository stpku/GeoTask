"""OpenAI Responses API implementation of the provider-neutral model Protocol."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass

from geotask_model_adapter_reference import (
    ProviderDiagnostic,
    StructuredModelInvocation,
    StructuredModelResult,
)

from .client import OpenAIClientResolutionError, OpenAIClientResolver
from .config import OpenAIResponsesConfig


_RESPONSE_ENVELOPE_SCHEMA = {
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
_RETRYABLE_STATUS_CODES = {408, 409, 429}
_RETRYABLE_RESPONSE_STATES = {"queued", "in_progress", "incomplete"}


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not allowed")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in pairs:
        if key in normalized:
            raise ValueError(f"duplicate JSON object key {key!r} is not allowed")
        normalized[key] = value
    return normalized


def _load_strict_object(text: object, label: str) -> dict[str, object]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{label} must be a non-empty JSON string")
    payload = json.loads(
        text,
        parse_constant=_reject_nonfinite,
        object_pairs_hook=_reject_duplicate_keys,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must have an object root")
    return payload


def _field(value: object, name: str) -> object:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _client_request_id(invocation: StructuredModelInvocation) -> str:
    value = f"{invocation.request_id}:{invocation.idempotency_key}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "geotask-openai-responses:" + value))


def _audit_ref(client_request_id: str, response: object | None = None) -> str:
    server_request_id = _field(response, "_request_id") if response is not None else None
    if not isinstance(server_request_id, str) or not server_request_id.strip():
        server_request_id = _field(response, "request_id") if response is not None else None
    response_id = _field(response, "id") if response is not None else None
    request_component = (
        server_request_id.strip()
        if isinstance(server_request_id, str) and server_request_id.strip()
        else "client-" + client_request_id
    )
    response_component = (
        response_id.strip()
        if isinstance(response_id, str) and response_id.strip()
        else "unknown-response"
    )
    return f"openai://responses/{request_component}/{response_component}"


def _diagnostic(
    code: str,
    message: str,
    suggested_fix: str,
    *,
    path: str = "provider.openai",
) -> ProviderDiagnostic:
    return ProviderDiagnostic(
        code=code,
        path=path,
        message=message,
        severity="error",
        suggested_fix=suggested_fix,
    )


def _blocked(code: str, message: str, suggested_fix: str) -> StructuredModelResult:
    return StructuredModelResult(
        state="blocked",
        output_payload=None,
        diagnostics=(_diagnostic(code, message, suggested_fix),),
        external_call_executed=False,
        audit_ref=None,
        retryable=False,
    )


def _failed(
    code: str,
    message: str,
    suggested_fix: str,
    *,
    retryable: bool,
    audit_ref: str,
    path: str = "provider.openai",
) -> StructuredModelResult:
    return StructuredModelResult.failed(
        _diagnostic(code, message, suggested_fix, path=path),
        retryable=retryable,
        external_call_executed=True,
        audit_ref=audit_ref,
    )


def _retryable_exception(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code in _RETRYABLE_STATUS_CODES or status_code >= 500
    name = type(exc).__name__.lower()
    return "timeout" in name or "connection" in name or "rate" in name


@dataclass(frozen=True)
class OpenAIResponsesStructuredProvider:
    """Perform one synchronous, non-streaming, structured Responses API call."""

    config: OpenAIResponsesConfig
    client_resolver: OpenAIClientResolver

    provider_id = "openai.responses"
    external_call = True
    requires_authorization = True
    audit_supported = True

    def __post_init__(self) -> None:
        if not isinstance(self.config, OpenAIResponsesConfig):
            raise TypeError("config must be an OpenAIResponsesConfig")
        if not isinstance(self.client_resolver, OpenAIClientResolver):
            raise TypeError("client_resolver must implement OpenAIClientResolver")

    def invoke(self, invocation: StructuredModelInvocation) -> StructuredModelResult:
        if not isinstance(invocation, StructuredModelInvocation):
            raise TypeError("invocation must be a StructuredModelInvocation")
        if invocation.authorization_ref is None:
            return _blocked(
                "openai_authorization_ref_missing",
                "The OpenAI provider requires an opaque authorization reference.",
                "Use the authorization reference accepted by the configured resolver.",
            )
        try:
            client = self.client_resolver.resolve(invocation.authorization_ref)
        except OpenAIClientResolutionError:
            return _blocked(
                "openai_client_unavailable",
                "An authenticated OpenAI client could not be resolved.",
                "Bind the opaque authorization reference to an externally constructed official SDK client.",
            )
        except Exception:
            return _blocked(
                "openai_client_resolver_failed",
                "The OpenAI client resolver failed without a safe diagnostic.",
                "Repair the external resolver without exposing private authentication data.",
            )

        with_options = getattr(client, "with_options", None)
        if not callable(with_options):
            return _blocked(
                "openai_client_options_unavailable",
                "The resolved client does not expose with_options.",
                "Use a supported official OpenAI SDK client that can disable retries per call.",
            )
        try:
            request_client = with_options(
                max_retries=0,
                timeout=float(self.config.timeout_seconds),
            )
        except Exception:
            return _blocked(
                "openai_client_options_failed",
                "The resolved client could not apply no-retry request options.",
                "Verify the official SDK version and client construction outside the Adapter.",
            )

        responses = getattr(request_client, "responses", None)
        create = getattr(responses, "create", None)
        if not callable(create):
            return _blocked(
                "openai_responses_api_unavailable",
                "The configured client does not expose responses.create.",
                "Use a supported official OpenAI SDK version from the package dependency range.",
            )

        client_request_id = _client_request_id(invocation)
        input_text = (
            "Generate the registered GeoTask execution-result for this document. "
            "Do not execute tools or claim independent verification.\n\n"
            + json.dumps(
                invocation.input_payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        )
        request_options: dict[str, object] = {
            "model": self.config.model,
            "instructions": self.config.instructions,
            "input": input_text,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "geotask_execution_result_envelope",
                    "description": (
                        "A strict envelope containing one serialized GeoTask execution-result Artifact."
                    ),
                    "schema": _RESPONSE_ENVELOPE_SCHEMA,
                    "strict": True,
                }
            },
            "store": False,
            "truncation": "disabled",
        }
        output_limit_name = "max_output_" + "tokens"
        request_options[output_limit_name] = self.config.max_output_tokens

        try:
            response = create(**request_options)
        except Exception as exc:
            return _failed(
                "openai_responses_call_failed",
                "The OpenAI Responses API call did not return a structured response.",
                "Review the audit reference before deciding whether to retry.",
                retryable=_retryable_exception(exc),
                audit_ref=_audit_ref(client_request_id, exc),
            )

        audit_ref = _audit_ref(client_request_id, response)
        status = _field(response, "status")
        if status != "completed":
            return _failed(
                "openai_response_not_completed",
                "The OpenAI response did not reach completed state.",
                "Inspect the audit reference and submit a new Runtime Request when appropriate.",
                retryable=status in _RETRYABLE_RESPONSE_STATES,
                audit_ref=audit_ref,
                path="provider.openai.response.status",
            )

        try:
            envelope = _load_strict_object(
                _field(response, "output_text"),
                "OpenAI response output_text",
            )
            if set(envelope) != {"artifact_json"}:
                raise ValueError(
                    "OpenAI response envelope must contain exactly artifact_json"
                )
            output_payload = _load_strict_object(
                envelope["artifact_json"],
                "OpenAI response artifact_json",
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            return _failed(
                "openai_structured_output_invalid",
                "The completed OpenAI response did not contain the required strict GeoTask artifact envelope.",
                "Use a compatible pinned model and preserve the strict response schema and instructions.",
                retryable=False,
                audit_ref=audit_ref,
                path="provider.openai.response.output_text",
            )

        return StructuredModelResult.completed(
            output_payload,
            external_call_executed=True,
            audit_ref=audit_ref,
        )


__all__ = ["OpenAIResponsesStructuredProvider"]
