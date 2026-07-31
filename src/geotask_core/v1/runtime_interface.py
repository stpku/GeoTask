"""Public Runtime SDK contracts for GeoTask Core.

This module defines only the external contract between the open Core and an
independently implemented Runtime. It intentionally contains no model routing,
encoding strategy selection, token budgeting, data connector, credential, or
production action implementation.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


RUNTIME_INTERFACE_PROFILE_ID = "geotask.runtime-interface"
RUNTIME_INTERFACE_PROFILE_VERSION = "0.1"

RUNTIME_DESCRIPTOR_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-runtime-descriptor-v0.1.schema.json"
)
RUNTIME_REQUEST_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-runtime-request-v0.1.schema.json"
)
RUNTIME_RESPONSE_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-runtime-response-v0.1.schema.json"
)
RUNTIME_DESCRIPTOR_SCHEMA_VERSION = "0.1"
RUNTIME_REQUEST_SCHEMA_VERSION = "0.1"
RUNTIME_RESPONSE_SCHEMA_VERSION = "0.1"

RUNTIME_DESCRIPTOR_ARTIFACT_ID = "geotask.runtime-descriptor"
RUNTIME_REQUEST_ARTIFACT_ID = "geotask.runtime-request"
RUNTIME_RESPONSE_ARTIFACT_ID = "geotask.runtime-response"

VALIDATE_ARTIFACT_OPERATION_ID = "geotask.runtime.validate-artifact"
EXECUTE_NONLOCAL_OPERATION_ID = "geotask.runtime.execute-nonlocal"
RESOLVE_EVIDENCE_OPERATION_ID = "geotask.runtime.resolve-evidence"
EXECUTE_ACTION_OPERATION_ID = "geotask.runtime.execute-action"

REFERENCE_RUNTIME_ID = "geotask.reference.fail-closed"
REFERENCE_RUNTIME_VERSION = "0.1"

_RUNTIME_IMPLEMENTATION_KINDS = {"mock", "external"}
_RUNTIME_SIDE_EFFECTS = {"none", "external_read", "external_write"}
_RUNTIME_RESPONSE_STATES = {"accepted", "completed", "blocked", "rejected", "failed"}
_RUNTIME_DIAGNOSTIC_SEVERITIES = {"error", "warning"}


class RuntimeInterfaceFormatError(ValueError):
    """Raised when a Runtime SDK artifact violates the public contract."""


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RuntimeInterfaceFormatError(f"{label} must be an object")
    return value


def _require_exact_fields(
    value: Mapping[str, object],
    expected: set[str],
    label: str,
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise RuntimeInterfaceFormatError(
            f"{label} is missing required field(s): {', '.join(missing)}"
        )
    if unknown:
        raise RuntimeInterfaceFormatError(
            f"{label} contains unknown field(s): {', '.join(unknown)}"
        )


def _require_non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeInterfaceFormatError(f"{label} must be a non-empty string")
    return value


def _require_optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise RuntimeInterfaceFormatError(f"{label} must be null or a non-empty string")
    return value


def _require_boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise RuntimeInterfaceFormatError(f"{label} must be boolean")
    return value


def _require_string_list(
    value: object,
    label: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise RuntimeInterfaceFormatError(f"{label} must be an array")
    if not allow_empty and not value:
        raise RuntimeInterfaceFormatError(f"{label} must not be empty")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _require_non_empty_string(item, f"{label}[{index}]")
        if text in seen:
            raise RuntimeInterfaceFormatError(f"{label} contains duplicate value {text!r}")
        seen.add(text)
        normalized.append(text)
    return tuple(normalized)


def _require_registered_artifact_id(value: object, label: str) -> str:
    artifact_id = _require_non_empty_string(value, label)
    from geotask_core.v1.artifact_registry import get_artifact_descriptor

    try:
        get_artifact_descriptor(artifact_id)
    except KeyError as exc:
        raise RuntimeInterfaceFormatError(str(exc)) from None
    return artifact_id


def _require_registered_artifact_ids(
    value: object,
    label: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    artifact_ids = _require_string_list(value, label, allow_empty=allow_empty)
    for index, artifact_id in enumerate(artifact_ids):
        _require_registered_artifact_id(artifact_id, f"{label}[{index}]")
    return artifact_ids


def _require_json_value(value: object, label: str) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RuntimeInterfaceFormatError(f"{label} must contain only finite numbers")
        return value
    if isinstance(value, list):
        return [
            _require_json_value(item, f"{label}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise RuntimeInterfaceFormatError(f"{label} keys must be strings")
            normalized[key] = _require_json_value(item, f"{label}.{key}")
        return normalized
    raise RuntimeInterfaceFormatError(f"{label} must contain only JSON values")


@dataclass(frozen=True)
class RuntimeArtifact:
    """One registered Artifact embedded in a Runtime request or response."""

    artifact_id: str
    payload: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class RuntimeDiagnostic:
    """Normalized Runtime diagnostic used by the response envelope."""

    code: str
    path: str
    message: str
    severity: str
    suggested_fix: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
            "suggested_fix": self.suggested_fix,
        }


@dataclass(frozen=True)
class RuntimeOperationDescriptor:
    """One operation advertised by a Runtime implementation."""

    operation_id: str
    title: str
    description: str
    input_artifact_ids: tuple[str, ...]
    accepts_any_registered_artifact: bool
    min_input_artifacts: int
    max_input_artifacts: int | None
    output_artifact_ids: tuple[str, ...]
    side_effect: str
    requires_authorization: bool
    synchronous: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "title": self.title,
            "description": self.description,
            "input_artifact_ids": list(self.input_artifact_ids),
            "accepts_any_registered_artifact": self.accepts_any_registered_artifact,
            "min_input_artifacts": self.min_input_artifacts,
            "max_input_artifacts": self.max_input_artifacts,
            "output_artifact_ids": list(self.output_artifact_ids),
            "side_effect": self.side_effect,
            "requires_authorization": self.requires_authorization,
            "synchronous": self.synchronous,
        }


@dataclass(frozen=True)
class RuntimeDescriptor:
    """Versioned capability advertisement for one Runtime implementation."""

    runtime_id: str
    runtime_version: str
    title: str
    implementation_kind: str
    production_ready: bool
    capabilities: tuple[str, ...]
    operations: tuple[RuntimeOperationDescriptor, ...]
    audit_supported: bool
    credentials_managed_externally: bool
    external_side_effects_allowed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime_descriptor": {
                "interface_version": RUNTIME_INTERFACE_PROFILE_VERSION,
                "runtime_id": self.runtime_id,
                "runtime_version": self.runtime_version,
                "title": self.title,
                "implementation_kind": self.implementation_kind,
                "production_ready": self.production_ready,
                "capabilities": list(self.capabilities),
                "operations": [item.to_dict() for item in self.operations],
                "audit_supported": self.audit_supported,
                "credentials_managed_externally": self.credentials_managed_externally,
                "external_side_effects_allowed": self.external_side_effects_allowed,
            }
        }


@dataclass(frozen=True)
class RuntimeRequest:
    """One versioned request submitted to a Runtime adapter."""

    request_id: str
    runtime_id: str
    operation_id: str
    input_artifacts: tuple[RuntimeArtifact, ...]
    expected_output_artifact_ids: tuple[str, ...]
    authorization_ref: str | None
    idempotency_key: str
    metadata: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime_request": {
                "interface_version": RUNTIME_INTERFACE_PROFILE_VERSION,
                "request_id": self.request_id,
                "runtime_id": self.runtime_id,
                "operation_id": self.operation_id,
                "input_artifacts": [item.to_dict() for item in self.input_artifacts],
                "expected_output_artifact_ids": list(
                    self.expected_output_artifact_ids
                ),
                "authorization_ref": self.authorization_ref,
                "idempotency_key": self.idempotency_key,
                "metadata": dict(self.metadata),
            }
        }


@dataclass(frozen=True)
class RuntimeResponse:
    """One versioned response returned by a Runtime adapter."""

    request_id: str
    runtime_id: str
    operation_id: str
    state: str
    output_artifacts: tuple[RuntimeArtifact, ...]
    diagnostics: tuple[RuntimeDiagnostic, ...]
    audit_ref: str | None
    side_effects_executed: bool
    retryable: bool
    next_poll_after_ms: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime_response": {
                "interface_version": RUNTIME_INTERFACE_PROFILE_VERSION,
                "request_id": self.request_id,
                "runtime_id": self.runtime_id,
                "operation_id": self.operation_id,
                "state": self.state,
                "output_artifacts": [item.to_dict() for item in self.output_artifacts],
                "diagnostics": [item.to_dict() for item in self.diagnostics],
                "audit_ref": self.audit_ref,
                "side_effects_executed": self.side_effects_executed,
                "retryable": self.retryable,
                "next_poll_after_ms": self.next_poll_after_ms,
            }
        }


@runtime_checkable
class RuntimeAdapter(Protocol):
    """Structural interface implemented by an external GeoTask Runtime."""

    def describe(self) -> RuntimeDescriptor:
        """Return a stable Runtime capability descriptor."""

    def submit(self, request: RuntimeRequest) -> RuntimeResponse:
        """Process one already validated Runtime request."""


def _load_runtime_artifact(value: object, label: str) -> RuntimeArtifact:
    artifact = _require_mapping(value, label)
    _require_exact_fields(artifact, {"artifact_id", "payload"}, label)
    artifact_id = _require_registered_artifact_id(
        artifact["artifact_id"], f"{label}.artifact_id"
    )
    payload = _require_mapping(artifact["payload"], f"{label}.payload")
    normalized_payload = _require_json_value(payload, f"{label}.payload")
    assert isinstance(normalized_payload, dict)
    return RuntimeArtifact(artifact_id=artifact_id, payload=normalized_payload)


def _load_runtime_diagnostic(value: object, label: str) -> RuntimeDiagnostic:
    diagnostic = _require_mapping(value, label)
    _require_exact_fields(
        diagnostic,
        {"code", "path", "message", "severity", "suggested_fix"},
        label,
    )
    code = _require_non_empty_string(diagnostic["code"], f"{label}.code")
    path = diagnostic["path"]
    if not isinstance(path, str):
        raise RuntimeInterfaceFormatError(f"{label}.path must be a string")
    message = _require_non_empty_string(diagnostic["message"], f"{label}.message")
    severity = diagnostic["severity"]
    if severity not in _RUNTIME_DIAGNOSTIC_SEVERITIES:
        raise RuntimeInterfaceFormatError(
            f"{label}.severity must be 'error' or 'warning'"
        )
    suggested_fix = diagnostic["suggested_fix"]
    if not isinstance(suggested_fix, str):
        raise RuntimeInterfaceFormatError(
            f"{label}.suggested_fix must be a string"
        )
    return RuntimeDiagnostic(
        code=code,
        path=path,
        message=message,
        severity=severity,
        suggested_fix=suggested_fix,
    )


def load_runtime_descriptor(payload: Mapping[str, object]) -> RuntimeDescriptor:
    """Strictly load a ``runtime_descriptor/0.1`` Artifact."""

    root = _require_mapping(payload, "Runtime Descriptor")
    _require_exact_fields(root, {"runtime_descriptor"}, "descriptor root")
    body = _require_mapping(root["runtime_descriptor"], "runtime_descriptor")
    _require_exact_fields(
        body,
        {
            "interface_version",
            "runtime_id",
            "runtime_version",
            "title",
            "implementation_kind",
            "production_ready",
            "capabilities",
            "operations",
            "audit_supported",
            "credentials_managed_externally",
            "external_side_effects_allowed",
        },
        "runtime_descriptor",
    )
    if body["interface_version"] != RUNTIME_INTERFACE_PROFILE_VERSION:
        raise RuntimeInterfaceFormatError(
            "runtime_descriptor.interface_version must be "
            f"{RUNTIME_INTERFACE_PROFILE_VERSION!r}"
        )
    runtime_id = _require_non_empty_string(
        body["runtime_id"], "runtime_descriptor.runtime_id"
    )
    runtime_version = _require_non_empty_string(
        body["runtime_version"], "runtime_descriptor.runtime_version"
    )
    title = _require_non_empty_string(body["title"], "runtime_descriptor.title")
    implementation_kind = body["implementation_kind"]
    if implementation_kind not in _RUNTIME_IMPLEMENTATION_KINDS:
        raise RuntimeInterfaceFormatError(
            "runtime_descriptor.implementation_kind must be 'mock' or 'external'"
        )
    production_ready = _require_boolean(
        body["production_ready"], "runtime_descriptor.production_ready"
    )
    capabilities = _require_string_list(
        body["capabilities"], "runtime_descriptor.capabilities"
    )
    operations_value = body["operations"]
    if not isinstance(operations_value, list) or not operations_value:
        raise RuntimeInterfaceFormatError(
            "runtime_descriptor.operations must be a non-empty array"
        )
    operations: list[RuntimeOperationDescriptor] = []
    operation_ids: set[str] = set()
    for index, item in enumerate(operations_value):
        label = f"runtime_descriptor.operations[{index}]"
        operation = _require_mapping(item, label)
        _require_exact_fields(
            operation,
            {
                "operation_id",
                "title",
                "description",
                "input_artifact_ids",
                "accepts_any_registered_artifact",
                "min_input_artifacts",
                "max_input_artifacts",
                "output_artifact_ids",
                "side_effect",
                "requires_authorization",
                "synchronous",
            },
            label,
        )
        operation_id = _require_non_empty_string(
            operation["operation_id"], f"{label}.operation_id"
        )
        if operation_id in operation_ids:
            raise RuntimeInterfaceFormatError(
                f"runtime_descriptor.operations contains duplicate operation {operation_id!r}"
            )
        operation_ids.add(operation_id)
        operation_title = _require_non_empty_string(
            operation["title"], f"{label}.title"
        )
        description = _require_non_empty_string(
            operation["description"], f"{label}.description"
        )
        accepts_any = _require_boolean(
            operation["accepts_any_registered_artifact"],
            f"{label}.accepts_any_registered_artifact",
        )
        input_artifact_ids = _require_registered_artifact_ids(
            operation["input_artifact_ids"], f"{label}.input_artifact_ids"
        )
        if accepts_any and input_artifact_ids:
            raise RuntimeInterfaceFormatError(
                f"{label}.input_artifact_ids must be empty when "
                "accepts_any_registered_artifact is true"
            )
        if not accepts_any and not input_artifact_ids:
            raise RuntimeInterfaceFormatError(
                f"{label} must declare input_artifact_ids or accept any registered Artifact"
            )
        min_input_artifacts = operation["min_input_artifacts"]
        if (
            not isinstance(min_input_artifacts, int)
            or isinstance(min_input_artifacts, bool)
            or min_input_artifacts < 1
        ):
            raise RuntimeInterfaceFormatError(
                f"{label}.min_input_artifacts must be a positive integer"
            )
        max_input_artifacts = operation["max_input_artifacts"]
        if max_input_artifacts is not None and (
            not isinstance(max_input_artifacts, int)
            or isinstance(max_input_artifacts, bool)
            or max_input_artifacts < min_input_artifacts
        ):
            raise RuntimeInterfaceFormatError(
                f"{label}.max_input_artifacts must be null or an integer greater "
                "than or equal to min_input_artifacts"
            )
        output_artifact_ids = _require_registered_artifact_ids(
            operation["output_artifact_ids"],
            f"{label}.output_artifact_ids",
            allow_empty=False,
        )
        side_effect = operation["side_effect"]
        if side_effect not in _RUNTIME_SIDE_EFFECTS:
            raise RuntimeInterfaceFormatError(
                f"{label}.side_effect must be one of {sorted(_RUNTIME_SIDE_EFFECTS)!r}"
            )
        requires_authorization = _require_boolean(
            operation["requires_authorization"],
            f"{label}.requires_authorization",
        )
        if side_effect == "external_write" and not requires_authorization:
            raise RuntimeInterfaceFormatError(
                f"{label}.requires_authorization must be true for external_write"
            )
        synchronous = _require_boolean(
            operation["synchronous"], f"{label}.synchronous"
        )
        operations.append(
            RuntimeOperationDescriptor(
                operation_id=operation_id,
                title=operation_title,
                description=description,
                input_artifact_ids=input_artifact_ids,
                accepts_any_registered_artifact=accepts_any,
                min_input_artifacts=min_input_artifacts,
                max_input_artifacts=max_input_artifacts,
                output_artifact_ids=output_artifact_ids,
                side_effect=side_effect,
                requires_authorization=requires_authorization,
                synchronous=synchronous,
            )
        )
    audit_supported = _require_boolean(
        body["audit_supported"], "runtime_descriptor.audit_supported"
    )
    credentials_managed_externally = _require_boolean(
        body["credentials_managed_externally"],
        "runtime_descriptor.credentials_managed_externally",
    )
    external_side_effects_allowed = _require_boolean(
        body["external_side_effects_allowed"],
        "runtime_descriptor.external_side_effects_allowed",
    )
    if not external_side_effects_allowed and any(
        operation.side_effect != "none" for operation in operations
    ):
        raise RuntimeInterfaceFormatError(
            "runtime_descriptor cannot advertise external side effects when "
            "external_side_effects_allowed is false"
        )
    if implementation_kind == "mock" and production_ready:
        raise RuntimeInterfaceFormatError(
            "runtime_descriptor.production_ready must be false for mock implementations"
        )
    return RuntimeDescriptor(
        runtime_id=runtime_id,
        runtime_version=runtime_version,
        title=title,
        implementation_kind=implementation_kind,
        production_ready=production_ready,
        capabilities=capabilities,
        operations=tuple(operations),
        audit_supported=audit_supported,
        credentials_managed_externally=credentials_managed_externally,
        external_side_effects_allowed=external_side_effects_allowed,
    )


def load_runtime_request(payload: Mapping[str, object]) -> RuntimeRequest:
    """Strictly load a ``runtime_request/0.1`` Artifact."""

    root = _require_mapping(payload, "Runtime Request")
    _require_exact_fields(root, {"runtime_request"}, "request root")
    body = _require_mapping(root["runtime_request"], "runtime_request")
    _require_exact_fields(
        body,
        {
            "interface_version",
            "request_id",
            "runtime_id",
            "operation_id",
            "input_artifacts",
            "expected_output_artifact_ids",
            "authorization_ref",
            "idempotency_key",
            "metadata",
        },
        "runtime_request",
    )
    if body["interface_version"] != RUNTIME_INTERFACE_PROFILE_VERSION:
        raise RuntimeInterfaceFormatError(
            "runtime_request.interface_version must be "
            f"{RUNTIME_INTERFACE_PROFILE_VERSION!r}"
        )
    request_id = _require_non_empty_string(
        body["request_id"], "runtime_request.request_id"
    )
    runtime_id = _require_non_empty_string(
        body["runtime_id"], "runtime_request.runtime_id"
    )
    operation_id = _require_non_empty_string(
        body["operation_id"], "runtime_request.operation_id"
    )
    input_value = body["input_artifacts"]
    if not isinstance(input_value, list) or not input_value:
        raise RuntimeInterfaceFormatError(
            "runtime_request.input_artifacts must be a non-empty array"
        )
    input_artifacts = tuple(
        _load_runtime_artifact(item, f"runtime_request.input_artifacts[{index}]")
        for index, item in enumerate(input_value)
    )
    expected_output_artifact_ids = _require_registered_artifact_ids(
        body["expected_output_artifact_ids"],
        "runtime_request.expected_output_artifact_ids",
        allow_empty=False,
    )
    authorization_ref = _require_optional_string(
        body["authorization_ref"], "runtime_request.authorization_ref"
    )
    idempotency_key = _require_non_empty_string(
        body["idempotency_key"], "runtime_request.idempotency_key"
    )
    metadata_mapping = _require_mapping(body["metadata"], "runtime_request.metadata")
    metadata = _require_json_value(metadata_mapping, "runtime_request.metadata")
    assert isinstance(metadata, dict)
    return RuntimeRequest(
        request_id=request_id,
        runtime_id=runtime_id,
        operation_id=operation_id,
        input_artifacts=input_artifacts,
        expected_output_artifact_ids=expected_output_artifact_ids,
        authorization_ref=authorization_ref,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )


def load_runtime_response(payload: Mapping[str, object]) -> RuntimeResponse:
    """Strictly load and cross-check a ``runtime_response/0.1`` Artifact."""

    root = _require_mapping(payload, "Runtime Response")
    _require_exact_fields(root, {"runtime_response"}, "response root")
    body = _require_mapping(root["runtime_response"], "runtime_response")
    _require_exact_fields(
        body,
        {
            "interface_version",
            "request_id",
            "runtime_id",
            "operation_id",
            "state",
            "output_artifacts",
            "diagnostics",
            "audit_ref",
            "side_effects_executed",
            "retryable",
            "next_poll_after_ms",
        },
        "runtime_response",
    )
    if body["interface_version"] != RUNTIME_INTERFACE_PROFILE_VERSION:
        raise RuntimeInterfaceFormatError(
            "runtime_response.interface_version must be "
            f"{RUNTIME_INTERFACE_PROFILE_VERSION!r}"
        )
    request_id = _require_non_empty_string(
        body["request_id"], "runtime_response.request_id"
    )
    runtime_id = _require_non_empty_string(
        body["runtime_id"], "runtime_response.runtime_id"
    )
    operation_id = _require_non_empty_string(
        body["operation_id"], "runtime_response.operation_id"
    )
    state = body["state"]
    if state not in _RUNTIME_RESPONSE_STATES:
        raise RuntimeInterfaceFormatError(
            f"runtime_response.state must be one of {sorted(_RUNTIME_RESPONSE_STATES)!r}"
        )
    output_value = body["output_artifacts"]
    if not isinstance(output_value, list):
        raise RuntimeInterfaceFormatError(
            "runtime_response.output_artifacts must be an array"
        )
    output_artifacts = tuple(
        _load_runtime_artifact(item, f"runtime_response.output_artifacts[{index}]")
        for index, item in enumerate(output_value)
    )
    diagnostics_value = body["diagnostics"]
    if not isinstance(diagnostics_value, list):
        raise RuntimeInterfaceFormatError("runtime_response.diagnostics must be an array")
    diagnostics = tuple(
        _load_runtime_diagnostic(item, f"runtime_response.diagnostics[{index}]")
        for index, item in enumerate(diagnostics_value)
    )
    error_count = sum(item.severity == "error" for item in diagnostics)
    audit_ref = _require_optional_string(
        body["audit_ref"], "runtime_response.audit_ref"
    )
    side_effects_executed = _require_boolean(
        body["side_effects_executed"], "runtime_response.side_effects_executed"
    )
    retryable = _require_boolean(body["retryable"], "runtime_response.retryable")
    next_poll_after_ms = body["next_poll_after_ms"]
    if next_poll_after_ms is not None and (
        not isinstance(next_poll_after_ms, int)
        or isinstance(next_poll_after_ms, bool)
        or next_poll_after_ms <= 0
    ):
        raise RuntimeInterfaceFormatError(
            "runtime_response.next_poll_after_ms must be null or a positive integer"
        )

    if state == "accepted":
        if output_artifacts:
            raise RuntimeInterfaceFormatError(
                "runtime_response.accepted must not contain output_artifacts"
            )
        if error_count:
            raise RuntimeInterfaceFormatError(
                "runtime_response.accepted must not contain error diagnostics"
            )
        if side_effects_executed:
            raise RuntimeInterfaceFormatError(
                "runtime_response.accepted cannot claim completed side effects"
            )
        if next_poll_after_ms is None:
            raise RuntimeInterfaceFormatError(
                "runtime_response.accepted requires next_poll_after_ms"
            )
    else:
        if next_poll_after_ms is not None:
            raise RuntimeInterfaceFormatError(
                "runtime_response.next_poll_after_ms is allowed only for accepted"
            )

    if state == "completed":
        if error_count:
            raise RuntimeInterfaceFormatError(
                "runtime_response.completed must not contain error diagnostics"
            )
        if retryable:
            raise RuntimeInterfaceFormatError(
                "runtime_response.completed cannot be retryable"
            )
    elif state in {"blocked", "rejected", "failed"} and error_count == 0:
        raise RuntimeInterfaceFormatError(
            f"runtime_response.{state} requires at least one error diagnostic"
        )

    if state in {"blocked", "rejected"} and side_effects_executed:
        raise RuntimeInterfaceFormatError(
            f"runtime_response.{state} cannot claim side effects were executed"
        )
    if side_effects_executed and audit_ref is None:
        raise RuntimeInterfaceFormatError(
            "runtime_response.side_effects_executed true requires audit_ref"
        )

    return RuntimeResponse(
        request_id=request_id,
        runtime_id=runtime_id,
        operation_id=operation_id,
        state=state,
        output_artifacts=output_artifacts,
        diagnostics=diagnostics,
        audit_ref=audit_ref,
        side_effects_executed=side_effects_executed,
        retryable=retryable,
        next_poll_after_ms=next_poll_after_ms,
    )


def validate_runtime_request_contract(
    descriptor: RuntimeDescriptor,
    request: RuntimeRequest,
) -> RuntimeOperationDescriptor:
    """Validate one request against an already inspected Runtime descriptor.

    The function is read-only and performs no submission. It returns the matched
    operation descriptor when the request target, operation, input Artifact set,
    expected outputs, and authorization presence are contract-compatible.
    """

    if request.runtime_id != descriptor.runtime_id:
        raise RuntimeInterfaceFormatError(
            "runtime_request.runtime_id must match runtime_descriptor.runtime_id"
        )
    operation = next(
        (
            item
            for item in descriptor.operations
            if item.operation_id == request.operation_id
        ),
        None,
    )
    if operation is None:
        raise RuntimeInterfaceFormatError(
            f"runtime_request.operation_id {request.operation_id!r} is not advertised "
            f"by Runtime {descriptor.runtime_id!r}"
        )
    input_count = len(request.input_artifacts)
    if input_count < operation.min_input_artifacts:
        raise RuntimeInterfaceFormatError(
            "runtime_request.input_artifacts contains fewer items than the advertised "
            f"minimum {operation.min_input_artifacts}"
        )
    if (
        operation.max_input_artifacts is not None
        and input_count > operation.max_input_artifacts
    ):
        raise RuntimeInterfaceFormatError(
            "runtime_request.input_artifacts contains more items than the advertised "
            f"maximum {operation.max_input_artifacts}"
        )
    if not operation.accepts_any_registered_artifact:
        allowed = set(operation.input_artifact_ids)
        unexpected = sorted(
            {
                artifact.artifact_id
                for artifact in request.input_artifacts
                if artifact.artifact_id not in allowed
            }
        )
        if unexpected:
            raise RuntimeInterfaceFormatError(
                "runtime_request.input_artifacts contains Artifact IDs outside the "
                f"advertised operation contract: {', '.join(unexpected)}"
            )
    if request.expected_output_artifact_ids != operation.output_artifact_ids:
        raise RuntimeInterfaceFormatError(
            "runtime_request.expected_output_artifact_ids must exactly match the "
            "advertised operation output_artifact_ids"
        )
    if operation.requires_authorization and request.authorization_ref is None:
        raise RuntimeInterfaceFormatError(
            "runtime_request.authorization_ref is required by the advertised operation"
        )
    if not operation.requires_authorization and request.authorization_ref is not None:
        raise RuntimeInterfaceFormatError(
            "runtime_request.authorization_ref must be null when the advertised "
            "operation does not require authorization"
        )
    return operation


def validate_runtime_response_contract(
    descriptor: RuntimeDescriptor,
    request: RuntimeRequest,
    response: RuntimeResponse,
) -> RuntimeOperationDescriptor | None:
    """Validate a Runtime response against its descriptor and submitted request.

    A request that violates the advertised contract may still be passed to a
    defensive adapter, but the only valid outcome is a side-effect-free
    ``rejected`` response with no output Artifacts. For a contract-compatible
    request, the response must preserve identity, output, synchrony, audit, and
    side-effect declarations.
    """

    if response.runtime_id != descriptor.runtime_id:
        raise RuntimeInterfaceFormatError(
            "runtime_response.runtime_id must match runtime_descriptor.runtime_id"
        )
    if response.request_id != request.request_id:
        raise RuntimeInterfaceFormatError(
            "runtime_response.request_id must match runtime_request.request_id"
        )
    if response.operation_id != request.operation_id:
        raise RuntimeInterfaceFormatError(
            "runtime_response.operation_id must match runtime_request.operation_id"
        )

    try:
        operation = validate_runtime_request_contract(descriptor, request)
    except RuntimeInterfaceFormatError as request_error:
        if response.state != "rejected":
            raise RuntimeInterfaceFormatError(
                "a Runtime Request that violates the advertised descriptor contract "
                "must produce a rejected Runtime Response: "
                f"{request_error}"
            ) from None
        if response.output_artifacts:
            raise RuntimeInterfaceFormatError(
                "a rejected response for an invalid Runtime Request must not contain "
                "output_artifacts"
            )
        if response.side_effects_executed:
            raise RuntimeInterfaceFormatError(
                "a rejected response for an invalid Runtime Request must not execute "
                "side effects"
            )
        return None

    output_artifact_ids = tuple(
        artifact.artifact_id for artifact in response.output_artifacts
    )
    expected_output_ids = request.expected_output_artifact_ids
    unexpected_outputs = sorted(
        artifact_id
        for artifact_id in set(output_artifact_ids)
        if artifact_id not in set(expected_output_ids)
    )
    if unexpected_outputs:
        raise RuntimeInterfaceFormatError(
            "runtime_response.output_artifacts contains Artifact IDs outside the "
            "request output contract: "
            + ", ".join(unexpected_outputs)
        )
    if response.state == "completed" and output_artifact_ids != expected_output_ids:
        raise RuntimeInterfaceFormatError(
            "runtime_response.completed output Artifact IDs must exactly match "
            "runtime_request.expected_output_artifact_ids"
        )
    if operation.synchronous and response.state == "accepted":
        raise RuntimeInterfaceFormatError(
            "a synchronous Runtime operation cannot return state 'accepted'"
        )
    if operation.side_effect == "none" and response.side_effects_executed:
        raise RuntimeInterfaceFormatError(
            "a Runtime operation declared with side_effect 'none' cannot claim "
            "side_effects_executed=true"
        )
    if response.side_effects_executed and not descriptor.external_side_effects_allowed:
        raise RuntimeInterfaceFormatError(
            "runtime_response cannot claim external side effects when the Runtime "
            "Descriptor disallows them"
        )
    if response.audit_ref is not None and not descriptor.audit_supported:
        raise RuntimeInterfaceFormatError(
            "runtime_response.audit_ref must be null when runtime_descriptor.audit_supported "
            "is false"
        )
    return operation


def reference_runtime_descriptor() -> RuntimeDescriptor:
    """Return the deterministic public fail-closed Runtime descriptor."""

    return RuntimeDescriptor(
        runtime_id=REFERENCE_RUNTIME_ID,
        runtime_version=REFERENCE_RUNTIME_VERSION,
        title="GeoTask Fail-Closed Reference Runtime",
        implementation_kind="mock",
        production_ready=False,
        capabilities=("artifact_validation", "deterministic_fail_closed"),
        operations=(
            RuntimeOperationDescriptor(
                operation_id=VALIDATE_ARTIFACT_OPERATION_ID,
                title="Validate a registered GeoTask Artifact",
                description=(
                    "Run the public Core's read-only Registry-driven Artifact validation "
                    "and return an Artifact Validation Report."
                ),
                input_artifact_ids=(),
                accepts_any_registered_artifact=True,
                min_input_artifacts=1,
                max_input_artifacts=1,
                output_artifact_ids=("geotask.artifact-validation-report",),
                side_effect="none",
                requires_authorization=False,
                synchronous=True,
            ),
        ),
        audit_supported=False,
        credentials_managed_externally=True,
        external_side_effects_allowed=False,
    )


def runtime_interface_profile_payload() -> dict[str, object]:
    """Return the machine-readable Runtime Interface Profile inventory."""

    return {
        "runtime_interface_profile": {
            "profile_id": RUNTIME_INTERFACE_PROFILE_ID,
            "profile_version": RUNTIME_INTERFACE_PROFILE_VERSION,
            "artifact_ids": [
                RUNTIME_DESCRIPTOR_ARTIFACT_ID,
                RUNTIME_REQUEST_ARTIFACT_ID,
                RUNTIME_RESPONSE_ARTIFACT_ID,
            ],
            "standard_operation_ids": [
                VALIDATE_ARTIFACT_OPERATION_ID,
                EXECUTE_NONLOCAL_OPERATION_ID,
                RESOLVE_EVIDENCE_OPERATION_ID,
                EXECUTE_ACTION_OPERATION_ID,
            ],
            "reference_runtime_id": REFERENCE_RUNTIME_ID,
            "offline_discovery": {
                "inspect_descriptor_cli": (
                    "geotask runtime inspect <runtime-descriptor.json> --format json"
                ),
                "check_request_cli": (
                    "geotask runtime check <runtime-descriptor.json> "
                    "<runtime-request.json> --format json"
                ),
                "submits_request": False,
                "executes_side_effects": False,
            },
            "exchange_validation": {
                "request_contract_preflight_available": True,
                "input_cardinality_enforced": True,
                "response_bound_to_descriptor_and_request": True,
                "invalid_request_must_be_rejected": True,
                "completed_outputs_must_match_request": True,
                "synchronous_operation_cannot_return_accepted": True,
                "side_effect_claim_must_match_descriptor": True,
            },
            "private_implementation_excluded": True,
            "core_imports_runtime": False,
            "credentials_in_core": False,
            "model_calls_in_reference_runtime": False,
            "external_side_effects_in_reference_runtime": False,
        }
    }


def _rejected_response(
    request: RuntimeRequest,
    *,
    code: str,
    message: str,
    path: str,
    suggested_fix: str,
) -> RuntimeResponse:
    return RuntimeResponse(
        request_id=request.request_id,
        runtime_id=REFERENCE_RUNTIME_ID,
        operation_id=request.operation_id,
        state="rejected",
        output_artifacts=(),
        diagnostics=(
            RuntimeDiagnostic(
                code=code,
                path=path,
                message=message,
                severity="error",
                suggested_fix=suggested_fix,
            ),
        ),
        audit_ref=None,
        side_effects_executed=False,
        retryable=False,
        next_poll_after_ms=None,
    )


class FailClosedMockRuntime:
    """Reference adapter that performs only read-only Artifact validation."""

    def describe(self) -> RuntimeDescriptor:
        return reference_runtime_descriptor()

    def submit(self, request: RuntimeRequest) -> RuntimeResponse:
        if request.runtime_id != REFERENCE_RUNTIME_ID:
            return _rejected_response(
                request,
                code="runtime_id_mismatch",
                path="runtime_request.runtime_id",
                message=(
                    f"request targets {request.runtime_id!r}, but this adapter is "
                    f"{REFERENCE_RUNTIME_ID!r}"
                ),
                suggested_fix=(
                    f"Set runtime_id to {REFERENCE_RUNTIME_ID!r} or route the request "
                    "to the named external Runtime."
                ),
            )
        if request.operation_id != VALIDATE_ARTIFACT_OPERATION_ID:
            return _rejected_response(
                request,
                code="unsupported_runtime_operation",
                path="runtime_request.operation_id",
                message=(
                    "The fail-closed reference Runtime supports only read-only "
                    f"{VALIDATE_ARTIFACT_OPERATION_ID!r}."
                ),
                suggested_fix=(
                    "Use a separately authorized external Runtime for model execution, "
                    "evidence resolution, or production actions."
                ),
            )
        if len(request.input_artifacts) != 1:
            return _rejected_response(
                request,
                code="invalid_runtime_input_count",
                path="runtime_request.input_artifacts",
                message="Artifact validation requires exactly one input Artifact.",
                suggested_fix="Provide exactly one registered Artifact payload.",
            )
        expected = ("geotask.artifact-validation-report",)
        if request.expected_output_artifact_ids != expected:
            return _rejected_response(
                request,
                code="unexpected_runtime_output_contract",
                path="runtime_request.expected_output_artifact_ids",
                message=(
                    "Artifact validation must request exactly one "
                    "geotask.artifact-validation-report output."
                ),
                suggested_fix=(
                    "Set expected_output_artifact_ids to "
                    "['geotask.artifact-validation-report']."
                ),
            )
        if request.authorization_ref is not None:
            return _rejected_response(
                request,
                code="unexpected_authorization_reference",
                path="runtime_request.authorization_ref",
                message="Read-only Artifact validation does not consume authorization.",
                suggested_fix="Set authorization_ref to null for the reference Runtime.",
            )

        from geotask_core.v1.artifact_validation import validate_artifact_payload

        artifact = request.input_artifacts[0]
        validation = validate_artifact_payload(
            artifact.artifact_id,
            artifact.payload,
            file=f"runtime-request:{request.request_id}",
        )
        return RuntimeResponse(
            request_id=request.request_id,
            runtime_id=REFERENCE_RUNTIME_ID,
            operation_id=request.operation_id,
            state="completed",
            output_artifacts=(
                RuntimeArtifact(
                    artifact_id="geotask.artifact-validation-report",
                    payload=validation.to_dict(),
                ),
            ),
            diagnostics=(),
            audit_ref=None,
            side_effects_executed=False,
            retryable=False,
            next_poll_after_ms=None,
        )


def submit_runtime_request(
    adapter: RuntimeAdapter,
    payload: Mapping[str, object],
) -> RuntimeResponse:
    """Strictly load a request and submit it through a RuntimeAdapter."""

    if not isinstance(adapter, RuntimeAdapter):
        raise TypeError("adapter must implement the RuntimeAdapter Protocol")
    descriptor = load_runtime_descriptor(adapter.describe().to_dict())
    request = load_runtime_request(payload)
    response = adapter.submit(request)
    loaded = load_runtime_response(response.to_dict())
    validate_runtime_response_contract(descriptor, request, loaded)
    return loaded


__all__ = [
    "RUNTIME_INTERFACE_PROFILE_ID",
    "RUNTIME_INTERFACE_PROFILE_VERSION",
    "RUNTIME_DESCRIPTOR_SCHEMA_ID",
    "RUNTIME_REQUEST_SCHEMA_ID",
    "RUNTIME_RESPONSE_SCHEMA_ID",
    "RUNTIME_DESCRIPTOR_SCHEMA_VERSION",
    "RUNTIME_REQUEST_SCHEMA_VERSION",
    "RUNTIME_RESPONSE_SCHEMA_VERSION",
    "RUNTIME_DESCRIPTOR_ARTIFACT_ID",
    "RUNTIME_REQUEST_ARTIFACT_ID",
    "RUNTIME_RESPONSE_ARTIFACT_ID",
    "VALIDATE_ARTIFACT_OPERATION_ID",
    "EXECUTE_NONLOCAL_OPERATION_ID",
    "RESOLVE_EVIDENCE_OPERATION_ID",
    "EXECUTE_ACTION_OPERATION_ID",
    "REFERENCE_RUNTIME_ID",
    "REFERENCE_RUNTIME_VERSION",
    "RuntimeInterfaceFormatError",
    "RuntimeArtifact",
    "RuntimeDiagnostic",
    "RuntimeOperationDescriptor",
    "RuntimeDescriptor",
    "RuntimeRequest",
    "RuntimeResponse",
    "RuntimeAdapter",
    "load_runtime_descriptor",
    "load_runtime_request",
    "load_runtime_response",
    "validate_runtime_request_contract",
    "validate_runtime_response_contract",
    "reference_runtime_descriptor",
    "runtime_interface_profile_payload",
    "FailClosedMockRuntime",
    "submit_runtime_request",
]
