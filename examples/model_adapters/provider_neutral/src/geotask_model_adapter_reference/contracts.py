"""Provider-neutral contracts for the public GeoTask model Adapter example.

These contracts are intentionally narrower than a production model SDK. They
carry one registered GeoTask input Artifact to one provider implementation and
require one structured provider result. They contain no HTTP client, credential
resolver, provider key, prompt registry, token budget, or routing policy.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


MODEL_ADAPTER_PACKAGE_VERSION = "0.1.0"
MODEL_RUNTIME_ID = "geotask.reference.provider-neutral-model"
MODEL_RUNTIME_VERSION = "0.1"
DEFAULT_MODEL_REF = "mock://geotask-structured-result-v1"

_PROVIDER_RESULT_STATES = {"completed", "blocked", "rejected", "failed"}
_DIAGNOSTIC_SEVERITIES = {"error", "warning"}


class ModelAdapterContractError(ValueError):
    """Raised when an Adapter configuration or provider result is untrustworthy."""


def _require_non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelAdapterContractError(f"{label} must be a non-empty string")
    return value.strip()


def _require_boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ModelAdapterContractError(f"{label} must be boolean")
    return value


def _require_json_value(value: object, label: str) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ModelAdapterContractError(f"{label} must contain only finite numbers")
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
                raise ModelAdapterContractError(f"{label} keys must be strings")
            normalized[key] = _require_json_value(item, f"{label}.{key}")
        return normalized
    raise ModelAdapterContractError(f"{label} must contain only JSON values")


@dataclass(frozen=True)
class ModelAdapterConfig:
    """Non-secret configuration for one provider-neutral Runtime Adapter."""

    runtime_id: str = MODEL_RUNTIME_ID
    runtime_version: str = MODEL_RUNTIME_VERSION
    title: str = "GeoTask Provider-Neutral Model Adapter Reference"
    model_ref: str = DEFAULT_MODEL_REF
    input_artifact_id: str = "geotask.document"
    output_artifact_id: str = "geotask.execution-result"

    def __post_init__(self) -> None:
        for field_name in (
            "runtime_id",
            "runtime_version",
            "title",
            "model_ref",
            "input_artifact_id",
            "output_artifact_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _require_non_empty_string(getattr(self, field_name), field_name),
            )
        lowered = self.model_ref.lower()
        credential_markers = (
            "api_" + "key=",
            "to" + "ken=",
            "pass" + "word=",
        )
        if any(marker in lowered for marker in credential_markers):
            raise ModelAdapterContractError(
                "model_ref must identify a model without embedding credentials"
            )


@dataclass(frozen=True)
class ProviderDiagnostic:
    """Provider-level diagnostic mapped into a public Runtime diagnostic."""

    code: str
    path: str
    message: str
    severity: str = "error"
    suggested_fix: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _require_non_empty_string(self.code, "code"))
        if not isinstance(self.path, str):
            raise ModelAdapterContractError("path must be a string")
        object.__setattr__(
            self,
            "message",
            _require_non_empty_string(self.message, "message"),
        )
        if self.severity not in _DIAGNOSTIC_SEVERITIES:
            raise ModelAdapterContractError("severity must be 'error' or 'warning'")
        if not isinstance(self.suggested_fix, str):
            raise ModelAdapterContractError("suggested_fix must be a string")


@dataclass(frozen=True)
class StructuredModelInvocation:
    """One provider-neutral structured model invocation."""

    request_id: str
    model_ref: str
    input_artifact_id: str
    input_payload: Mapping[str, object]
    expected_output_artifact_id: str
    authorization_ref: str | None
    idempotency_key: str
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "model_ref",
            "input_artifact_id",
            "expected_output_artifact_id",
            "idempotency_key",
        ):
            object.__setattr__(
                self,
                field_name,
                _require_non_empty_string(getattr(self, field_name), field_name),
            )
        if self.authorization_ref is not None:
            object.__setattr__(
                self,
                "authorization_ref",
                _require_non_empty_string(
                    self.authorization_ref,
                    "authorization_ref",
                ),
            )
        input_payload = _require_json_value(self.input_payload, "input_payload")
        metadata = _require_json_value(self.metadata, "metadata")
        if not isinstance(input_payload, dict) or not isinstance(metadata, dict):
            raise ModelAdapterContractError(
                "input_payload and metadata must have object roots"
            )
        object.__setattr__(self, "input_payload", input_payload)
        object.__setattr__(self, "metadata", metadata)


@dataclass(frozen=True)
class StructuredModelResult:
    """One strictly normalized result returned by a model provider implementation."""

    state: str
    output_payload: Mapping[str, object] | None
    diagnostics: tuple[ProviderDiagnostic, ...]
    external_call_executed: bool
    audit_ref: str | None
    retryable: bool

    def __post_init__(self) -> None:
        if self.state not in _PROVIDER_RESULT_STATES:
            raise ModelAdapterContractError(
                f"state must be one of {sorted(_PROVIDER_RESULT_STATES)!r}"
            )
        if not isinstance(self.diagnostics, tuple) or not all(
            isinstance(item, ProviderDiagnostic) for item in self.diagnostics
        ):
            raise ModelAdapterContractError(
                "diagnostics must be a tuple of ProviderDiagnostic values"
            )
        _require_boolean(self.external_call_executed, "external_call_executed")
        _require_boolean(self.retryable, "retryable")
        if self.audit_ref is not None:
            object.__setattr__(
                self,
                "audit_ref",
                _require_non_empty_string(self.audit_ref, "audit_ref"),
            )
        error_count = sum(item.severity == "error" for item in self.diagnostics)
        if self.state == "completed":
            if self.output_payload is None:
                raise ModelAdapterContractError(
                    "completed provider results require output_payload"
                )
            if error_count:
                raise ModelAdapterContractError(
                    "completed provider results must not contain error diagnostics"
                )
            if self.retryable:
                raise ModelAdapterContractError(
                    "completed provider results cannot be retryable"
                )
            normalized = _require_json_value(self.output_payload, "output_payload")
            if not isinstance(normalized, dict):
                raise ModelAdapterContractError(
                    "completed output_payload must have an object root"
                )
            object.__setattr__(self, "output_payload", normalized)
        else:
            if self.output_payload is not None:
                raise ModelAdapterContractError(
                    f"{self.state} provider results must not contain output_payload"
                )
            if error_count == 0:
                raise ModelAdapterContractError(
                    f"{self.state} provider results require an error diagnostic"
                )
        if self.state in {"blocked", "rejected"} and self.external_call_executed:
            raise ModelAdapterContractError(
                f"{self.state} provider results cannot claim an external call executed"
            )
        if self.external_call_executed and self.audit_ref is None:
            raise ModelAdapterContractError(
                "external_call_executed true requires audit_ref"
            )

    @classmethod
    def completed(
        cls,
        output_payload: Mapping[str, object],
        *,
        diagnostics: tuple[ProviderDiagnostic, ...] = (),
        external_call_executed: bool = False,
        audit_ref: str | None = None,
    ) -> "StructuredModelResult":
        return cls(
            state="completed",
            output_payload=output_payload,
            diagnostics=diagnostics,
            external_call_executed=external_call_executed,
            audit_ref=audit_ref,
            retryable=False,
        )

    @classmethod
    def failed(
        cls,
        diagnostic: ProviderDiagnostic,
        *,
        retryable: bool,
        external_call_executed: bool = False,
        audit_ref: str | None = None,
    ) -> "StructuredModelResult":
        return cls(
            state="failed",
            output_payload=None,
            diagnostics=(diagnostic,),
            external_call_executed=external_call_executed,
            audit_ref=audit_ref,
            retryable=retryable,
        )


@runtime_checkable
class StructuredModelProvider(Protocol):
    """Structural interface implemented by one model-provider integration."""

    provider_id: str
    external_call: bool
    requires_authorization: bool
    audit_supported: bool

    def invoke(self, invocation: StructuredModelInvocation) -> StructuredModelResult:
        """Return one structured result without exposing provider-native objects."""


__all__ = [
    "MODEL_ADAPTER_PACKAGE_VERSION",
    "MODEL_RUNTIME_ID",
    "MODEL_RUNTIME_VERSION",
    "DEFAULT_MODEL_REF",
    "ModelAdapterContractError",
    "ModelAdapterConfig",
    "ProviderDiagnostic",
    "StructuredModelInvocation",
    "StructuredModelResult",
    "StructuredModelProvider",
]
