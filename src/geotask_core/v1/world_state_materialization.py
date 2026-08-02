"""Bounded successor World State materialization for GeoTask Core.

The public materializer applies one already-validated ``CorrectionRequest`` to an
immutable base ``WorldState``. Declarative add/replace/remove values come from the
request itself; recompute values must be supplied explicitly by the caller. Core
never guesses a recomputed value, fetches evidence, executes a provider, runs a
recheck, releases an output, or authorizes an action.

Successful materialization returns a new World State plus an immutable
``geotask.world-state-materialization-result`` Artifact that binds the exact base,
request, and generated successor bytes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Mapping, Sequence

from geotask_core.v1.correction_request import (
    CorrectionChange,
    CorrectionRequest,
    CorrectionRequestFormatError,
    load_correction_request,
    validate_correction_request_bindings,
)
from geotask_core.v1.discrepancy_report import DiscrepancyReport
from geotask_core.v1.world_state import (
    WORLD_STATE_ARTIFACT_ID,
    WORLD_STATE_SCHEMA_VERSION,
    WorldState,
    WorldStateFormatError,
    load_world_state,
)


WORLD_STATE_MATERIALIZATION_RESULT_ARTIFACT_ID = (
    "geotask.world-state-materialization-result"
)
WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-world-state-materialization-result-v0.1.schema.json"
)
WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_VERSION = "0.1"
WORLD_STATE_MATERIALIZATION_RESULT_FORMAT_VERSION = "0.1"
WORLD_STATE_MATERIALIZATION_STATES = frozenset({"completed"})
WORLD_STATE_MATERIALIZATION_CHANGE_STATES = frozenset({"applied"})
WORLD_STATE_MATERIALIZATION_NEXT_ACTIONS = frozenset(
    {"reevaluate_successor_state"}
)


class WorldStateMaterializationError(ValueError):
    """Raised when bounded materialization or result validation fails."""


def _fail(path: str, message: str) -> None:
    raise WorldStateMaterializationError(f"{path}: {message}")


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
        raise WorldStateMaterializationError(
            f"{path}: must be an ISO 8601 timestamp"
        ) from exc
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
        return [
            _json_value(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    _fail(path, "must be a JSON-compatible value")


def _decode_pointer(pointer: str) -> tuple[str, ...]:
    if not pointer.startswith("/") or pointer.endswith("/"):
        _fail("target_path", "must be a non-root JSON Pointer")
    return tuple(
        segment.replace("~1", "/").replace("~0", "~")
        for segment in pointer.split("/")[1:]
    )


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def serialize_world_state(world_state: WorldState) -> bytes:
    """Return the canonical public JSON bytes emitted by the materializer."""

    return _canonical_bytes(world_state.to_dict())


def _json_mapping_from_bytes(content: bytes, path: str) -> Mapping[str, object]:
    if not isinstance(content, bytes):
        _fail(path, "must be bytes")
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorldStateMaterializationError(
            f"{path}: must be UTF-8 JSON bytes"
        ) from exc
    try:
        payload = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise WorldStateMaterializationError(
            f"{path}: must contain valid JSON"
        ) from exc
    return _mapping(payload, path)


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True)
class MaterializationArtifactRef:
    ref_id: str
    artifact_id: str
    schema_version: str
    instance_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ref_id": self.ref_id,
            "artifact_id": self.artifact_id,
            "schema_version": self.schema_version,
            "instance_id": self.instance_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class MaterializationWorldStateRef:
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
class MaterializedCorrectionChange:
    change_id: str
    target_path: str
    operation: str
    state: str
    request_basis_refs: tuple[str, ...]
    observation_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    input_fields: tuple[str, ...]
    acceptance_criterion_refs: tuple[str, ...]
    has_before: bool
    before: object
    has_after: bool
    after: object

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "change_id": self.change_id,
            "target_path": self.target_path,
            "operation": self.operation,
            "state": self.state,
            "request_basis_refs": sorted(self.request_basis_refs),
            "observation_refs": sorted(self.observation_refs),
            "evidence_refs": sorted(self.evidence_refs),
            "input_fields": sorted(self.input_fields),
            "acceptance_criterion_refs": sorted(self.acceptance_criterion_refs),
        }
        if self.has_before:
            payload["before"] = copy.deepcopy(self.before)
        if self.has_after:
            payload["after"] = copy.deepcopy(self.after)
        return payload


@dataclass(frozen=True)
class WorldStateMaterializationResult:
    materialization_id: str
    created_at: str
    state: str
    reason: str
    base_world_state: MaterializationWorldStateRef
    correction_request_ref: MaterializationArtifactRef
    successor_world_state: MaterializationWorldStateRef
    applied_changes: tuple[MaterializedCorrectionChange, ...]
    preserved_observation_refs: tuple[str, ...]
    preserved_evidence_refs: tuple[str, ...]
    blocked_outputs: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    next_action: str
    reevaluation_executed: bool
    outputs_released: bool
    external_truth_verified: bool
    action_authorized: bool
    action_executed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "world_state_materialization_result": {
                "schema_id": WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID,
                "schema_version": WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_VERSION,
                "materialization_id": self.materialization_id,
                "created_at": self.created_at,
                "state": self.state,
                "reason": self.reason,
                "base_world_state": self.base_world_state.to_dict(),
                "correction_request_ref": self.correction_request_ref.to_dict(),
                "successor_world_state": self.successor_world_state.to_dict(),
                "applied_changes": [
                    item.to_dict()
                    for item in sorted(
                        self.applied_changes,
                        key=lambda item: item.change_id,
                    )
                ],
                "preserved_observation_refs": sorted(
                    self.preserved_observation_refs
                ),
                "preserved_evidence_refs": sorted(self.preserved_evidence_refs),
                "blocked_outputs": sorted(self.blocked_outputs),
                "blocked_actions": sorted(self.blocked_actions),
                "next_action": self.next_action,
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
class MaterializedWorldStateOutput:
    """Deterministic output of bounded successor-state materialization."""

    world_state: WorldState
    result: WorldStateMaterializationResult
    world_state_bytes: bytes
    result_bytes: bytes


def _load_artifact_ref(value: object, path: str) -> MaterializationArtifactRef:
    ref = _mapping(value, path)
    _exact_fields(
        ref,
        path,
        required={
            "ref_id",
            "artifact_id",
            "schema_version",
            "instance_id",
            "content_sha256",
        },
    )
    return MaterializationArtifactRef(
        ref_id=_string(ref["ref_id"], f"{path}.ref_id"),
        artifact_id=_string(ref["artifact_id"], f"{path}.artifact_id"),
        schema_version=_string(ref["schema_version"], f"{path}.schema_version"),
        instance_id=_string(ref["instance_id"], f"{path}.instance_id"),
        content_sha256=_sha256(ref["content_sha256"], f"{path}.content_sha256"),
    )


def _load_world_state_ref(
    value: object,
    path: str,
) -> tuple[MaterializationWorldStateRef, datetime, datetime]:
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
        MaterializationWorldStateRef(
            ref_id=_string(ref["ref_id"], f"{path}.ref_id"),
            artifact_id=WORLD_STATE_ARTIFACT_ID,
            schema_version=WORLD_STATE_SCHEMA_VERSION,
            world_state_id=_string(
                ref["world_state_id"], f"{path}.world_state_id"
            ),
            revision=_positive_integer(ref["revision"], f"{path}.revision"),
            as_of=as_of_text,
            materialized_at=materialized_text,
            semantic_fingerprint=_sha256(
                ref["semantic_fingerprint"], f"{path}.semantic_fingerprint"
            ),
            content_sha256=_sha256(
                ref["content_sha256"], f"{path}.content_sha256"
            ),
        ),
        as_of,
        materialized_at,
    )


def _load_applied_change(
    value: object,
    *,
    index: int,
) -> MaterializedCorrectionChange:
    path = f"world_state_materialization_result.applied_changes[{index}]"
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={
            "change_id",
            "target_path",
            "operation",
            "state",
            "request_basis_refs",
            "observation_refs",
            "evidence_refs",
            "input_fields",
            "acceptance_criterion_refs",
        },
        optional={"before", "after"},
    )
    operation = _enum(
        item["operation"],
        f"{path}.operation",
        frozenset({"add", "replace", "remove", "recompute"}),
    )
    has_before = "before" in item
    has_after = "after" in item
    before = _json_value(item["before"], f"{path}.before") if has_before else None
    after = _json_value(item["after"], f"{path}.after") if has_after else None
    if operation == "add" and (has_before or not has_after):
        _fail(path, "add requires after and forbids before")
    if operation in {"replace", "recompute"} and (
        not has_before or not has_after
    ):
        _fail(path, f"{operation} requires before and after")
    if operation == "remove" and (not has_before or has_after):
        _fail(path, "remove requires before and forbids after")
    return MaterializedCorrectionChange(
        change_id=_string(item["change_id"], f"{path}.change_id"),
        target_path=_string(item["target_path"], f"{path}.target_path"),
        operation=operation,
        state=_enum(
            item["state"],
            f"{path}.state",
            WORLD_STATE_MATERIALIZATION_CHANGE_STATES,
        ),
        request_basis_refs=_string_list(
            item["request_basis_refs"], f"{path}.request_basis_refs", non_empty=True
        ),
        observation_refs=_string_list(
            item["observation_refs"], f"{path}.observation_refs"
        ),
        evidence_refs=_string_list(
            item["evidence_refs"], f"{path}.evidence_refs"
        ),
        input_fields=_string_list(item["input_fields"], f"{path}.input_fields"),
        acceptance_criterion_refs=_string_list(
            item["acceptance_criterion_refs"],
            f"{path}.acceptance_criterion_refs",
            non_empty=True,
        ),
        has_before=has_before,
        before=before,
        has_after=has_after,
        after=after,
    )


def load_world_state_materialization_result(
    payload: Mapping[str, object],
) -> WorldStateMaterializationResult:
    """Strictly load one materialization result Artifact."""

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"world_state_materialization_result"})
    body = _mapping(
        root["world_state_materialization_result"],
        "world_state_materialization_result",
    )
    _exact_fields(
        body,
        "world_state_materialization_result",
        required={
            "schema_id",
            "schema_version",
            "materialization_id",
            "created_at",
            "state",
            "reason",
            "base_world_state",
            "correction_request_ref",
            "successor_world_state",
            "applied_changes",
            "preserved_observation_refs",
            "preserved_evidence_refs",
            "blocked_outputs",
            "blocked_actions",
            "next_action",
            "reevaluation_executed",
            "outputs_released",
            "external_truth_verified",
            "action_authorized",
            "action_executed",
        },
    )
    if body["schema_id"] != WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID:
        _fail(
            "world_state_materialization_result.schema_id",
            f"must equal {WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID!r}",
        )
    if (
        body["schema_version"]
        != WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_VERSION
    ):
        _fail(
            "world_state_materialization_result.schema_version",
            f"must equal {WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_VERSION!r}",
        )

    created_at_text, created_at = _timestamp(
        body["created_at"], "world_state_materialization_result.created_at"
    )
    base_ref, base_as_of, _base_materialized = _load_world_state_ref(
        body["base_world_state"],
        "world_state_materialization_result.base_world_state",
    )
    successor_ref, successor_as_of, successor_materialized = _load_world_state_ref(
        body["successor_world_state"],
        "world_state_materialization_result.successor_world_state",
    )
    if successor_ref.world_state_id != base_ref.world_state_id:
        _fail(
            "world_state_materialization_result.successor_world_state.world_state_id",
            "must equal base World State ID",
        )
    if successor_ref.revision <= base_ref.revision:
        _fail(
            "world_state_materialization_result.successor_world_state.revision",
            "must be greater than the base revision",
        )
    if successor_as_of < base_as_of:
        _fail(
            "world_state_materialization_result.successor_world_state.as_of",
            "must not precede the base snapshot",
        )
    if created_at < successor_materialized:
        _fail(
            "world_state_materialization_result.created_at",
            "must not precede successor materialization",
        )
    if successor_ref.content_sha256 == base_ref.content_sha256:
        _fail(
            "world_state_materialization_result.successor_world_state.content_sha256",
            "must differ from the base snapshot bytes",
        )

    raw_changes = body["applied_changes"]
    if not isinstance(raw_changes, Sequence) or isinstance(
        raw_changes, (str, bytes, bytearray)
    ):
        _fail(
            "world_state_materialization_result.applied_changes",
            "must be a non-empty array",
        )
    if not raw_changes:
        _fail(
            "world_state_materialization_result.applied_changes",
            "must contain at least one item",
        )
    changes: list[MaterializedCorrectionChange] = []
    change_ids: set[str] = set()
    target_paths: set[str] = set()
    for index, raw in enumerate(raw_changes):
        change = _load_applied_change(raw, index=index)
        if change.change_id in change_ids:
            _fail(
                f"world_state_materialization_result.applied_changes[{index}].change_id",
                f"duplicates {change.change_id!r}",
            )
        if change.target_path in target_paths:
            _fail(
                f"world_state_materialization_result.applied_changes[{index}].target_path",
                f"duplicates {change.target_path!r}",
            )
        change_ids.add(change.change_id)
        target_paths.add(change.target_path)
        changes.append(change)

    false_boundaries = {
        "reevaluation_executed": _boolean(
            body["reevaluation_executed"],
            "world_state_materialization_result.reevaluation_executed",
        ),
        "outputs_released": _boolean(
            body["outputs_released"],
            "world_state_materialization_result.outputs_released",
        ),
        "external_truth_verified": _boolean(
            body["external_truth_verified"],
            "world_state_materialization_result.external_truth_verified",
        ),
        "action_authorized": _boolean(
            body["action_authorized"],
            "world_state_materialization_result.action_authorized",
        ),
        "action_executed": _boolean(
            body["action_executed"],
            "world_state_materialization_result.action_executed",
        ),
    }
    enabled = sorted(key for key, value in false_boundaries.items() if value)
    if enabled:
        _fail(
            "world_state_materialization_result",
            "operational boundary fields must remain false: " + ", ".join(enabled),
        )

    return WorldStateMaterializationResult(
        materialization_id=_string(
            body["materialization_id"],
            "world_state_materialization_result.materialization_id",
        ),
        created_at=created_at_text,
        state=_enum(
            body["state"],
            "world_state_materialization_result.state",
            WORLD_STATE_MATERIALIZATION_STATES,
        ),
        reason=_string(
            body["reason"], "world_state_materialization_result.reason"
        ),
        base_world_state=base_ref,
        correction_request_ref=_load_artifact_ref(
            body["correction_request_ref"],
            "world_state_materialization_result.correction_request_ref",
        ),
        successor_world_state=successor_ref,
        applied_changes=tuple(sorted(changes, key=lambda item: item.change_id)),
        preserved_observation_refs=_string_list(
            body["preserved_observation_refs"],
            "world_state_materialization_result.preserved_observation_refs",
        ),
        preserved_evidence_refs=_string_list(
            body["preserved_evidence_refs"],
            "world_state_materialization_result.preserved_evidence_refs",
        ),
        blocked_outputs=_string_list(
            body["blocked_outputs"],
            "world_state_materialization_result.blocked_outputs",
        ),
        blocked_actions=_string_list(
            body["blocked_actions"],
            "world_state_materialization_result.blocked_actions",
        ),
        next_action=_enum(
            body["next_action"],
            "world_state_materialization_result.next_action",
            WORLD_STATE_MATERIALIZATION_NEXT_ACTIONS,
        ),
        reevaluation_executed=false_boundaries["reevaluation_executed"],
        outputs_released=false_boundaries["outputs_released"],
        external_truth_verified=false_boundaries["external_truth_verified"],
        action_authorized=false_boundaries["action_authorized"],
        action_executed=false_boundaries["action_executed"],
    )


def _identity_root(
    world_state_body: Mapping[str, object],
    segments: Sequence[str],
    *,
    path: str,
) -> tuple[object, tuple[str, ...]]:
    if len(segments) < 3:
        _fail(path, "must target a field below a World State object or relation")
    if segments[0] == "objects":
        objects = world_state_body.get("objects")
        if not isinstance(objects, list):
            _fail(path, "World State objects are unavailable")
        selected = next(
            (
                item
                for item in objects
                if isinstance(item, dict) and item.get("id") == segments[1]
            ),
            None,
        )
        if selected is None:
            _fail(path, f"references unknown object {segments[1]!r}")
        if len(segments) >= 4 and segments[2] == "attributes":
            attributes = selected.get("attributes")
            if not isinstance(attributes, list):
                _fail(path, "object attributes are unavailable")
            attribute = next(
                (
                    item
                    for item in attributes
                    if isinstance(item, dict) and item.get("name") == segments[3]
                ),
                None,
            )
            if attribute is None:
                _fail(path, f"references unknown attribute {segments[3]!r}")
            return attribute, tuple(segments[4:])
        return selected, tuple(segments[2:])
    if segments[0] == "relations":
        relations = world_state_body.get("relations")
        if not isinstance(relations, list):
            _fail(path, "World State relations are unavailable")
        selected = next(
            (
                item
                for item in relations
                if isinstance(item, dict) and item.get("id") == segments[1]
            ),
            None,
        )
        if selected is None:
            _fail(path, f"references unknown relation {segments[1]!r}")
        return selected, tuple(segments[2:])
    _fail(path, "must start with /objects or /relations")


def _navigate_parent(
    root: object,
    segments: Sequence[str],
    *,
    path: str,
) -> tuple[object, str]:
    if not segments:
        _fail(path, "must target a field below the selected identity")
    current = root
    for segment in segments[:-1]:
        if isinstance(current, dict):
            if segment not in current:
                _fail(path, f"parent segment {segment!r} does not exist")
            current = current[segment]
            continue
        if isinstance(current, list):
            try:
                index = int(segment)
            except ValueError:
                _fail(path, f"list segment {segment!r} must be an integer")
            if index < 0 or index >= len(current):
                _fail(path, f"list index {index} is out of range")
            current = current[index]
            continue
        _fail(path, f"cannot traverse scalar parent at segment {segment!r}")
    return current, segments[-1]


def _read_target(
    world_state_body: Mapping[str, object],
    target_path: str,
) -> tuple[bool, object]:
    segments = _decode_pointer(target_path)
    root, remainder = _identity_root(
        world_state_body, segments, path=target_path
    )
    parent, key = _navigate_parent(root, remainder, path=target_path)
    if isinstance(parent, dict):
        if key not in parent:
            return False, None
        return True, copy.deepcopy(parent[key])
    if isinstance(parent, list):
        try:
            index = int(key)
        except ValueError:
            _fail(target_path, f"list segment {key!r} must be an integer")
        if index < 0 or index >= len(parent):
            return False, None
        return True, copy.deepcopy(parent[index])
    _fail(target_path, "target parent must be an object or array")


def _write_target(
    world_state_body: dict[str, object],
    target_path: str,
    *,
    operation: str,
    value: object = None,
) -> None:
    segments = _decode_pointer(target_path)
    root, remainder = _identity_root(
        world_state_body, segments, path=target_path
    )
    parent, key = _navigate_parent(root, remainder, path=target_path)
    if isinstance(parent, dict):
        exists = key in parent
        if operation == "add":
            if exists:
                _fail(target_path, "add target already exists")
            parent[key] = copy.deepcopy(value)
            return
        if not exists:
            _fail(target_path, f"{operation} target does not exist")
        if operation == "remove":
            del parent[key]
        else:
            parent[key] = copy.deepcopy(value)
        return
    if isinstance(parent, list):
        try:
            index = int(key)
        except ValueError:
            _fail(target_path, f"list segment {key!r} must be an integer")
        if operation == "add":
            _fail(target_path, "array insertion is not supported in v0.1")
        if index < 0 or index >= len(parent):
            _fail(target_path, f"list index {index} is out of range")
        if operation == "remove":
            del parent[index]
        else:
            parent[index] = copy.deepcopy(value)
        return
    _fail(target_path, "target parent must be an object or array")


def _normalized_world_state_body(world_state: WorldState) -> dict[str, object]:
    body = copy.deepcopy(world_state.to_dict()["world_state"])
    objects = body.pop("objects")
    relations = body.pop("relations")
    body.pop("revision", None)
    body.pop("as_of", None)
    body.pop("materialized_at", None)
    normalized_objects: dict[str, object] = {}
    for item in objects:
        object_item = copy.deepcopy(item)
        attributes = object_item.pop("attributes")
        object_item["attributes"] = {
            attribute["name"]: attribute for attribute in attributes
        }
        normalized_objects[object_item["id"]] = object_item
    body["objects"] = normalized_objects
    body["relations"] = {item["id"]: item for item in relations}
    return body


def _flatten(value: object, path: str = "") -> dict[str, object]:
    if isinstance(value, Mapping):
        flattened: dict[str, object] = {}
        if not value:
            flattened[path or "/"] = {}
        for key in sorted(value):
            segment = str(key).replace("~", "~0").replace("/", "~1")
            flattened.update(_flatten(value[key], f"{path}/{segment}"))
        return flattened
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        flattened = {}
        if not value:
            flattened[path or "/"] = []
        for index, item in enumerate(value):
            flattened.update(_flatten(item, f"{path}/{index}"))
        return flattened
    return {path or "/": copy.deepcopy(value)}


def _path_within(path: str, parent: str) -> bool:
    return path == parent or path.startswith(parent + "/")


def _check_world_ref(
    ref: MaterializationWorldStateRef,
    world_state: WorldState,
    content: bytes,
    path: str,
) -> None:
    checks = (
        ("world_state_id", ref.world_state_id, world_state.world_state_id),
        ("revision", ref.revision, world_state.revision),
        ("as_of", ref.as_of, world_state.as_of),
        ("materialized_at", ref.materialized_at, world_state.materialized_at),
        (
            "semantic_fingerprint",
            ref.semantic_fingerprint,
            world_state.semantic_fingerprint(),
        ),
        ("content_sha256", ref.content_sha256, _hash_bytes(content)),
    )
    for field, expected, actual in checks:
        if expected != actual:
            _fail(f"{path}.{field}", f"expected {expected!r}, got {actual!r}")


def _applied_change_from_request(
    change: CorrectionChange,
    *,
    before_exists: bool,
    before: object,
    after_exists: bool,
    after: object,
) -> MaterializedCorrectionChange:
    return MaterializedCorrectionChange(
        change_id=change.id,
        target_path=change.target_path,
        operation=change.operation,
        state="applied",
        request_basis_refs=change.basis_refs,
        observation_refs=change.observation_refs,
        evidence_refs=change.evidence_refs,
        input_fields=change.input_fields,
        acceptance_criterion_refs=change.acceptance_criterion_refs,
        has_before=before_exists,
        before=copy.deepcopy(before),
        has_after=after_exists,
        after=copy.deepcopy(after),
    )


def materialize_successor_world_state(
    *,
    materialization_id: str,
    reason: str,
    created_at: str,
    base_world_state: WorldState,
    correction_request: CorrectionRequest,
    correction_request_ref_id: str,
    correction_request_content: bytes,
    discrepancy_reports: Mapping[str, DiscrepancyReport],
    artifact_contents: Mapping[str, bytes],
    recomputed_values: Mapping[str, object],
    as_of: str,
    materialized_at: str,
    successor_ref_id: str = "successor-world-state",
) -> MaterializedWorldStateOutput:
    """Apply one required Correction Request and generate a successor snapshot.

    ``artifact_contents`` is the exact byte map required by
    ``validate_correction_request_bindings``. Only recompute changes accept caller
    values, keyed by change ID. Add/replace/remove values are fixed by the request.
    """

    materialization_id = _string(materialization_id, "materialization_id")
    reason = _string(reason, "reason")
    correction_request_ref_id = _string(
        correction_request_ref_id, "correction_request_ref_id"
    )
    successor_ref_id = _string(successor_ref_id, "successor_ref_id")
    created_at_text, created_time = _timestamp(created_at, "created_at")
    as_of_text, as_of_time = _timestamp(as_of, "as_of")
    materialized_text, materialized_time = _timestamp(
        materialized_at, "materialized_at"
    )
    request_created_time = _timestamp(
        correction_request.created_at, "correction_request.created_at"
    )[1]
    base_as_of_time = _timestamp(base_world_state.as_of, "base_world_state.as_of")[1]
    if correction_request.state != "required":
        _fail("correction_request.state", "must equal 'required'")
    if correction_request.next_action != "materialize_successor_state":
        _fail(
            "correction_request.next_action",
            "must equal 'materialize_successor_state'",
        )
    if as_of_time < base_as_of_time or as_of_time < request_created_time:
        _fail("as_of", "must not precede the base snapshot or Correction Request")
    if materialized_time < as_of_time:
        _fail("materialized_at", "must not precede as_of")
    if created_time < materialized_time:
        _fail("created_at", "must not precede materialized_at")

    try:
        validate_correction_request_bindings(
            correction_request,
            base_world_state,
            discrepancy_reports,
            artifact_contents,
        )
    except CorrectionRequestFormatError as exc:
        raise WorldStateMaterializationError(
            f"correction_request: binding validation failed: {exc}"
        ) from exc

    try:
        parsed_request = load_correction_request(
            _json_mapping_from_bytes(
                correction_request_content, "correction_request_content"
            )
        )
    except CorrectionRequestFormatError as exc:
        raise WorldStateMaterializationError(
            f"correction_request_content: strict loading failed: {exc}"
        ) from exc
    if parsed_request != correction_request:
        _fail(
            "correction_request_content",
            "does not strictly load to the supplied Correction Request",
        )

    base_content = artifact_contents.get(correction_request.base_world_state.ref_id)
    if not isinstance(base_content, bytes):
        _fail("artifact_contents", "is missing exact base World State bytes")
    try:
        parsed_base = load_world_state(
            _json_mapping_from_bytes(base_content, "base_world_state_content")
        )
    except WorldStateFormatError as exc:
        raise WorldStateMaterializationError(
            f"base_world_state_content: strict loading failed: {exc}"
        ) from exc
    if parsed_base != base_world_state:
        _fail(
            "base_world_state_content",
            "does not strictly load to the supplied base World State",
        )

    if not isinstance(recomputed_values, Mapping):
        _fail("recomputed_values", "must be an object keyed by change ID")
    recompute_ids = {
        change.id
        for change in correction_request.changes
        if change.operation == "recompute"
    }
    if set(recomputed_values) != recompute_ids:
        missing = sorted(recompute_ids - set(recomputed_values))
        extra = sorted(set(recomputed_values) - recompute_ids)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unexpected: " + ", ".join(extra))
        _fail("recomputed_values", "; ".join(details))
    normalized_recomputed = {
        key: _json_value(value, f"recomputed_values[{key!r}]")
        for key, value in recomputed_values.items()
    }

    undeclared_observations = sorted(
        set(correction_request.observation_refs)
        - set(base_world_state.observation_refs)
    )
    undeclared_evidence = sorted(
        set(correction_request.evidence_refs) - set(base_world_state.evidence_refs)
    )
    if undeclared_observations or undeclared_evidence:
        details = []
        if undeclared_observations:
            details.append(
                "new observation refs require Observation merging: "
                + ", ".join(undeclared_observations)
            )
        if undeclared_evidence:
            details.append(
                "new evidence refs require explicit provenance update: "
                + ", ".join(undeclared_evidence)
            )
        _fail("correction_request", "; ".join(details))

    body = copy.deepcopy(base_world_state.to_dict()["world_state"])
    applied: list[MaterializedCorrectionChange] = []
    for change in sorted(correction_request.changes, key=lambda item: item.id):
        before_exists, before = _read_target(body, change.target_path)
        if change.operation == "add":
            if before_exists:
                _fail(change.target_path, "add target already exists")
            after = copy.deepcopy(change.after)
            _write_target(
                body,
                change.target_path,
                operation="add",
                value=after,
            )
            applied.append(
                _applied_change_from_request(
                    change,
                    before_exists=False,
                    before=None,
                    after_exists=True,
                    after=after,
                )
            )
            continue
        if not before_exists:
            _fail(change.target_path, f"{change.operation} target does not exist")
        if not change.has_before or before != change.before:
            _fail(
                change.target_path,
                "base value does not match Correction Request before value",
            )
        if change.operation == "remove":
            _write_target(body, change.target_path, operation="remove")
            applied.append(
                _applied_change_from_request(
                    change,
                    before_exists=True,
                    before=before,
                    after_exists=False,
                    after=None,
                )
            )
            continue
        after = (
            copy.deepcopy(change.after)
            if change.operation == "replace"
            else copy.deepcopy(normalized_recomputed[change.id])
        )
        _write_target(
            body,
            change.target_path,
            operation=change.operation,
            value=after,
        )
        applied.append(
            _applied_change_from_request(
                change,
                before_exists=True,
                before=before,
                after_exists=True,
                after=after,
            )
        )

    body["revision"] = max(
        base_world_state.revision + 1,
        correction_request.output_contract.minimum_revision,
    )
    body["as_of"] = as_of_text
    body["materialized_at"] = materialized_text
    body["world_state_id"] = correction_request.output_contract.world_state_id
    try:
        successor = load_world_state({"world_state": body})
    except WorldStateFormatError as exc:
        raise WorldStateMaterializationError(
            f"successor_world_state: generated snapshot is invalid: {exc}"
        ) from exc

    if successor.observation_refs != base_world_state.observation_refs:
        _fail(
            "successor_world_state.observation_refs",
            "v0.1 materialization must preserve base observation refs",
        )
    if successor.evidence_refs != base_world_state.evidence_refs:
        _fail(
            "successor_world_state.evidence_refs",
            "v0.1 materialization must preserve base evidence refs",
        )

    successor_bytes = serialize_world_state(successor)
    base_ref = MaterializationWorldStateRef(
        ref_id=correction_request.base_world_state.ref_id,
        artifact_id=WORLD_STATE_ARTIFACT_ID,
        schema_version=WORLD_STATE_SCHEMA_VERSION,
        world_state_id=base_world_state.world_state_id,
        revision=base_world_state.revision,
        as_of=base_world_state.as_of,
        materialized_at=base_world_state.materialized_at,
        semantic_fingerprint=base_world_state.semantic_fingerprint(),
        content_sha256=_hash_bytes(base_content),
    )
    successor_ref = MaterializationWorldStateRef(
        ref_id=successor_ref_id,
        artifact_id=WORLD_STATE_ARTIFACT_ID,
        schema_version=WORLD_STATE_SCHEMA_VERSION,
        world_state_id=successor.world_state_id,
        revision=successor.revision,
        as_of=successor.as_of,
        materialized_at=successor.materialized_at,
        semantic_fingerprint=successor.semantic_fingerprint(),
        content_sha256=_hash_bytes(successor_bytes),
    )
    request_ref = MaterializationArtifactRef(
        ref_id=correction_request_ref_id,
        artifact_id="geotask.correction-request",
        schema_version="0.1",
        instance_id=correction_request.request_id,
        content_sha256=_hash_bytes(correction_request_content),
    )
    result = WorldStateMaterializationResult(
        materialization_id=materialization_id,
        created_at=created_at_text,
        state="completed",
        reason=reason,
        base_world_state=base_ref,
        correction_request_ref=request_ref,
        successor_world_state=successor_ref,
        applied_changes=tuple(sorted(applied, key=lambda item: item.change_id)),
        preserved_observation_refs=base_world_state.observation_refs,
        preserved_evidence_refs=base_world_state.evidence_refs,
        blocked_outputs=correction_request.blocked_outputs,
        blocked_actions=correction_request.blocked_actions,
        next_action="reevaluate_successor_state",
        reevaluation_executed=False,
        outputs_released=False,
        external_truth_verified=False,
        action_authorized=False,
        action_executed=False,
    )
    result_bytes = _canonical_bytes(result.to_dict())
    output = MaterializedWorldStateOutput(
        world_state=successor,
        result=result,
        world_state_bytes=successor_bytes,
        result_bytes=result_bytes,
    )
    validate_world_state_materialization_result_bindings(
        result,
        base_world_state,
        correction_request,
        successor,
        {
            base_ref.ref_id: base_content,
            request_ref.ref_id: correction_request_content,
            successor_ref.ref_id: successor_bytes,
        },
    )
    return output


def validate_world_state_materialization_result_bindings(
    result: WorldStateMaterializationResult,
    base_world_state: WorldState,
    correction_request: CorrectionRequest,
    successor_world_state: WorldState,
    artifact_contents: Mapping[str, bytes],
) -> None:
    """Validate exact bytes and bounded successor-state materialization semantics."""

    expected_refs = {
        result.base_world_state.ref_id,
        result.correction_request_ref.ref_id,
        result.successor_world_state.ref_id,
    }
    if set(artifact_contents) != expected_refs:
        _fail(
            "artifact_contents",
            "keys must exactly match base, Correction Request, and successor refs",
        )
    for ref_id, content in artifact_contents.items():
        if not isinstance(content, bytes):
            _fail(f"artifact_contents[{ref_id!r}]", "must be bytes")

    base_content = artifact_contents[result.base_world_state.ref_id]
    request_content = artifact_contents[result.correction_request_ref.ref_id]
    successor_content = artifact_contents[result.successor_world_state.ref_id]
    _check_world_ref(
        result.base_world_state,
        base_world_state,
        base_content,
        "world_state_materialization_result.base_world_state",
    )
    _check_world_ref(
        result.successor_world_state,
        successor_world_state,
        successor_content,
        "world_state_materialization_result.successor_world_state",
    )
    if result.correction_request_ref.artifact_id != "geotask.correction-request":
        _fail(
            "world_state_materialization_result.correction_request_ref.artifact_id",
            "must equal 'geotask.correction-request'",
        )
    if result.correction_request_ref.schema_version != "0.1":
        _fail(
            "world_state_materialization_result.correction_request_ref.schema_version",
            "must equal '0.1'",
        )
    if result.correction_request_ref.instance_id != correction_request.request_id:
        _fail(
            "world_state_materialization_result.correction_request_ref.instance_id",
            "does not match Correction Request ID",
        )
    if result.correction_request_ref.content_sha256 != _hash_bytes(request_content):
        _fail(
            "world_state_materialization_result.correction_request_ref.content_sha256",
            "does not match exact Correction Request bytes",
        )

    try:
        parsed_base = load_world_state(
            _json_mapping_from_bytes(base_content, "artifact_contents.base")
        )
        parsed_request = load_correction_request(
            _json_mapping_from_bytes(request_content, "artifact_contents.request")
        )
        parsed_successor = load_world_state(
            _json_mapping_from_bytes(successor_content, "artifact_contents.successor")
        )
    except (WorldStateFormatError, CorrectionRequestFormatError) as exc:
        raise WorldStateMaterializationError(
            f"artifact_contents: strict loading failed: {exc}"
        ) from exc
    if parsed_base != base_world_state:
        _fail("artifact_contents.base", "does not load to the supplied base World State")
    if parsed_request != correction_request:
        _fail(
            "artifact_contents.request",
            "does not load to the supplied Correction Request",
        )
    if parsed_successor != successor_world_state:
        _fail(
            "artifact_contents.successor",
            "does not load to the supplied successor World State",
        )

    if correction_request.state != "required":
        _fail("correction_request.state", "must equal 'required'")
    if result.blocked_outputs != correction_request.blocked_outputs:
        _fail("blocked_outputs", "must preserve Correction Request blocked outputs")
    if result.blocked_actions != correction_request.blocked_actions:
        _fail("blocked_actions", "must preserve Correction Request blocked actions")
    if result.preserved_observation_refs != base_world_state.observation_refs:
        _fail("preserved_observation_refs", "must equal base observation refs")
    if result.preserved_evidence_refs != base_world_state.evidence_refs:
        _fail("preserved_evidence_refs", "must equal base evidence refs")
    if successor_world_state.observation_refs != base_world_state.observation_refs:
        _fail("successor_world_state.observation_refs", "must preserve base refs")
    if successor_world_state.evidence_refs != base_world_state.evidence_refs:
        _fail("successor_world_state.evidence_refs", "must preserve base refs")
    if successor_world_state.world_state_id != correction_request.output_contract.world_state_id:
        _fail("successor_world_state.world_state_id", "violates output contract")
    if successor_world_state.revision < correction_request.output_contract.minimum_revision:
        _fail("successor_world_state.revision", "is below output-contract minimum")

    request_change_by_id = {item.id: item for item in correction_request.changes}
    result_change_by_id = {item.change_id: item for item in result.applied_changes}
    if set(result_change_by_id) != set(request_change_by_id):
        _fail("applied_changes", "must cover every Correction Request change exactly once")
    for change_id, request_change in request_change_by_id.items():
        applied = result_change_by_id[change_id]
        copied_fields = (
            ("target_path", applied.target_path, request_change.target_path),
            ("operation", applied.operation, request_change.operation),
            (
                "request_basis_refs",
                applied.request_basis_refs,
                request_change.basis_refs,
            ),
            (
                "observation_refs",
                applied.observation_refs,
                request_change.observation_refs,
            ),
            ("evidence_refs", applied.evidence_refs, request_change.evidence_refs),
            ("input_fields", applied.input_fields, request_change.input_fields),
            (
                "acceptance_criterion_refs",
                applied.acceptance_criterion_refs,
                request_change.acceptance_criterion_refs,
            ),
        )
        for field, actual, expected in copied_fields:
            if actual != expected:
                _fail(
                    f"applied_changes[{change_id!r}].{field}",
                    "does not match the Correction Request",
                )
        base_exists, base_value = _read_target(
            base_world_state.to_dict()["world_state"], request_change.target_path
        )
        successor_exists, successor_value = _read_target(
            successor_world_state.to_dict()["world_state"],
            request_change.target_path,
        )
        if applied.has_before != base_exists or (
            base_exists and applied.before != base_value
        ):
            _fail(
                f"applied_changes[{change_id!r}].before",
                "does not match the base snapshot",
            )
        if applied.has_after != successor_exists or (
            successor_exists and applied.after != successor_value
        ):
            _fail(
                f"applied_changes[{change_id!r}].after",
                "does not match the successor snapshot",
            )
        if request_change.operation == "add" and base_exists:
            _fail(request_change.target_path, "add target existed in base")
        if request_change.operation in {"replace", "remove", "recompute"}:
            if not base_exists or base_value != request_change.before:
                _fail(request_change.target_path, "base value disagrees with request")
        if request_change.operation == "remove" and successor_exists:
            _fail(request_change.target_path, "remove target remains in successor")
        if request_change.operation in {"add", "replace"} and (
            not successor_exists or successor_value != request_change.after
        ):
            _fail(request_change.target_path, "successor disagrees with requested after")

    base_flat = _flatten(_normalized_world_state_body(base_world_state))
    successor_flat = _flatten(_normalized_world_state_body(successor_world_state))
    changed_paths = {
        path
        for path in set(base_flat) | set(successor_flat)
        if base_flat.get(path) != successor_flat.get(path)
    }
    requested_paths = {item.target_path for item in correction_request.changes}
    unauthorized = sorted(
        path
        for path in changed_paths
        if not any(_path_within(path, target) for target in requested_paths)
    )
    if unauthorized:
        _fail(
            "successor_world_state",
            "contains changes outside requested paths: " + ", ".join(unauthorized),
        )


__all__ = [
    "WORLD_STATE_MATERIALIZATION_RESULT_ARTIFACT_ID",
    "WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID",
    "WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_VERSION",
    "WORLD_STATE_MATERIALIZATION_RESULT_FORMAT_VERSION",
    "WORLD_STATE_MATERIALIZATION_STATES",
    "WORLD_STATE_MATERIALIZATION_CHANGE_STATES",
    "WORLD_STATE_MATERIALIZATION_NEXT_ACTIONS",
    "WorldStateMaterializationError",
    "MaterializationArtifactRef",
    "MaterializationWorldStateRef",
    "MaterializedCorrectionChange",
    "WorldStateMaterializationResult",
    "MaterializedWorldStateOutput",
    "serialize_world_state",
    "load_world_state_materialization_result",
    "materialize_successor_world_state",
    "validate_world_state_materialization_result_bindings",
]
