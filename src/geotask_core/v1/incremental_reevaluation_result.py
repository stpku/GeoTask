"""Public Incremental Reevaluation Result v0.1 contract.

The artifact records one bounded reevaluation of an exact Impact Graph against an
immutable base World State and one explicit successor World State. It closes the
loop across graph nodes, reevaluation targets, Correction Request acceptance
criteria, discrepancy outcomes, and output/action gates.

Strict loading validates only the authored result. Binding validation checks exact
source bytes, snapshot identity and revision ordering, graph/request/report
coverage, requested-path confinement, immutable-path preservation, execution-result
bindings, and declared outcome semantics. It does not execute a task, generate a
successor World State, discover impact, release an external output, authorize an
action, or execute an action.
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
    CorrectionRequest,
    load_correction_request,
)
from geotask_core.v1.discrepancy_report import (
    DiscrepancyFinding,
    DiscrepancyReport,
    load_discrepancy_report,
)
from geotask_core.v1.impact_graph import ImpactGraph, load_impact_graph
from geotask_core.v1.result import GeotaskResult
from geotask_core.v1.world_state import WorldState, load_world_state


INCREMENTAL_REEVALUATION_RESULT_ARTIFACT_ID = (
    "geotask.incremental-reevaluation-result"
)
INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-incremental-reevaluation-result-v0.1.schema.json"
)
INCREMENTAL_REEVALUATION_RESULT_SCHEMA_VERSION = "0.1"
INCREMENTAL_REEVALUATION_RESULT_FORMAT_VERSION = "0.1"

INCREMENTAL_REEVALUATION_STATES = frozenset(
    {"completed", "partial", "blocked", "failed", "unknown"}
)
NODE_RESULT_STATES = frozenset(
    {
        "preserved",
        "recomputed",
        "resolved",
        "invalidated",
        "released",
        "eligible",
        "blocked",
        "failed",
        "unknown",
    }
)
TARGET_RESULT_STATES = frozenset(
    {"completed", "blocked", "failed", "unknown", "not_required"}
)
ACCEPTANCE_RESULT_STATES = frozenset(
    {"satisfied", "failed", "blocked", "unknown"}
)
DISCREPANCY_RESULT_STATES = frozenset({"resolved", "unresolved", "unknown"})
OUTPUT_GATE_STATES = frozenset({"released", "blocked", "unknown"})
ACTION_GATE_STATES = frozenset({"eligible", "blocked", "unknown"})
INCREMENTAL_REEVALUATION_NEXT_ACTIONS = frozenset(
    {"none", "continue_reevaluation", "request_evidence", "human_review"}
)


class IncrementalReevaluationResultFormatError(ValueError):
    """Raised when an Incremental Reevaluation Result violates v0.1."""


def _fail(path: str, message: str) -> None:
    raise IncrementalReevaluationResultFormatError(f"{path}: {message}")


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
        raise IncrementalReevaluationResultFormatError(
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


def _closed_refs(
    refs: Sequence[str],
    path: str,
    declared: AbstractSet[str],
    declaration_path: str,
) -> None:
    for index, ref in enumerate(refs):
        if ref not in declared:
            _fail(f"{path}[{index}]", f"must be declared in {declaration_path}: {ref!r}")


def _decode_pointer_segments(pointer: str) -> tuple[str, ...]:
    if not pointer.startswith("/") or pointer.endswith("/"):
        _fail("identity path", "must be a non-root JSON Pointer without a trailing slash")
    return tuple(
        segment.replace("~1", "/").replace("~0", "~")
        for segment in pointer.split("/")[1:]
    )


def _resolve_nested(value: object, segments: Sequence[str]) -> tuple[bool, object]:
    current = value
    for segment in segments:
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


def _resolve_world_state_path(
    world_state: WorldState,
    pointer: str,
) -> tuple[bool, object]:
    segments = _decode_pointer_segments(pointer)
    if len(segments) < 2:
        return False, None
    if segments[0] == "objects":
        world_object = next((item for item in world_state.objects if item.id == segments[1]), None)
        if world_object is None:
            return False, None
        if len(segments) >= 4 and segments[2] == "attributes":
            attribute = next(
                (item for item in world_object.attributes if item.name == segments[3]),
                None,
            )
            if attribute is None:
                return False, None
            return _resolve_nested(attribute.to_dict(), segments[4:])
        return _resolve_nested(world_object.to_dict(), segments[2:])
    if segments[0] == "relations":
        relation = next((item for item in world_state.relations if item.id == segments[1]), None)
        if relation is None:
            return False, None
        return _resolve_nested(relation.to_dict(), segments[2:])
    return False, None


def _path_within(path: str, parent: str) -> bool:
    return path == parent or path.startswith(parent + "/")


def _flatten_world_state(world_state: WorldState) -> dict[str, object]:
    flattened: dict[str, object] = {}

    def visit(value: object, prefix: str) -> None:
        if isinstance(value, Mapping):
            for key in sorted(value):
                visit(value[key], f"{prefix}/{key}")
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, item in enumerate(value):
                visit(item, f"{prefix}/{index}")
            return
        flattened[prefix] = copy.deepcopy(value)

    for world_object in world_state.objects:
        object_dict = world_object.to_dict()
        attributes = object_dict.pop("attributes")
        visit(object_dict, f"/objects/{world_object.id}")
        for attribute in attributes:
            name = attribute["name"]
            visit(attribute, f"/objects/{world_object.id}/attributes/{name}")
    for relation in world_state.relations:
        visit(relation.to_dict(), f"/relations/{relation.id}")
    return flattened


@dataclass(frozen=True)
class ReevaluationArtifactRef:
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
class ReevaluationWorldStateRef:
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
class ReevaluationNodeResult:
    id: str
    node_ref: str
    state: str
    reason: str
    basis_refs: tuple[str, ...]
    has_previous: bool = False
    previous: object = None
    has_current: bool = False
    current: object = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "node_ref": self.node_ref,
            "state": self.state,
            "reason": self.reason,
            "basis_refs": sorted(self.basis_refs),
        }
        if self.has_previous:
            payload["previous"] = copy.deepcopy(self.previous)
        if self.has_current:
            payload["current"] = copy.deepcopy(self.current)
        return payload


@dataclass(frozen=True)
class ReevaluationTargetResult:
    id: str
    target_ref: str
    node_ref: str
    node_result_ref: str
    state: str
    reason: str
    basis_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "target_ref": self.target_ref,
            "node_ref": self.node_ref,
            "node_result_ref": self.node_result_ref,
            "state": self.state,
            "reason": self.reason,
            "basis_refs": sorted(self.basis_refs),
        }


@dataclass(frozen=True)
class ReevaluationAcceptanceResult:
    id: str
    request_ref: str
    criterion_id: str
    state: str
    reason: str
    node_result_refs: tuple[str, ...]
    target_result_refs: tuple[str, ...]
    basis_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "request_ref": self.request_ref,
            "criterion_id": self.criterion_id,
            "state": self.state,
            "reason": self.reason,
            "node_result_refs": sorted(self.node_result_refs),
            "target_result_refs": sorted(self.target_result_refs),
            "basis_refs": sorted(self.basis_refs),
        }


@dataclass(frozen=True)
class ReevaluationDiscrepancyResult:
    id: str
    request_ref: str
    discrepancy_ref: str
    state: str
    reason: str
    node_result_refs: tuple[str, ...]
    basis_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "request_ref": self.request_ref,
            "discrepancy_ref": self.discrepancy_ref,
            "state": self.state,
            "reason": self.reason,
            "node_result_refs": sorted(self.node_result_refs),
            "basis_refs": sorted(self.basis_refs),
        }


@dataclass(frozen=True)
class ReevaluationOutputGateResult:
    output_ref: str
    state: str
    reason: str
    target_result_refs: tuple[str, ...]
    criterion_result_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "output_ref": self.output_ref,
            "state": self.state,
            "reason": self.reason,
            "target_result_refs": sorted(self.target_result_refs),
            "criterion_result_refs": sorted(self.criterion_result_refs),
        }


@dataclass(frozen=True)
class ReevaluationActionGateResult:
    action_ref: str
    state: str
    reason: str
    output_refs: tuple[str, ...]
    criterion_result_refs: tuple[str, ...]
    external_authorization_required: bool
    authorized: bool
    executed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "action_ref": self.action_ref,
            "state": self.state,
            "reason": self.reason,
            "output_refs": sorted(self.output_refs),
            "criterion_result_refs": sorted(self.criterion_result_refs),
            "external_authorization_required": self.external_authorization_required,
            "authorized": self.authorized,
            "executed": self.executed,
        }


@dataclass(frozen=True)
class IncrementalReevaluationResult:
    result_id: str
    recorded_at: str
    state: str
    reason: str
    base_world_state: ReevaluationWorldStateRef
    successor_world_state: ReevaluationWorldStateRef
    impact_graph_ref: ReevaluationArtifactRef
    correction_request_refs: tuple[ReevaluationArtifactRef, ...]
    discrepancy_report_refs: tuple[ReevaluationArtifactRef, ...]
    execution_result_refs: tuple[ReevaluationArtifactRef, ...]
    node_results: tuple[ReevaluationNodeResult, ...]
    target_results: tuple[ReevaluationTargetResult, ...]
    acceptance_results: tuple[ReevaluationAcceptanceResult, ...]
    discrepancy_results: tuple[ReevaluationDiscrepancyResult, ...]
    output_gates: tuple[ReevaluationOutputGateResult, ...]
    action_gates: tuple[ReevaluationActionGateResult, ...]
    next_action: str

    def all_artifact_refs(self) -> tuple[ReevaluationWorldStateRef | ReevaluationArtifactRef, ...]:
        return (
            self.base_world_state,
            self.successor_world_state,
            self.impact_graph_ref,
            *self.correction_request_refs,
            *self.discrepancy_report_refs,
            *self.execution_result_refs,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "incremental_reevaluation_result": {
                "schema_id": INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID,
                "schema_version": INCREMENTAL_REEVALUATION_RESULT_SCHEMA_VERSION,
                "result_id": self.result_id,
                "recorded_at": self.recorded_at,
                "state": self.state,
                "reason": self.reason,
                "base_world_state": self.base_world_state.to_dict(),
                "successor_world_state": self.successor_world_state.to_dict(),
                "impact_graph_ref": self.impact_graph_ref.to_dict(),
                "correction_request_refs": [
                    item.to_dict()
                    for item in sorted(self.correction_request_refs, key=lambda item: item.ref_id)
                ],
                "discrepancy_report_refs": [
                    item.to_dict()
                    for item in sorted(self.discrepancy_report_refs, key=lambda item: item.ref_id)
                ],
                "execution_result_refs": [
                    item.to_dict()
                    for item in sorted(self.execution_result_refs, key=lambda item: item.ref_id)
                ],
                "node_results": [
                    item.to_dict() for item in sorted(self.node_results, key=lambda item: item.id)
                ],
                "target_results": [
                    item.to_dict() for item in sorted(self.target_results, key=lambda item: item.id)
                ],
                "acceptance_results": [
                    item.to_dict() for item in sorted(self.acceptance_results, key=lambda item: item.id)
                ],
                "discrepancy_results": [
                    item.to_dict() for item in sorted(self.discrepancy_results, key=lambda item: item.id)
                ],
                "output_gates": [
                    item.to_dict() for item in sorted(self.output_gates, key=lambda item: item.output_ref)
                ],
                "action_gates": [
                    item.to_dict() for item in sorted(self.action_gates, key=lambda item: item.action_ref)
                ],
                "next_action": self.next_action,
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


def _load_world_state_ref(value: object, path: str) -> tuple[ReevaluationWorldStateRef, datetime]:
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
        ReevaluationWorldStateRef(
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
    artifact_id: str,
    schema_version: str,
) -> ReevaluationArtifactRef:
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={"ref_id", "artifact_id", "schema_version", "instance_id", "content_sha256"},
    )
    if item["artifact_id"] != artifact_id:
        _fail(f"{path}.artifact_id", f"must equal {artifact_id!r}")
    if item["schema_version"] != schema_version:
        _fail(f"{path}.schema_version", f"must equal {schema_version!r}")
    return ReevaluationArtifactRef(
        ref_id=_string(item["ref_id"], f"{path}.ref_id"),
        artifact_id=artifact_id,
        schema_version=schema_version,
        instance_id=_string(item["instance_id"], f"{path}.instance_id"),
        content_sha256=_sha256(item["content_sha256"], f"{path}.content_sha256"),
    )


def _load_artifact_refs(
    value: object,
    path: str,
    *,
    artifact_id: str,
    schema_version: str,
) -> tuple[ReevaluationArtifactRef, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be a non-empty array")
    if not value:
        _fail(path, "must contain at least one item")
    items = tuple(
        _load_artifact_ref(
            item,
            f"{path}[{index}]",
            artifact_id=artifact_id,
            schema_version=schema_version,
        )
        for index, item in enumerate(value)
    )
    ref_ids = [item.ref_id for item in items]
    if len(ref_ids) != len(set(ref_ids)):
        _fail(path, "contains duplicate ref_id values")
    return tuple(sorted(items, key=lambda item: item.ref_id))


def _load_node_results(
    value: object,
    declared_artifact_refs: AbstractSet[str],
) -> tuple[ReevaluationNodeResult, ...]:
    path = "incremental_reevaluation_result.node_results"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
        _fail(path, "must be a non-empty array")
    items: list[ReevaluationNodeResult] = []
    ids: set[str] = set()
    node_refs: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={"id", "node_ref", "state", "reason", "basis_refs"},
            optional={"previous", "current"},
        )
        identifier = _string(item["id"], f"{item_path}.id")
        node_ref = _string(item["node_ref"], f"{item_path}.node_ref")
        if identifier in ids or node_ref in node_refs:
            _fail(item_path, "id and node_ref must each be unique")
        ids.add(identifier)
        node_refs.add(node_ref)
        state = _enum(item["state"], f"{item_path}.state", NODE_RESULT_STATES)
        has_previous = "previous" in item
        has_current = "current" in item
        previous = _json_value(item["previous"], f"{item_path}.previous") if has_previous else None
        current = _json_value(item["current"], f"{item_path}.current") if has_current else None
        if state == "preserved" and (not has_previous or not has_current or previous != current):
            _fail(item_path, "state 'preserved' requires equal previous and current values")
        if state == "recomputed" and (not has_previous or not has_current):
            _fail(item_path, "state 'recomputed' requires previous and current values")
        if state == "invalidated" and (not has_previous or has_current):
            _fail(item_path, "state 'invalidated' requires previous and forbids current")
        basis_refs = _string_list(item["basis_refs"], f"{item_path}.basis_refs", non_empty=True)
        _closed_refs(
            basis_refs,
            f"{item_path}.basis_refs",
            declared_artifact_refs,
            "incremental_reevaluation_result artifact references",
        )
        items.append(
            ReevaluationNodeResult(
                id=identifier,
                node_ref=node_ref,
                state=state,
                reason=_string(item["reason"], f"{item_path}.reason"),
                basis_refs=tuple(sorted(basis_refs)),
                has_previous=has_previous,
                previous=previous,
                has_current=has_current,
                current=current,
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def _load_target_results(
    value: object,
    *,
    node_results: Mapping[str, ReevaluationNodeResult],
    declared_artifact_refs: AbstractSet[str],
) -> tuple[ReevaluationTargetResult, ...]:
    path = "incremental_reevaluation_result.target_results"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
        _fail(path, "must be a non-empty array")
    items: list[ReevaluationTargetResult] = []
    ids: set[str] = set()
    target_refs: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={
                "id",
                "target_ref",
                "node_ref",
                "node_result_ref",
                "state",
                "reason",
                "basis_refs",
            },
        )
        identifier = _string(item["id"], f"{item_path}.id")
        target_ref = _string(item["target_ref"], f"{item_path}.target_ref")
        node_result_ref = _string(item["node_result_ref"], f"{item_path}.node_result_ref")
        if identifier in ids or target_ref in target_refs:
            _fail(item_path, "id and target_ref must each be unique")
        if node_result_ref not in node_results:
            _fail(f"{item_path}.node_result_ref", "must reference node_results")
        ids.add(identifier)
        target_refs.add(target_ref)
        node_ref = _string(item["node_ref"], f"{item_path}.node_ref")
        if node_results[node_result_ref].node_ref != node_ref:
            _fail(f"{item_path}.node_ref", "must match the referenced node result")
        basis_refs = _string_list(item["basis_refs"], f"{item_path}.basis_refs", non_empty=True)
        _closed_refs(
            basis_refs,
            f"{item_path}.basis_refs",
            declared_artifact_refs,
            "incremental_reevaluation_result artifact references",
        )
        items.append(
            ReevaluationTargetResult(
                id=identifier,
                target_ref=target_ref,
                node_ref=node_ref,
                node_result_ref=node_result_ref,
                state=_enum(item["state"], f"{item_path}.state", TARGET_RESULT_STATES),
                reason=_string(item["reason"], f"{item_path}.reason"),
                basis_refs=tuple(sorted(basis_refs)),
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def _load_acceptance_results(
    value: object,
    *,
    request_refs: AbstractSet[str],
    node_result_refs: AbstractSet[str],
    target_result_refs: AbstractSet[str],
    declared_artifact_refs: AbstractSet[str],
) -> tuple[ReevaluationAcceptanceResult, ...]:
    path = "incremental_reevaluation_result.acceptance_results"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
        _fail(path, "must be a non-empty array")
    items: list[ReevaluationAcceptanceResult] = []
    ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={
                "id",
                "request_ref",
                "criterion_id",
                "state",
                "reason",
                "node_result_refs",
                "target_result_refs",
                "basis_refs",
            },
        )
        identifier = _string(item["id"], f"{item_path}.id")
        request_ref = _string(item["request_ref"], f"{item_path}.request_ref")
        criterion_id = _string(item["criterion_id"], f"{item_path}.criterion_id")
        pair = (request_ref, criterion_id)
        if identifier in ids or pair in pairs:
            _fail(item_path, "id and request/criterion pair must each be unique")
        if request_ref not in request_refs:
            _fail(f"{item_path}.request_ref", "must reference correction_request_refs")
        ids.add(identifier)
        pairs.add(pair)
        node_refs = _string_list(item["node_result_refs"], f"{item_path}.node_result_refs")
        target_refs = _string_list(item["target_result_refs"], f"{item_path}.target_result_refs")
        _closed_refs(node_refs, f"{item_path}.node_result_refs", node_result_refs, "node_results")
        _closed_refs(target_refs, f"{item_path}.target_result_refs", target_result_refs, "target_results")
        basis_refs = _string_list(item["basis_refs"], f"{item_path}.basis_refs", non_empty=True)
        _closed_refs(
            basis_refs,
            f"{item_path}.basis_refs",
            declared_artifact_refs,
            "incremental_reevaluation_result artifact references",
        )
        items.append(
            ReevaluationAcceptanceResult(
                id=identifier,
                request_ref=request_ref,
                criterion_id=criterion_id,
                state=_enum(
                    item["state"], f"{item_path}.state", ACCEPTANCE_RESULT_STATES
                ),
                reason=_string(item["reason"], f"{item_path}.reason"),
                node_result_refs=tuple(sorted(node_refs)),
                target_result_refs=tuple(sorted(target_refs)),
                basis_refs=tuple(sorted(basis_refs)),
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def _load_discrepancy_results(
    value: object,
    *,
    request_refs: AbstractSet[str],
    node_result_refs: AbstractSet[str],
    declared_artifact_refs: AbstractSet[str],
) -> tuple[ReevaluationDiscrepancyResult, ...]:
    path = "incremental_reevaluation_result.discrepancy_results"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
        _fail(path, "must be a non-empty array")
    items: list[ReevaluationDiscrepancyResult] = []
    ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={
                "id",
                "request_ref",
                "discrepancy_ref",
                "state",
                "reason",
                "node_result_refs",
                "basis_refs",
            },
        )
        identifier = _string(item["id"], f"{item_path}.id")
        request_ref = _string(item["request_ref"], f"{item_path}.request_ref")
        discrepancy_ref = _string(item["discrepancy_ref"], f"{item_path}.discrepancy_ref")
        pair = (request_ref, discrepancy_ref)
        if identifier in ids or pair in pairs:
            _fail(item_path, "id and request/discrepancy pair must each be unique")
        if request_ref not in request_refs:
            _fail(f"{item_path}.request_ref", "must reference correction_request_refs")
        ids.add(identifier)
        pairs.add(pair)
        node_refs = _string_list(
            item["node_result_refs"], f"{item_path}.node_result_refs", non_empty=True
        )
        _closed_refs(node_refs, f"{item_path}.node_result_refs", node_result_refs, "node_results")
        basis_refs = _string_list(item["basis_refs"], f"{item_path}.basis_refs", non_empty=True)
        _closed_refs(
            basis_refs,
            f"{item_path}.basis_refs",
            declared_artifact_refs,
            "incremental_reevaluation_result artifact references",
        )
        items.append(
            ReevaluationDiscrepancyResult(
                id=identifier,
                request_ref=request_ref,
                discrepancy_ref=discrepancy_ref,
                state=_enum(
                    item["state"], f"{item_path}.state", DISCREPANCY_RESULT_STATES
                ),
                reason=_string(item["reason"], f"{item_path}.reason"),
                node_result_refs=tuple(sorted(node_refs)),
                basis_refs=tuple(sorted(basis_refs)),
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def _load_output_gates(
    value: object,
    *,
    target_result_refs: AbstractSet[str],
    criterion_result_refs: AbstractSet[str],
) -> tuple[ReevaluationOutputGateResult, ...]:
    path = "incremental_reevaluation_result.output_gates"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    items: list[ReevaluationOutputGateResult] = []
    refs: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={"output_ref", "state", "reason", "target_result_refs", "criterion_result_refs"},
        )
        output_ref = _string(item["output_ref"], f"{item_path}.output_ref")
        if output_ref in refs:
            _fail(f"{item_path}.output_ref", f"duplicates {output_ref!r}")
        refs.add(output_ref)
        targets = _string_list(item["target_result_refs"], f"{item_path}.target_result_refs")
        criteria = _string_list(
            item["criterion_result_refs"], f"{item_path}.criterion_result_refs"
        )
        _closed_refs(targets, f"{item_path}.target_result_refs", target_result_refs, "target_results")
        _closed_refs(
            criteria,
            f"{item_path}.criterion_result_refs",
            criterion_result_refs,
            "acceptance_results",
        )
        items.append(
            ReevaluationOutputGateResult(
                output_ref=output_ref,
                state=_enum(item["state"], f"{item_path}.state", OUTPUT_GATE_STATES),
                reason=_string(item["reason"], f"{item_path}.reason"),
                target_result_refs=tuple(sorted(targets)),
                criterion_result_refs=tuple(sorted(criteria)),
            )
        )
    return tuple(sorted(items, key=lambda item: item.output_ref))


def _load_action_gates(
    value: object,
    *,
    output_refs: AbstractSet[str],
    criterion_result_refs: AbstractSet[str],
) -> tuple[ReevaluationActionGateResult, ...]:
    path = "incremental_reevaluation_result.action_gates"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    items: list[ReevaluationActionGateResult] = []
    refs: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={
                "action_ref",
                "state",
                "reason",
                "output_refs",
                "criterion_result_refs",
                "external_authorization_required",
                "authorized",
                "executed",
            },
        )
        action_ref = _string(item["action_ref"], f"{item_path}.action_ref")
        if action_ref in refs:
            _fail(f"{item_path}.action_ref", f"duplicates {action_ref!r}")
        refs.add(action_ref)
        linked_outputs = _string_list(item["output_refs"], f"{item_path}.output_refs")
        criteria = _string_list(
            item["criterion_result_refs"], f"{item_path}.criterion_result_refs"
        )
        _closed_refs(linked_outputs, f"{item_path}.output_refs", output_refs, "output_gates")
        _closed_refs(
            criteria,
            f"{item_path}.criterion_result_refs",
            criterion_result_refs,
            "acceptance_results",
        )
        state = _enum(item["state"], f"{item_path}.state", ACTION_GATE_STATES)
        external_required = _boolean(
            item["external_authorization_required"],
            f"{item_path}.external_authorization_required",
        )
        authorized = _boolean(item["authorized"], f"{item_path}.authorized")
        executed = _boolean(item["executed"], f"{item_path}.executed")
        if authorized or executed:
            _fail(item_path, "Core v0.1 result must keep authorized and executed false")
        if state == "eligible" and not external_required:
            _fail(item_path, "eligible actions require external_authorization_required=true")
        items.append(
            ReevaluationActionGateResult(
                action_ref=action_ref,
                state=state,
                reason=_string(item["reason"], f"{item_path}.reason"),
                output_refs=tuple(sorted(linked_outputs)),
                criterion_result_refs=tuple(sorted(criteria)),
                external_authorization_required=external_required,
                authorized=False,
                executed=False,
            )
        )
    return tuple(sorted(items, key=lambda item: item.action_ref))


def _expected_state(
    node_results: Sequence[ReevaluationNodeResult],
    target_results: Sequence[ReevaluationTargetResult],
    acceptance_results: Sequence[ReevaluationAcceptanceResult],
    discrepancy_results: Sequence[ReevaluationDiscrepancyResult],
    output_gates: Sequence[ReevaluationOutputGateResult],
    action_gates: Sequence[ReevaluationActionGateResult],
) -> str:
    has_failed = (
        any(item.state == "failed" for item in node_results)
        or any(item.state == "failed" for item in target_results)
        or any(item.state == "failed" for item in acceptance_results)
    )
    if has_failed:
        return "failed"
    has_blocked = (
        any(item.state == "blocked" for item in node_results)
        or any(item.state == "blocked" for item in target_results)
        or any(item.state == "blocked" for item in acceptance_results)
        or any(item.state == "blocked" for item in output_gates)
        or any(item.state == "blocked" for item in action_gates)
        or any(item.state == "unresolved" for item in discrepancy_results)
    )
    if has_blocked:
        return "blocked"
    has_unknown = (
        any(item.state == "unknown" for item in node_results)
        or any(item.state == "unknown" for item in target_results)
        or any(item.state == "unknown" for item in acceptance_results)
        or any(item.state == "unknown" for item in discrepancy_results)
        or any(item.state == "unknown" for item in output_gates)
        or any(item.state == "unknown" for item in action_gates)
    )
    if has_unknown:
        has_success = (
            any(item.state not in {"unknown", "failed", "blocked"} for item in target_results)
            or any(item.state == "satisfied" for item in acceptance_results)
            or any(item.state == "resolved" for item in discrepancy_results)
        )
        return "partial" if has_success else "unknown"
    return "completed"


def load_incremental_reevaluation_result(
    payload: Mapping[str, object],
) -> IncrementalReevaluationResult:
    """Load and strictly validate one Incremental Reevaluation Result v0.1."""

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"incremental_reevaluation_result"})
    body = _mapping(
        root["incremental_reevaluation_result"],
        "incremental_reevaluation_result",
    )
    _exact_fields(
        body,
        "incremental_reevaluation_result",
        required={
            "schema_id",
            "schema_version",
            "result_id",
            "recorded_at",
            "state",
            "reason",
            "base_world_state",
            "successor_world_state",
            "impact_graph_ref",
            "correction_request_refs",
            "discrepancy_report_refs",
            "execution_result_refs",
            "node_results",
            "target_results",
            "acceptance_results",
            "discrepancy_results",
            "output_gates",
            "action_gates",
            "next_action",
        },
    )
    if body["schema_id"] != INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID:
        _fail(
            "incremental_reevaluation_result.schema_id",
            f"must equal {INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID!r}",
        )
    if body["schema_version"] != INCREMENTAL_REEVALUATION_RESULT_SCHEMA_VERSION:
        _fail(
            "incremental_reevaluation_result.schema_version",
            f"must equal {INCREMENTAL_REEVALUATION_RESULT_SCHEMA_VERSION!r}",
        )
    recorded_at_text, recorded_at = _timestamp(
        body["recorded_at"], "incremental_reevaluation_result.recorded_at"
    )
    base, base_as_of = _load_world_state_ref(
        body["base_world_state"], "incremental_reevaluation_result.base_world_state"
    )
    successor, successor_as_of = _load_world_state_ref(
        body["successor_world_state"],
        "incremental_reevaluation_result.successor_world_state",
    )
    if base.ref_id == successor.ref_id:
        _fail("incremental_reevaluation_result", "base and successor ref_id values must differ")
    if base.world_state_id != successor.world_state_id:
        _fail("incremental_reevaluation_result.successor_world_state.world_state_id", "must equal base world_state_id")
    if successor.revision <= base.revision:
        _fail("incremental_reevaluation_result.successor_world_state.revision", "must be greater than base revision")
    if successor_as_of < base_as_of:
        _fail("incremental_reevaluation_result.successor_world_state.as_of", "must not precede base as_of")
    if recorded_at < successor_as_of:
        _fail("incremental_reevaluation_result.recorded_at", "must not precede successor as_of")

    impact_ref = _load_artifact_ref(
        body["impact_graph_ref"],
        "incremental_reevaluation_result.impact_graph_ref",
        artifact_id="geotask.impact-graph",
        schema_version="0.1",
    )
    correction_refs = _load_artifact_refs(
        body["correction_request_refs"],
        "incremental_reevaluation_result.correction_request_refs",
        artifact_id="geotask.correction-request",
        schema_version="0.1",
    )
    discrepancy_refs = _load_artifact_refs(
        body["discrepancy_report_refs"],
        "incremental_reevaluation_result.discrepancy_report_refs",
        artifact_id="geotask.discrepancy-report",
        schema_version="0.1",
    )
    execution_refs = _load_artifact_refs(
        body["execution_result_refs"],
        "incremental_reevaluation_result.execution_result_refs",
        artifact_id="geotask.execution-result",
        schema_version="1.0",
    )
    all_refs = (base, successor, impact_ref, *correction_refs, *discrepancy_refs, *execution_refs)
    ref_ids = [item.ref_id for item in all_refs]
    if len(ref_ids) != len(set(ref_ids)):
        _fail("incremental_reevaluation_result artifact references", "ref_id values must be globally unique")
    declared_refs = frozenset(ref_ids)

    node_results = _load_node_results(body["node_results"], declared_refs)
    node_by_id = {item.id: item for item in node_results}
    target_results = _load_target_results(
        body["target_results"],
        node_results=node_by_id,
        declared_artifact_refs=declared_refs,
    )
    target_ids = frozenset(item.id for item in target_results)
    request_ref_ids = frozenset(item.ref_id for item in correction_refs)
    acceptance_results = _load_acceptance_results(
        body["acceptance_results"],
        request_refs=request_ref_ids,
        node_result_refs=frozenset(node_by_id),
        target_result_refs=target_ids,
        declared_artifact_refs=declared_refs,
    )
    discrepancy_results = _load_discrepancy_results(
        body["discrepancy_results"],
        request_refs=request_ref_ids,
        node_result_refs=frozenset(node_by_id),
        declared_artifact_refs=declared_refs,
    )
    acceptance_ids = frozenset(item.id for item in acceptance_results)
    output_gates = _load_output_gates(
        body["output_gates"],
        target_result_refs=target_ids,
        criterion_result_refs=acceptance_ids,
    )
    action_gates = _load_action_gates(
        body["action_gates"],
        output_refs=frozenset(item.output_ref for item in output_gates),
        criterion_result_refs=acceptance_ids,
    )
    state = _enum(
        body["state"],
        "incremental_reevaluation_result.state",
        INCREMENTAL_REEVALUATION_STATES,
    )
    expected_state = _expected_state(
        node_results,
        target_results,
        acceptance_results,
        discrepancy_results,
        output_gates,
        action_gates,
    )
    if state != expected_state:
        _fail(
            "incremental_reevaluation_result.state",
            f"must equal aggregate state {expected_state!r}",
        )
    next_action = _enum(
        body["next_action"],
        "incremental_reevaluation_result.next_action",
        INCREMENTAL_REEVALUATION_NEXT_ACTIONS,
    )
    if state == "completed" and next_action != "none":
        _fail("incremental_reevaluation_result.next_action", "completed state requires 'none'")
    if state in {"partial", "failed"} and next_action != "continue_reevaluation":
        _fail(
            "incremental_reevaluation_result.next_action",
            f"state {state!r} requires 'continue_reevaluation'",
        )
    if state == "unknown" and next_action not in {"request_evidence", "human_review"}:
        _fail("incremental_reevaluation_result.next_action", "unknown state requires evidence or review")
    if state == "blocked" and next_action == "none":
        _fail("incremental_reevaluation_result.next_action", "blocked state forbids 'none'")

    return IncrementalReevaluationResult(
        result_id=_string(body["result_id"], "incremental_reevaluation_result.result_id"),
        recorded_at=recorded_at_text,
        state=state,
        reason=_string(body["reason"], "incremental_reevaluation_result.reason"),
        base_world_state=base,
        successor_world_state=successor,
        impact_graph_ref=impact_ref,
        correction_request_refs=correction_refs,
        discrepancy_report_refs=discrepancy_refs,
        execution_result_refs=execution_refs,
        node_results=node_results,
        target_results=target_results,
        acceptance_results=acceptance_results,
        discrepancy_results=discrepancy_results,
        output_gates=output_gates,
        action_gates=action_gates,
        next_action=next_action,
    )


def _check_world_ref(
    declared: ReevaluationWorldStateRef,
    actual: WorldState,
    path: str,
) -> None:
    checks = (
        ("world_state_id", declared.world_state_id, actual.world_state_id),
        ("revision", declared.revision, actual.revision),
        ("as_of", declared.as_of, actual.as_of),
        ("semantic_fingerprint", declared.semantic_fingerprint, actual.semantic_fingerprint()),
    )
    for field, expected, observed in checks:
        if expected != observed:
            _fail(f"{path}.{field}", f"does not match bound World State: expected {observed!r}")


def _resolve_request_discrepancy(
    request: CorrectionRequest,
    discrepancy_ref_id: str,
    reports: Mapping[str, DiscrepancyReport],
) -> DiscrepancyFinding:
    local_ref = next(
        (item for item in request.discrepancy_refs if item.id == discrepancy_ref_id),
        None,
    )
    if local_ref is None:
        _fail("discrepancy_results", f"unknown discrepancy_ref {discrepancy_ref_id!r}")
    report = reports[local_ref.report_ref]
    finding = next((item for item in report.discrepancies if item.id == local_ref.discrepancy_id), None)
    if finding is None:
        _fail("discrepancy_results", f"missing discrepancy {local_ref.discrepancy_id!r}")
    return finding


def _find_graph_node_for_change(
    graph: ImpactGraph,
    request_ref: str,
    change_id: str,
) -> str | None:
    entities = {
        item.id: item
        for item in graph.entity_refs
        if item.kind == "correction_change"
        and item.artifact_ref == request_ref
        and item.entity_id == change_id
    }
    if len(entities) != 1:
        return None
    entity_ref = next(iter(entities))
    nodes = [
        item.id
        for item in graph.nodes
        if item.kind == "correction_change" and item.entity_ref == entity_ref
    ]
    return nodes[0] if len(nodes) == 1 else None


def _expected_artifact_bytes(
    result: IncrementalReevaluationResult,
) -> dict[str, str]:
    return {
        item.ref_id: item.content_sha256
        for item in result.all_artifact_refs()
    }


def _json_mapping_from_bytes(content: bytes, path: str) -> Mapping[str, object]:
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IncrementalReevaluationResultFormatError(
            f"{path}: must be UTF-8 JSON bytes"
        ) from exc
    try:
        payload = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise IncrementalReevaluationResultFormatError(
            f"{path}: must contain valid JSON"
        ) from exc
    return _mapping(payload, path)


def validate_incremental_reevaluation_result_bindings(
    result: IncrementalReevaluationResult,
    base_world_state: WorldState,
    successor_world_state: WorldState,
    impact_graph: ImpactGraph,
    correction_requests: Mapping[str, CorrectionRequest],
    discrepancy_reports: Mapping[str, DiscrepancyReport],
    execution_results: Mapping[str, GeotaskResult],
    artifact_contents: Mapping[str, bytes],
) -> None:
    """Validate exact bindings and declared incremental-reevaluation semantics.

    The function validates an already-authored result. It does not execute the
    reevaluation, materialize either snapshot, release external outputs, authorize
    actions, or execute actions.
    """

    _check_world_ref(
        result.base_world_state,
        base_world_state,
        "incremental_reevaluation_result.base_world_state",
    )
    _check_world_ref(
        result.successor_world_state,
        successor_world_state,
        "incremental_reevaluation_result.successor_world_state",
    )
    if successor_world_state.world_state_id != base_world_state.world_state_id:
        _fail("successor_world_state.world_state_id", "must equal base World State ID")
    if successor_world_state.revision <= base_world_state.revision:
        _fail("successor_world_state.revision", "must be greater than base revision")

    if result.impact_graph_ref.instance_id != impact_graph.graph_id:
        _fail("incremental_reevaluation_result.impact_graph_ref.instance_id", "does not match graph_id")
    if impact_graph.world_state.world_state_id != base_world_state.world_state_id:
        _fail("impact_graph.world_state.world_state_id", "does not match base World State")
    if impact_graph.world_state.revision != base_world_state.revision:
        _fail("impact_graph.world_state.revision", "does not match base World State")
    if impact_graph.world_state.semantic_fingerprint != base_world_state.semantic_fingerprint():
        _fail("impact_graph.world_state.semantic_fingerprint", "does not match base World State")

    correction_ref_by_id = {item.ref_id: item for item in result.correction_request_refs}
    discrepancy_ref_by_id = {item.ref_id: item for item in result.discrepancy_report_refs}
    execution_ref_by_id = {item.ref_id: item for item in result.execution_result_refs}
    graph_correction_refs = {
        item.ref_id: item
        for item in impact_graph.artifact_refs
        if item.artifact_id == "geotask.correction-request"
    }
    graph_discrepancy_refs = {
        item.ref_id: item
        for item in impact_graph.artifact_refs
        if item.artifact_id == "geotask.discrepancy-report"
    }
    if set(graph_correction_refs) != set(correction_ref_by_id):
        _fail(
            "incremental_reevaluation_result.correction_request_refs",
            "must exactly match the Impact Graph correction-request references",
        )
    if set(graph_discrepancy_refs) != set(discrepancy_ref_by_id):
        _fail(
            "incremental_reevaluation_result.discrepancy_report_refs",
            "must exactly match the Impact Graph discrepancy-report references",
        )
    for ref_id, graph_ref in graph_correction_refs.items():
        result_ref = correction_ref_by_id[ref_id]
        if (
            result_ref.instance_id != graph_ref.instance_id
            or result_ref.content_sha256 != graph_ref.content_sha256
        ):
            _fail(
                f"incremental_reevaluation_result.correction_request_refs[{ref_id!r}]",
                "must preserve the exact Impact Graph instance and content binding",
            )
    for ref_id, graph_ref in graph_discrepancy_refs.items():
        result_ref = discrepancy_ref_by_id[ref_id]
        if (
            result_ref.instance_id != graph_ref.instance_id
            or result_ref.content_sha256 != graph_ref.content_sha256
        ):
            _fail(
                f"incremental_reevaluation_result.discrepancy_report_refs[{ref_id!r}]",
                "must preserve the exact Impact Graph instance and content binding",
            )
    if set(correction_requests) != set(correction_ref_by_id):
        _fail("correction_requests", "keys must exactly match correction_request_refs")
    if set(discrepancy_reports) != set(discrepancy_ref_by_id):
        _fail("discrepancy_reports", "keys must exactly match discrepancy_report_refs")
    if set(execution_results) != set(execution_ref_by_id):
        _fail("execution_results", "keys must exactly match execution_result_refs")

    for ref_id, request in correction_requests.items():
        if correction_ref_by_id[ref_id].instance_id != request.request_id:
            _fail(f"correction_request_refs[{ref_id!r}].instance_id", "does not match request_id")
        if request.base_world_state.semantic_fingerprint != base_world_state.semantic_fingerprint():
            _fail(f"correction_requests[{ref_id!r}].base_world_state", "does not match base snapshot")
        if successor_world_state.revision < request.output_contract.minimum_revision:
            _fail(
                "successor_world_state.revision",
                f"must satisfy request {ref_id!r} minimum_revision",
            )
        if request.output_contract.world_state_id != successor_world_state.world_state_id:
            _fail(f"correction_requests[{ref_id!r}].output_contract", "does not match successor ID")
        request_report_refs = {item.ref_id for item in request.discrepancy_report_refs}
        if not request_report_refs.issubset(discrepancy_ref_by_id):
            _fail(
                f"correction_requests[{ref_id!r}].discrepancy_report_refs",
                "must be present in incremental_reevaluation_result.discrepancy_report_refs",
            )
        missing_change_nodes = [
            change.id
            for change in request.changes
            if _find_graph_node_for_change(impact_graph, ref_id, change.id) is None
        ]
        if missing_change_nodes:
            _fail(
                f"correction_requests[{ref_id!r}].changes",
                "Impact Graph is missing correction changes: "
                + ", ".join(sorted(missing_change_nodes)),
            )

    for ref_id, report in discrepancy_reports.items():
        if discrepancy_ref_by_id[ref_id].instance_id != report.report_id:
            _fail(f"discrepancy_report_refs[{ref_id!r}].instance_id", "does not match report_id")
        if report.world_state.semantic_fingerprint != base_world_state.semantic_fingerprint():
            _fail(f"discrepancy_reports[{ref_id!r}].world_state", "does not match base snapshot")

    expected_bytes = _expected_artifact_bytes(result)
    if set(artifact_contents) != set(expected_bytes):
        _fail("artifact_contents", "keys must exactly match all declared artifact refs")
    for ref_id, digest in expected_bytes.items():
        content = artifact_contents[ref_id]
        if not isinstance(content, bytes):
            _fail(f"artifact_contents[{ref_id!r}]", "must be bytes")
        actual = hashlib.sha256(content).hexdigest()
        if actual != digest:
            _fail(
                f"artifact_contents[{ref_id!r}]",
                f"SHA-256 mismatch: expected {digest!r}, got {actual!r}",
            )

    try:
        parsed_base = load_world_state(
            _json_mapping_from_bytes(
                artifact_contents[result.base_world_state.ref_id],
                f"artifact_contents[{result.base_world_state.ref_id!r}]",
            )
        )
        parsed_successor = load_world_state(
            _json_mapping_from_bytes(
                artifact_contents[result.successor_world_state.ref_id],
                f"artifact_contents[{result.successor_world_state.ref_id!r}]",
            )
        )
        parsed_graph = load_impact_graph(
            _json_mapping_from_bytes(
                artifact_contents[result.impact_graph_ref.ref_id],
                f"artifact_contents[{result.impact_graph_ref.ref_id!r}]",
            )
        )
        parsed_requests = {
            ref_id: load_correction_request(
                _json_mapping_from_bytes(
                    artifact_contents[ref_id],
                    f"artifact_contents[{ref_id!r}]",
                )
            )
            for ref_id in correction_requests
        }
        parsed_reports = {
            ref_id: load_discrepancy_report(
                _json_mapping_from_bytes(
                    artifact_contents[ref_id],
                    f"artifact_contents[{ref_id!r}]",
                )
            )
            for ref_id in discrepancy_reports
        }
        parsed_executions = {
            ref_id: GeotaskResult.from_dict(
                _json_mapping_from_bytes(
                    artifact_contents[ref_id],
                    f"artifact_contents[{ref_id!r}]",
                )
            )
            for ref_id in execution_results
        }
    except (ValueError, TypeError, KeyError) as exc:
        raise IncrementalReevaluationResultFormatError(
            f"artifact_contents: exact source bytes failed strict loading: {exc}"
        ) from exc

    exact_object_checks = (
        ("base World State", parsed_base, base_world_state),
        ("successor World State", parsed_successor, successor_world_state),
        ("Impact Graph", parsed_graph, impact_graph),
        ("Correction Requests", parsed_requests, dict(correction_requests)),
        ("Discrepancy Reports", parsed_reports, dict(discrepancy_reports)),
        ("execution results", parsed_executions, dict(execution_results)),
    )
    for label, parsed, supplied in exact_object_checks:
        if parsed != supplied:
            _fail(
                "artifact_contents",
                f"supplied {label} do not match objects strictly loaded from exact bytes",
            )

    recorded_at = _timestamp(
        result.recorded_at, "incremental_reevaluation_result.recorded_at"
    )[1]
    successor_materialized_at = _timestamp(
        successor_world_state.materialized_at, "successor_world_state.materialized_at"
    )[1]
    if recorded_at < successor_materialized_at:
        _fail("incremental_reevaluation_result.recorded_at", "must not precede successor materialization")
    for ref_id, execution in execution_results.items():
        if execution_ref_by_id[ref_id].instance_id != execution.task_id:
            _fail(f"execution_result_refs[{ref_id!r}].instance_id", "must equal execution task_id")
        finished_at = _timestamp(
            execution.execution.finished_at,
            f"execution_results[{ref_id!r}].execution.finished_at",
        )[1]
        if finished_at < successor_materialized_at or finished_at > recorded_at:
            _fail(
                f"execution_results[{ref_id!r}].execution.finished_at",
                "must be between successor materialization and result recording",
            )

    graph_nodes = {item.id: item for item in impact_graph.nodes}
    node_result_by_id = {item.id: item for item in result.node_results}
    node_result_by_node = {item.node_ref: item for item in result.node_results}
    if set(node_result_by_node) != set(graph_nodes):
        _fail("node_results", "must cover every Impact Graph node exactly once")

    allowed_states = {
        "discrepancy": {"resolved", "blocked", "unknown"},
        "correction_change": {"recomputed", "blocked", "failed", "unknown"},
        "world_state_path": {"preserved", "recomputed", "invalidated", "failed", "unknown"},
        "assertion": {"preserved", "recomputed", "invalidated", "failed", "unknown"},
        "output": {"preserved", "recomputed", "released", "invalidated", "blocked", "failed", "unknown"},
        "action": {"preserved", "eligible", "blocked", "unknown"},
        "artifact": {"preserved", "recomputed", "invalidated", "failed", "unknown"},
        "acceptance_criterion": {"resolved", "blocked", "unknown"},
        "review_requirement": {"resolved", "blocked", "unknown"},
    }
    execution_checks = {
        (ref_id, check.assertion_id): check
        for ref_id, execution in execution_results.items()
        for check in execution.checks
    }
    graph_entity_by_id = {item.id: item for item in impact_graph.entity_refs}
    for node_ref, node in graph_nodes.items():
        node_result = node_result_by_node[node_ref]
        if node_result.state not in allowed_states[node.kind]:
            _fail(
                f"node_results[{node_result.id!r}].state",
                f"is incompatible with graph node kind {node.kind!r}",
            )
        if node.kind == "world_state_path":
            base_exists, base_value = _resolve_world_state_path(base_world_state, node.identity)
            successor_exists, successor_value = _resolve_world_state_path(
                successor_world_state, node.identity
            )
            if node_result.has_previous != base_exists or (
                base_exists and node_result.previous != base_value
            ):
                _fail(f"node_results[{node_result.id!r}].previous", "does not match base path")
            if node_result.has_current != successor_exists or (
                successor_exists and node_result.current != successor_value
            ):
                _fail(f"node_results[{node_result.id!r}].current", "does not match successor path")
        elif node.kind == "correction_change":
            entity = graph_entity_by_id[node.entity_ref]
            request = correction_requests[entity.artifact_ref]
            change = next((item for item in request.changes if item.id == entity.entity_id), None)
            if change is None:
                _fail(f"node_results[{node_result.id!r}]", "cannot resolve correction change")
            base_exists, base_value = _resolve_world_state_path(base_world_state, change.target_path)
            successor_exists, successor_value = _resolve_world_state_path(
                successor_world_state, change.target_path
            )
            if not base_exists or node_result.previous != base_value:
                _fail(f"node_results[{node_result.id!r}].previous", "does not match change base value")
            if change.operation == "remove":
                if successor_exists or node_result.has_current:
                    _fail(f"node_results[{node_result.id!r}].current", "removed path must be absent")
            elif not successor_exists or node_result.current != successor_value:
                _fail(f"node_results[{node_result.id!r}].current", "does not match successor value")
            if change.operation == "recompute" and node_result.state != "recomputed":
                _fail(f"node_results[{node_result.id!r}].state", "recompute changes require state 'recomputed'")
        elif node.kind == "assertion" and node_result.state == "recomputed":
            matches = [
                (ref_id, check)
                for (ref_id, assertion_id), check in execution_checks.items()
                if assertion_id == node.identity
            ]
            if len(matches) != 1:
                _fail(f"node_results[{node_result.id!r}]", "requires one execution-result check")
            ref_id, check = matches[0]
            if ref_id not in node_result.basis_refs or node_result.current != check.value:
                _fail(f"node_results[{node_result.id!r}]", "does not bind the recomputed assertion result")
        elif node.kind == "discrepancy" and node_result.state == "resolved":
            entity = graph_entity_by_id[node.entity_ref]
            report = discrepancy_reports[entity.artifact_ref]
            finding = next((item for item in report.discrepancies if item.id == entity.entity_id), None)
            if finding is None:
                _fail(f"node_results[{node_result.id!r}]", "cannot resolve discrepancy")
            if finding.subject_path.startswith(("/objects/", "/relations/")):
                exists, current = _resolve_world_state_path(
                    successor_world_state, finding.subject_path
                )
                if not exists:
                    _fail(f"node_results[{node_result.id!r}]", "resolved subject path is absent")
                if finding.has_observed and current != finding.observed:
                    _fail(f"node_results[{node_result.id!r}]", "successor value does not equal observed value")
                if finding.has_expected and current == finding.expected:
                    _fail(f"node_results[{node_result.id!r}]", "successor retains the discrepant expected value")

    graph_targets = {item.id: item for item in impact_graph.reevaluation_targets}
    target_result_by_id = {item.id: item for item in result.target_results}
    target_result_by_target = {item.target_ref: item for item in result.target_results}
    if set(target_result_by_target) != set(graph_targets):
        _fail("target_results", "must cover every Impact Graph reevaluation target exactly once")
    completed_node_states = {"preserved", "recomputed", "resolved", "released", "eligible"}
    for target_ref, graph_target in graph_targets.items():
        target_result = target_result_by_target[target_ref]
        if target_result.node_ref != graph_target.node_ref:
            _fail(f"target_results[{target_result.id!r}].node_ref", "does not match Impact Graph target")
        if result.impact_graph_ref.ref_id not in target_result.basis_refs:
            _fail(
                f"target_results[{target_result.id!r}].basis_refs",
                "must include the bound Impact Graph ref",
            )
        node_result = node_result_by_id[target_result.node_result_ref]
        if target_result.state == "completed" and node_result.state not in completed_node_states:
            _fail(f"target_results[{target_result.id!r}].state", "completed target requires a completed node result")
        if target_result.state == "blocked" and node_result.state != "blocked":
            _fail(f"target_results[{target_result.id!r}].state", "blocked target requires blocked node result")
        if target_result.state == "failed" and node_result.state != "failed":
            _fail(f"target_results[{target_result.id!r}].state", "failed target requires failed node result")
        if target_result.state == "unknown" and node_result.state != "unknown":
            _fail(f"target_results[{target_result.id!r}].state", "unknown target requires unknown node result")
        if target_result.state == "not_required" and (
            graph_target.state != "not_required" or node_result.state != "preserved"
        ):
            _fail(
                f"target_results[{target_result.id!r}].state",
                "not_required requires a not-required graph target and preserved node result",
            )

    criterion_by_pair = {
        (request_ref, criterion.id): criterion
        for request_ref, request in correction_requests.items()
        for criterion in request.acceptance_criteria
    }
    expected_criteria = set(criterion_by_pair)
    acceptance_by_pair = {
        (item.request_ref, item.criterion_id): item for item in result.acceptance_results
    }
    if set(acceptance_by_pair) != expected_criteria:
        _fail("acceptance_results", "must cover every Correction Request criterion exactly once")

    local_discrepancy_by_pair = {
        (request_ref, discrepancy.id): discrepancy
        for request_ref, request in correction_requests.items()
        for discrepancy in request.discrepancy_refs
    }
    expected_discrepancies = set(local_discrepancy_by_pair)
    discrepancy_by_pair = {
        (item.request_ref, item.discrepancy_ref): item
        for item in result.discrepancy_results
    }
    if set(discrepancy_by_pair) != expected_discrepancies:
        _fail("discrepancy_results", "must cover every Correction Request discrepancy exactly once")

    for pair, discrepancy_result in discrepancy_by_pair.items():
        request_ref, discrepancy_ref = pair
        request = correction_requests[request_ref]
        local_discrepancy = local_discrepancy_by_pair[pair]
        finding = _resolve_request_discrepancy(request, discrepancy_ref, discrepancy_reports)
        graph_node_ref = next(
            (
                node.id
                for node in impact_graph.nodes
                if node.kind == "discrepancy"
                and node.entity_ref is not None
                and graph_entity_by_id[node.entity_ref].artifact_ref
                == local_discrepancy.report_ref
                and graph_entity_by_id[node.entity_ref].entity_id == finding.id
            ),
            None,
        )
        if graph_node_ref is None:
            _fail(
                f"discrepancy_results[{discrepancy_result.id!r}]",
                "requires a matching Impact Graph discrepancy node",
            )
        graph_node_result = node_result_by_node[graph_node_ref]
        expected_node_state = {
            "resolved": "resolved",
            "unresolved": "blocked",
            "unknown": "unknown",
        }[discrepancy_result.state]
        if graph_node_result.state != expected_node_state:
            _fail(
                f"discrepancy_results[{discrepancy_result.id!r}]",
                f"requires graph discrepancy node state {expected_node_state!r}",
            )
        if graph_node_result.id not in discrepancy_result.node_result_refs:
            _fail(
                f"discrepancy_results[{discrepancy_result.id!r}].node_result_refs",
                "must include the matching graph discrepancy node result",
            )

    for pair, acceptance in acceptance_by_pair.items():
        request_ref, _criterion_id = pair
        request = correction_requests[request_ref]
        criterion = criterion_by_pair[pair]
        if request_ref not in acceptance.basis_refs:
            _fail(
                f"acceptance_results[{acceptance.id!r}].basis_refs",
                "must include the bound Correction Request ref",
            )

        required_node_result_refs: set[str] = set()
        required_target_result_refs: set[str] = set()
        satisfied = False
        if criterion.kind in {"path_equals", "path_absent", "path_recomputed"}:
            if result.successor_world_state.ref_id not in acceptance.basis_refs:
                _fail(
                    f"acceptance_results[{acceptance.id!r}].basis_refs",
                    "path criteria must include the successor World State ref",
                )
            path_node_results = [
                node_result
                for node_ref, node_result in node_result_by_node.items()
                if graph_nodes[node_ref].kind == "world_state_path"
                and graph_nodes[node_ref].identity == criterion.target_path
            ]
            required_node_result_refs.update(item.id for item in path_node_results)

        if criterion.kind == "path_equals":
            exists, value = _resolve_world_state_path(
                successor_world_state, criterion.target_path
            )
            satisfied = exists and value == criterion.expected
        elif criterion.kind == "path_absent":
            exists, _ = _resolve_world_state_path(
                successor_world_state, criterion.target_path
            )
            satisfied = not exists
        elif criterion.kind == "path_recomputed":
            matching_paths = [
                item for item in path_node_results if item.state == "recomputed"
            ]
            matching_change_ids = [
                change.id
                for change in request.changes
                if change.target_path == criterion.target_path
            ]
            if len(matching_change_ids) != 1:
                _fail(
                    f"acceptance_results[{acceptance.id!r}]",
                    "path_recomputed requires exactly one matching Correction Request change",
                )
            change_node_ref = _find_graph_node_for_change(
                impact_graph,
                request_ref,
                matching_change_ids[0],
            )
            matching_changes = (
                [node_result_by_node[change_node_ref]]
                if change_node_ref is not None
                and node_result_by_node[change_node_ref].state == "recomputed"
                else []
            )
            required_node_result_refs.update(item.id for item in matching_changes)
            satisfied = bool(matching_paths and matching_changes)
        elif criterion.kind == "artifact_valid":
            if result.successor_world_state.ref_id not in acceptance.basis_refs:
                _fail(
                    f"acceptance_results[{acceptance.id!r}].basis_refs",
                    "artifact_valid must include the successor World State ref",
                )
            satisfied = criterion.artifact_id == result.successor_world_state.artifact_id
        elif criterion.kind == "discrepancy_resolved":
            discrepancy_pair = (request_ref, criterion.discrepancy_ref)
            discrepancy_result = discrepancy_by_pair.get(discrepancy_pair)
            if discrepancy_result is None:
                _fail(
                    f"acceptance_results[{acceptance.id!r}]",
                    "references an undeclared Correction Request discrepancy",
                )
            required_node_result_refs.update(discrepancy_result.node_result_refs)
            satisfied = discrepancy_result.state == "resolved"
        elif criterion.kind == "recheck_completed":
            output_node_results = [
                node_result
                for node_ref, node_result in node_result_by_node.items()
                if graph_nodes[node_ref].kind == "output"
                and graph_nodes[node_ref].identity in criterion.output_refs
            ]
            output_target_results = [
                target
                for target in result.target_results
                if graph_nodes[target.node_ref].kind == "output"
                and graph_nodes[target.node_ref].identity in criterion.output_refs
            ]
            required_node_result_refs.update(item.id for item in output_node_results)
            required_target_result_refs.update(item.id for item in output_target_results)
            satisfied = all(
                any(
                    graph_nodes[node_ref].kind == "output"
                    and graph_nodes[node_ref].identity == output_ref
                    and node_result.state == "released"
                    for node_ref, node_result in node_result_by_node.items()
                )
                for output_ref in criterion.output_refs
            ) and all(
                any(
                    target.state == "completed"
                    and graph_nodes[target.node_ref].kind == "output"
                    and graph_nodes[target.node_ref].identity == output_ref
                    for target in result.target_results
                )
                for output_ref in criterion.output_refs
            )
        elif criterion.kind == "human_reviewed":
            matching_review_results: list[ReevaluationNodeResult] = []
            for node_ref, node_result in node_result_by_node.items():
                node = graph_nodes[node_ref]
                if node.kind != "review_requirement" or node.entity_ref is None:
                    continue
                entity = graph_entity_by_id[node.entity_ref]
                if entity.artifact_ref != request_ref:
                    continue
                review = next(
                    (
                        item
                        for item in request.review_requirements
                        if item.id == entity.entity_id
                    ),
                    None,
                )
                if review is not None and review.reviewer_role == criterion.reviewer_role:
                    matching_review_results.append(node_result)
            required_node_result_refs.update(
                item.id for item in matching_review_results
            )
            satisfied = any(
                item.state == "resolved" for item in matching_review_results
            )

        criterion_graph_results = [
            node_result
            for node_ref, node_result in node_result_by_node.items()
            if graph_nodes[node_ref].kind == "acceptance_criterion"
            and graph_nodes[node_ref].entity_ref is not None
            and graph_entity_by_id[graph_nodes[node_ref].entity_ref].artifact_ref
            == request_ref
            and graph_entity_by_id[graph_nodes[node_ref].entity_ref].entity_id
            == criterion.id
        ]
        required_node_result_refs.update(item.id for item in criterion_graph_results)
        missing_node_refs = sorted(
            required_node_result_refs - set(acceptance.node_result_refs)
        )
        if missing_node_refs:
            _fail(
                f"acceptance_results[{acceptance.id!r}].node_result_refs",
                "must include supporting node results: " + ", ".join(missing_node_refs),
            )
        missing_target_refs = sorted(
            required_target_result_refs - set(acceptance.target_result_refs)
        )
        if missing_target_refs:
            _fail(
                f"acceptance_results[{acceptance.id!r}].target_result_refs",
                "must include supporting target results: "
                + ", ".join(missing_target_refs),
            )

        expected_acceptance_state = "satisfied" if satisfied else "failed"
        if acceptance.state != expected_acceptance_state:
            _fail(
                f"acceptance_results[{acceptance.id!r}].state",
                f"must equal evaluated state {expected_acceptance_state!r}",
            )
        for criterion_node_result in criterion_graph_results:
            expected_node_state = "resolved" if satisfied else "blocked"
            if criterion_node_result.state != expected_node_state:
                _fail(
                    f"node_results[{criterion_node_result.id!r}].state",
                    "does not match the evaluated acceptance criterion state",
                )

    requested_paths = {
        change.target_path
        for request in correction_requests.values()
        for change in request.changes
    }
    base_flat = _flatten_world_state(base_world_state)
    successor_flat = _flatten_world_state(successor_world_state)
    changed_leaf_paths = {
        path
        for path in set(base_flat) | set(successor_flat)
        if base_flat.get(path) != successor_flat.get(path)
    }
    unauthorized = sorted(
        path
        for path in changed_leaf_paths
        if not any(_path_within(path, requested) for requested in requested_paths)
    )
    if unauthorized:
        _fail(
            "successor_world_state",
            "contains changes outside requested paths: " + ", ".join(unauthorized),
        )
    for request in correction_requests.values():
        for local_ref in request.discrepancy_refs:
            finding = _resolve_request_discrepancy(request, local_ref.id, discrepancy_reports)
            for immutable_path in finding.correction_scope.immutable_paths:
                base_exists, base_value = _resolve_world_state_path(base_world_state, immutable_path)
                successor_exists, successor_value = _resolve_world_state_path(
                    successor_world_state, immutable_path
                )
                if base_exists != successor_exists or base_value != successor_value:
                    _fail("successor_world_state", f"immutable path changed: {immutable_path!r}")

    expected_outputs = {
        output_ref
        for request in correction_requests.values()
        for output_ref in request.blocked_outputs
    }
    output_by_ref = {item.output_ref: item for item in result.output_gates}
    if set(output_by_ref) != expected_outputs:
        _fail("output_gates", "must cover every blocked output exactly once")
    acceptance_by_id = {item.id: item for item in result.acceptance_results}
    for output_ref, gate in output_by_ref.items():
        output_node = next(
            (item for item in impact_graph.nodes if item.kind == "output" and item.identity == output_ref),
            None,
        )
        if output_node is None:
            _fail(f"output_gates[{output_ref!r}]", "missing Impact Graph output node")
        node_state = node_result_by_node[output_node.id].state
        required_criterion_refs = {
            acceptance.id
            for request_ref, request in correction_requests.items()
            if output_ref in request.blocked_outputs
            for acceptance in result.acceptance_results
            if acceptance.request_ref == request_ref
        }
        if set(gate.criterion_result_refs) != required_criterion_refs:
            _fail(
                f"output_gates[{output_ref!r}].criterion_result_refs",
                "must include every acceptance result for the gating Correction Request",
            )
        gate_target_results = [
            target_result_by_id[ref] for ref in gate.target_result_refs
        ]
        criterion_states = [
            acceptance_by_id[ref].state for ref in gate.criterion_result_refs
        ]
        output_targets = [
            target
            for target in gate_target_results
            if graph_nodes[target.node_ref].kind == "output"
            and graph_nodes[target.node_ref].identity == output_ref
        ]
        if gate.state == "released":
            if (
                node_state != "released"
                or not output_targets
                or any(target.state != "completed" for target in output_targets)
                or len(output_targets) != len(gate_target_results)
                or any(state != "satisfied" for state in criterion_states)
            ):
                _fail(
                    f"output_gates[{output_ref!r}]",
                    "released output requires only completed targets for that output and satisfied criteria",
                )
        elif gate.state == "blocked":
            has_blocking_cause = any(
                target.state in {"blocked", "failed"}
                for target in gate_target_results
            ) or any(state != "satisfied" for state in criterion_states)
            if node_state != "blocked" or not has_blocking_cause:
                _fail(
                    f"output_gates[{output_ref!r}]",
                    "blocked output requires a blocked node and an explicit blocking cause",
                )
        elif gate.state == "unknown":
            has_unknown_cause = any(
                target.state == "unknown" for target in gate_target_results
            ) or any(state == "unknown" for state in criterion_states)
            if node_state != "unknown" or not has_unknown_cause:
                _fail(
                    f"output_gates[{output_ref!r}]",
                    "unknown output requires an unknown node and an explicit unknown cause",
                )

    expected_actions = {
        action_ref
        for request in correction_requests.values()
        for action_ref in request.blocked_actions
    }
    action_by_ref = {item.action_ref: item for item in result.action_gates}
    if set(action_by_ref) != expected_actions:
        _fail("action_gates", "must cover every blocked action exactly once")
    for action_ref, gate in action_by_ref.items():
        action_node = next(
            (item for item in impact_graph.nodes if item.kind == "action" and item.identity == action_ref),
            None,
        )
        if action_node is None:
            _fail(f"action_gates[{action_ref!r}]", "missing Impact Graph action node")
        required_criterion_refs = {
            acceptance.id
            for request_ref, request in correction_requests.items()
            if action_ref in request.blocked_actions
            for acceptance in result.acceptance_results
            if acceptance.request_ref == request_ref
        }
        if set(gate.criterion_result_refs) != required_criterion_refs:
            _fail(
                f"action_gates[{action_ref!r}].criterion_result_refs",
                "must include every acceptance result for the gating Correction Request",
            )
        required_output_refs = {
            output_ref
            for request in correction_requests.values()
            if action_ref in request.blocked_actions
            for output_ref in request.blocked_outputs
        }
        if set(gate.output_refs) != required_output_refs:
            _fail(
                f"action_gates[{action_ref!r}].output_refs",
                "must include every output gate from the gating Correction Request",
            )
        node_state = node_result_by_node[action_node.id].state
        output_states = [output_by_ref[ref].state for ref in gate.output_refs]
        criterion_states = [
            acceptance_by_id[ref].state for ref in gate.criterion_result_refs
        ]
        if gate.state == "eligible":
            if (
                node_state != "eligible"
                or not gate.output_refs
                or any(state != "released" for state in output_states)
                or any(state != "satisfied" for state in criterion_states)
            ):
                _fail(
                    f"action_gates[{action_ref!r}]",
                    "eligible action requires all request outputs released and criteria satisfied",
                )
            if gate.authorized or gate.executed:
                _fail(f"action_gates[{action_ref!r}]", "eligible action remains unauthorized and unexecuted")
        elif gate.state == "blocked":
            has_blocking_cause = any(
                state == "blocked" for state in output_states
            ) or any(state != "satisfied" for state in criterion_states)
            if node_state != "blocked" or not has_blocking_cause:
                _fail(
                    f"action_gates[{action_ref!r}]",
                    "blocked action requires a blocked node and an explicit blocking cause",
                )
        elif gate.state == "unknown":
            has_unknown_cause = any(
                state == "unknown" for state in output_states
            ) or any(state == "unknown" for state in criterion_states)
            if node_state != "unknown" or not has_unknown_cause:
                _fail(
                    f"action_gates[{action_ref!r}]",
                    "unknown action requires an unknown node and an explicit unknown cause",
                )


__all__ = [
    "INCREMENTAL_REEVALUATION_RESULT_ARTIFACT_ID",
    "INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID",
    "INCREMENTAL_REEVALUATION_RESULT_SCHEMA_VERSION",
    "INCREMENTAL_REEVALUATION_RESULT_FORMAT_VERSION",
    "INCREMENTAL_REEVALUATION_STATES",
    "NODE_RESULT_STATES",
    "TARGET_RESULT_STATES",
    "ACCEPTANCE_RESULT_STATES",
    "DISCREPANCY_RESULT_STATES",
    "OUTPUT_GATE_STATES",
    "ACTION_GATE_STATES",
    "INCREMENTAL_REEVALUATION_NEXT_ACTIONS",
    "IncrementalReevaluationResultFormatError",
    "ReevaluationArtifactRef",
    "ReevaluationWorldStateRef",
    "ReevaluationNodeResult",
    "ReevaluationTargetResult",
    "ReevaluationAcceptanceResult",
    "ReevaluationDiscrepancyResult",
    "ReevaluationOutputGateResult",
    "ReevaluationActionGateResult",
    "IncrementalReevaluationResult",
    "load_incremental_reevaluation_result",
    "validate_incremental_reevaluation_result_bindings",
]
