"""Bounded Observation merge for explicit GeoTask World State snapshots.

Observation Merge v0.1 applies every claim from one or more exact Observation
artifacts to an existing object attribute or existing relation in one immutable
base World State. The caller must provide an explicit claim-to-target mapping.
Core does not infer object identity, create objects or relations, resolve
conflicts, verify claim truth, compute a State Transition, propagate impact, or
authorize action.

A successful merge emits a new immutable World State revision and one
``geotask.observation-merge-result`` artifact binding the exact base,
Observation, and successor bytes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Mapping, Sequence

from geotask_core.v1.observation import (
    OBSERVATION_ARTIFACT_ID,
    OBSERVATION_SCHEMA_VERSION,
    Observation,
    WorldClaim,
    load_observation,
)
from geotask_core.v1.world_state import (
    WORLD_STATE_ARTIFACT_ID,
    WORLD_STATE_SCHEMA_ID,
    WORLD_STATE_SCHEMA_VERSION,
    WorldState,
    load_world_state,
)


OBSERVATION_MERGE_RESULT_ARTIFACT_ID = "geotask.observation-merge-result"
OBSERVATION_MERGE_RESULT_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-observation-merge-result-v0.1.schema.json"
)
OBSERVATION_MERGE_RESULT_SCHEMA_VERSION = "0.1"
OBSERVATION_MERGE_RESULT_FORMAT_VERSION = "0.1"
OBSERVATION_MERGE_STATES = frozenset({"completed"})
OBSERVATION_MERGE_APPLICATION_STATES = frozenset({"applied"})
OBSERVATION_MERGE_TARGET_KINDS = frozenset({"attribute", "relation"})
OBSERVATION_MERGE_NEXT_ACTIONS = frozenset({"compute_state_transition"})


class ObservationMergeError(ValueError):
    """Raised when bounded Observation merge or result validation fails."""


def _fail(path: str, message: str) -> None:
    raise ObservationMergeError(f"{path}: {message}")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _exact_fields(
    value: Mapping[str, object],
    path: str,
    *,
    required: AbstractSet[str],
    optional: AbstractSet[str] = frozenset(),
) -> None:
    missing = sorted(required - set(value))
    if missing:
        _fail(path, "missing required fields: " + ", ".join(missing))
    unknown = sorted(set(value) - required - optional)
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
    if not isinstance(value, bool):
        _fail(path, "must be a boolean")
    return value


def _positive_integer(value: object, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        _fail(path, "must be an integer greater than or equal to 1")
    return value


def _timestamp(value: object, path: str) -> tuple[str, datetime]:
    text = _string(value, path)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ObservationMergeError(f"{path}: must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must include a timezone offset")
    return text, parsed


def _sha256(value: object, path: str) -> str:
    text = _string(value, path)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        _fail(path, "must be a lowercase 64-character SHA-256 hexadecimal digest")
    return text


def _string_list(
    value: object,
    path: str,
    *,
    non_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array of non-empty strings")
    if non_empty and not value:
        _fail(path, "must contain at least one item")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _string(item, f"{path}[{index}]")
        if text in seen:
            _fail(f"{path}[{index}]", f"duplicates {text!r}")
        seen.add(text)
        items.append(text)
    return tuple(sorted(items))


def _json_value(value: object, path: str) -> object:
    if value is None or isinstance(value, (str, bool)):
        return copy.deepcopy(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            _fail(path, "must not contain a non-finite number")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(path, "object keys must be strings")
            normalized[key] = _json_value(item, f"{path}.{key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    _fail(path, "must be a JSON-compatible value")


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def _hash_bytes(content: bytes) -> str:
    if not isinstance(content, bytes):
        _fail("content", "must be bytes")
    return hashlib.sha256(content).hexdigest()


def _json_mapping_from_bytes(content: bytes, path: str) -> Mapping[str, object]:
    if not isinstance(content, bytes):
        _fail(path, "must be bytes")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ObservationMergeError(f"{path}: must be UTF-8 JSON bytes") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ObservationMergeError(f"{path}: must contain valid JSON") from exc
    return _mapping(payload, path)


def _decode_pointer(pointer: str, path: str) -> tuple[str, ...]:
    if not pointer.startswith("/") or pointer.endswith("/"):
        _fail(path, "must be a non-root identity JSON Pointer")
    return tuple(
        segment.replace("~1", "/").replace("~0", "~")
        for segment in pointer.split("/")[1:]
    )


def _effective_claim_observed_at(observation: Observation, claim: WorldClaim) -> str:
    return claim.observed_at or observation.observed_at


@dataclass(frozen=True)
class ObservationMergeInstruction:
    """Explicit mapping from one Observation claim to one existing state target."""

    observation_id: str
    claim_id: str
    target_path: str


@dataclass(frozen=True)
class ObservationMergeWorldStateRef:
    ref_id: str
    artifact_id: str
    schema_version: str
    world_state_id: str
    revision: int
    as_of: str
    materialized_at: str
    semantic_fingerprint: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ref_id": self.ref_id,
            "artifact_id": self.artifact_id,
            "schema_version": self.schema_version,
            "world_state_id": self.world_state_id,
            "revision": self.revision,
            "as_of": self.as_of,
            "materialized_at": self.materialized_at,
            "semantic_fingerprint": self.semantic_fingerprint,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ObservationMergeObservationRef:
    ref_id: str
    artifact_id: str
    schema_version: str
    observation_id: str
    observed_at: str
    received_at: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ref_id": self.ref_id,
            "artifact_id": self.artifact_id,
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "observed_at": self.observed_at,
            "received_at": self.received_at,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class AppliedObservationClaim:
    application_id: str
    observation_ref: str
    claim_id: str
    target_path: str
    target_kind: str
    state: str
    before: object
    after: object

    def to_dict(self) -> dict[str, object]:
        return {
            "application_id": self.application_id,
            "observation_ref": self.observation_ref,
            "claim_id": self.claim_id,
            "target_path": self.target_path,
            "target_kind": self.target_kind,
            "state": self.state,
            "before": copy.deepcopy(self.before),
            "after": copy.deepcopy(self.after),
        }


@dataclass(frozen=True)
class ObservationMergeResult:
    merge_id: str
    created_at: str
    state: str
    reason: str
    base_world_state: ObservationMergeWorldStateRef
    observation_refs: tuple[ObservationMergeObservationRef, ...]
    successor_world_state: ObservationMergeWorldStateRef
    applied_claims: tuple[AppliedObservationClaim, ...]
    preserved_observation_refs: tuple[str, ...]
    added_observation_refs: tuple[str, ...]
    preserved_evidence_refs: tuple[str, ...]
    added_evidence_refs: tuple[str, ...]
    next_action: str
    state_transition_computed: bool
    impact_propagation_executed: bool
    reevaluation_executed: bool
    outputs_released: bool
    external_truth_verified: bool
    action_authorized: bool
    action_executed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_merge_result": {
                "schema_id": OBSERVATION_MERGE_RESULT_SCHEMA_ID,
                "schema_version": OBSERVATION_MERGE_RESULT_SCHEMA_VERSION,
                "merge_id": self.merge_id,
                "created_at": self.created_at,
                "state": self.state,
                "reason": self.reason,
                "base_world_state": self.base_world_state.to_dict(),
                "observation_refs": [
                    item.to_dict()
                    for item in sorted(
                        self.observation_refs, key=lambda item: item.observation_id
                    )
                ],
                "successor_world_state": self.successor_world_state.to_dict(),
                "applied_claims": [
                    item.to_dict()
                    for item in sorted(
                        self.applied_claims, key=lambda item: item.application_id
                    )
                ],
                "preserved_observation_refs": sorted(
                    self.preserved_observation_refs
                ),
                "added_observation_refs": sorted(self.added_observation_refs),
                "preserved_evidence_refs": sorted(self.preserved_evidence_refs),
                "added_evidence_refs": sorted(self.added_evidence_refs),
                "next_action": self.next_action,
                "state_transition_computed": self.state_transition_computed,
                "impact_propagation_executed": self.impact_propagation_executed,
                "reevaluation_executed": self.reevaluation_executed,
                "outputs_released": self.outputs_released,
                "external_truth_verified": self.external_truth_verified,
                "action_authorized": self.action_authorized,
                "action_executed": self.action_executed,
            }
        }

    def semantic_fingerprint(self) -> str:
        raw = json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ObservationMergeOutput:
    world_state: WorldState
    result: ObservationMergeResult
    world_state_bytes: bytes
    result_bytes: bytes


def serialize_observation_merge_world_state(world_state: WorldState) -> bytes:
    return _canonical_bytes(world_state.to_dict())


def serialize_observation_merge_result(result: ObservationMergeResult) -> bytes:
    return _canonical_bytes(result.to_dict())


def _world_state_ref(
    world_state: WorldState,
    content: bytes,
    *,
    ref_id: str,
) -> ObservationMergeWorldStateRef:
    return ObservationMergeWorldStateRef(
        ref_id=ref_id,
        artifact_id=WORLD_STATE_ARTIFACT_ID,
        schema_version=WORLD_STATE_SCHEMA_VERSION,
        world_state_id=world_state.world_state_id,
        revision=world_state.revision,
        as_of=world_state.as_of,
        materialized_at=world_state.materialized_at,
        semantic_fingerprint=world_state.semantic_fingerprint(),
        content_sha256=_hash_bytes(content),
    )


def _observation_ref(
    observation: Observation,
    content: bytes,
) -> ObservationMergeObservationRef:
    return ObservationMergeObservationRef(
        ref_id=f"observation:{observation.observation_id}",
        artifact_id=OBSERVATION_ARTIFACT_ID,
        schema_version=OBSERVATION_SCHEMA_VERSION,
        observation_id=observation.observation_id,
        observed_at=observation.observed_at,
        received_at=observation.received_at,
        content_sha256=_hash_bytes(content),
    )


def _find_claim(observation: Observation, claim_id: str) -> WorldClaim:
    claim = next((item for item in observation.claims if item.id == claim_id), None)
    if claim is None:
        _fail(
            "instructions.claim_id",
            f"Observation {observation.observation_id!r} has no claim {claim_id!r}",
        )
    return claim


def _find_object(body: Mapping[str, object], object_id: str, path: str) -> dict[str, object]:
    objects = body.get("objects")
    if not isinstance(objects, list):
        _fail(path, "World State objects are unavailable")
    item = next(
        (
            candidate
            for candidate in objects
            if isinstance(candidate, dict) and candidate.get("id") == object_id
        ),
        None,
    )
    if item is None:
        _fail(path, f"references unknown object {object_id!r}")
    return item


def _find_attribute(
    body: Mapping[str, object], object_id: str, name: str, path: str
) -> dict[str, object]:
    item = _find_object(body, object_id, path)
    attributes = item.get("attributes")
    if not isinstance(attributes, list):
        _fail(path, "object attributes are unavailable")
    attribute = next(
        (
            candidate
            for candidate in attributes
            if isinstance(candidate, dict) and candidate.get("name") == name
        ),
        None,
    )
    if attribute is None:
        _fail(path, f"references unknown attribute {name!r}")
    return attribute


def _find_relation(body: Mapping[str, object], relation_id: str, path: str) -> dict[str, object]:
    relations = body.get("relations")
    if not isinstance(relations, list):
        _fail(path, "World State relations are unavailable")
    relation = next(
        (
            candidate
            for candidate in relations
            if isinstance(candidate, dict) and candidate.get("id") == relation_id
        ),
        None,
    )
    if relation is None:
        _fail(path, f"references unknown relation {relation_id!r}")
    return relation


def _claim_projection(
    *,
    body: dict[str, object],
    observation: Observation,
    claim: WorldClaim,
    target_path: str,
    successor_as_of: datetime,
) -> tuple[str, dict[str, object], dict[str, object]]:
    segments = _decode_pointer(target_path, "instructions.target_path")
    observed_text = _effective_claim_observed_at(observation, claim)
    _, claim_observed_at = _timestamp(observed_text, "claim.observed_at")
    if claim_observed_at > successor_as_of:
        _fail(
            "instructions.target_path",
            "claim observation time must not be later than successor_as_of",
        )

    if len(segments) == 4 and segments[0] == "objects" and segments[2] == "attributes":
        object_id = segments[1]
        attribute_name = segments[3]
        if claim.object_ref is not None:
            _fail(
                "instructions.target_path",
                "attribute targets require a claim without object_ref",
            )
        if claim.subject_ref != object_id:
            _fail(
                "instructions.target_path",
                f"object identity {object_id!r} disagrees with claim subject_ref {claim.subject_ref!r}",
            )
        if claim.predicate != attribute_name:
            _fail(
                "instructions.target_path",
                f"attribute name {attribute_name!r} disagrees with claim predicate {claim.predicate!r}",
            )
        target = _find_attribute(body, object_id, attribute_name, target_path)
        before = copy.deepcopy(target)
        after: dict[str, object] = {
            "name": attribute_name,
            "value": copy.deepcopy(claim.value),
            "basis": claim.basis,
            "verification_status": "asserted",
            "valid_from": observed_text,
            "observation_refs": [observation.observation_id],
            "evidence_refs": sorted(claim.evidence_refs),
        }
        if claim.valid_until is not None:
            after["valid_until"] = claim.valid_until
        if claim.uncertainty is not None:
            after["uncertainty"] = claim.uncertainty.to_dict()
        target.clear()
        target.update(copy.deepcopy(after))
        return "attribute", before, after

    if len(segments) == 2 and segments[0] == "relations":
        relation_id = segments[1]
        if claim.object_ref is None:
            _fail(
                "instructions.target_path",
                "relation targets require claim.object_ref",
            )
        target = _find_relation(body, relation_id, target_path)
        for field, actual, expected in (
            ("subject_ref", target.get("subject_ref"), claim.subject_ref),
            ("predicate", target.get("predicate"), claim.predicate),
            ("object_ref", target.get("object_ref"), claim.object_ref),
        ):
            if actual != expected:
                _fail(
                    "instructions.target_path",
                    f"relation {field} {actual!r} disagrees with claim value {expected!r}",
                )
        before = copy.deepcopy(target)
        after = {
            "id": relation_id,
            "subject_ref": claim.subject_ref,
            "predicate": claim.predicate,
            "object_ref": claim.object_ref,
            "value": copy.deepcopy(claim.value),
            "basis": claim.basis,
            "verification_status": "asserted",
            "valid_from": observed_text,
            "observation_refs": [observation.observation_id],
            "evidence_refs": sorted(claim.evidence_refs),
        }
        if claim.valid_until is not None:
            after["valid_until"] = claim.valid_until
        if claim.uncertainty is not None:
            after["uncertainty"] = claim.uncertainty.to_dict()
        target.clear()
        target.update(copy.deepcopy(after))
        return "relation", before, after

    _fail(
        "instructions.target_path",
        "v0.1 targets must be /objects/<id>/attributes/<name> or /relations/<id>",
    )


def _load_world_state_ref(
    value: object, path: str
) -> tuple[ObservationMergeWorldStateRef, datetime, datetime]:
    ref = _mapping(value, path)
    _exact_fields(
        ref,
        path,
        required={
            "ref_id",
            "artifact_id",
            "schema_version",
            "world_state_id",
            "revision",
            "as_of",
            "materialized_at",
            "semantic_fingerprint",
            "content_sha256",
        },
    )
    if ref["artifact_id"] != WORLD_STATE_ARTIFACT_ID:
        _fail(f"{path}.artifact_id", f"must equal {WORLD_STATE_ARTIFACT_ID!r}")
    if ref["schema_version"] != WORLD_STATE_SCHEMA_VERSION:
        _fail(
            f"{path}.schema_version",
            f"must equal {WORLD_STATE_SCHEMA_VERSION!r}",
        )
    as_of_text, as_of = _timestamp(ref["as_of"], f"{path}.as_of")
    materialized_text, materialized_at = _timestamp(
        ref["materialized_at"], f"{path}.materialized_at"
    )
    if materialized_at < as_of:
        _fail(f"{path}.materialized_at", "must not precede as_of")
    return (
        ObservationMergeWorldStateRef(
            ref_id=_string(ref["ref_id"], f"{path}.ref_id"),
            artifact_id=WORLD_STATE_ARTIFACT_ID,
            schema_version=WORLD_STATE_SCHEMA_VERSION,
            world_state_id=_string(ref["world_state_id"], f"{path}.world_state_id"),
            revision=_positive_integer(ref["revision"], f"{path}.revision"),
            as_of=as_of_text,
            materialized_at=materialized_text,
            semantic_fingerprint=_sha256(
                ref["semantic_fingerprint"], f"{path}.semantic_fingerprint"
            ),
            content_sha256=_sha256(ref["content_sha256"], f"{path}.content_sha256"),
        ),
        as_of,
        materialized_at,
    )


def _load_observation_ref(
    value: object, path: str
) -> tuple[ObservationMergeObservationRef, datetime, datetime]:
    ref = _mapping(value, path)
    _exact_fields(
        ref,
        path,
        required={
            "ref_id",
            "artifact_id",
            "schema_version",
            "observation_id",
            "observed_at",
            "received_at",
            "content_sha256",
        },
    )
    if ref["artifact_id"] != OBSERVATION_ARTIFACT_ID:
        _fail(f"{path}.artifact_id", f"must equal {OBSERVATION_ARTIFACT_ID!r}")
    if ref["schema_version"] != OBSERVATION_SCHEMA_VERSION:
        _fail(
            f"{path}.schema_version",
            f"must equal {OBSERVATION_SCHEMA_VERSION!r}",
        )
    observed_text, observed_at = _timestamp(ref["observed_at"], f"{path}.observed_at")
    received_text, received_at = _timestamp(ref["received_at"], f"{path}.received_at")
    if received_at < observed_at:
        _fail(f"{path}.received_at", "must not precede observed_at")
    observation_id = _string(ref["observation_id"], f"{path}.observation_id")
    expected_ref_id = f"observation:{observation_id}"
    ref_id = _string(ref["ref_id"], f"{path}.ref_id")
    if ref_id != expected_ref_id:
        _fail(f"{path}.ref_id", f"must equal {expected_ref_id!r}")
    return (
        ObservationMergeObservationRef(
            ref_id=ref_id,
            artifact_id=OBSERVATION_ARTIFACT_ID,
            schema_version=OBSERVATION_SCHEMA_VERSION,
            observation_id=observation_id,
            observed_at=observed_text,
            received_at=received_text,
            content_sha256=_sha256(ref["content_sha256"], f"{path}.content_sha256"),
        ),
        observed_at,
        received_at,
    )


def _load_applied_claim(value: object, index: int) -> AppliedObservationClaim:
    path = f"observation_merge_result.applied_claims[{index}]"
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={
            "application_id",
            "observation_ref",
            "claim_id",
            "target_path",
            "target_kind",
            "state",
            "before",
            "after",
        },
    )
    observation_ref = _string(item["observation_ref"], f"{path}.observation_ref")
    claim_id = _string(item["claim_id"], f"{path}.claim_id")
    expected_application_id = f"{observation_ref.removeprefix('observation:')}#{claim_id}"
    application_id = _string(item["application_id"], f"{path}.application_id")
    if application_id != expected_application_id:
        _fail(f"{path}.application_id", f"must equal {expected_application_id!r}")
    before = _json_value(item["before"], f"{path}.before")
    after = _json_value(item["after"], f"{path}.after")
    if before == after:
        _fail(path, "before and after must differ")
    target_kind = _enum(
        item["target_kind"], f"{path}.target_kind", OBSERVATION_MERGE_TARGET_KINDS
    )
    target_path = _string(item["target_path"], f"{path}.target_path")
    segments = _decode_pointer(target_path, f"{path}.target_path")
    if target_kind == "attribute" and not (
        len(segments) == 4 and segments[0] == "objects" and segments[2] == "attributes"
    ):
        _fail(f"{path}.target_path", "attribute target_kind requires an attribute path")
    if target_kind == "relation" and not (
        len(segments) == 2 and segments[0] == "relations"
    ):
        _fail(f"{path}.target_path", "relation target_kind requires a relation path")
    return AppliedObservationClaim(
        application_id=application_id,
        observation_ref=observation_ref,
        claim_id=claim_id,
        target_path=target_path,
        target_kind=target_kind,
        state=_enum(
            item["state"],
            f"{path}.state",
            OBSERVATION_MERGE_APPLICATION_STATES,
        ),
        before=before,
        after=after,
    )


def load_observation_merge_result(
    payload: Mapping[str, object],
) -> ObservationMergeResult:
    """Strictly load one Observation Merge Result v0.1 artifact."""

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"observation_merge_result"})
    body = _mapping(root["observation_merge_result"], "observation_merge_result")
    _exact_fields(
        body,
        "observation_merge_result",
        required={
            "schema_id",
            "schema_version",
            "merge_id",
            "created_at",
            "state",
            "reason",
            "base_world_state",
            "observation_refs",
            "successor_world_state",
            "applied_claims",
            "preserved_observation_refs",
            "added_observation_refs",
            "preserved_evidence_refs",
            "added_evidence_refs",
            "next_action",
            "state_transition_computed",
            "impact_propagation_executed",
            "reevaluation_executed",
            "outputs_released",
            "external_truth_verified",
            "action_authorized",
            "action_executed",
        },
    )
    if body["schema_id"] != OBSERVATION_MERGE_RESULT_SCHEMA_ID:
        _fail(
            "observation_merge_result.schema_id",
            f"must equal {OBSERVATION_MERGE_RESULT_SCHEMA_ID!r}",
        )
    if body["schema_version"] != OBSERVATION_MERGE_RESULT_SCHEMA_VERSION:
        _fail(
            "observation_merge_result.schema_version",
            f"must equal {OBSERVATION_MERGE_RESULT_SCHEMA_VERSION!r}",
        )

    created_text, created_at = _timestamp(
        body["created_at"], "observation_merge_result.created_at"
    )
    base_ref, base_as_of, _ = _load_world_state_ref(
        body["base_world_state"], "observation_merge_result.base_world_state"
    )
    successor_ref, successor_as_of, successor_materialized = _load_world_state_ref(
        body["successor_world_state"], "observation_merge_result.successor_world_state"
    )
    if successor_ref.world_state_id != base_ref.world_state_id:
        _fail(
            "observation_merge_result.successor_world_state.world_state_id",
            "must equal base World State ID",
        )
    if successor_ref.revision != base_ref.revision + 1:
        _fail(
            "observation_merge_result.successor_world_state.revision",
            "must equal base revision plus one",
        )
    if successor_as_of < base_as_of:
        _fail(
            "observation_merge_result.successor_world_state.as_of",
            "must not precede base as_of",
        )
    if created_at < successor_materialized:
        _fail(
            "observation_merge_result.created_at",
            "must not precede successor materialization",
        )
    if successor_ref.content_sha256 == base_ref.content_sha256:
        _fail(
            "observation_merge_result.successor_world_state.content_sha256",
            "must differ from base World State bytes",
        )

    raw_refs = body["observation_refs"]
    if not isinstance(raw_refs, Sequence) or isinstance(raw_refs, (str, bytes, bytearray)):
        _fail("observation_merge_result.observation_refs", "must be a non-empty array")
    if not raw_refs:
        _fail("observation_merge_result.observation_refs", "must contain at least one item")
    observation_refs: list[ObservationMergeObservationRef] = []
    observation_ref_ids: set[str] = set()
    observation_ids: set[str] = set()
    for index, raw in enumerate(raw_refs):
        ref, observed_at, received_at = _load_observation_ref(
            raw, f"observation_merge_result.observation_refs[{index}]"
        )
        if ref.ref_id in observation_ref_ids:
            _fail(
                f"observation_merge_result.observation_refs[{index}].ref_id",
                f"duplicates {ref.ref_id!r}",
            )
        if ref.observation_id in observation_ids:
            _fail(
                f"observation_merge_result.observation_refs[{index}].observation_id",
                f"duplicates {ref.observation_id!r}",
            )
        if observed_at > successor_as_of:
            _fail(
                f"observation_merge_result.observation_refs[{index}].observed_at",
                "must not be later than successor as_of",
            )
        if received_at > successor_materialized:
            _fail(
                f"observation_merge_result.observation_refs[{index}].received_at",
                "must not be later than successor materialization",
            )
        observation_ref_ids.add(ref.ref_id)
        observation_ids.add(ref.observation_id)
        observation_refs.append(ref)

    raw_claims = body["applied_claims"]
    if not isinstance(raw_claims, Sequence) or isinstance(
        raw_claims, (str, bytes, bytearray)
    ):
        _fail("observation_merge_result.applied_claims", "must be a non-empty array")
    if not raw_claims:
        _fail("observation_merge_result.applied_claims", "must contain at least one item")
    applications: list[AppliedObservationClaim] = []
    application_ids: set[str] = set()
    claim_keys: set[tuple[str, str]] = set()
    target_paths: set[str] = set()
    for index, raw in enumerate(raw_claims):
        application = _load_applied_claim(raw, index)
        if application.application_id in application_ids:
            _fail(
                f"observation_merge_result.applied_claims[{index}].application_id",
                f"duplicates {application.application_id!r}",
            )
        if application.observation_ref not in observation_ref_ids:
            _fail(
                f"observation_merge_result.applied_claims[{index}].observation_ref",
                f"references undeclared Observation ref {application.observation_ref!r}",
            )
        claim_key = (application.observation_ref, application.claim_id)
        if claim_key in claim_keys:
            _fail(
                f"observation_merge_result.applied_claims[{index}].claim_id",
                "duplicates an Observation claim application",
            )
        if application.target_path in target_paths:
            _fail(
                f"observation_merge_result.applied_claims[{index}].target_path",
                f"duplicates target path {application.target_path!r}",
            )
        application_ids.add(application.application_id)
        claim_keys.add(claim_key)
        target_paths.add(application.target_path)
        applications.append(application)

    preserved_observation_refs = _string_list(
        body["preserved_observation_refs"],
        "observation_merge_result.preserved_observation_refs",
    )
    added_observation_refs = _string_list(
        body["added_observation_refs"],
        "observation_merge_result.added_observation_refs",
        non_empty=True,
    )
    preserved_evidence_refs = _string_list(
        body["preserved_evidence_refs"],
        "observation_merge_result.preserved_evidence_refs",
    )
    added_evidence_refs = _string_list(
        body["added_evidence_refs"],
        "observation_merge_result.added_evidence_refs",
    )
    if set(preserved_observation_refs) & set(added_observation_refs):
        _fail(
            "observation_merge_result.added_observation_refs",
            "must not overlap preserved_observation_refs",
        )
    if set(preserved_evidence_refs) & set(added_evidence_refs):
        _fail(
            "observation_merge_result.added_evidence_refs",
            "must not overlap preserved_evidence_refs",
        )
    if set(added_observation_refs) != observation_ids - set(preserved_observation_refs):
        _fail(
            "observation_merge_result.added_observation_refs",
            "must equal merged Observation IDs not already preserved by the base snapshot",
        )

    boundary_fields = (
        "state_transition_computed",
        "impact_propagation_executed",
        "reevaluation_executed",
        "outputs_released",
        "external_truth_verified",
        "action_authorized",
        "action_executed",
    )
    boundaries: dict[str, bool] = {}
    for field in boundary_fields:
        value = _boolean(body[field], f"observation_merge_result.{field}")
        if value:
            _fail(
                f"observation_merge_result.{field}",
                "must be false in Observation Merge Result v0.1",
            )
        boundaries[field] = value

    return ObservationMergeResult(
        merge_id=_string(body["merge_id"], "observation_merge_result.merge_id"),
        created_at=created_text,
        state=_enum(
            body["state"], "observation_merge_result.state", OBSERVATION_MERGE_STATES
        ),
        reason=_string(body["reason"], "observation_merge_result.reason"),
        base_world_state=base_ref,
        observation_refs=tuple(
            sorted(observation_refs, key=lambda item: item.observation_id)
        ),
        successor_world_state=successor_ref,
        applied_claims=tuple(sorted(applications, key=lambda item: item.application_id)),
        preserved_observation_refs=preserved_observation_refs,
        added_observation_refs=added_observation_refs,
        preserved_evidence_refs=preserved_evidence_refs,
        added_evidence_refs=added_evidence_refs,
        next_action=_enum(
            body["next_action"],
            "observation_merge_result.next_action",
            OBSERVATION_MERGE_NEXT_ACTIONS,
        ),
        state_transition_computed=boundaries["state_transition_computed"],
        impact_propagation_executed=boundaries["impact_propagation_executed"],
        reevaluation_executed=boundaries["reevaluation_executed"],
        outputs_released=boundaries["outputs_released"],
        external_truth_verified=boundaries["external_truth_verified"],
        action_authorized=boundaries["action_authorized"],
        action_executed=boundaries["action_executed"],
    )


def merge_observations_into_world_state(
    *,
    merge_id: str,
    created_at: str,
    reason: str,
    base_world_state_bytes: bytes,
    observation_bytes: Sequence[bytes],
    instructions: Sequence[ObservationMergeInstruction],
    successor_as_of: str,
    successor_materialized_at: str,
) -> ObservationMergeOutput:
    """Apply every supplied Observation claim to one explicit existing target.

    The function consumes exact serialized inputs, validates every claim and
    target, and returns canonical successor/result bytes. Every claim in every
    supplied Observation must be mapped exactly once; every target may be written
    at most once.
    """

    merge_id = _string(merge_id, "merge_id")
    reason = _string(reason, "reason")
    created_text, created_at_dt = _timestamp(created_at, "created_at")
    successor_as_of_text, successor_as_of_dt = _timestamp(
        successor_as_of, "successor_as_of"
    )
    successor_materialized_text, successor_materialized_dt = _timestamp(
        successor_materialized_at, "successor_materialized_at"
    )
    if successor_materialized_dt < successor_as_of_dt:
        _fail("successor_materialized_at", "must not precede successor_as_of")
    if created_at_dt < successor_materialized_dt:
        _fail("created_at", "must not precede successor materialization")

    base_payload = _json_mapping_from_bytes(base_world_state_bytes, "base_world_state_bytes")
    try:
        base_world_state = load_world_state(base_payload)
    except ValueError as exc:
        raise ObservationMergeError(f"base_world_state_bytes: {exc}") from exc
    _, base_as_of_dt = _timestamp(base_world_state.as_of, "base_world_state.as_of")
    if successor_as_of_dt < base_as_of_dt:
        _fail("successor_as_of", "must not precede base World State as_of")

    if not isinstance(observation_bytes, Sequence) or isinstance(
        observation_bytes, (bytes, bytearray, str)
    ):
        _fail("observation_bytes", "must be a non-empty sequence of bytes")
    if not observation_bytes:
        _fail("observation_bytes", "must contain at least one Observation")
    observations: dict[str, Observation] = {}
    observation_content: dict[str, bytes] = {}
    for index, raw in enumerate(observation_bytes):
        payload = _json_mapping_from_bytes(raw, f"observation_bytes[{index}]")
        try:
            observation = load_observation(payload)
        except ValueError as exc:
            raise ObservationMergeError(f"observation_bytes[{index}]: {exc}") from exc
        if observation.observation_id in observations:
            _fail(
                f"observation_bytes[{index}]",
                f"duplicates Observation ID {observation.observation_id!r}",
            )
        _, observed_at = _timestamp(observation.observed_at, "observation.observed_at")
        _, received_at = _timestamp(observation.received_at, "observation.received_at")
        if observed_at > successor_as_of_dt:
            _fail(
                f"observation_bytes[{index}]",
                "Observation observed_at must not be later than successor_as_of",
            )
        if received_at > successor_materialized_dt:
            _fail(
                f"observation_bytes[{index}]",
                "Observation received_at must not be later than successor materialization",
            )
        observations[observation.observation_id] = observation
        observation_content[observation.observation_id] = raw

    if not isinstance(instructions, Sequence) or isinstance(
        instructions, (str, bytes, bytearray)
    ):
        _fail("instructions", "must be a non-empty sequence")
    if not instructions:
        _fail("instructions", "must contain at least one claim mapping")
    instruction_by_claim: dict[tuple[str, str], ObservationMergeInstruction] = {}
    target_paths: set[str] = set()
    for index, instruction in enumerate(instructions):
        if not isinstance(instruction, ObservationMergeInstruction):
            _fail(f"instructions[{index}]", "must be ObservationMergeInstruction")
        observation_id = _string(
            instruction.observation_id, f"instructions[{index}].observation_id"
        )
        claim_id = _string(instruction.claim_id, f"instructions[{index}].claim_id")
        target_path = _string(
            instruction.target_path, f"instructions[{index}].target_path"
        )
        if observation_id not in observations:
            _fail(
                f"instructions[{index}].observation_id",
                f"references unknown Observation {observation_id!r}",
            )
        _find_claim(observations[observation_id], claim_id)
        key = (observation_id, claim_id)
        if key in instruction_by_claim:
            _fail(f"instructions[{index}].claim_id", "duplicates a claim mapping")
        if target_path in target_paths:
            _fail(
                f"instructions[{index}].target_path",
                f"duplicates target path {target_path!r}",
            )
        instruction_by_claim[key] = ObservationMergeInstruction(
            observation_id=observation_id,
            claim_id=claim_id,
            target_path=target_path,
        )
        target_paths.add(target_path)

    expected_claims = {
        (observation.observation_id, claim.id)
        for observation in observations.values()
        for claim in observation.claims
    }
    if set(instruction_by_claim) != expected_claims:
        missing = sorted(expected_claims - set(instruction_by_claim))
        extra = sorted(set(instruction_by_claim) - expected_claims)
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(f"{a}#{b}" for a, b in missing))
        if extra:
            details.append("unexpected " + ", ".join(f"{a}#{b}" for a, b in extra))
        _fail("instructions", "must cover every supplied claim exactly once: " + "; ".join(details))

    body = copy.deepcopy(base_world_state.to_dict()["world_state"])
    body["revision"] = base_world_state.revision + 1
    body["as_of"] = successor_as_of_text
    body["materialized_at"] = successor_materialized_text

    preserved_observation_refs = tuple(sorted(base_world_state.observation_refs))
    preserved_evidence_refs = tuple(sorted(base_world_state.evidence_refs))
    new_observation_ids = set(observations)
    added_observation_refs = tuple(
        sorted(new_observation_ids - set(preserved_observation_refs))
    )
    if not added_observation_refs:
        _fail(
            "observation_bytes",
            "must contain at least one Observation not already declared by the base World State",
        )
    claim_evidence_refs = {
        evidence_ref
        for observation in observations.values()
        for claim in observation.claims
        for evidence_ref in claim.evidence_refs
    }
    added_evidence_refs = tuple(
        sorted(claim_evidence_refs - set(preserved_evidence_refs))
    )
    body["observation_refs"] = sorted(
        set(preserved_observation_refs) | new_observation_ids
    )
    body["evidence_refs"] = sorted(
        set(preserved_evidence_refs) | claim_evidence_refs
    )

    applications: list[AppliedObservationClaim] = []
    for observation_id, claim_id in sorted(instruction_by_claim):
        instruction = instruction_by_claim[(observation_id, claim_id)]
        observation = observations[observation_id]
        claim = _find_claim(observation, claim_id)
        target_kind, before, after = _claim_projection(
            body=body,
            observation=observation,
            claim=claim,
            target_path=instruction.target_path,
            successor_as_of=successor_as_of_dt,
        )
        applications.append(
            AppliedObservationClaim(
                application_id=f"{observation_id}#{claim_id}",
                observation_ref=f"observation:{observation_id}",
                claim_id=claim_id,
                target_path=instruction.target_path,
                target_kind=target_kind,
                state="applied",
                before=before,
                after=after,
            )
        )

    body["schema_id"] = WORLD_STATE_SCHEMA_ID
    body["schema_version"] = WORLD_STATE_SCHEMA_VERSION
    try:
        successor = load_world_state({"world_state": body})
    except ValueError as exc:
        raise ObservationMergeError(
            "successor_world_state: merged snapshot violates World State v0.1: "
            + str(exc)
        ) from exc
    successor_bytes = serialize_observation_merge_world_state(successor)

    base_ref = _world_state_ref(
        base_world_state, base_world_state_bytes, ref_id="base-world-state"
    )
    successor_ref = _world_state_ref(
        successor, successor_bytes, ref_id="successor-world-state"
    )
    refs = tuple(
        sorted(
            (
                _observation_ref(observations[observation_id], observation_content[observation_id])
                for observation_id in observations
            ),
            key=lambda item: item.observation_id,
        )
    )
    result = ObservationMergeResult(
        merge_id=merge_id,
        created_at=created_text,
        state="completed",
        reason=reason,
        base_world_state=base_ref,
        observation_refs=refs,
        successor_world_state=successor_ref,
        applied_claims=tuple(sorted(applications, key=lambda item: item.application_id)),
        preserved_observation_refs=preserved_observation_refs,
        added_observation_refs=added_observation_refs,
        preserved_evidence_refs=preserved_evidence_refs,
        added_evidence_refs=added_evidence_refs,
        next_action="compute_state_transition",
        state_transition_computed=False,
        impact_propagation_executed=False,
        reevaluation_executed=False,
        outputs_released=False,
        external_truth_verified=False,
        action_authorized=False,
        action_executed=False,
    )
    result = load_observation_merge_result(result.to_dict())
    result_bytes = serialize_observation_merge_result(result)
    return ObservationMergeOutput(
        world_state=successor,
        result=result,
        world_state_bytes=successor_bytes,
        result_bytes=result_bytes,
    )


def validate_observation_merge_result_bindings(
    result: ObservationMergeResult,
    *,
    base_world_state_bytes: bytes,
    observation_bytes: Sequence[bytes],
    successor_world_state_bytes: bytes,
) -> None:
    """Verify exact bindings and deterministically replay one merge result."""

    instructions = tuple(
        ObservationMergeInstruction(
            observation_id=application.observation_ref.removeprefix("observation:"),
            claim_id=application.claim_id,
            target_path=application.target_path,
        )
        for application in result.applied_claims
    )
    replay = merge_observations_into_world_state(
        merge_id=result.merge_id,
        created_at=result.created_at,
        reason=result.reason,
        base_world_state_bytes=base_world_state_bytes,
        observation_bytes=observation_bytes,
        instructions=instructions,
        successor_as_of=result.successor_world_state.as_of,
        successor_materialized_at=result.successor_world_state.materialized_at,
    )
    if replay.world_state_bytes != successor_world_state_bytes:
        _fail(
            "successor_world_state_bytes",
            "must equal the canonical bytes produced by deterministic Observation merge",
        )
    try:
        supplied_successor = load_world_state(
            _json_mapping_from_bytes(
                successor_world_state_bytes, "successor_world_state_bytes"
            )
        )
    except ValueError as exc:
        raise ObservationMergeError(f"successor_world_state_bytes: {exc}") from exc
    if supplied_successor != replay.world_state:
        _fail(
            "successor_world_state_bytes",
            "parsed successor differs from deterministic merge output",
        )
    if result.to_dict() != replay.result.to_dict():
        _fail(
            "observation_merge_result",
            "declared result differs from deterministic replay over the exact source bytes",
        )


__all__ = [
    "OBSERVATION_MERGE_RESULT_ARTIFACT_ID",
    "OBSERVATION_MERGE_RESULT_SCHEMA_ID",
    "OBSERVATION_MERGE_RESULT_SCHEMA_VERSION",
    "OBSERVATION_MERGE_RESULT_FORMAT_VERSION",
    "OBSERVATION_MERGE_STATES",
    "OBSERVATION_MERGE_APPLICATION_STATES",
    "OBSERVATION_MERGE_TARGET_KINDS",
    "OBSERVATION_MERGE_NEXT_ACTIONS",
    "ObservationMergeError",
    "ObservationMergeInstruction",
    "ObservationMergeWorldStateRef",
    "ObservationMergeObservationRef",
    "AppliedObservationClaim",
    "ObservationMergeResult",
    "ObservationMergeOutput",
    "serialize_observation_merge_world_state",
    "serialize_observation_merge_result",
    "load_observation_merge_result",
    "merge_observations_into_world_state",
    "validate_observation_merge_result_bindings",
]
