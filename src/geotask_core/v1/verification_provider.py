"""Public Verification Provider contracts for GeoTask Core.

The module defines a read-only, fail-closed interface between GeoTask Core and
independently implemented verification providers. Providers may report what they
observed or checked, but they cannot self-assign independent verification,
release production outputs, authorize actions, or execute side effects.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


VERIFICATION_PROVIDER_INTERFACE_ID = "geotask.verification-provider"
VERIFICATION_PROVIDER_INTERFACE_VERSION = "0.1"

_SCHEMA_ROOT = "https://stpku.github.io/GeoTask/schemas/"
VERIFICATION_PROVIDER_DESCRIPTOR_SCHEMA_ID = (
    _SCHEMA_ROOT + "geotask-verification-provider-descriptor-v0.1.schema.json"
)
VERIFICATION_REQUEST_SCHEMA_ID = (
    _SCHEMA_ROOT + "geotask-verification-request-v0.1.schema.json"
)
VERIFICATION_RESPONSE_SCHEMA_ID = (
    _SCHEMA_ROOT + "geotask-verification-response-v0.1.schema.json"
)
ASSURANCE_PROFILE_SCHEMA_ID = (
    _SCHEMA_ROOT + "geotask-assurance-profile-v0.1.schema.json"
)
VERIFICATION_PROVIDER_DESCRIPTOR_SCHEMA_VERSION = "0.1"
VERIFICATION_REQUEST_SCHEMA_VERSION = "0.1"
VERIFICATION_RESPONSE_SCHEMA_VERSION = "0.1"
ASSURANCE_PROFILE_SCHEMA_VERSION = "0.1"

VERIFICATION_PROVIDER_DESCRIPTOR_ARTIFACT_ID = (
    "geotask.verification-provider-descriptor"
)
VERIFICATION_REQUEST_ARTIFACT_ID = "geotask.verification-request"
VERIFICATION_RESPONSE_ARTIFACT_ID = "geotask.verification-response"
ASSURANCE_PROFILE_ARTIFACT_ID = "geotask.assurance-profile"

_PROVIDER_TYPES = {
    "deterministic_operator",
    "rule_engine",
    "authoritative_data_provider",
    "sensor_data_provider",
    "local_predictive_model",
    "human_review",
}
_IMPLEMENTATION_KINDS = {"mock", "external"}
_REPRODUCIBILITY_STATES = {"deterministic", "repeatable", "non_deterministic"}
_CALIBRATION_STATES = {"not_applicable", "uncalibrated", "calibrated", "expired"}
_RESPONSE_STATES = {"verified", "contradicted", "unknown", "failed"}
_CONFLICT_POLICIES = {"unknown", "contradicted"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


class VerificationProviderFormatError(ValueError):
    """Raised when a Verification Provider artifact violates the public contract."""


def _mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise VerificationProviderFormatError(f"{path} must be an object")
    return dict(value)


def _exact_fields(
    value: Mapping[str, Any],
    *,
    path: str,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    actual = set(value)
    missing = sorted(required - actual)
    unknown = sorted(actual - required - optional)
    if missing:
        raise VerificationProviderFormatError(
            f"{path} is missing required field(s): {', '.join(missing)}"
        )
    if unknown:
        raise VerificationProviderFormatError(
            f"{path} contains unknown field(s): {', '.join(unknown)}"
        )


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VerificationProviderFormatError(f"{path} must be a non-empty string")
    return value


def _identifier(value: object, path: str) -> str:
    text = _string(value, path)
    if not _ID_RE.fullmatch(text):
        raise VerificationProviderFormatError(f"{path} must be a stable identifier")
    return text


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        raise VerificationProviderFormatError(f"{path} must be boolean")
    return bool(value)


def _integer(value: object, path: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise VerificationProviderFormatError(
            f"{path} must be an integer greater than or equal to {minimum}"
        )
    return int(value)


def _number(value: object, path: str) -> float:
    if type(value) not in {int, float} or isinstance(value, bool):
        raise VerificationProviderFormatError(f"{path} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise VerificationProviderFormatError(f"{path} must be finite")
    return number


def _enum(value: object, allowed: set[str], path: str) -> str:
    text = _string(value, path)
    if text not in allowed:
        raise VerificationProviderFormatError(
            f"{path} must be one of: {', '.join(sorted(allowed))}"
        )
    return text


def _string_list(value: object, path: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise VerificationProviderFormatError(f"{path} must be an array")
    if not allow_empty and not value:
        raise VerificationProviderFormatError(f"{path} must not be empty")
    result = tuple(_string(item, f"{path}[{index}]") for index, item in enumerate(value))
    if len(set(result)) != len(result):
        raise VerificationProviderFormatError(f"{path} must not contain duplicates")
    return result


def _timestamp(value: object, path: str) -> str:
    text = _string(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VerificationProviderFormatError(f"{path} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise VerificationProviderFormatError(f"{path} must include a timezone")
    return text


def _timestamp_or_none(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _timestamp(value, path)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


def _sha256(value: object, path: str) -> str:
    text = _string(value, path)
    if not _SHA256_RE.fullmatch(text):
        raise VerificationProviderFormatError(f"{path} must be a lowercase SHA-256 digest")
    return text


def _json_value(value: object, path: str) -> object:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise VerificationProviderFormatError(f"{path} must not contain non-finite values")
        return value
    if isinstance(value, list):
        return [_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise VerificationProviderFormatError(f"{path} object keys must be strings")
            result[key] = _json_value(item, f"{path}.{key}")
        return result
    raise VerificationProviderFormatError(f"{path} must contain only JSON-compatible values")


def sha256_bytes(raw: bytes) -> str:
    """Return a lowercase SHA-256 digest for exact serialized bytes."""

    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class VerificationProviderDescriptor:
    provider_id: str
    provider_version: str
    title: str
    provider_type: str
    implementation_kind: str
    production_ready: bool
    capabilities: tuple[str, ...]
    supported_methods: tuple[str, ...]
    independence_group: str
    reproducibility: str
    calibration_status: str
    valid_until: str | None
    audit_supported: bool
    credentials_managed_externally: bool
    external_side_effects_allowed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "verification_provider_descriptor": {
                "interface_version": VERIFICATION_PROVIDER_INTERFACE_VERSION,
                "provider_id": self.provider_id,
                "provider_version": self.provider_version,
                "title": self.title,
                "provider_type": self.provider_type,
                "implementation_kind": self.implementation_kind,
                "production_ready": self.production_ready,
                "capabilities": list(self.capabilities),
                "supported_methods": list(self.supported_methods),
                "independence_group": self.independence_group,
                "reproducibility": self.reproducibility,
                "calibration_status": self.calibration_status,
                "valid_until": self.valid_until,
                "audit_supported": self.audit_supported,
                "credentials_managed_externally": self.credentials_managed_externally,
                "external_side_effects_allowed": self.external_side_effects_allowed,
            }
        }


@dataclass(frozen=True)
class ArtifactBinding:
    ref_id: str
    artifact_id: str
    sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "ref_id": self.ref_id,
            "artifact_id": self.artifact_id,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class VerificationSubject:
    claim_id: str
    claim_type: str
    value: object
    unit: str | None
    observed_at: str
    valid_until: str

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "claim_type": self.claim_type,
            "value": self.value,
            "unit": self.unit,
            "observed_at": self.observed_at,
            "valid_until": self.valid_until,
        }


@dataclass(frozen=True)
class VerificationRequest:
    request_id: str
    created_at: str
    subject: VerificationSubject
    input_artifacts: tuple[ArtifactBinding, ...]
    verification_method: str
    required_capabilities: tuple[str, ...]
    allowed_provider_types: tuple[str, ...]
    assurance_profile_id: str
    assurance_profile_sha256: str
    deadline: str
    external_side_effects_allowed: bool
    action_authorized: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "verification_request": {
                "request_version": VERIFICATION_REQUEST_SCHEMA_VERSION,
                "request_id": self.request_id,
                "created_at": self.created_at,
                "subject": self.subject.to_dict(),
                "input_artifacts": [item.to_dict() for item in self.input_artifacts],
                "verification_method": self.verification_method,
                "required_capabilities": list(self.required_capabilities),
                "allowed_provider_types": list(self.allowed_provider_types),
                "assurance_profile_ref": {
                    "profile_id": self.assurance_profile_id,
                    "sha256": self.assurance_profile_sha256,
                },
                "deadline": self.deadline,
                "external_side_effects_allowed": self.external_side_effects_allowed,
                "action_authorized": self.action_authorized,
            }
        }


@dataclass(frozen=True)
class VerificationResponse:
    response_id: str
    request_id: str
    request_sha256: str
    provider_id: str
    provider_version: str
    provider_sha256: str
    state: str
    claim_id: str
    claim_type: str
    value: object | None
    unit: str | None
    observed_at: str | None
    valid_until: str | None
    verification_method: str
    evidence_refs: tuple[str, ...]
    independence_group: str
    reproducibility: str
    calibration_status: str
    confidence: float | None
    diagnostics: tuple[dict[str, str], ...]
    completed_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "verification_response": {
                "response_version": VERIFICATION_RESPONSE_SCHEMA_VERSION,
                "response_id": self.response_id,
                "request_ref": {
                    "request_id": self.request_id,
                    "sha256": self.request_sha256,
                },
                "provider_ref": {
                    "provider_id": self.provider_id,
                    "provider_version": self.provider_version,
                    "sha256": self.provider_sha256,
                },
                "state": self.state,
                "result": {
                    "claim_id": self.claim_id,
                    "claim_type": self.claim_type,
                    "value": self.value,
                    "unit": self.unit,
                    "observed_at": self.observed_at,
                    "valid_until": self.valid_until,
                },
                "verification_method": self.verification_method,
                "evidence_refs": list(self.evidence_refs),
                "assurance_declarations": {
                    "independence_group": self.independence_group,
                    "reproducibility": self.reproducibility,
                    "calibration_status": self.calibration_status,
                    "confidence": self.confidence,
                },
                "diagnostics": [dict(item) for item in self.diagnostics],
                "completed_at": self.completed_at,
                "independently_verified": False,
                "production_output_released": False,
                "action_authorized": False,
                "action_executed": False,
            }
        }


@dataclass(frozen=True)
class AssuranceProfile:
    profile_id: str
    title: str
    minimum_provider_count: int
    minimum_independent_groups: int
    allowed_provider_types: tuple[str, ...]
    require_fresh_results: bool
    max_result_age_seconds: int
    require_reproducible: bool
    accepted_reproducibility: tuple[str, ...]
    require_calibration: bool
    accepted_calibration_states: tuple[str, ...]
    conflict_policy: str
    eligible_output: str
    blocked_outputs: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    next_action_on_insufficient_assurance: str

    def to_dict(self) -> dict[str, object]:
        return {
            "assurance_profile": {
                "profile_version": ASSURANCE_PROFILE_SCHEMA_VERSION,
                "profile_id": self.profile_id,
                "title": self.title,
                "minimum_provider_count": self.minimum_provider_count,
                "minimum_independent_groups": self.minimum_independent_groups,
                "allowed_provider_types": list(self.allowed_provider_types),
                "require_fresh_results": self.require_fresh_results,
                "max_result_age_seconds": self.max_result_age_seconds,
                "require_reproducible": self.require_reproducible,
                "accepted_reproducibility": list(self.accepted_reproducibility),
                "require_calibration": self.require_calibration,
                "accepted_calibration_states": list(self.accepted_calibration_states),
                "conflict_policy": self.conflict_policy,
                "eligible_output": self.eligible_output,
                "blocked_outputs": list(self.blocked_outputs),
                "blocked_actions": list(self.blocked_actions),
                "next_action_on_insufficient_assurance": (
                    self.next_action_on_insufficient_assurance
                ),
                "action_authorized": False,
                "action_executed": False,
            }
        }


def load_verification_provider_descriptor(
    payload: Mapping[str, object],
) -> VerificationProviderDescriptor:
    root = _mapping(payload, "Verification Provider Descriptor")
    _exact_fields(
        root,
        path="descriptor root",
        required={"verification_provider_descriptor"},
    )
    body = _mapping(
        root["verification_provider_descriptor"],
        "verification_provider_descriptor",
    )
    required = {
        "interface_version",
        "provider_id",
        "provider_version",
        "title",
        "provider_type",
        "implementation_kind",
        "production_ready",
        "capabilities",
        "supported_methods",
        "independence_group",
        "reproducibility",
        "calibration_status",
        "valid_until",
        "audit_supported",
        "credentials_managed_externally",
        "external_side_effects_allowed",
    }
    _exact_fields(body, path="verification_provider_descriptor", required=required)
    if body["interface_version"] != VERIFICATION_PROVIDER_INTERFACE_VERSION:
        raise VerificationProviderFormatError(
            "verification_provider_descriptor.interface_version must be '0.1'"
        )
    provider_type = _enum(
        body["provider_type"], _PROVIDER_TYPES, "verification_provider_descriptor.provider_type"
    )
    implementation_kind = _enum(
        body["implementation_kind"],
        _IMPLEMENTATION_KINDS,
        "verification_provider_descriptor.implementation_kind",
    )
    production_ready = _boolean(
        body["production_ready"], "verification_provider_descriptor.production_ready"
    )
    if implementation_kind == "mock" and production_ready:
        raise VerificationProviderFormatError("mock providers cannot be production_ready")
    external_side_effects_allowed = _boolean(
        body["external_side_effects_allowed"],
        "verification_provider_descriptor.external_side_effects_allowed",
    )
    if external_side_effects_allowed:
        raise VerificationProviderFormatError(
            "public Verification Providers must not allow external side effects"
        )
    return VerificationProviderDescriptor(
        provider_id=_identifier(body["provider_id"], "verification_provider_descriptor.provider_id"),
        provider_version=_string(
            body["provider_version"], "verification_provider_descriptor.provider_version"
        ),
        title=_string(body["title"], "verification_provider_descriptor.title"),
        provider_type=provider_type,
        implementation_kind=implementation_kind,
        production_ready=production_ready,
        capabilities=_string_list(
            body["capabilities"], "verification_provider_descriptor.capabilities", allow_empty=False
        ),
        supported_methods=_string_list(
            body["supported_methods"],
            "verification_provider_descriptor.supported_methods",
            allow_empty=False,
        ),
        independence_group=_identifier(
            body["independence_group"],
            "verification_provider_descriptor.independence_group",
        ),
        reproducibility=_enum(
            body["reproducibility"],
            _REPRODUCIBILITY_STATES,
            "verification_provider_descriptor.reproducibility",
        ),
        calibration_status=_enum(
            body["calibration_status"],
            _CALIBRATION_STATES,
            "verification_provider_descriptor.calibration_status",
        ),
        valid_until=_timestamp_or_none(
            body["valid_until"], "verification_provider_descriptor.valid_until"
        ),
        audit_supported=_boolean(
            body["audit_supported"], "verification_provider_descriptor.audit_supported"
        ),
        credentials_managed_externally=_boolean(
            body["credentials_managed_externally"],
            "verification_provider_descriptor.credentials_managed_externally",
        ),
        external_side_effects_allowed=external_side_effects_allowed,
    )


def _load_artifact_binding(value: object, path: str) -> ArtifactBinding:
    item = _mapping(value, path)
    _exact_fields(item, path=path, required={"ref_id", "artifact_id", "sha256"})
    return ArtifactBinding(
        ref_id=_identifier(item["ref_id"], f"{path}.ref_id"),
        artifact_id=_string(item["artifact_id"], f"{path}.artifact_id"),
        sha256=_sha256(item["sha256"], f"{path}.sha256"),
    )


def _load_subject(value: object, path: str) -> VerificationSubject:
    item = _mapping(value, path)
    _exact_fields(
        item,
        path=path,
        required={"claim_id", "claim_type", "value", "unit", "observed_at", "valid_until"},
    )
    value_normalized = _json_value(item["value"], f"{path}.value")
    unit = item["unit"]
    if unit is not None:
        unit = _string(unit, f"{path}.unit")
    observed_at = _timestamp(item["observed_at"], f"{path}.observed_at")
    valid_until = _timestamp(item["valid_until"], f"{path}.valid_until")
    if _parse_timestamp(valid_until) < _parse_timestamp(observed_at):
        raise VerificationProviderFormatError(f"{path}.valid_until must not precede observed_at")
    return VerificationSubject(
        claim_id=_identifier(item["claim_id"], f"{path}.claim_id"),
        claim_type=_identifier(item["claim_type"], f"{path}.claim_type"),
        value=value_normalized,
        unit=unit,
        observed_at=observed_at,
        valid_until=valid_until,
    )


def load_verification_request(payload: Mapping[str, object]) -> VerificationRequest:
    root = _mapping(payload, "Verification Request")
    _exact_fields(root, path="request root", required={"verification_request"})
    body = _mapping(root["verification_request"], "verification_request")
    required = {
        "request_version",
        "request_id",
        "created_at",
        "subject",
        "input_artifacts",
        "verification_method",
        "required_capabilities",
        "allowed_provider_types",
        "assurance_profile_ref",
        "deadline",
        "external_side_effects_allowed",
        "action_authorized",
    }
    _exact_fields(body, path="verification_request", required=required)
    if body["request_version"] != VERIFICATION_REQUEST_SCHEMA_VERSION:
        raise VerificationProviderFormatError("verification_request.request_version must be '0.1'")
    created_at = _timestamp(body["created_at"], "verification_request.created_at")
    deadline = _timestamp(body["deadline"], "verification_request.deadline")
    if _parse_timestamp(deadline) < _parse_timestamp(created_at):
        raise VerificationProviderFormatError("verification_request.deadline must not precede created_at")
    artifacts_raw = body["input_artifacts"]
    if not isinstance(artifacts_raw, list) or not artifacts_raw:
        raise VerificationProviderFormatError("verification_request.input_artifacts must not be empty")
    artifacts = tuple(
        _load_artifact_binding(item, f"verification_request.input_artifacts[{index}]")
        for index, item in enumerate(artifacts_raw)
    )
    if len({item.ref_id for item in artifacts}) != len(artifacts):
        raise VerificationProviderFormatError(
            "verification_request.input_artifacts ref_id values must be unique"
        )
    allowed_types = _string_list(
        body["allowed_provider_types"],
        "verification_request.allowed_provider_types",
        allow_empty=False,
    )
    unknown_types = sorted(set(allowed_types) - _PROVIDER_TYPES)
    if unknown_types:
        raise VerificationProviderFormatError(
            "verification_request.allowed_provider_types contains unsupported value(s): "
            + ", ".join(unknown_types)
        )
    profile_ref = _mapping(
        body["assurance_profile_ref"], "verification_request.assurance_profile_ref"
    )
    _exact_fields(
        profile_ref,
        path="verification_request.assurance_profile_ref",
        required={"profile_id", "sha256"},
    )
    external_side_effects_allowed = _boolean(
        body["external_side_effects_allowed"],
        "verification_request.external_side_effects_allowed",
    )
    action_authorized = _boolean(
        body["action_authorized"], "verification_request.action_authorized"
    )
    if external_side_effects_allowed or action_authorized:
        raise VerificationProviderFormatError(
            "public Verification Requests must not allow side effects or authorize actions"
        )
    return VerificationRequest(
        request_id=_identifier(body["request_id"], "verification_request.request_id"),
        created_at=created_at,
        subject=_load_subject(body["subject"], "verification_request.subject"),
        input_artifacts=artifacts,
        verification_method=_identifier(
            body["verification_method"], "verification_request.verification_method"
        ),
        required_capabilities=_string_list(
            body["required_capabilities"],
            "verification_request.required_capabilities",
            allow_empty=False,
        ),
        allowed_provider_types=allowed_types,
        assurance_profile_id=_identifier(
            profile_ref["profile_id"], "verification_request.assurance_profile_ref.profile_id"
        ),
        assurance_profile_sha256=_sha256(
            profile_ref["sha256"], "verification_request.assurance_profile_ref.sha256"
        ),
        deadline=deadline,
        external_side_effects_allowed=external_side_effects_allowed,
        action_authorized=action_authorized,
    )


def _load_diagnostics(value: object, path: str) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list):
        raise VerificationProviderFormatError(f"{path} must be an array")
    result: list[dict[str, str]] = []
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(item, path=item_path, required={"code", "message", "severity"})
        severity = _enum(item["severity"], {"error", "warning"}, f"{item_path}.severity")
        result.append(
            {
                "code": _identifier(item["code"], f"{item_path}.code"),
                "message": _string(item["message"], f"{item_path}.message"),
                "severity": severity,
            }
        )
    return tuple(result)


def load_verification_response(payload: Mapping[str, object]) -> VerificationResponse:
    root = _mapping(payload, "Verification Response")
    _exact_fields(root, path="response root", required={"verification_response"})
    body = _mapping(root["verification_response"], "verification_response")
    required = {
        "response_version",
        "response_id",
        "request_ref",
        "provider_ref",
        "state",
        "result",
        "verification_method",
        "evidence_refs",
        "assurance_declarations",
        "diagnostics",
        "completed_at",
        "independently_verified",
        "production_output_released",
        "action_authorized",
        "action_executed",
    }
    _exact_fields(body, path="verification_response", required=required)
    if body["response_version"] != VERIFICATION_RESPONSE_SCHEMA_VERSION:
        raise VerificationProviderFormatError("verification_response.response_version must be '0.1'")
    for field in (
        "independently_verified",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        if _boolean(body[field], f"verification_response.{field}"):
            raise VerificationProviderFormatError(
                f"verification_response.{field} must remain false"
            )
    request_ref = _mapping(body["request_ref"], "verification_response.request_ref")
    _exact_fields(
        request_ref,
        path="verification_response.request_ref",
        required={"request_id", "sha256"},
    )
    provider_ref = _mapping(body["provider_ref"], "verification_response.provider_ref")
    _exact_fields(
        provider_ref,
        path="verification_response.provider_ref",
        required={"provider_id", "provider_version", "sha256"},
    )
    result = _mapping(body["result"], "verification_response.result")
    _exact_fields(
        result,
        path="verification_response.result",
        required={"claim_id", "claim_type", "value", "unit", "observed_at", "valid_until"},
    )
    assurance = _mapping(
        body["assurance_declarations"], "verification_response.assurance_declarations"
    )
    _exact_fields(
        assurance,
        path="verification_response.assurance_declarations",
        required={"independence_group", "reproducibility", "calibration_status", "confidence"},
    )
    state = _enum(body["state"], _RESPONSE_STATES, "verification_response.state")
    value = _json_value(result["value"], "verification_response.result.value")
    unit = result["unit"]
    observed_at = result["observed_at"]
    valid_until = result["valid_until"]
    if state in {"verified", "contradicted"}:
        if value is None or observed_at is None or valid_until is None:
            raise VerificationProviderFormatError(
                "verified or contradicted responses require value and validity timestamps"
            )
    if unit is not None:
        unit = _string(unit, "verification_response.result.unit")
    if observed_at is not None:
        observed_at = _timestamp(observed_at, "verification_response.result.observed_at")
    if valid_until is not None:
        valid_until = _timestamp(valid_until, "verification_response.result.valid_until")
    if observed_at is not None and valid_until is not None:
        if _parse_timestamp(valid_until) < _parse_timestamp(observed_at):
            raise VerificationProviderFormatError(
                "verification_response.result.valid_until must not precede observed_at"
            )
    confidence_raw = assurance["confidence"]
    confidence: float | None
    if confidence_raw is None:
        confidence = None
    else:
        confidence = _number(
            confidence_raw, "verification_response.assurance_declarations.confidence"
        )
        if not 0.0 <= confidence <= 1.0:
            raise VerificationProviderFormatError(
                "verification_response.assurance_declarations.confidence must be between 0 and 1"
            )
    diagnostics = _load_diagnostics(body["diagnostics"], "verification_response.diagnostics")
    if state == "failed" and not any(item["severity"] == "error" for item in diagnostics):
        raise VerificationProviderFormatError(
            "failed verification responses require an error diagnostic"
        )
    return VerificationResponse(
        response_id=_identifier(body["response_id"], "verification_response.response_id"),
        request_id=_identifier(
            request_ref["request_id"], "verification_response.request_ref.request_id"
        ),
        request_sha256=_sha256(
            request_ref["sha256"], "verification_response.request_ref.sha256"
        ),
        provider_id=_identifier(
            provider_ref["provider_id"], "verification_response.provider_ref.provider_id"
        ),
        provider_version=_string(
            provider_ref["provider_version"],
            "verification_response.provider_ref.provider_version",
        ),
        provider_sha256=_sha256(
            provider_ref["sha256"], "verification_response.provider_ref.sha256"
        ),
        state=state,
        claim_id=_identifier(result["claim_id"], "verification_response.result.claim_id"),
        claim_type=_identifier(result["claim_type"], "verification_response.result.claim_type"),
        value=value,
        unit=unit,
        observed_at=observed_at,
        valid_until=valid_until,
        verification_method=_identifier(
            body["verification_method"], "verification_response.verification_method"
        ),
        evidence_refs=_string_list(
            body["evidence_refs"], "verification_response.evidence_refs"
        ),
        independence_group=_identifier(
            assurance["independence_group"],
            "verification_response.assurance_declarations.independence_group",
        ),
        reproducibility=_enum(
            assurance["reproducibility"],
            _REPRODUCIBILITY_STATES,
            "verification_response.assurance_declarations.reproducibility",
        ),
        calibration_status=_enum(
            assurance["calibration_status"],
            _CALIBRATION_STATES,
            "verification_response.assurance_declarations.calibration_status",
        ),
        confidence=confidence,
        diagnostics=diagnostics,
        completed_at=_timestamp(body["completed_at"], "verification_response.completed_at"),
    )


def load_assurance_profile(payload: Mapping[str, object]) -> AssuranceProfile:
    root = _mapping(payload, "Assurance Profile")
    _exact_fields(root, path="profile root", required={"assurance_profile"})
    body = _mapping(root["assurance_profile"], "assurance_profile")
    required = {
        "profile_version",
        "profile_id",
        "title",
        "minimum_provider_count",
        "minimum_independent_groups",
        "allowed_provider_types",
        "require_fresh_results",
        "max_result_age_seconds",
        "require_reproducible",
        "accepted_reproducibility",
        "require_calibration",
        "accepted_calibration_states",
        "conflict_policy",
        "eligible_output",
        "blocked_outputs",
        "blocked_actions",
        "next_action_on_insufficient_assurance",
        "action_authorized",
        "action_executed",
    }
    _exact_fields(body, path="assurance_profile", required=required)
    if body["profile_version"] != ASSURANCE_PROFILE_SCHEMA_VERSION:
        raise VerificationProviderFormatError("assurance_profile.profile_version must be '0.1'")
    if _boolean(body["action_authorized"], "assurance_profile.action_authorized"):
        raise VerificationProviderFormatError("assurance_profile.action_authorized must be false")
    if _boolean(body["action_executed"], "assurance_profile.action_executed"):
        raise VerificationProviderFormatError("assurance_profile.action_executed must be false")
    minimum_provider_count = _integer(
        body["minimum_provider_count"], "assurance_profile.minimum_provider_count", minimum=1
    )
    minimum_independent_groups = _integer(
        body["minimum_independent_groups"],
        "assurance_profile.minimum_independent_groups",
        minimum=1,
    )
    if minimum_independent_groups > minimum_provider_count:
        raise VerificationProviderFormatError(
            "assurance_profile.minimum_independent_groups cannot exceed minimum_provider_count"
        )
    allowed_types = _string_list(
        body["allowed_provider_types"],
        "assurance_profile.allowed_provider_types",
        allow_empty=False,
    )
    if set(allowed_types) - _PROVIDER_TYPES:
        raise VerificationProviderFormatError(
            "assurance_profile.allowed_provider_types contains unsupported values"
        )
    accepted_reproducibility = _string_list(
        body["accepted_reproducibility"],
        "assurance_profile.accepted_reproducibility",
        allow_empty=False,
    )
    if set(accepted_reproducibility) - _REPRODUCIBILITY_STATES:
        raise VerificationProviderFormatError(
            "assurance_profile.accepted_reproducibility contains unsupported values"
        )
    accepted_calibration = _string_list(
        body["accepted_calibration_states"],
        "assurance_profile.accepted_calibration_states",
        allow_empty=False,
    )
    if set(accepted_calibration) - _CALIBRATION_STATES:
        raise VerificationProviderFormatError(
            "assurance_profile.accepted_calibration_states contains unsupported values"
        )
    eligible_output = _identifier(body["eligible_output"], "assurance_profile.eligible_output")
    blocked_outputs = _string_list(
        body["blocked_outputs"], "assurance_profile.blocked_outputs", allow_empty=False
    )
    if eligible_output in blocked_outputs:
        raise VerificationProviderFormatError(
            "assurance_profile.eligible_output must not also be a blocked output"
        )
    return AssuranceProfile(
        profile_id=_identifier(body["profile_id"], "assurance_profile.profile_id"),
        title=_string(body["title"], "assurance_profile.title"),
        minimum_provider_count=minimum_provider_count,
        minimum_independent_groups=minimum_independent_groups,
        allowed_provider_types=allowed_types,
        require_fresh_results=_boolean(
            body["require_fresh_results"], "assurance_profile.require_fresh_results"
        ),
        max_result_age_seconds=_integer(
            body["max_result_age_seconds"],
            "assurance_profile.max_result_age_seconds",
            minimum=0,
        ),
        require_reproducible=_boolean(
            body["require_reproducible"], "assurance_profile.require_reproducible"
        ),
        accepted_reproducibility=accepted_reproducibility,
        require_calibration=_boolean(
            body["require_calibration"], "assurance_profile.require_calibration"
        ),
        accepted_calibration_states=accepted_calibration,
        conflict_policy=_enum(
            body["conflict_policy"], _CONFLICT_POLICIES, "assurance_profile.conflict_policy"
        ),
        eligible_output=eligible_output,
        blocked_outputs=blocked_outputs,
        blocked_actions=_string_list(
            body["blocked_actions"], "assurance_profile.blocked_actions", allow_empty=False
        ),
        next_action_on_insufficient_assurance=_identifier(
            body["next_action_on_insufficient_assurance"],
            "assurance_profile.next_action_on_insufficient_assurance",
        ),
    )


def validate_verification_request_contract(
    descriptor: VerificationProviderDescriptor,
    request: VerificationRequest,
) -> dict[str, object]:
    """Check whether one Provider Descriptor can accept one Verification Request."""

    diagnostics: list[dict[str, str]] = []
    missing_capabilities = sorted(set(request.required_capabilities) - set(descriptor.capabilities))
    if missing_capabilities:
        diagnostics.append(
            {
                "code": "missing_provider_capability",
                "message": "missing capabilities: " + ", ".join(missing_capabilities),
            }
        )
    if request.verification_method not in descriptor.supported_methods:
        diagnostics.append(
            {
                "code": "unsupported_verification_method",
                "message": f"unsupported method: {request.verification_method}",
            }
        )
    if descriptor.provider_type not in request.allowed_provider_types:
        diagnostics.append(
            {
                "code": "provider_type_not_allowed",
                "message": f"provider type not allowed: {descriptor.provider_type}",
            }
        )
    if descriptor.valid_until is not None:
        if _parse_timestamp(descriptor.valid_until) < _parse_timestamp(request.created_at):
            diagnostics.append(
                {
                    "code": "provider_descriptor_expired",
                    "message": "provider descriptor expired before request creation",
                }
            )
    return {
        "verification_provider_contract": {
            "valid": not diagnostics,
            "provider_id": descriptor.provider_id,
            "request_id": request.request_id,
            "diagnostics": diagnostics,
            "request_submitted": False,
            "external_side_effects_executed": False,
            "action_authorized": False,
            "action_executed": False,
        }
    }


def validate_verification_response_bindings(
    response: VerificationResponse,
    *,
    request: VerificationRequest,
    request_bytes: bytes,
    descriptor: VerificationProviderDescriptor,
    descriptor_bytes: bytes,
) -> None:
    """Validate exact Request/Descriptor bindings and anti-self-promotion rules."""

    if response.request_id != request.request_id:
        raise VerificationProviderFormatError("response request_id does not match request")
    if response.request_sha256 != sha256_bytes(request_bytes):
        raise VerificationProviderFormatError("response request SHA-256 does not match exact bytes")
    if response.provider_id != descriptor.provider_id:
        raise VerificationProviderFormatError("response provider_id does not match descriptor")
    if response.provider_version != descriptor.provider_version:
        raise VerificationProviderFormatError("response provider_version does not match descriptor")
    if response.provider_sha256 != sha256_bytes(descriptor_bytes):
        raise VerificationProviderFormatError("response provider SHA-256 does not match exact bytes")
    if response.verification_method != request.verification_method:
        raise VerificationProviderFormatError("response method does not match request")
    if response.verification_method not in descriptor.supported_methods:
        raise VerificationProviderFormatError("response method is not supported by descriptor")
    if response.claim_id != request.subject.claim_id:
        raise VerificationProviderFormatError("response claim_id does not match request subject")
    if response.claim_type != request.subject.claim_type:
        raise VerificationProviderFormatError("response claim_type does not match request subject")
    if response.independence_group != descriptor.independence_group:
        raise VerificationProviderFormatError(
            "response independence_group must exactly match descriptor"
        )
    if response.reproducibility != descriptor.reproducibility:
        raise VerificationProviderFormatError(
            "response reproducibility must exactly match descriptor"
        )
    if response.calibration_status != descriptor.calibration_status:
        raise VerificationProviderFormatError(
            "response calibration_status must exactly match descriptor"
        )
    if descriptor.provider_type not in request.allowed_provider_types:
        raise VerificationProviderFormatError("descriptor provider_type is not allowed by request")
    if set(request.required_capabilities) - set(descriptor.capabilities):
        raise VerificationProviderFormatError("descriptor does not cover required capabilities")


def evaluate_verification_assurance(
    profile: AssuranceProfile,
    *,
    request: VerificationRequest,
    bound_results: Sequence[tuple[VerificationProviderDescriptor, VerificationResponse]],
    evaluated_at: str,
) -> dict[str, object]:
    """Evaluate multi-provider assurance without inferring precedence or averaging values."""

    evaluation_time = _parse_timestamp(_timestamp(evaluated_at, "evaluated_at"))
    diagnostics: list[dict[str, str]] = []
    provider_ids = [descriptor.provider_id for descriptor, _ in bound_results]
    if len(set(provider_ids)) != len(provider_ids):
        diagnostics.append(
            {"code": "duplicate_provider", "message": "provider IDs must be unique"}
        )
    if len(bound_results) < profile.minimum_provider_count:
        diagnostics.append(
            {
                "code": "insufficient_provider_count",
                "message": (
                    f"requires {profile.minimum_provider_count} providers, got {len(bound_results)}"
                ),
            }
        )
    groups = {descriptor.independence_group for descriptor, _ in bound_results}
    if len(groups) < profile.minimum_independent_groups:
        diagnostics.append(
            {
                "code": "insufficient_independent_groups",
                "message": (
                    f"requires {profile.minimum_independent_groups} independent groups, "
                    f"got {len(groups)}"
                ),
            }
        )

    usable: list[tuple[VerificationProviderDescriptor, VerificationResponse]] = []
    for descriptor, response in bound_results:
        if descriptor.provider_type not in profile.allowed_provider_types:
            diagnostics.append(
                {
                    "code": "provider_type_not_accepted",
                    "message": f"{descriptor.provider_id}: {descriptor.provider_type}",
                }
            )
            continue
        if response.state != "verified":
            diagnostics.append(
                {
                    "code": "response_not_verified",
                    "message": f"{response.response_id}: {response.state}",
                }
            )
            continue
        if profile.require_reproducible and (
            descriptor.reproducibility not in profile.accepted_reproducibility
        ):
            diagnostics.append(
                {
                    "code": "reproducibility_not_accepted",
                    "message": f"{descriptor.provider_id}: {descriptor.reproducibility}",
                }
            )
            continue
        if profile.require_calibration and (
            descriptor.calibration_status not in profile.accepted_calibration_states
        ):
            diagnostics.append(
                {
                    "code": "calibration_not_accepted",
                    "message": f"{descriptor.provider_id}: {descriptor.calibration_status}",
                }
            )
            continue
        if profile.require_fresh_results:
            if response.valid_until is None or response.observed_at is None:
                diagnostics.append(
                    {
                        "code": "missing_result_validity",
                        "message": response.response_id,
                    }
                )
                continue
            if _parse_timestamp(response.valid_until) < evaluation_time:
                diagnostics.append(
                    {"code": "stale_response", "message": response.response_id}
                )
                continue
            age_seconds = (evaluation_time - _parse_timestamp(response.observed_at)).total_seconds()
            if age_seconds < 0 or age_seconds > profile.max_result_age_seconds:
                diagnostics.append(
                    {
                        "code": "response_age_out_of_range",
                        "message": f"{response.response_id}: {age_seconds:.0f}s",
                    }
                )
                continue
        usable.append((descriptor, response))

    value_keys = {
        (
            response.unit,
            repr(response.value),
        )
        for _, response in usable
    }
    assurance_state: str
    reason: str
    if diagnostics or len(usable) < profile.minimum_provider_count:
        assurance_state = "unknown"
        reason = "insufficient_assurance"
    elif len(value_keys) > 1:
        assurance_state = profile.conflict_policy
        reason = "independent_provider_conflict"
    else:
        assurance_state = "verified"
        reason = "assurance_requirements_satisfied"

    eligible_outputs = [profile.eligible_output] if assurance_state == "verified" else []
    blocked_outputs = [] if assurance_state == "verified" else list(profile.blocked_outputs)
    blocked_actions = list(profile.blocked_actions)
    next_action = (
        "none"
        if assurance_state == "verified"
        else profile.next_action_on_insufficient_assurance
    )
    return {
        "assurance_evaluation": {
            "profile_id": profile.profile_id,
            "request_id": request.request_id,
            "evaluated_at": evaluated_at,
            "state": assurance_state,
            "reason": reason,
            "provider_count": len(bound_results),
            "usable_provider_count": len(usable),
            "independent_group_count": len(groups),
            "response_ids": [response.response_id for _, response in bound_results],
            "diagnostics": diagnostics,
            "eligible_outputs": eligible_outputs,
            "blocked_outputs": blocked_outputs,
            "blocked_actions": blocked_actions,
            "next_action": next_action,
            "independent_verification_completed": assurance_state == "verified",
            "production_output_released": False,
            "action_authorized": False,
            "action_executed": False,
        }
    }


def verification_provider_profile_payload() -> dict[str, object]:
    """Return the public interface summary used by the CLI and documentation."""

    return {
        "verification_provider_profile": {
            "profile_id": VERIFICATION_PROVIDER_INTERFACE_ID,
            "profile_version": VERIFICATION_PROVIDER_INTERFACE_VERSION,
            "provider_types": sorted(_PROVIDER_TYPES),
            "artifacts": [
                VERIFICATION_PROVIDER_DESCRIPTOR_ARTIFACT_ID,
                VERIFICATION_REQUEST_ARTIFACT_ID,
                VERIFICATION_RESPONSE_ARTIFACT_ID,
                ASSURANCE_PROFILE_ARTIFACT_ID,
            ],
            "provider_self_assurance_allowed": False,
            "external_side_effects_allowed": False,
            "production_output_release_supported": False,
            "action_authorization_supported": False,
            "action_execution_supported": False,
        }
    }


__all__ = [
    "VERIFICATION_PROVIDER_INTERFACE_ID",
    "VERIFICATION_PROVIDER_INTERFACE_VERSION",
    "VERIFICATION_PROVIDER_DESCRIPTOR_SCHEMA_ID",
    "VERIFICATION_REQUEST_SCHEMA_ID",
    "VERIFICATION_RESPONSE_SCHEMA_ID",
    "ASSURANCE_PROFILE_SCHEMA_ID",
    "VERIFICATION_PROVIDER_DESCRIPTOR_SCHEMA_VERSION",
    "VERIFICATION_REQUEST_SCHEMA_VERSION",
    "VERIFICATION_RESPONSE_SCHEMA_VERSION",
    "ASSURANCE_PROFILE_SCHEMA_VERSION",
    "VERIFICATION_PROVIDER_DESCRIPTOR_ARTIFACT_ID",
    "VERIFICATION_REQUEST_ARTIFACT_ID",
    "VERIFICATION_RESPONSE_ARTIFACT_ID",
    "ASSURANCE_PROFILE_ARTIFACT_ID",
    "VerificationProviderFormatError",
    "VerificationProviderDescriptor",
    "VerificationRequest",
    "VerificationResponse",
    "AssuranceProfile",
    "sha256_bytes",
    "load_verification_provider_descriptor",
    "load_verification_request",
    "load_verification_response",
    "load_assurance_profile",
    "validate_verification_request_contract",
    "validate_verification_response_bindings",
    "evaluate_verification_assurance",
    "verification_provider_profile_payload",
]
