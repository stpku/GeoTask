"""Deterministic recompute-value derivation for bounded World State correction.

A Recompute Derivation Result binds one immutable base World State, one exact
Correction Request, and exact source Artifact bytes. Each requested ``recompute``
change is covered by a small allowlisted deterministic method whose named inputs
are either exact Artifact JSON/YAML paths or explicit literals.

The contract never evaluates arbitrary code, fetches evidence, calls a model or
Provider, mutates a World State, runs reevaluation, releases an output, verifies
external truth, authorizes an action, or executes an action.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Mapping, Sequence

import yaml

from geotask_core.v1.correction_request import CorrectionRequest, load_correction_request
from geotask_core.v1.observation import Observation, load_observation
from geotask_core.v1.world_state import WorldState, load_world_state


RECOMPUTE_DERIVATION_RESULT_ARTIFACT_ID = "geotask.recompute-derivation-result"
RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-recompute-derivation-result-v0.1.schema.json"
)
RECOMPUTE_DERIVATION_RESULT_SCHEMA_VERSION = "0.1"
RECOMPUTE_DERIVATION_RESULT_FORMAT_VERSION = "0.1"

RECOMPUTE_DERIVATION_STATES = frozenset(
    {"completed", "partial", "blocked", "failed", "unknown"}
)
RECOMPUTE_ITEM_STATES = frozenset({"completed", "blocked", "failed", "unknown"})
RECOMPUTE_INPUT_KINDS = frozenset({"artifact_path", "literal"})
RECOMPUTE_METHODS = frozenset(
    {"copy_input", "subtract", "interval_gap_minus_delay_seconds"}
)
RECOMPUTE_DERIVATION_NEXT_ACTIONS = frozenset(
    {
        "materialize_successor_state",
        "continue_derivation",
        "request_evidence",
        "human_review",
    }
)


class RecomputeDerivationError(ValueError):
    """Raised when a recompute derivation contract or binding is invalid."""


def _fail(path: str, message: str) -> None:
    raise RecomputeDerivationError(f"{path}: {message}")


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


def _positive_integer(value: object, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        _fail(path, "must be an integer greater than or equal to 1")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        _fail(path, "must be a boolean")
    return value


def _timestamp(value: object, path: str) -> tuple[str, datetime]:
    text = _string(value, path)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RecomputeDerivationError(f"{path}: must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must include a timezone offset")
    return text, parsed


def _sha256(value: object, path: str) -> str:
    text = _string(value, path)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        _fail(path, "must be a lowercase 64-character SHA-256 hexadecimal digest")
    return text


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
    return tuple(items)


def _json_pointer(value: object, path: str) -> str:
    pointer = _string(value, path)
    if not pointer.startswith("/") or pointer.endswith("/"):
        _fail(path, "must be a non-root JSON Pointer without a trailing slash")
    segments = pointer.split("/")[1:]
    if any(not segment for segment in segments):
        _fail(path, "must not contain empty path segments")
    for segment in segments:
        index = 0
        while index < len(segment):
            if segment[index] == "~":
                if index + 1 >= len(segment) or segment[index + 1] not in {"0", "1"}:
                    _fail(path, "contains an invalid JSON Pointer escape")
                index += 2
            else:
                index += 1
    return pointer


def _resolve_pointer(payload: object, pointer: str) -> tuple[bool, object]:
    current = payload
    for raw_segment in pointer.split("/")[1:]:
        segment = raw_segment.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if segment not in current:
                return False, None
            current = current[segment]
        elif isinstance(current, Sequence) and not isinstance(
            current, (str, bytes, bytearray)
        ):
            if not segment.isdigit() or int(segment) >= len(current):
                return False, None
            current = current[int(segment)]
        else:
            return False, None
    return True, copy.deepcopy(current)


def _closed_refs(
    refs: Sequence[str],
    path: str,
    declared: AbstractSet[str],
    declaration_path: str,
) -> None:
    for index, ref in enumerate(refs):
        if ref not in declared:
            _fail(f"{path}[{index}]", f"must be declared in {declaration_path}: {ref!r}")


def _number(value: object, path: str) -> float | int:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        _fail(path, "must be a finite number")
    if isinstance(value, float) and not math.isfinite(value):
        _fail(path, "must be a finite number")
    return value


def _clock_seconds(value: object, path: str) -> int:
    text = _string(value, path)
    pieces = text.split(":")
    if len(pieces) not in {2, 3} or any(not piece.isdigit() for piece in pieces):
        _fail(path, "must be HH:MM or HH:MM:SS")
    hour, minute = int(pieces[0]), int(pieces[1])
    second = int(pieces[2]) if len(pieces) == 3 else 0
    if hour > 23 or minute > 59 or second > 59:
        _fail(path, "contains an out-of-range clock value")
    return hour * 3600 + minute * 60 + second


def _interval(value: object, path: str) -> tuple[int, int]:
    item = _mapping(value, path)
    if "start" not in item or "end" not in item:
        _fail(path, "must contain start and end")
    start = _clock_seconds(item["start"], f"{path}.start")
    end = _clock_seconds(item["end"], f"{path}.end")
    if end < start:
        _fail(path, "end must not precede start; midnight wrapping is not supported")
    return start, end


@dataclass(frozen=True)
class RecomputeArtifactRef:
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
class RecomputeWorldStateRef:
    ref_id: str
    artifact_id: str
    schema_version: str
    world_state_id: str
    revision: int
    as_of: str
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
            "semantic_fingerprint": self.semantic_fingerprint,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class RecomputeInput:
    name: str
    kind: str
    value: object
    source_ref: str | None = None
    pointer: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "kind": self.kind,
            "value": copy.deepcopy(self.value),
        }
        if self.source_ref is not None:
            payload["source_ref"] = self.source_ref
        if self.pointer is not None:
            payload["pointer"] = self.pointer
        return payload


@dataclass(frozen=True)
class RecomputeDerivation:
    id: str
    change_id: str
    target_path: str
    state: str
    method: str
    input_refs: tuple[str, ...]
    inputs: tuple[RecomputeInput, ...]
    reason: str
    basis_refs: tuple[str, ...]
    has_result: bool
    result: object

    def input_by_name(self) -> dict[str, RecomputeInput]:
        return {item.name: item for item in self.inputs}

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "change_id": self.change_id,
            "target_path": self.target_path,
            "state": self.state,
            "method": self.method,
            "input_refs": list(self.input_refs),
            "inputs": [
                item.to_dict() for item in sorted(self.inputs, key=lambda item: item.name)
            ],
            "reason": self.reason,
            "basis_refs": sorted(self.basis_refs),
        }
        if self.has_result:
            payload["result"] = copy.deepcopy(self.result)
        return payload


@dataclass(frozen=True)
class RecomputeValue:
    change_id: str
    value: object

    def to_dict(self) -> dict[str, object]:
        return {"change_id": self.change_id, "value": copy.deepcopy(self.value)}


@dataclass(frozen=True)
class RecomputeDerivationResult:
    derivation_id: str
    created_at: str
    state: str
    reason: str
    base_world_state: RecomputeWorldStateRef
    correction_request_ref: RecomputeArtifactRef
    source_artifact_refs: tuple[RecomputeArtifactRef, ...]
    derivations: tuple[RecomputeDerivation, ...]
    recompute_values: tuple[RecomputeValue, ...]
    next_action: str
    successor_materialized: bool
    reevaluation_executed: bool
    outputs_released: bool
    external_truth_verified: bool
    action_authorized: bool
    action_executed: bool

    def all_artifact_refs(self) -> tuple[RecomputeWorldStateRef | RecomputeArtifactRef, ...]:
        return (
            self.base_world_state,
            self.correction_request_ref,
            *self.source_artifact_refs,
        )

    def recompute_value_map(self) -> dict[str, object]:
        return {item.change_id: copy.deepcopy(item.value) for item in self.recompute_values}

    def to_dict(self) -> dict[str, object]:
        return {
            "recompute_derivation_result": {
                "schema_id": RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID,
                "schema_version": RECOMPUTE_DERIVATION_RESULT_SCHEMA_VERSION,
                "derivation_id": self.derivation_id,
                "created_at": self.created_at,
                "state": self.state,
                "reason": self.reason,
                "base_world_state": self.base_world_state.to_dict(),
                "correction_request_ref": self.correction_request_ref.to_dict(),
                "source_artifact_refs": [
                    item.to_dict()
                    for item in sorted(self.source_artifact_refs, key=lambda item: item.ref_id)
                ],
                "derivations": [
                    item.to_dict() for item in sorted(self.derivations, key=lambda item: item.id)
                ],
                "recompute_values": [
                    item.to_dict()
                    for item in sorted(self.recompute_values, key=lambda item: item.change_id)
                ],
                "next_action": self.next_action,
                "successor_materialized": self.successor_materialized,
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


def _load_world_state_ref(value: object) -> tuple[RecomputeWorldStateRef, datetime]:
    path = "recompute_derivation_result.base_world_state"
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={
            "ref_id",
            "artifact_id",
            "schema_version",
            "world_state_id",
            "revision",
            "as_of",
            "semantic_fingerprint",
            "content_sha256",
        },
    )
    if item["artifact_id"] != "geotask.world-state":
        _fail(f"{path}.artifact_id", "must equal 'geotask.world-state'")
    if item["schema_version"] != "0.1":
        _fail(f"{path}.schema_version", "must equal '0.1'")
    as_of_text, as_of = _timestamp(item["as_of"], f"{path}.as_of")
    return (
        RecomputeWorldStateRef(
            ref_id=_string(item["ref_id"], f"{path}.ref_id"),
            artifact_id="geotask.world-state",
            schema_version="0.1",
            world_state_id=_string(item["world_state_id"], f"{path}.world_state_id"),
            revision=_positive_integer(item["revision"], f"{path}.revision"),
            as_of=as_of_text,
            semantic_fingerprint=_sha256(
                item["semantic_fingerprint"], f"{path}.semantic_fingerprint"
            ),
            content_sha256=_sha256(item["content_sha256"], f"{path}.content_sha256"),
        ),
        as_of,
    )


def _load_artifact_ref(
    value: object,
    path: str,
    *,
    allowed_artifact_ids: AbstractSet[str],
) -> RecomputeArtifactRef:
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={"ref_id", "artifact_id", "schema_version", "instance_id", "content_sha256"},
    )
    artifact_id = _string(item["artifact_id"], f"{path}.artifact_id")
    if artifact_id not in allowed_artifact_ids:
        _fail(f"{path}.artifact_id", "must be one of: " + ", ".join(sorted(allowed_artifact_ids)))
    schema_version = _string(item["schema_version"], f"{path}.schema_version")
    expected_versions = {
        "geotask.correction-request": "0.1",
        "geotask.observation": "0.1",
        "geotask.document": "1.0",
    }
    if schema_version != expected_versions[artifact_id]:
        _fail(
            f"{path}.schema_version",
            f"must equal {expected_versions[artifact_id]!r} for {artifact_id}",
        )
    return RecomputeArtifactRef(
        ref_id=_string(item["ref_id"], f"{path}.ref_id"),
        artifact_id=artifact_id,
        schema_version=schema_version,
        instance_id=_string(item["instance_id"], f"{path}.instance_id"),
        content_sha256=_sha256(item["content_sha256"], f"{path}.content_sha256"),
    )


def _load_input(
    value: object,
    path: str,
    declared_source_refs: AbstractSet[str],
) -> RecomputeInput:
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={"name", "kind", "value"},
        optional={"source_ref", "pointer"},
    )
    kind = _enum(item["kind"], f"{path}.kind", RECOMPUTE_INPUT_KINDS)
    source_ref = _string(item["source_ref"], f"{path}.source_ref") if "source_ref" in item else None
    pointer = _json_pointer(item["pointer"], f"{path}.pointer") if "pointer" in item else None
    if kind == "artifact_path":
        if source_ref is None or pointer is None:
            _fail(path, "artifact_path inputs require source_ref and pointer")
        if source_ref not in declared_source_refs:
            _fail(f"{path}.source_ref", "must reference source_artifact_refs")
    elif source_ref is not None or pointer is not None:
        _fail(path, "literal inputs forbid source_ref and pointer")
    return RecomputeInput(
        name=_string(item["name"], f"{path}.name"),
        kind=kind,
        value=_json_value(item["value"], f"{path}.value"),
        source_ref=source_ref,
        pointer=pointer,
    )


def _load_derivations(
    value: object,
    *,
    declared_refs: AbstractSet[str],
    source_refs: AbstractSet[str],
) -> tuple[RecomputeDerivation, ...]:
    path = "recompute_derivation_result.derivations"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
        _fail(path, "must be a non-empty array")
    items: list[RecomputeDerivation] = []
    ids: set[str] = set()
    change_ids: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={
                "id",
                "change_id",
                "target_path",
                "state",
                "method",
                "input_refs",
                "inputs",
                "reason",
                "basis_refs",
            },
            optional={"result"},
        )
        identifier = _string(item["id"], f"{item_path}.id")
        change_id = _string(item["change_id"], f"{item_path}.change_id")
        if identifier in ids or change_id in change_ids:
            _fail(item_path, "id and change_id must each be unique")
        ids.add(identifier)
        change_ids.add(change_id)
        state = _enum(item["state"], f"{item_path}.state", RECOMPUTE_ITEM_STATES)
        method = _enum(item["method"], f"{item_path}.method", RECOMPUTE_METHODS)
        raw_inputs = item["inputs"]
        if not isinstance(raw_inputs, Sequence) or isinstance(raw_inputs, (str, bytes, bytearray)):
            _fail(f"{item_path}.inputs", "must be an array")
        inputs = tuple(
            _load_input(input_value, f"{item_path}.inputs[{input_index}]", source_refs)
            for input_index, input_value in enumerate(raw_inputs)
        )
        names = [input_item.name for input_item in inputs]
        if len(names) != len(set(names)):
            _fail(f"{item_path}.inputs", "input names must be unique")
        input_refs = _string_list(
            item["input_refs"], f"{item_path}.input_refs", non_empty=True
        )
        _closed_refs(input_refs, f"{item_path}.input_refs", set(names), "derivation inputs")
        basis_refs = _string_list(
            item["basis_refs"], f"{item_path}.basis_refs", non_empty=True
        )
        _closed_refs(
            basis_refs,
            f"{item_path}.basis_refs",
            declared_refs,
            "recompute_derivation_result artifact references",
        )
        has_result = "result" in item
        result_value = _json_value(item["result"], f"{item_path}.result") if has_result else None
        if state == "completed" and not has_result:
            _fail(item_path, "completed derivations require result")
        if state != "completed" and has_result:
            _fail(item_path, "non-completed derivations forbid result")
        items.append(
            RecomputeDerivation(
                id=identifier,
                change_id=change_id,
                target_path=_json_pointer(item["target_path"], f"{item_path}.target_path"),
                state=state,
                method=method,
                input_refs=input_refs,
                inputs=tuple(sorted(inputs, key=lambda input_item: input_item.name)),
                reason=_string(item["reason"], f"{item_path}.reason"),
                basis_refs=basis_refs,
                has_result=has_result,
                result=result_value,
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def _load_recompute_values(value: object) -> tuple[RecomputeValue, ...]:
    path = "recompute_derivation_result.recompute_values"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    items: list[RecomputeValue] = []
    ids: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(item, item_path, required={"change_id", "value"})
        change_id = _string(item["change_id"], f"{item_path}.change_id")
        if change_id in ids:
            _fail(f"{item_path}.change_id", f"duplicates {change_id!r}")
        ids.add(change_id)
        items.append(
            RecomputeValue(
                change_id=change_id,
                value=_json_value(item["value"], f"{item_path}.value"),
            )
        )
    return tuple(sorted(items, key=lambda item: item.change_id))


def _expected_state(derivations: Sequence[RecomputeDerivation]) -> str:
    states = {item.state for item in derivations}
    if "failed" in states:
        return "failed"
    if "blocked" in states:
        return "blocked"
    if "unknown" in states:
        return "partial" if "completed" in states else "unknown"
    return "completed"


def load_recompute_derivation_result(
    payload: Mapping[str, object],
) -> RecomputeDerivationResult:
    """Load and strictly validate one Recompute Derivation Result v0.1."""

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"recompute_derivation_result"})
    body = _mapping(root["recompute_derivation_result"], "recompute_derivation_result")
    _exact_fields(
        body,
        "recompute_derivation_result",
        required={
            "schema_id",
            "schema_version",
            "derivation_id",
            "created_at",
            "state",
            "reason",
            "base_world_state",
            "correction_request_ref",
            "source_artifact_refs",
            "derivations",
            "recompute_values",
            "next_action",
            "successor_materialized",
            "reevaluation_executed",
            "outputs_released",
            "external_truth_verified",
            "action_authorized",
            "action_executed",
        },
    )
    if body["schema_id"] != RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID:
        _fail(
            "recompute_derivation_result.schema_id",
            f"must equal {RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID!r}",
        )
    if body["schema_version"] != RECOMPUTE_DERIVATION_RESULT_SCHEMA_VERSION:
        _fail(
            "recompute_derivation_result.schema_version",
            f"must equal {RECOMPUTE_DERIVATION_RESULT_SCHEMA_VERSION!r}",
        )
    created_at_text, created_at = _timestamp(
        body["created_at"], "recompute_derivation_result.created_at"
    )
    base, base_as_of = _load_world_state_ref(body["base_world_state"])
    if created_at < base_as_of:
        _fail("recompute_derivation_result.created_at", "must not precede base as_of")
    correction_ref = _load_artifact_ref(
        body["correction_request_ref"],
        "recompute_derivation_result.correction_request_ref",
        allowed_artifact_ids={"geotask.correction-request"},
    )
    raw_source_refs = body["source_artifact_refs"]
    if not isinstance(raw_source_refs, Sequence) or isinstance(
        raw_source_refs, (str, bytes, bytearray)
    ) or not raw_source_refs:
        _fail("recompute_derivation_result.source_artifact_refs", "must be a non-empty array")
    source_refs = tuple(
        _load_artifact_ref(
            raw,
            f"recompute_derivation_result.source_artifact_refs[{index}]",
            allowed_artifact_ids={"geotask.observation", "geotask.document"},
        )
        for index, raw in enumerate(raw_source_refs)
    )
    all_refs = (base, correction_ref, *source_refs)
    ref_ids = [item.ref_id for item in all_refs]
    if len(ref_ids) != len(set(ref_ids)):
        _fail("recompute_derivation_result artifact references", "ref_id values must be unique")
    source_ref_ids = frozenset(item.ref_id for item in source_refs)
    derivations = _load_derivations(
        body["derivations"],
        declared_refs=frozenset(ref_ids),
        source_refs=source_ref_ids,
    )
    recompute_values = _load_recompute_values(body["recompute_values"])
    completed = {
        item.change_id: item.result
        for item in derivations
        if item.state == "completed"
    }
    declared_values = {item.change_id: item.value for item in recompute_values}
    if completed != declared_values:
        _fail(
            "recompute_derivation_result.recompute_values",
            "must exactly equal completed derivation results",
        )
    state = _enum(
        body["state"],
        "recompute_derivation_result.state",
        RECOMPUTE_DERIVATION_STATES,
    )
    expected_state = _expected_state(derivations)
    if state != expected_state:
        _fail(
            "recompute_derivation_result.state",
            f"must equal aggregate state {expected_state!r}",
        )
    next_action = _enum(
        body["next_action"],
        "recompute_derivation_result.next_action",
        RECOMPUTE_DERIVATION_NEXT_ACTIONS,
    )
    if state == "completed" and next_action != "materialize_successor_state":
        _fail("recompute_derivation_result.next_action", "completed state requires materialization")
    if state in {"partial", "failed"} and next_action != "continue_derivation":
        _fail("recompute_derivation_result.next_action", f"state {state!r} requires continue_derivation")
    if state in {"blocked", "unknown"} and next_action not in {
        "request_evidence",
        "human_review",
    }:
        _fail("recompute_derivation_result.next_action", "blocked/unknown requires evidence or review")
    boundary_fields = {
        name: _boolean(body[name], f"recompute_derivation_result.{name}")
        for name in (
            "successor_materialized",
            "reevaluation_executed",
            "outputs_released",
            "external_truth_verified",
            "action_authorized",
            "action_executed",
        )
    }
    if any(boundary_fields.values()):
        _fail(
            "recompute_derivation_result",
            "derivation must keep materialization, reevaluation, release, truth, authorization, and execution false",
        )
    return RecomputeDerivationResult(
        derivation_id=_string(body["derivation_id"], "recompute_derivation_result.derivation_id"),
        created_at=created_at_text,
        state=state,
        reason=_string(body["reason"], "recompute_derivation_result.reason"),
        base_world_state=base,
        correction_request_ref=correction_ref,
        source_artifact_refs=tuple(sorted(source_refs, key=lambda item: item.ref_id)),
        derivations=derivations,
        recompute_values=recompute_values,
        next_action=next_action,
        successor_materialized=False,
        reevaluation_executed=False,
        outputs_released=False,
        external_truth_verified=False,
        action_authorized=False,
        action_executed=False,
    )


def _evaluate_derivation(item: RecomputeDerivation) -> object:
    values = item.input_by_name()
    operands = [values[name].value for name in item.input_refs]
    if item.method == "copy_input":
        if len(operands) != 1:
            _fail(f"derivations[{item.id!r}].input_refs", "copy_input requires one operand")
        return copy.deepcopy(operands[0])
    if item.method == "subtract":
        if len(operands) != 2:
            _fail(f"derivations[{item.id!r}].input_refs", "subtract requires two operands")
        left = _number(operands[0], f"derivations[{item.id!r}].input_refs[0]")
        right = _number(operands[1], f"derivations[{item.id!r}].input_refs[1]")
        return left - right
    if len(operands) != 3:
        _fail(
            f"derivations[{item.id!r}].input_refs",
            "interval_gap_minus_delay_seconds requires three operands",
        )
    _first_start, first_end = _interval(
        operands[0], f"derivations[{item.id!r}].input_refs[0]"
    )
    second_start, _second_end = _interval(
        operands[1], f"derivations[{item.id!r}].input_refs[1]"
    )
    delay = _number(operands[2], f"derivations[{item.id!r}].input_refs[2]")
    gap = second_start - first_end
    if gap < 0:
        _fail(
            f"derivations[{item.id!r}]",
            "interval order produces a negative base gap; reverse ordering is not supported",
        )
    return gap - delay


def evaluate_recompute_derivations(
    result: RecomputeDerivationResult,
) -> dict[str, object]:
    """Evaluate every completed allowlisted derivation and return change values."""

    if result.state != "completed":
        _fail("recompute_derivation_result.state", "must be completed before values are consumed")
    values: dict[str, object] = {}
    for item in result.derivations:
        computed = _evaluate_derivation(item)
        if not item.has_result or computed != item.result:
            _fail(
                f"recompute_derivation_result.derivations[{item.id!r}].result",
                f"does not equal deterministic result {computed!r}",
            )
        values[item.change_id] = copy.deepcopy(computed)
    if values != result.recompute_value_map():
        _fail("recompute_derivation_result.recompute_values", "does not match evaluated results")
    return values


def _decode_artifact(content: bytes, path: str) -> Mapping[str, object]:
    if not isinstance(content, bytes):
        _fail(path, "must be bytes")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RecomputeDerivationError(f"{path}: must be UTF-8") from exc
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RecomputeDerivationError(f"{path}: must be valid JSON or YAML") from exc
    return _mapping(payload, path)


def validate_recompute_derivation_bindings(
    result: RecomputeDerivationResult,
    base_world_state: WorldState,
    correction_request: CorrectionRequest,
    source_artifacts: Mapping[str, Mapping[str, object]],
    artifact_contents: Mapping[str, bytes],
) -> None:
    """Validate exact bytes, source paths, request coverage, and deterministic values."""

    checks = (
        ("world_state_id", result.base_world_state.world_state_id, base_world_state.world_state_id),
        ("revision", result.base_world_state.revision, base_world_state.revision),
        ("as_of", result.base_world_state.as_of, base_world_state.as_of),
        (
            "semantic_fingerprint",
            result.base_world_state.semantic_fingerprint,
            base_world_state.semantic_fingerprint(),
        ),
    )
    for field, declared, actual in checks:
        if declared != actual:
            _fail(
                f"recompute_derivation_result.base_world_state.{field}",
                f"does not match bound World State: expected {actual!r}",
            )
    if result.correction_request_ref.instance_id != correction_request.request_id:
        _fail("recompute_derivation_result.correction_request_ref.instance_id", "does not match request_id")
    if correction_request.state != "required":
        _fail("correction_request.state", "recompute derivation requires state 'required'")
    if correction_request.base_world_state.semantic_fingerprint != base_world_state.semantic_fingerprint():
        _fail("correction_request.base_world_state", "does not match bound base World State")

    source_refs = {item.ref_id: item for item in result.source_artifact_refs}
    if set(source_artifacts) != set(source_refs):
        _fail("source_artifacts", "keys must exactly match source_artifact_refs")
    expected_hashes = {
        item.ref_id: item.content_sha256 for item in result.all_artifact_refs()
    }
    if set(artifact_contents) != set(expected_hashes):
        _fail("artifact_contents", "keys must exactly match all declared Artifact refs")
    decoded: dict[str, Mapping[str, object]] = {}
    for ref_id, expected_hash in expected_hashes.items():
        content = artifact_contents[ref_id]
        if hashlib.sha256(content).hexdigest() != expected_hash:
            _fail(f"artifact_contents[{ref_id!r}]", "SHA-256 mismatch")
        decoded[ref_id] = _decode_artifact(content, f"artifact_contents[{ref_id!r}]")

    exact_base = load_world_state(decoded[result.base_world_state.ref_id])
    exact_request = load_correction_request(decoded[result.correction_request_ref.ref_id])
    if exact_base != base_world_state or exact_request != correction_request:
        _fail("artifact_contents", "base/request objects do not match exact bytes")

    request_support = {
        item.ref_id: item for item in correction_request.supporting_artifact_refs
    }
    loaded_sources: dict[str, object] = {}
    for ref_id, ref in source_refs.items():
        supplied = source_artifacts[ref_id]
        if supplied != decoded[ref_id]:
            _fail(f"source_artifacts[{ref_id!r}]", "does not match exact source bytes")
        if ref.artifact_id == "geotask.observation":
            observation = load_observation(decoded[ref_id])
            loaded_sources[ref_id] = observation
            if observation.observation_id != ref.instance_id:
                _fail(f"source_artifact_refs[{ref_id!r}].instance_id", "does not match observation_id")
            if observation.observation_id not in correction_request.observation_refs:
                _fail(f"source_artifact_refs[{ref_id!r}]", "Observation is absent from request observation_refs")
            if observation.source.reference not in correction_request.evidence_refs:
                _fail(f"source_artifact_refs[{ref_id!r}]", "Observation source is absent from request evidence_refs")
        else:
            loaded_sources[ref_id] = decoded[ref_id]
            geotask = _mapping(decoded[ref_id].get("geotask"), f"source_artifacts[{ref_id!r}].geotask")
            if geotask.get("id") != ref.instance_id:
                _fail(f"source_artifact_refs[{ref_id!r}].instance_id", "does not match geotask.id")
            if ref_id not in request_support:
                _fail(
                    f"source_artifact_refs[{ref_id!r}]",
                    "GeoTask Document source must be declared in Correction Request supporting_artifact_refs",
                )
        if ref_id in request_support:
            request_ref = request_support[ref_id]
            if (
                request_ref.artifact_id != ref.artifact_id
                or request_ref.schema_version != ref.schema_version
                or request_ref.instance_id != ref.instance_id
                or request_ref.content_sha256 != ref.content_sha256
            ):
                _fail(f"source_artifact_refs[{ref_id!r}]", "does not preserve request supporting Artifact binding")

    recompute_changes = {
        item.id: item
        for item in correction_request.changes
        if item.operation == "recompute"
    }
    if {item.change_id for item in result.derivations} != set(recompute_changes):
        _fail("recompute_derivation_result.derivations", "must cover every recompute change exactly once")
    created_at = _timestamp(result.created_at, "recompute_derivation_result.created_at")[1]
    base_as_of = _timestamp(base_world_state.as_of, "base_world_state.as_of")[1]

    for derivation in result.derivations:
        change = recompute_changes[derivation.change_id]
        if derivation.target_path != change.target_path:
            _fail(f"derivations[{derivation.id!r}].target_path", "does not match Correction Request change")
        input_map = derivation.input_by_name()
        if set(input_map) != set(change.input_fields):
            _fail(
                f"derivations[{derivation.id!r}].inputs",
                "input names must exactly match Correction Request input_fields",
            )
        used_sources = {
            item.source_ref
            for item in derivation.inputs
            if item.kind == "artifact_path" and item.source_ref is not None
        }
        required_basis = {result.correction_request_ref.ref_id, *used_sources}
        if not required_basis.issubset(derivation.basis_refs):
            _fail(
                f"derivations[{derivation.id!r}].basis_refs",
                "must include Correction Request and every used source Artifact ref",
            )
        for input_item in derivation.inputs:
            if input_item.kind == "artifact_path":
                exists, actual = _resolve_pointer(
                    decoded[input_item.source_ref], input_item.pointer
                )
                if not exists:
                    _fail(
                        f"derivations[{derivation.id!r}].inputs[{input_item.name!r}].pointer",
                        "does not resolve in exact source Artifact",
                    )
                if actual != input_item.value:
                    _fail(
                        f"derivations[{derivation.id!r}].inputs[{input_item.name!r}].value",
                        f"does not match exact source value {actual!r}",
                    )
        if "calculation_method" in input_map and input_map["calculation_method"].value != derivation.method:
            _fail(
                f"derivations[{derivation.id!r}].inputs['calculation_method']",
                "must equal derivation method",
            )
        if "verified_at" in input_map:
            _text, verified_at = _timestamp(
                input_map["verified_at"].value,
                f"derivations[{derivation.id!r}].inputs['verified_at'].value",
            )
            if verified_at < base_as_of or verified_at > created_at:
                _fail(
                    f"derivations[{derivation.id!r}].inputs['verified_at'].value",
                    "must be between base as_of and derivation created_at",
                )

    evaluate_recompute_derivations(result)


def __all_public() -> list[str]:
    return [
        "RECOMPUTE_DERIVATION_RESULT_ARTIFACT_ID",
        "RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID",
        "RECOMPUTE_DERIVATION_RESULT_SCHEMA_VERSION",
        "RECOMPUTE_DERIVATION_RESULT_FORMAT_VERSION",
        "RECOMPUTE_DERIVATION_STATES",
        "RECOMPUTE_ITEM_STATES",
        "RECOMPUTE_INPUT_KINDS",
        "RECOMPUTE_METHODS",
        "RECOMPUTE_DERIVATION_NEXT_ACTIONS",
        "RecomputeDerivationError",
        "RecomputeArtifactRef",
        "RecomputeWorldStateRef",
        "RecomputeInput",
        "RecomputeDerivation",
        "RecomputeValue",
        "RecomputeDerivationResult",
        "load_recompute_derivation_result",
        "evaluate_recompute_derivations",
        "validate_recompute_derivation_bindings",
    ]


__all__ = __all_public()
