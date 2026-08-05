"""Trajectory identity adjudication for bound GT37 candidates and Provider evidence.

The public contract binds one exact execution result containing a
``trajectory_identity_candidate`` output to an exact Verification Request,
Assurance Profile, Provider Descriptors, and Verification Responses. Core may
produce a review recommendation after the caller-authored assurance policy is
satisfied, but it never merges identities, mutates ``subject_ref``, releases a
production update, authorizes action, or executes action.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from geotask_core.v1.result import GeotaskResult
from geotask_core.v1.verification_provider import (
    ASSURANCE_PROFILE_ARTIFACT_ID,
    VERIFICATION_PROVIDER_DESCRIPTOR_ARTIFACT_ID,
    VERIFICATION_REQUEST_ARTIFACT_ID,
    VERIFICATION_RESPONSE_ARTIFACT_ID,
    AssuranceProfile,
    VerificationProviderDescriptor,
    VerificationRequest,
    VerificationResponse,
    evaluate_verification_assurance,
    load_assurance_profile,
    load_verification_provider_descriptor,
    load_verification_request,
    load_verification_response,
    validate_verification_request_contract,
    validate_verification_response_bindings,
)


TRAJECTORY_IDENTITY_ADJUDICATION_ARTIFACT_ID = (
    "geotask.trajectory-identity-adjudication"
)
TRAJECTORY_IDENTITY_ADJUDICATION_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-trajectory-identity-adjudication-v0.1.schema.json"
)
TRAJECTORY_IDENTITY_ADJUDICATION_SCHEMA_VERSION = "0.1"
TRAJECTORY_IDENTITY_ADJUDICATION_FORMAT_VERSION = "0.1"

CANDIDATE_STATES = frozenset(
    {"same_object_candidate", "different_object_candidate", "unverifiable"}
)
IDENTITY_VERDICTS = frozenset({"same_object", "different_objects", "unknown"})
ADJUDICATION_STATES = frozenset(
    {"same_object_confirmed", "different_objects_confirmed", "unresolved"}
)
CANDIDATE_ALIGNMENT_STATES = frozenset(
    {"aligned", "contradicted", "not_comparable", "unresolved"}
)
MERGE_RECOMMENDATIONS = frozenset(
    {
        "recommend_identity_merge_review",
        "recommend_keep_separate",
        "request_more_evidence",
    }
)
NEXT_ACTIONS = frozenset(
    {
        "review_identity_merge",
        "retain_separate_identities",
        "request_identity_evidence",
    }
)
ASSURANCE_STATES = frozenset({"verified", "unknown", "contradicted"})


class TrajectoryIdentityAdjudicationError(ValueError):
    """Raised when identity adjudication structure or bindings fail closed."""


def _fail(path: str, message: str) -> None:
    raise TrajectoryIdentityAdjudicationError(f"{path}: {message}")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _exact_fields(
    value: Mapping[str, object],
    path: str,
    *,
    required: frozenset[str] | set[str],
    optional: frozenset[str] | set[str] = frozenset(),
) -> None:
    actual = set(value)
    missing = sorted(set(required) - actual)
    unknown = sorted(actual - set(required) - set(optional))
    if missing:
        _fail(path, "missing required fields: " + ", ".join(missing))
    if unknown:
        _fail(path, "contains unknown fields: " + ", ".join(unknown))


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")
    return value


def _enum(value: object, path: str, allowed: frozenset[str]) -> str:
    text = _string(value, path)
    if text not in allowed:
        _fail(path, "must be one of: " + ", ".join(sorted(allowed)))
    return text


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        _fail(path, "must be boolean")
    return bool(value)


def _integer(value: object, path: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail(path, f"must be an integer greater than or equal to {minimum}")
    return int(value)


def _timestamp(value: object, path: str) -> str:
    text = _string(value, path)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TrajectoryIdentityAdjudicationError(
            f"{path}: must be an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must include a timezone")
    return text


def _sha256(value: object, path: str) -> str:
    text = _string(value, path)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        _fail(path, "must be a lowercase 64-character SHA-256 digest")
    return text


def _string_tuple(value: object, path: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array of strings")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _string(item, f"{path}[{index}]")
        if text in seen:
            _fail(f"{path}[{index}]", f"duplicates {text!r}")
        seen.add(text)
        result.append(text)
    return tuple(result)


def _diagnostics(value: object, path: str) -> tuple[dict[str, str], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    result: list[dict[str, str]] = []
    for index, item in enumerate(value):
        body = _mapping(item, f"{path}[{index}]")
        _exact_fields(
            body,
            f"{path}[{index}]",
            required={"code", "message"},
        )
        result.append(
            {
                "code": _string(body["code"], f"{path}[{index}].code"),
                "message": _string(body["message"], f"{path}[{index}].message"),
            }
        )
    return tuple(result)


def _json_mapping_from_bytes(content: bytes, path: str) -> Mapping[str, object]:
    if not isinstance(content, bytes):
        _fail(path, "must be bytes")
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrajectoryIdentityAdjudicationError(
            f"{path}: must contain UTF-8 JSON"
        ) from exc
    return _mapping(payload, path)


def _hash_bytes(content: bytes) -> str:
    if not isinstance(content, bytes):
        _fail("content", "must be bytes")
    return hashlib.sha256(content).hexdigest()


def _semantic_fingerprint(payload: Mapping[str, object]) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class IdentityCandidateResultRef:
    artifact_id: str
    task_id: str
    assertion_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "task_id": self.task_id,
            "assertion_id": self.assertion_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class IdentityVerificationRequestRef:
    artifact_id: str
    request_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "request_id": self.request_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class IdentityAssuranceProfileRef:
    artifact_id: str
    profile_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "profile_id": self.profile_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class IdentityProviderRef:
    ref_id: str
    artifact_id: str
    provider_id: str
    provider_version: str
    provider_type: str
    independence_group: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ref_id": self.ref_id,
            "artifact_id": self.artifact_id,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "provider_type": self.provider_type,
            "independence_group": self.independence_group,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class IdentityResponseRef:
    ref_id: str
    artifact_id: str
    response_id: str
    request_id: str
    provider_id: str
    independence_group: str
    verdict: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ref_id": self.ref_id,
            "artifact_id": self.artifact_id,
            "response_id": self.response_id,
            "request_id": self.request_id,
            "provider_id": self.provider_id,
            "independence_group": self.independence_group,
            "verdict": self.verdict,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class IdentityPair:
    first_trajectory_ref: str
    second_trajectory_ref: str
    first_subject_ref: str
    second_subject_ref: str
    first_object_class: str
    second_object_class: str

    def to_dict(self) -> dict[str, object]:
        return {
            "first_trajectory_ref": self.first_trajectory_ref,
            "second_trajectory_ref": self.second_trajectory_ref,
            "first_subject_ref": self.first_subject_ref,
            "second_subject_ref": self.second_subject_ref,
            "first_object_class": self.first_object_class,
            "second_object_class": self.second_object_class,
        }


@dataclass(frozen=True)
class IdentityPolicyResult:
    state: str
    reason: str
    provider_count: int
    usable_provider_count: int
    independent_group_count: int
    same_object_response_refs: tuple[str, ...]
    different_objects_response_refs: tuple[str, ...]
    unknown_response_refs: tuple[str, ...]
    diagnostics: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "reason": self.reason,
            "provider_count": self.provider_count,
            "usable_provider_count": self.usable_provider_count,
            "independent_group_count": self.independent_group_count,
            "same_object_response_refs": list(self.same_object_response_refs),
            "different_objects_response_refs": list(
                self.different_objects_response_refs
            ),
            "unknown_response_refs": list(self.unknown_response_refs),
            "diagnostics": [dict(item) for item in self.diagnostics],
        }


@dataclass(frozen=True)
class TrajectoryIdentityAdjudication:
    adjudication_id: str
    created_at: str
    candidate_result_ref: IdentityCandidateResultRef
    verification_request_ref: IdentityVerificationRequestRef
    assurance_profile_ref: IdentityAssuranceProfileRef
    provider_refs: tuple[IdentityProviderRef, ...]
    response_refs: tuple[IdentityResponseRef, ...]
    identity_pair: IdentityPair
    candidate_state: str
    requested_verdict: str
    policy_result: IdentityPolicyResult
    adjudication_state: str
    adjudication_reason: str
    candidate_alignment: str
    identity_merge_recommendation: str
    next_action: str
    candidate_binding_verified: bool
    verification_bindings_verified: bool
    independent_evidence_satisfied: bool
    external_identity_verified_by_core: bool
    identity_merge_performed: bool
    subject_refs_mutated: bool
    production_output_released: bool
    action_authorized: bool
    action_executed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "trajectory_identity_adjudication": {
                "adjudication_version": (
                    TRAJECTORY_IDENTITY_ADJUDICATION_FORMAT_VERSION
                ),
                "adjudication_id": self.adjudication_id,
                "created_at": self.created_at,
                "candidate_result_ref": self.candidate_result_ref.to_dict(),
                "verification_request_ref": self.verification_request_ref.to_dict(),
                "assurance_profile_ref": self.assurance_profile_ref.to_dict(),
                "provider_refs": [item.to_dict() for item in self.provider_refs],
                "response_refs": [item.to_dict() for item in self.response_refs],
                "identity_pair": self.identity_pair.to_dict(),
                "candidate_state": self.candidate_state,
                "requested_verdict": self.requested_verdict,
                "policy_result": self.policy_result.to_dict(),
                "adjudication_state": self.adjudication_state,
                "adjudication_reason": self.adjudication_reason,
                "candidate_alignment": self.candidate_alignment,
                "identity_merge_recommendation": self.identity_merge_recommendation,
                "next_action": self.next_action,
                "candidate_binding_verified": self.candidate_binding_verified,
                "verification_bindings_verified": self.verification_bindings_verified,
                "independent_evidence_satisfied": self.independent_evidence_satisfied,
                "external_identity_verified_by_core": (
                    self.external_identity_verified_by_core
                ),
                "identity_merge_performed": self.identity_merge_performed,
                "subject_refs_mutated": self.subject_refs_mutated,
                "production_output_released": self.production_output_released,
                "action_authorized": self.action_authorized,
                "action_executed": self.action_executed,
            }
        }

    def semantic_fingerprint(self) -> str:
        return _semantic_fingerprint(self.to_dict())


def _load_candidate_result(
    content: bytes,
) -> tuple[GeotaskResult, Mapping[str, object], IdentityPair, str]:
    payload = _json_mapping_from_bytes(content, "candidate_result_bytes")
    try:
        result = GeotaskResult.from_dict(dict(payload))
    except Exception as exc:
        raise TrajectoryIdentityAdjudicationError(
            f"candidate_result_bytes: invalid execution result: {exc}"
        ) from exc
    record = result.outputs.get("identity_candidate")
    if not isinstance(record, Mapping):
        _fail(
            "candidate_result_bytes.outputs.identity_candidate",
            "must be a structured trajectory identity candidate",
        )
    required = {
        "candidate_state",
        "first_trajectory_ref",
        "second_trajectory_ref",
        "first_subject_ref",
        "second_subject_ref",
        "first_object_class",
        "second_object_class",
        "identity_merge_performed",
        "subject_refs_mutated",
    }
    missing = sorted(required - set(record))
    if missing:
        _fail(
            "candidate_result_bytes.outputs.identity_candidate",
            "missing required fields: " + ", ".join(missing),
        )
    candidate_state = _enum(
        record["candidate_state"],
        "candidate_result_bytes.outputs.identity_candidate.candidate_state",
        CANDIDATE_STATES,
    )
    if record["identity_merge_performed"] is not False:
        _fail(
            "candidate_result_bytes.outputs.identity_candidate.identity_merge_performed",
            "must be false",
        )
    if record["subject_refs_mutated"] is not False:
        _fail(
            "candidate_result_bytes.outputs.identity_candidate.subject_refs_mutated",
            "must be false",
        )
    pair = IdentityPair(
        first_trajectory_ref=_string(
            record["first_trajectory_ref"], "candidate first_trajectory_ref"
        ),
        second_trajectory_ref=_string(
            record["second_trajectory_ref"], "candidate second_trajectory_ref"
        ),
        first_subject_ref=_string(
            record["first_subject_ref"], "candidate first_subject_ref"
        ),
        second_subject_ref=_string(
            record["second_subject_ref"], "candidate second_subject_ref"
        ),
        first_object_class=_string(
            record["first_object_class"], "candidate first_object_class"
        ),
        second_object_class=_string(
            record["second_object_class"], "candidate second_object_class"
        ),
    )
    if pair.first_trajectory_ref == pair.second_trajectory_ref:
        _fail("candidate identity_pair", "trajectory references must be distinct")
    if pair.first_subject_ref == pair.second_subject_ref:
        _fail(
            "candidate identity_pair",
            "GT38 requires two distinct provisional subject references",
        )
    return result, record, pair, candidate_state


def _requested_verdict(request: VerificationRequest) -> str:
    if request.subject.claim_type != "trajectory_identity":
        _fail(
            "verification_request.subject.claim_type",
            "must be 'trajectory_identity'",
        )
    value = request.subject.value
    if not isinstance(value, str) or value not in {
        "same_object",
        "different_objects",
    }:
        _fail(
            "verification_request.subject.value",
            "must be 'same_object' or 'different_objects'",
        )
    return value


def _response_verdict(response: VerificationResponse, path: str) -> str:
    if response.state == "verified":
        if response.value not in {"same_object", "different_objects"}:
            _fail(
                f"{path}.result.value",
                "verified identity responses must be 'same_object' or 'different_objects'",
            )
        if response.unit is not None:
            _fail(f"{path}.result.unit", "identity verdicts must have unit null")
        return str(response.value)
    if response.value is not None and response.value not in {
        "same_object",
        "different_objects",
    }:
        _fail(
            f"{path}.result.value",
            "must be null, 'same_object', or 'different_objects'",
        )
    return "unknown"


def _derive_candidate_alignment(candidate_state: str, adjudication_state: str) -> str:
    if adjudication_state == "unresolved":
        return "unresolved"
    if candidate_state == "unverifiable":
        return "not_comparable"
    if (
        candidate_state == "same_object_candidate"
        and adjudication_state == "same_object_confirmed"
    ) or (
        candidate_state == "different_object_candidate"
        and adjudication_state == "different_objects_confirmed"
    ):
        return "aligned"
    return "contradicted"


def build_trajectory_identity_adjudication(
    *,
    adjudication_id: str,
    created_at: str,
    candidate_result_bytes: bytes,
    verification_request_bytes: bytes,
    assurance_profile_bytes: bytes,
    provider_descriptor_bytes: Sequence[bytes],
    verification_response_bytes: Sequence[bytes],
) -> TrajectoryIdentityAdjudication:
    """Build one exact-bound identity adjudication without modifying objects."""

    adjudication_id = _string(adjudication_id, "adjudication_id")
    created_at = _timestamp(created_at, "created_at")
    result, _candidate, pair, candidate_state = _load_candidate_result(
        candidate_result_bytes
    )

    request_payload = _json_mapping_from_bytes(
        verification_request_bytes, "verification_request_bytes"
    )
    profile_payload = _json_mapping_from_bytes(
        assurance_profile_bytes, "assurance_profile_bytes"
    )
    try:
        request = load_verification_request(request_payload)
        profile = load_assurance_profile(profile_payload)
    except Exception as exc:
        raise TrajectoryIdentityAdjudicationError(str(exc)) from exc

    requested_verdict = _requested_verdict(request)
    if request.assurance_profile_id != profile.profile_id:
        _fail(
            "verification_request.assurance_profile_ref.profile_id",
            "does not match the supplied Assurance Profile",
        )
    if request.assurance_profile_sha256 != _hash_bytes(assurance_profile_bytes):
        _fail(
            "verification_request.assurance_profile_ref.sha256",
            "does not match exact Assurance Profile bytes",
        )
    candidate_hash = _hash_bytes(candidate_result_bytes)
    candidate_bindings = [
        item
        for item in request.input_artifacts
        if item.artifact_id == "geotask.execution-result"
        and item.sha256 == candidate_hash
    ]
    if len(candidate_bindings) != 1:
        _fail(
            "verification_request.input_artifacts",
            "must contain exactly one exact geotask.execution-result binding for the candidate",
        )
    if profile.eligible_output != "identity_merge_recommendation":
        _fail(
            "assurance_profile.eligible_output",
            "must be 'identity_merge_recommendation'",
        )
    required_blocked_outputs = {"automatic_identity_merge", "subject_ref_update"}
    if not required_blocked_outputs.issubset(set(profile.blocked_outputs)):
        _fail(
            "assurance_profile.blocked_outputs",
            "must block automatic_identity_merge and subject_ref_update",
        )
    required_blocked_actions = {"merge_identity", "rewrite_subject_ref"}
    if not required_blocked_actions.issubset(set(profile.blocked_actions)):
        _fail(
            "assurance_profile.blocked_actions",
            "must block merge_identity and rewrite_subject_ref",
        )

    if len(provider_descriptor_bytes) != len(verification_response_bytes):
        _fail(
            "provider/response inputs",
            "descriptor and response counts must match",
        )
    if not provider_descriptor_bytes:
        _fail("provider_descriptor_bytes", "must contain at least one descriptor")

    descriptors: list[tuple[bytes, VerificationProviderDescriptor]] = []
    descriptor_by_provider: dict[str, tuple[bytes, VerificationProviderDescriptor]] = {}
    for index, content in enumerate(provider_descriptor_bytes):
        payload = _json_mapping_from_bytes(
            content, f"provider_descriptor_bytes[{index}]"
        )
        try:
            descriptor = load_verification_provider_descriptor(payload)
        except Exception as exc:
            raise TrajectoryIdentityAdjudicationError(str(exc)) from exc
        if descriptor.provider_id in descriptor_by_provider:
            _fail(
                f"provider_descriptor_bytes[{index}]",
                f"duplicates provider_id {descriptor.provider_id!r}",
            )
        contract = validate_verification_request_contract(descriptor, request)[
            "verification_provider_contract"
        ]
        if not contract["valid"]:
            _fail(
                f"provider_descriptor_bytes[{index}]",
                f"cannot accept request: {contract['diagnostics']}",
            )
        descriptors.append((content, descriptor))
        descriptor_by_provider[descriptor.provider_id] = (content, descriptor)

    responses: list[tuple[bytes, VerificationResponse, str]] = []
    seen_response_ids: set[str] = set()
    bound_results: list[
        tuple[VerificationProviderDescriptor, VerificationResponse]
    ] = []
    for index, content in enumerate(verification_response_bytes):
        payload = _json_mapping_from_bytes(
            content, f"verification_response_bytes[{index}]"
        )
        try:
            response = load_verification_response(payload)
        except Exception as exc:
            raise TrajectoryIdentityAdjudicationError(str(exc)) from exc
        if response.response_id in seen_response_ids:
            _fail(
                f"verification_response_bytes[{index}]",
                f"duplicates response_id {response.response_id!r}",
            )
        seen_response_ids.add(response.response_id)
        bound = descriptor_by_provider.get(response.provider_id)
        if bound is None:
            _fail(
                f"verification_response_bytes[{index}].provider_ref.provider_id",
                "has no supplied Provider Descriptor",
            )
        descriptor_content, descriptor = bound
        try:
            validate_verification_response_bindings(
                response,
                request=request,
                request_bytes=verification_request_bytes,
                descriptor=descriptor,
                descriptor_bytes=descriptor_content,
            )
        except Exception as exc:
            raise TrajectoryIdentityAdjudicationError(str(exc)) from exc
        verdict = _response_verdict(
            response, f"verification_response_bytes[{index}]"
        )
        responses.append((content, response, verdict))
        bound_results.append((descriptor, response))

    if {descriptor.provider_id for _, descriptor in descriptors} != {
        response.provider_id for _, response, _ in responses
    }:
        _fail(
            "provider/response inputs",
            "every supplied descriptor must have exactly one supplied response",
        )

    evaluation = evaluate_verification_assurance(
        profile,
        request=request,
        bound_results=bound_results,
        evaluated_at=created_at,
    )["assurance_evaluation"]
    assurance_state = _enum(
        evaluation["state"], "assurance_evaluation.state", ASSURANCE_STATES
    )

    provider_ref_by_id: dict[str, IdentityProviderRef] = {}
    provider_refs: list[IdentityProviderRef] = []
    for index, (content, descriptor) in enumerate(descriptors):
        ref = IdentityProviderRef(
            ref_id=f"provider-{index + 1}",
            artifact_id=VERIFICATION_PROVIDER_DESCRIPTOR_ARTIFACT_ID,
            provider_id=descriptor.provider_id,
            provider_version=descriptor.provider_version,
            provider_type=descriptor.provider_type,
            independence_group=descriptor.independence_group,
            content_sha256=_hash_bytes(content),
        )
        provider_refs.append(ref)
        provider_ref_by_id[descriptor.provider_id] = ref

    response_refs: list[IdentityResponseRef] = []
    same_refs: list[str] = []
    different_refs: list[str] = []
    unknown_refs: list[str] = []
    for index, (content, response, verdict) in enumerate(responses):
        ref_id = f"response-{index + 1}"
        response_ref = IdentityResponseRef(
            ref_id=ref_id,
            artifact_id=VERIFICATION_RESPONSE_ARTIFACT_ID,
            response_id=response.response_id,
            request_id=response.request_id,
            provider_id=response.provider_id,
            independence_group=response.independence_group,
            verdict=verdict,
            content_sha256=_hash_bytes(content),
        )
        response_refs.append(response_ref)
        if verdict == "same_object":
            same_refs.append(ref_id)
        elif verdict == "different_objects":
            different_refs.append(ref_id)
        else:
            unknown_refs.append(ref_id)

    if assurance_state == "verified" and same_refs and not different_refs and not unknown_refs:
        adjudication_state = "same_object_confirmed"
        adjudication_reason = "independent_bound_evidence_supports_same_object"
        recommendation = "recommend_identity_merge_review"
        next_action = "review_identity_merge"
        independent_evidence_satisfied = True
    elif (
        assurance_state == "verified"
        and different_refs
        and not same_refs
        and not unknown_refs
    ):
        adjudication_state = "different_objects_confirmed"
        adjudication_reason = "independent_bound_evidence_supports_different_objects"
        recommendation = "recommend_keep_separate"
        next_action = "retain_separate_identities"
        independent_evidence_satisfied = True
    else:
        adjudication_state = "unresolved"
        adjudication_reason = str(evaluation["reason"])
        recommendation = "request_more_evidence"
        next_action = "request_identity_evidence"
        independent_evidence_satisfied = False

    policy_result = IdentityPolicyResult(
        state=assurance_state,
        reason=_string(evaluation["reason"], "assurance_evaluation.reason"),
        provider_count=_integer(
            evaluation["provider_count"], "assurance_evaluation.provider_count"
        ),
        usable_provider_count=_integer(
            evaluation["usable_provider_count"],
            "assurance_evaluation.usable_provider_count",
        ),
        independent_group_count=_integer(
            evaluation["independent_group_count"],
            "assurance_evaluation.independent_group_count",
        ),
        same_object_response_refs=tuple(same_refs),
        different_objects_response_refs=tuple(different_refs),
        unknown_response_refs=tuple(unknown_refs),
        diagnostics=tuple(
            {
                "code": _string(item["code"], "assurance diagnostic code"),
                "message": _string(
                    item["message"], "assurance diagnostic message"
                ),
            }
            for item in evaluation["diagnostics"]
        ),
    )

    return TrajectoryIdentityAdjudication(
        adjudication_id=adjudication_id,
        created_at=created_at,
        candidate_result_ref=IdentityCandidateResultRef(
            artifact_id="geotask.execution-result",
            task_id=result.task_id,
            assertion_id="identity_candidate",
            content_sha256=candidate_hash,
        ),
        verification_request_ref=IdentityVerificationRequestRef(
            artifact_id=VERIFICATION_REQUEST_ARTIFACT_ID,
            request_id=request.request_id,
            content_sha256=_hash_bytes(verification_request_bytes),
        ),
        assurance_profile_ref=IdentityAssuranceProfileRef(
            artifact_id=ASSURANCE_PROFILE_ARTIFACT_ID,
            profile_id=profile.profile_id,
            content_sha256=_hash_bytes(assurance_profile_bytes),
        ),
        provider_refs=tuple(provider_refs),
        response_refs=tuple(response_refs),
        identity_pair=pair,
        candidate_state=candidate_state,
        requested_verdict=requested_verdict,
        policy_result=policy_result,
        adjudication_state=adjudication_state,
        adjudication_reason=adjudication_reason,
        candidate_alignment=_derive_candidate_alignment(
            candidate_state, adjudication_state
        ),
        identity_merge_recommendation=recommendation,
        next_action=next_action,
        candidate_binding_verified=True,
        verification_bindings_verified=True,
        independent_evidence_satisfied=independent_evidence_satisfied,
        external_identity_verified_by_core=False,
        identity_merge_performed=False,
        subject_refs_mutated=False,
        production_output_released=False,
        action_authorized=False,
        action_executed=False,
    )


def _load_candidate_ref(value: object, path: str) -> IdentityCandidateResultRef:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={"artifact_id", "task_id", "assertion_id", "content_sha256"},
    )
    artifact_id = _string(body["artifact_id"], f"{path}.artifact_id")
    if artifact_id != "geotask.execution-result":
        _fail(f"{path}.artifact_id", "must be 'geotask.execution-result'")
    assertion_id = _string(body["assertion_id"], f"{path}.assertion_id")
    if assertion_id != "identity_candidate":
        _fail(f"{path}.assertion_id", "must be 'identity_candidate'")
    return IdentityCandidateResultRef(
        artifact_id=artifact_id,
        task_id=_string(body["task_id"], f"{path}.task_id"),
        assertion_id=assertion_id,
        content_sha256=_sha256(body["content_sha256"], f"{path}.content_sha256"),
    )


def _load_request_ref(value: object, path: str) -> IdentityVerificationRequestRef:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={"artifact_id", "request_id", "content_sha256"},
    )
    artifact_id = _string(body["artifact_id"], f"{path}.artifact_id")
    if artifact_id != VERIFICATION_REQUEST_ARTIFACT_ID:
        _fail(
            f"{path}.artifact_id",
            f"must be {VERIFICATION_REQUEST_ARTIFACT_ID!r}",
        )
    return IdentityVerificationRequestRef(
        artifact_id=artifact_id,
        request_id=_string(body["request_id"], f"{path}.request_id"),
        content_sha256=_sha256(body["content_sha256"], f"{path}.content_sha256"),
    )


def _load_profile_ref(value: object, path: str) -> IdentityAssuranceProfileRef:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={"artifact_id", "profile_id", "content_sha256"},
    )
    artifact_id = _string(body["artifact_id"], f"{path}.artifact_id")
    if artifact_id != ASSURANCE_PROFILE_ARTIFACT_ID:
        _fail(
            f"{path}.artifact_id",
            f"must be {ASSURANCE_PROFILE_ARTIFACT_ID!r}",
        )
    return IdentityAssuranceProfileRef(
        artifact_id=artifact_id,
        profile_id=_string(body["profile_id"], f"{path}.profile_id"),
        content_sha256=_sha256(body["content_sha256"], f"{path}.content_sha256"),
    )


def _load_provider_refs(value: object, path: str) -> tuple[IdentityProviderRef, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if not value:
        _fail(path, "must contain at least one provider")
    refs: list[IdentityProviderRef] = []
    ref_ids: set[str] = set()
    provider_ids: set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        body = _mapping(item, item_path)
        _exact_fields(
            body,
            item_path,
            required={
                "ref_id",
                "artifact_id",
                "provider_id",
                "provider_version",
                "provider_type",
                "independence_group",
                "content_sha256",
            },
        )
        ref_id = _string(body["ref_id"], f"{item_path}.ref_id")
        provider_id = _string(body["provider_id"], f"{item_path}.provider_id")
        if ref_id in ref_ids:
            _fail(f"{item_path}.ref_id", "must be unique")
        if provider_id in provider_ids:
            _fail(f"{item_path}.provider_id", "must be unique")
        ref_ids.add(ref_id)
        provider_ids.add(provider_id)
        artifact_id = _string(body["artifact_id"], f"{item_path}.artifact_id")
        if artifact_id != VERIFICATION_PROVIDER_DESCRIPTOR_ARTIFACT_ID:
            _fail(
                f"{item_path}.artifact_id",
                f"must be {VERIFICATION_PROVIDER_DESCRIPTOR_ARTIFACT_ID!r}",
            )
        refs.append(
            IdentityProviderRef(
                ref_id=ref_id,
                artifact_id=artifact_id,
                provider_id=provider_id,
                provider_version=_string(
                    body["provider_version"], f"{item_path}.provider_version"
                ),
                provider_type=_string(
                    body["provider_type"], f"{item_path}.provider_type"
                ),
                independence_group=_string(
                    body["independence_group"],
                    f"{item_path}.independence_group",
                ),
                content_sha256=_sha256(
                    body["content_sha256"], f"{item_path}.content_sha256"
                ),
            )
        )
    return tuple(refs)


def _load_response_refs(value: object, path: str) -> tuple[IdentityResponseRef, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if not value:
        _fail(path, "must contain at least one response")
    refs: list[IdentityResponseRef] = []
    ref_ids: set[str] = set()
    response_ids: set[str] = set()
    provider_ids: set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        body = _mapping(item, item_path)
        _exact_fields(
            body,
            item_path,
            required={
                "ref_id",
                "artifact_id",
                "response_id",
                "request_id",
                "provider_id",
                "independence_group",
                "verdict",
                "content_sha256",
            },
        )
        ref_id = _string(body["ref_id"], f"{item_path}.ref_id")
        response_id = _string(body["response_id"], f"{item_path}.response_id")
        provider_id = _string(body["provider_id"], f"{item_path}.provider_id")
        for label, item_value, seen in (
            ("ref_id", ref_id, ref_ids),
            ("response_id", response_id, response_ids),
            ("provider_id", provider_id, provider_ids),
        ):
            if item_value in seen:
                _fail(f"{item_path}.{label}", "must be unique")
            seen.add(item_value)
        artifact_id = _string(body["artifact_id"], f"{item_path}.artifact_id")
        if artifact_id != VERIFICATION_RESPONSE_ARTIFACT_ID:
            _fail(
                f"{item_path}.artifact_id",
                f"must be {VERIFICATION_RESPONSE_ARTIFACT_ID!r}",
            )
        refs.append(
            IdentityResponseRef(
                ref_id=ref_id,
                artifact_id=artifact_id,
                response_id=response_id,
                request_id=_string(body["request_id"], f"{item_path}.request_id"),
                provider_id=provider_id,
                independence_group=_string(
                    body["independence_group"],
                    f"{item_path}.independence_group",
                ),
                verdict=_enum(
                    body["verdict"], f"{item_path}.verdict", IDENTITY_VERDICTS
                ),
                content_sha256=_sha256(
                    body["content_sha256"], f"{item_path}.content_sha256"
                ),
            )
        )
    return tuple(refs)


def _load_identity_pair(value: object, path: str) -> IdentityPair:
    body = _mapping(value, path)
    fields = {
        "first_trajectory_ref",
        "second_trajectory_ref",
        "first_subject_ref",
        "second_subject_ref",
        "first_object_class",
        "second_object_class",
    }
    _exact_fields(body, path, required=fields)
    pair = IdentityPair(
        first_trajectory_ref=_string(
            body["first_trajectory_ref"], f"{path}.first_trajectory_ref"
        ),
        second_trajectory_ref=_string(
            body["second_trajectory_ref"], f"{path}.second_trajectory_ref"
        ),
        first_subject_ref=_string(
            body["first_subject_ref"], f"{path}.first_subject_ref"
        ),
        second_subject_ref=_string(
            body["second_subject_ref"], f"{path}.second_subject_ref"
        ),
        first_object_class=_string(
            body["first_object_class"], f"{path}.first_object_class"
        ),
        second_object_class=_string(
            body["second_object_class"], f"{path}.second_object_class"
        ),
    )
    if pair.first_trajectory_ref == pair.second_trajectory_ref:
        _fail(path, "trajectory references must be distinct")
    if pair.first_subject_ref == pair.second_subject_ref:
        _fail(path, "subject references must be distinct")
    return pair


def _load_policy_result(value: object, path: str) -> IdentityPolicyResult:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={
            "state",
            "reason",
            "provider_count",
            "usable_provider_count",
            "independent_group_count",
            "same_object_response_refs",
            "different_objects_response_refs",
            "unknown_response_refs",
            "diagnostics",
        },
    )
    result = IdentityPolicyResult(
        state=_enum(body["state"], f"{path}.state", ASSURANCE_STATES),
        reason=_string(body["reason"], f"{path}.reason"),
        provider_count=_integer(
            body["provider_count"], f"{path}.provider_count", minimum=1
        ),
        usable_provider_count=_integer(
            body["usable_provider_count"], f"{path}.usable_provider_count"
        ),
        independent_group_count=_integer(
            body["independent_group_count"],
            f"{path}.independent_group_count",
            minimum=1,
        ),
        same_object_response_refs=_string_tuple(
            body["same_object_response_refs"],
            f"{path}.same_object_response_refs",
        ),
        different_objects_response_refs=_string_tuple(
            body["different_objects_response_refs"],
            f"{path}.different_objects_response_refs",
        ),
        unknown_response_refs=_string_tuple(
            body["unknown_response_refs"], f"{path}.unknown_response_refs"
        ),
        diagnostics=_diagnostics(body["diagnostics"], f"{path}.diagnostics"),
    )
    if result.usable_provider_count > result.provider_count:
        _fail(path, "usable_provider_count cannot exceed provider_count")
    if result.independent_group_count > result.provider_count:
        _fail(path, "independent_group_count cannot exceed provider_count")
    return result


def load_trajectory_identity_adjudication(
    payload: Mapping[str, object],
) -> TrajectoryIdentityAdjudication:
    """Strictly load one serialized GT38 identity adjudication artifact."""

    root = _mapping(payload, "Trajectory Identity Adjudication")
    _exact_fields(
        root,
        "artifact root",
        required={"trajectory_identity_adjudication"},
    )
    body = _mapping(
        root["trajectory_identity_adjudication"],
        "trajectory_identity_adjudication",
    )
    required = {
        "adjudication_version",
        "adjudication_id",
        "created_at",
        "candidate_result_ref",
        "verification_request_ref",
        "assurance_profile_ref",
        "provider_refs",
        "response_refs",
        "identity_pair",
        "candidate_state",
        "requested_verdict",
        "policy_result",
        "adjudication_state",
        "adjudication_reason",
        "candidate_alignment",
        "identity_merge_recommendation",
        "next_action",
        "candidate_binding_verified",
        "verification_bindings_verified",
        "independent_evidence_satisfied",
        "external_identity_verified_by_core",
        "identity_merge_performed",
        "subject_refs_mutated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    }
    _exact_fields(body, "trajectory_identity_adjudication", required=required)
    if body["adjudication_version"] != TRAJECTORY_IDENTITY_ADJUDICATION_FORMAT_VERSION:
        _fail(
            "trajectory_identity_adjudication.adjudication_version",
            f"must be {TRAJECTORY_IDENTITY_ADJUDICATION_FORMAT_VERSION!r}",
        )

    adjudication = TrajectoryIdentityAdjudication(
        adjudication_id=_string(
            body["adjudication_id"],
            "trajectory_identity_adjudication.adjudication_id",
        ),
        created_at=_timestamp(
            body["created_at"], "trajectory_identity_adjudication.created_at"
        ),
        candidate_result_ref=_load_candidate_ref(
            body["candidate_result_ref"],
            "trajectory_identity_adjudication.candidate_result_ref",
        ),
        verification_request_ref=_load_request_ref(
            body["verification_request_ref"],
            "trajectory_identity_adjudication.verification_request_ref",
        ),
        assurance_profile_ref=_load_profile_ref(
            body["assurance_profile_ref"],
            "trajectory_identity_adjudication.assurance_profile_ref",
        ),
        provider_refs=_load_provider_refs(
            body["provider_refs"], "trajectory_identity_adjudication.provider_refs"
        ),
        response_refs=_load_response_refs(
            body["response_refs"], "trajectory_identity_adjudication.response_refs"
        ),
        identity_pair=_load_identity_pair(
            body["identity_pair"], "trajectory_identity_adjudication.identity_pair"
        ),
        candidate_state=_enum(
            body["candidate_state"],
            "trajectory_identity_adjudication.candidate_state",
            CANDIDATE_STATES,
        ),
        requested_verdict=_enum(
            body["requested_verdict"],
            "trajectory_identity_adjudication.requested_verdict",
            frozenset({"same_object", "different_objects"}),
        ),
        policy_result=_load_policy_result(
            body["policy_result"],
            "trajectory_identity_adjudication.policy_result",
        ),
        adjudication_state=_enum(
            body["adjudication_state"],
            "trajectory_identity_adjudication.adjudication_state",
            ADJUDICATION_STATES,
        ),
        adjudication_reason=_string(
            body["adjudication_reason"],
            "trajectory_identity_adjudication.adjudication_reason",
        ),
        candidate_alignment=_enum(
            body["candidate_alignment"],
            "trajectory_identity_adjudication.candidate_alignment",
            CANDIDATE_ALIGNMENT_STATES,
        ),
        identity_merge_recommendation=_enum(
            body["identity_merge_recommendation"],
            "trajectory_identity_adjudication.identity_merge_recommendation",
            MERGE_RECOMMENDATIONS,
        ),
        next_action=_enum(
            body["next_action"],
            "trajectory_identity_adjudication.next_action",
            NEXT_ACTIONS,
        ),
        candidate_binding_verified=_boolean(
            body["candidate_binding_verified"],
            "trajectory_identity_adjudication.candidate_binding_verified",
        ),
        verification_bindings_verified=_boolean(
            body["verification_bindings_verified"],
            "trajectory_identity_adjudication.verification_bindings_verified",
        ),
        independent_evidence_satisfied=_boolean(
            body["independent_evidence_satisfied"],
            "trajectory_identity_adjudication.independent_evidence_satisfied",
        ),
        external_identity_verified_by_core=_boolean(
            body["external_identity_verified_by_core"],
            "trajectory_identity_adjudication.external_identity_verified_by_core",
        ),
        identity_merge_performed=_boolean(
            body["identity_merge_performed"],
            "trajectory_identity_adjudication.identity_merge_performed",
        ),
        subject_refs_mutated=_boolean(
            body["subject_refs_mutated"],
            "trajectory_identity_adjudication.subject_refs_mutated",
        ),
        production_output_released=_boolean(
            body["production_output_released"],
            "trajectory_identity_adjudication.production_output_released",
        ),
        action_authorized=_boolean(
            body["action_authorized"],
            "trajectory_identity_adjudication.action_authorized",
        ),
        action_executed=_boolean(
            body["action_executed"],
            "trajectory_identity_adjudication.action_executed",
        ),
    )

    if len(adjudication.provider_refs) != len(adjudication.response_refs):
        _fail(
            "trajectory_identity_adjudication",
            "provider_refs and response_refs must have equal length",
        )
    provider_ids = {item.provider_id for item in adjudication.provider_refs}
    response_provider_ids = {item.provider_id for item in adjudication.response_refs}
    if provider_ids != response_provider_ids:
        _fail(
            "trajectory_identity_adjudication.response_refs",
            "must cover exactly the supplied provider IDs",
        )
    request_ids = {item.request_id for item in adjudication.response_refs}
    if request_ids != {adjudication.verification_request_ref.request_id}:
        _fail(
            "trajectory_identity_adjudication.response_refs",
            "all responses must bind the declared request_id",
        )
    response_ref_ids = {item.ref_id for item in adjudication.response_refs}
    classified_ref_ids = (
        set(adjudication.policy_result.same_object_response_refs)
        | set(adjudication.policy_result.different_objects_response_refs)
        | set(adjudication.policy_result.unknown_response_refs)
    )
    if classified_ref_ids != response_ref_ids:
        _fail(
            "trajectory_identity_adjudication.policy_result",
            "verdict reference arrays must partition all response refs",
        )
    if (
        set(adjudication.policy_result.same_object_response_refs)
        & set(adjudication.policy_result.different_objects_response_refs)
        or set(adjudication.policy_result.same_object_response_refs)
        & set(adjudication.policy_result.unknown_response_refs)
        or set(adjudication.policy_result.different_objects_response_refs)
        & set(adjudication.policy_result.unknown_response_refs)
    ):
        _fail(
            "trajectory_identity_adjudication.policy_result",
            "verdict reference arrays must be disjoint",
        )
    verdict_by_ref = {item.ref_id: item.verdict for item in adjudication.response_refs}
    for ref_id in adjudication.policy_result.same_object_response_refs:
        if verdict_by_ref[ref_id] != "same_object":
            _fail(
                "trajectory_identity_adjudication.policy_result.same_object_response_refs",
                f"{ref_id!r} does not have same_object verdict",
            )
    for ref_id in adjudication.policy_result.different_objects_response_refs:
        if verdict_by_ref[ref_id] != "different_objects":
            _fail(
                "trajectory_identity_adjudication.policy_result.different_objects_response_refs",
                f"{ref_id!r} does not have different_objects verdict",
            )
    for ref_id in adjudication.policy_result.unknown_response_refs:
        if verdict_by_ref[ref_id] != "unknown":
            _fail(
                "trajectory_identity_adjudication.policy_result.unknown_response_refs",
                f"{ref_id!r} does not have unknown verdict",
            )
    if adjudication.policy_result.provider_count != len(adjudication.provider_refs):
        _fail(
            "trajectory_identity_adjudication.policy_result.provider_count",
            "must equal provider_refs length",
        )

    if adjudication.adjudication_state == "same_object_confirmed":
        expected = (
            "recommend_identity_merge_review",
            "review_identity_merge",
            True,
        )
        if not adjudication.policy_result.same_object_response_refs:
            _fail(
                "trajectory_identity_adjudication.policy_result",
                "same_object_confirmed requires same-object responses",
            )
        if (
            adjudication.policy_result.different_objects_response_refs
            or adjudication.policy_result.unknown_response_refs
            or adjudication.policy_result.state != "verified"
        ):
            _fail(
                "trajectory_identity_adjudication.policy_result",
                "same_object_confirmed requires verified unanimous same-object evidence",
            )
    elif adjudication.adjudication_state == "different_objects_confirmed":
        expected = ("recommend_keep_separate", "retain_separate_identities", True)
        if not adjudication.policy_result.different_objects_response_refs:
            _fail(
                "trajectory_identity_adjudication.policy_result",
                "different_objects_confirmed requires different-object responses",
            )
        if (
            adjudication.policy_result.same_object_response_refs
            or adjudication.policy_result.unknown_response_refs
            or adjudication.policy_result.state != "verified"
        ):
            _fail(
                "trajectory_identity_adjudication.policy_result",
                "different_objects_confirmed requires verified unanimous different-object evidence",
            )
    else:
        expected = ("request_more_evidence", "request_identity_evidence", False)

    if (
        adjudication.identity_merge_recommendation,
        adjudication.next_action,
        adjudication.independent_evidence_satisfied,
    ) != expected:
        _fail(
            "trajectory_identity_adjudication",
            "adjudication state, recommendation, next action, and assurance flag disagree",
        )
    expected_alignment = _derive_candidate_alignment(
        adjudication.candidate_state, adjudication.adjudication_state
    )
    if adjudication.candidate_alignment != expected_alignment:
        _fail(
            "trajectory_identity_adjudication.candidate_alignment",
            f"must be {expected_alignment!r} for the declared states",
        )
    if not adjudication.candidate_binding_verified:
        _fail(
            "trajectory_identity_adjudication.candidate_binding_verified",
            "must be true for a produced adjudication artifact",
        )
    if not adjudication.verification_bindings_verified:
        _fail(
            "trajectory_identity_adjudication.verification_bindings_verified",
            "must be true for a produced adjudication artifact",
        )
    for field in (
        "external_identity_verified_by_core",
        "identity_merge_performed",
        "subject_refs_mutated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        if getattr(adjudication, field):
            _fail(f"trajectory_identity_adjudication.{field}", "must be false")
    return adjudication


def validate_trajectory_identity_adjudication_bindings(
    adjudication: TrajectoryIdentityAdjudication,
    *,
    candidate_result_bytes: bytes,
    verification_request_bytes: bytes,
    assurance_profile_bytes: bytes,
    provider_descriptor_bytes: Sequence[bytes],
    verification_response_bytes: Sequence[bytes],
) -> None:
    """Rebuild from exact bytes and require semantic equality with the artifact."""

    rebuilt = build_trajectory_identity_adjudication(
        adjudication_id=adjudication.adjudication_id,
        created_at=adjudication.created_at,
        candidate_result_bytes=candidate_result_bytes,
        verification_request_bytes=verification_request_bytes,
        assurance_profile_bytes=assurance_profile_bytes,
        provider_descriptor_bytes=provider_descriptor_bytes,
        verification_response_bytes=verification_response_bytes,
    )
    if rebuilt.to_dict() != adjudication.to_dict():
        _fail(
            "trajectory_identity_adjudication",
            "does not match the result rebuilt from exact bound artifacts",
        )


__all__ = [
    "TRAJECTORY_IDENTITY_ADJUDICATION_ARTIFACT_ID",
    "TRAJECTORY_IDENTITY_ADJUDICATION_SCHEMA_ID",
    "TRAJECTORY_IDENTITY_ADJUDICATION_SCHEMA_VERSION",
    "TRAJECTORY_IDENTITY_ADJUDICATION_FORMAT_VERSION",
    "TrajectoryIdentityAdjudicationError",
    "IdentityCandidateResultRef",
    "IdentityVerificationRequestRef",
    "IdentityAssuranceProfileRef",
    "IdentityProviderRef",
    "IdentityResponseRef",
    "IdentityPair",
    "IdentityPolicyResult",
    "TrajectoryIdentityAdjudication",
    "build_trajectory_identity_adjudication",
    "load_trajectory_identity_adjudication",
    "validate_trajectory_identity_adjudication_bindings",
]
