"""Public Correction Request v0.1 contract.

A Correction Request binds one immutable World State base snapshot and one or
more exact Discrepancy Report artifacts. It requests bounded changes for a new
successor World State, records machine-checkable acceptance criteria, preserves
immutable paths, and keeps affected outputs/actions blocked until explicit
resume conditions are satisfied.

Loading validates only the declared request. Binding validation checks the base
World State, exact artifact bytes, referenced Discrepancy Reports, and whether
requested paths stay within the reports' mutable correction scope. It does not
edit the base snapshot, create a successor state, execute a verifier, resolve a
discrepancy, rerun a task, release an output, or authorize an action.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Mapping, Sequence

from geotask_core.v1.discrepancy_report import (
    DISCREPANCY_REPORT_ARTIFACT_ID,
    DISCREPANCY_REPORT_SCHEMA_VERSION,
    DiscrepancyFinding,
    DiscrepancyReport,
)
from geotask_core.v1.world_state import WorldState


CORRECTION_REQUEST_ARTIFACT_ID = "geotask.correction-request"
CORRECTION_REQUEST_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-correction-request-v0.1.schema.json"
)
CORRECTION_REQUEST_SCHEMA_VERSION = "0.1"
CORRECTION_REQUEST_FORMAT_VERSION = "0.1"

CORRECTION_REQUEST_STATES = frozenset({"required", "need_review", "blocked"})
CORRECTION_OPERATIONS = frozenset({"add", "replace", "remove", "recompute"})
CORRECTION_SUBJECT_KINDS = frozenset({"object", "attribute", "relation"})
CORRECTION_ACCEPTANCE_KINDS = frozenset(
    {
        "path_equals",
        "path_absent",
        "path_recomputed",
        "artifact_valid",
        "discrepancy_resolved",
        "recheck_completed",
        "human_reviewed",
    }
)
CORRECTION_NEXT_ACTIONS = frozenset(
    {"materialize_successor_state", "human_review", "none"}
)


class CorrectionRequestFormatError(ValueError):
    """Raised when a Correction Request payload violates the v0.1 contract."""


def _fail(path: str, message: str) -> None:
    raise CorrectionRequestFormatError(f"{path}: {message}")


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
        raise CorrectionRequestFormatError(
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
    return tuple(items)


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


def _json_pointer(value: object, path: str, *, subject_kind: str | None = None) -> str:
    pointer = _string(value, path)
    if not pointer.startswith("/") or pointer.endswith("/"):
        _fail(path, "must be a non-root JSON Pointer without a trailing slash")
    segments = pointer.split("/")[1:]
    if not segments or any(not segment for segment in segments):
        _fail(path, "must not contain an empty path segment")
    for segment in segments:
        index = 0
        while index < len(segment):
            if segment[index] == "~":
                if index + 1 >= len(segment) or segment[index + 1] not in {"0", "1"}:
                    _fail(path, "contains an invalid JSON Pointer escape")
                index += 2
            else:
                index += 1

    if subject_kind == "object":
        if len(segments) < 2 or segments[0] != "objects" or "attributes" in segments:
            _fail(path, "object subjects must target /objects/<object-id>/...")
    elif subject_kind == "attribute":
        if len(segments) < 4 or segments[0] != "objects" or segments[2] != "attributes":
            _fail(
                path,
                "attribute subjects must target /objects/<object-id>/attributes/<name>/...",
            )
    elif subject_kind == "relation":
        if len(segments) < 2 or segments[0] != "relations":
            _fail(path, "relation subjects must target /relations/<relation-id>/...")
    return pointer


def _paths_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _path_within(path: str, parent: str) -> bool:
    return path == parent or path.startswith(parent + "/")


def _decode_pointer_segments(pointer: str) -> tuple[str, ...]:
    return tuple(
        segment.replace("~1", "/").replace("~0", "~")
        for segment in pointer.split("/")[1:]
    )


def _resolve_nested_value(
    value: object,
    segments: Sequence[str],
) -> tuple[bool, object]:
    current = value
    for segment in segments:
        if isinstance(current, Mapping):
            if segment not in current:
                return False, None
            current = current[segment]
            continue
        if isinstance(current, Sequence) and not isinstance(
            current, (str, bytes, bytearray)
        ):
            if not segment.isdigit():
                return False, None
            index = int(segment)
            if index >= len(current):
                return False, None
            current = current[index]
            continue
        return False, None
    return True, copy.deepcopy(current)


def _resolve_world_state_path(
    world_state: WorldState,
    pointer: str,
) -> tuple[bool, object]:
    """Resolve an identity-based Correction path against one loaded snapshot."""

    segments = _decode_pointer_segments(pointer)
    if len(segments) < 2:
        return False, None

    if segments[0] == "objects":
        world_object = next(
            (item for item in world_state.objects if item.id == segments[1]),
            None,
        )
        if world_object is None:
            return False, None
        if len(segments) >= 4 and segments[2] == "attributes":
            attribute = next(
                (item for item in world_object.attributes if item.name == segments[3]),
                None,
            )
            if attribute is None:
                return False, None
            return _resolve_nested_value(attribute.to_dict(), segments[4:])
        return _resolve_nested_value(world_object.to_dict(), segments[2:])

    if segments[0] == "relations":
        relation = next(
            (item for item in world_state.relations if item.id == segments[1]),
            None,
        )
        if relation is None:
            return False, None
        return _resolve_nested_value(relation.to_dict(), segments[2:])

    return False, None


def _validate_change_target_contract(
    target_path: str,
    subject_kind: str,
    path: str,
) -> None:
    """Reject whole-entity replacement and intrinsic identity/provenance edits."""

    segments = _decode_pointer_segments(target_path)
    if subject_kind == "object":
        if len(segments) < 3:
            _fail(
                path,
                "must target a field below /objects/<object-id>; whole-object changes are forbidden",
            )
        immutable_fields = {"id", "type", "observation_refs", "evidence_refs"}
        field = segments[2]
    elif subject_kind == "attribute":
        if len(segments) < 5:
            _fail(
                path,
                "must target a field below /objects/<object-id>/attributes/<name>; whole-attribute changes are forbidden",
            )
        immutable_fields = {"name", "observation_refs", "evidence_refs"}
        field = segments[4]
    else:
        if len(segments) < 3:
            _fail(
                path,
                "must target a field below /relations/<relation-id>; whole-relation changes are forbidden",
            )
        immutable_fields = {
            "id",
            "subject_ref",
            "predicate",
            "object_ref",
            "observation_refs",
            "evidence_refs",
        }
        field = segments[2]

    if field in immutable_fields:
        _fail(
            path,
            f"targets intrinsically immutable identity or provenance field {field!r}",
        )


def _closed_refs(
    refs: tuple[str, ...],
    path: str,
    declared: AbstractSet[str],
    declaration_path: str,
) -> None:
    for index, ref in enumerate(refs):
        if ref not in declared:
            _fail(f"{path}[{index}]", f"must be declared in {declaration_path}: {ref!r}")


@dataclass(frozen=True)
class CorrectionArtifactRef:
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
class CorrectionWorldStateRef:
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
class CorrectionDiscrepancyRef:
    id: str
    report_ref: str
    discrepancy_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "report_ref": self.report_ref,
            "discrepancy_id": self.discrepancy_id,
        }


@dataclass(frozen=True)
class CorrectionAcceptanceCriterion:
    id: str
    kind: str
    reason: str
    target_path: str | None
    has_expected: bool
    expected: object
    artifact_id: str | None
    discrepancy_ref: str | None
    output_refs: tuple[str, ...]
    reviewer_role: str | None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "kind": self.kind,
            "reason": self.reason,
            "output_refs": sorted(self.output_refs),
        }
        if self.target_path is not None:
            payload["target_path"] = self.target_path
        if self.has_expected:
            payload["expected"] = copy.deepcopy(self.expected)
        if self.artifact_id is not None:
            payload["artifact_id"] = self.artifact_id
        if self.discrepancy_ref is not None:
            payload["discrepancy_ref"] = self.discrepancy_ref
        if self.reviewer_role is not None:
            payload["reviewer_role"] = self.reviewer_role
        return payload


@dataclass(frozen=True)
class CorrectionChange:
    id: str
    discrepancy_ref: str
    subject_kind: str
    target_path: str
    operation: str
    reason: str
    basis_refs: tuple[str, ...]
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
            "id": self.id,
            "discrepancy_ref": self.discrepancy_ref,
            "subject_kind": self.subject_kind,
            "target_path": self.target_path,
            "operation": self.operation,
            "reason": self.reason,
            "basis_refs": sorted(self.basis_refs),
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
class CorrectionReviewRequirement:
    id: str
    discrepancy_refs: tuple[str, ...]
    reviewer_role: str
    reason: str
    affected_paths: tuple[str, ...]
    basis_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "discrepancy_refs": sorted(self.discrepancy_refs),
            "reviewer_role": self.reviewer_role,
            "reason": self.reason,
            "affected_paths": sorted(self.affected_paths),
            "basis_refs": sorted(self.basis_refs),
        }


@dataclass(frozen=True)
class CorrectionOutputContract:
    artifact_id: str
    schema_version: str
    world_state_id: str
    minimum_revision: int
    preserve_immutable_paths: bool
    require_semantic_fingerprint: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "schema_version": self.schema_version,
            "world_state_id": self.world_state_id,
            "minimum_revision": self.minimum_revision,
            "preserve_immutable_paths": self.preserve_immutable_paths,
            "require_semantic_fingerprint": self.require_semantic_fingerprint,
        }


@dataclass(frozen=True)
class CorrectionRequest:
    request_id: str
    created_at: str
    state: str
    reason: str
    base_world_state: CorrectionWorldStateRef
    discrepancy_report_refs: tuple[CorrectionArtifactRef, ...]
    supporting_artifact_refs: tuple[CorrectionArtifactRef, ...]
    observation_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    discrepancy_refs: tuple[CorrectionDiscrepancyRef, ...]
    changes: tuple[CorrectionChange, ...]
    review_requirements: tuple[CorrectionReviewRequirement, ...]
    acceptance_criteria: tuple[CorrectionAcceptanceCriterion, ...]
    output_contract: CorrectionOutputContract
    blocked_outputs: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    resume_when: str
    next_action: str

    def all_artifact_refs(self) -> tuple[CorrectionArtifactRef | CorrectionWorldStateRef, ...]:
        return (
            self.base_world_state,
            *self.discrepancy_report_refs,
            *self.supporting_artifact_refs,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "correction_request": {
                "schema_id": CORRECTION_REQUEST_SCHEMA_ID,
                "schema_version": CORRECTION_REQUEST_SCHEMA_VERSION,
                "request_id": self.request_id,
                "created_at": self.created_at,
                "state": self.state,
                "reason": self.reason,
                "base_world_state": self.base_world_state.to_dict(),
                "discrepancy_report_refs": [
                    item.to_dict()
                    for item in sorted(
                        self.discrepancy_report_refs, key=lambda item: item.ref_id
                    )
                ],
                "supporting_artifact_refs": [
                    item.to_dict()
                    for item in sorted(
                        self.supporting_artifact_refs, key=lambda item: item.ref_id
                    )
                ],
                "observation_refs": sorted(self.observation_refs),
                "evidence_refs": sorted(self.evidence_refs),
                "discrepancy_refs": [
                    item.to_dict()
                    for item in sorted(self.discrepancy_refs, key=lambda item: item.id)
                ],
                "changes": [
                    item.to_dict()
                    for item in sorted(self.changes, key=lambda item: item.id)
                ],
                "review_requirements": [
                    item.to_dict()
                    for item in sorted(
                        self.review_requirements, key=lambda item: item.id
                    )
                ],
                "acceptance_criteria": [
                    item.to_dict()
                    for item in sorted(
                        self.acceptance_criteria, key=lambda item: item.id
                    )
                ],
                "output_contract": self.output_contract.to_dict(),
                "blocked_outputs": sorted(self.blocked_outputs),
                "blocked_actions": sorted(self.blocked_actions),
                "resume_when": self.resume_when,
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


def _load_artifact_ref(
    value: object,
    path: str,
    *,
    expected_artifact_id: str | None = None,
    expected_schema_version: str | None = None,
) -> CorrectionArtifactRef:
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
    artifact_id = _string(ref["artifact_id"], f"{path}.artifact_id")
    schema_version = _string(ref["schema_version"], f"{path}.schema_version")
    if expected_artifact_id is not None and artifact_id != expected_artifact_id:
        _fail(f"{path}.artifact_id", f"must equal {expected_artifact_id!r}")
    if expected_schema_version is not None and schema_version != expected_schema_version:
        _fail(
            f"{path}.schema_version",
            f"must equal {expected_schema_version!r}",
        )
    return CorrectionArtifactRef(
        ref_id=_string(ref["ref_id"], f"{path}.ref_id"),
        artifact_id=artifact_id,
        schema_version=schema_version,
        instance_id=_string(ref["instance_id"], f"{path}.instance_id"),
        content_sha256=_sha256(ref["content_sha256"], f"{path}.content_sha256"),
    )


def _load_artifact_refs(
    value: object,
    path: str,
    *,
    expected_artifact_id: str | None = None,
    expected_schema_version: str | None = None,
    non_empty: bool = False,
) -> tuple[CorrectionArtifactRef, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if non_empty and not value:
        _fail(path, "must contain at least one item")
    return tuple(
        sorted(
            (
                _load_artifact_ref(
                    item,
                    f"{path}[{index}]",
                    expected_artifact_id=expected_artifact_id,
                    expected_schema_version=expected_schema_version,
                )
                for index, item in enumerate(value)
            ),
            key=lambda item: item.ref_id,
        )
    )


def _load_world_state_ref(
    value: object,
) -> tuple[CorrectionWorldStateRef, datetime]:
    path = "correction_request.base_world_state"
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
            "semantic_fingerprint",
            "content_sha256",
        },
    )
    if ref["artifact_id"] != "geotask.world-state":
        _fail(f"{path}.artifact_id", "must equal 'geotask.world-state'")
    if ref["schema_version"] != "0.1":
        _fail(f"{path}.schema_version", "must equal '0.1'")
    as_of_text, as_of = _timestamp(ref["as_of"], f"{path}.as_of")
    return (
        CorrectionWorldStateRef(
            ref_id=_string(ref["ref_id"], f"{path}.ref_id"),
            artifact_id="geotask.world-state",
            schema_version="0.1",
            world_state_id=_string(ref["world_state_id"], f"{path}.world_state_id"),
            revision=_positive_integer(ref["revision"], f"{path}.revision"),
            as_of=as_of_text,
            semantic_fingerprint=_sha256(
                ref["semantic_fingerprint"], f"{path}.semantic_fingerprint"
            ),
            content_sha256=_sha256(
                ref["content_sha256"], f"{path}.content_sha256"
            ),
        ),
        as_of,
    )


def _load_discrepancy_refs(
    value: object,
    declared_report_refs: AbstractSet[str],
) -> tuple[CorrectionDiscrepancyRef, ...]:
    path = "correction_request.discrepancy_refs"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if not value:
        _fail(path, "must contain at least one item")
    items: list[CorrectionDiscrepancyRef] = []
    ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={"id", "report_ref", "discrepancy_id"},
        )
        identifier = _string(item["id"], f"{item_path}.id")
        report_ref = _string(item["report_ref"], f"{item_path}.report_ref")
        discrepancy_id = _string(
            item["discrepancy_id"], f"{item_path}.discrepancy_id"
        )
        if identifier in ids:
            _fail(f"{item_path}.id", f"duplicates id {identifier!r}")
        if report_ref not in declared_report_refs:
            _fail(
                f"{item_path}.report_ref",
                "must be declared in correction_request.discrepancy_report_refs",
            )
        pair = (report_ref, discrepancy_id)
        if pair in pairs:
            _fail(item_path, f"duplicates report/discrepancy pair {pair!r}")
        ids.add(identifier)
        pairs.add(pair)
        items.append(
            CorrectionDiscrepancyRef(
                id=identifier,
                report_ref=report_ref,
                discrepancy_id=discrepancy_id,
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def _load_acceptance_criterion(
    value: object,
    *,
    index: int,
    declared_discrepancy_refs: AbstractSet[str],
) -> CorrectionAcceptanceCriterion:
    path = f"correction_request.acceptance_criteria[{index}]"
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={"id", "kind", "reason", "output_refs"},
        optional={
            "target_path",
            "expected",
            "artifact_id",
            "discrepancy_ref",
            "reviewer_role",
        },
    )
    kind = _enum(item["kind"], f"{path}.kind", CORRECTION_ACCEPTANCE_KINDS)
    target_path = (
        _json_pointer(item["target_path"], f"{path}.target_path")
        if "target_path" in item
        else None
    )
    has_expected = "expected" in item
    expected = _json_value(item["expected"], f"{path}.expected") if has_expected else None
    artifact_id = (
        _string(item["artifact_id"], f"{path}.artifact_id")
        if "artifact_id" in item
        else None
    )
    discrepancy_ref = (
        _string(item["discrepancy_ref"], f"{path}.discrepancy_ref")
        if "discrepancy_ref" in item
        else None
    )
    output_refs = _string_list(item["output_refs"], f"{path}.output_refs")
    reviewer_role = (
        _string(item["reviewer_role"], f"{path}.reviewer_role")
        if "reviewer_role" in item
        else None
    )

    if kind == "path_equals":
        if target_path is None or not has_expected:
            _fail(path, "kind 'path_equals' requires target_path and expected")
        if artifact_id or discrepancy_ref or output_refs or reviewer_role:
            _fail(path, "kind 'path_equals' forbids unrelated acceptance fields")
    elif kind in {"path_absent", "path_recomputed"}:
        if target_path is None:
            _fail(path, f"kind {kind!r} requires target_path")
        if has_expected or artifact_id or discrepancy_ref or output_refs or reviewer_role:
            _fail(path, f"kind {kind!r} forbids unrelated acceptance fields")
    elif kind == "artifact_valid":
        if artifact_id is None:
            _fail(path, "kind 'artifact_valid' requires artifact_id")
        if target_path or has_expected or discrepancy_ref or output_refs or reviewer_role:
            _fail(path, "kind 'artifact_valid' forbids unrelated acceptance fields")
    elif kind == "discrepancy_resolved":
        if discrepancy_ref is None:
            _fail(path, "kind 'discrepancy_resolved' requires discrepancy_ref")
        if discrepancy_ref not in declared_discrepancy_refs:
            _fail(
                f"{path}.discrepancy_ref",
                "must be declared in correction_request.discrepancy_refs",
            )
        if target_path or has_expected or artifact_id or output_refs or reviewer_role:
            _fail(path, "kind 'discrepancy_resolved' forbids unrelated acceptance fields")
    elif kind == "recheck_completed":
        if not output_refs:
            _fail(path, "kind 'recheck_completed' requires at least one output_ref")
        if target_path or has_expected or artifact_id or discrepancy_ref or reviewer_role:
            _fail(path, "kind 'recheck_completed' forbids unrelated acceptance fields")
    elif kind == "human_reviewed":
        if reviewer_role is None:
            _fail(path, "kind 'human_reviewed' requires reviewer_role")
        if target_path or has_expected or artifact_id or discrepancy_ref or output_refs:
            _fail(path, "kind 'human_reviewed' forbids unrelated acceptance fields")

    return CorrectionAcceptanceCriterion(
        id=_string(item["id"], f"{path}.id"),
        kind=kind,
        reason=_string(item["reason"], f"{path}.reason"),
        target_path=target_path,
        has_expected=has_expected,
        expected=expected,
        artifact_id=artifact_id,
        discrepancy_ref=discrepancy_ref,
        output_refs=tuple(sorted(output_refs)),
        reviewer_role=reviewer_role,
    )


def _load_change(
    value: object,
    *,
    index: int,
    declared_discrepancy_refs: AbstractSet[str],
    declared_artifact_refs: AbstractSet[str],
    declared_observation_refs: AbstractSet[str],
    declared_evidence_refs: AbstractSet[str],
    acceptance_by_id: Mapping[str, CorrectionAcceptanceCriterion],
) -> CorrectionChange:
    path = f"correction_request.changes[{index}]"
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={
            "id",
            "discrepancy_ref",
            "subject_kind",
            "target_path",
            "operation",
            "reason",
            "basis_refs",
            "observation_refs",
            "evidence_refs",
            "input_fields",
            "acceptance_criterion_refs",
        },
        optional={"before", "after"},
    )
    discrepancy_ref = _string(
        item["discrepancy_ref"], f"{path}.discrepancy_ref"
    )
    if discrepancy_ref not in declared_discrepancy_refs:
        _fail(
            f"{path}.discrepancy_ref",
            "must be declared in correction_request.discrepancy_refs",
        )
    subject_kind = _enum(
        item["subject_kind"], f"{path}.subject_kind", CORRECTION_SUBJECT_KINDS
    )
    target_path = _json_pointer(
        item["target_path"], f"{path}.target_path", subject_kind=subject_kind
    )
    _validate_change_target_contract(
        target_path,
        subject_kind,
        f"{path}.target_path",
    )
    operation = _enum(
        item["operation"], f"{path}.operation", CORRECTION_OPERATIONS
    )
    has_before = "before" in item
    has_after = "after" in item
    before = _json_value(item["before"], f"{path}.before") if has_before else None
    after = _json_value(item["after"], f"{path}.after") if has_after else None
    input_fields = _string_list(item["input_fields"], f"{path}.input_fields")

    if operation == "add" and (has_before or not has_after or input_fields):
        _fail(path, "operation 'add' requires after, forbids before, and forbids input_fields")
    if operation == "replace" and (
        not has_before or not has_after or before == after or input_fields
    ):
        _fail(
            path,
            "operation 'replace' requires different before/after values and forbids input_fields",
        )
    if operation == "remove" and (not has_before or has_after or input_fields):
        _fail(path, "operation 'remove' requires before and forbids after/input_fields")
    if operation == "recompute" and (not has_before or has_after or not input_fields):
        _fail(
            path,
            "operation 'recompute' requires before and non-empty input_fields, and forbids after",
        )

    basis_refs = _string_list(item["basis_refs"], f"{path}.basis_refs", non_empty=True)
    observation_refs = _string_list(
        item["observation_refs"], f"{path}.observation_refs"
    )
    evidence_refs = _string_list(item["evidence_refs"], f"{path}.evidence_refs")
    acceptance_refs = _string_list(
        item["acceptance_criterion_refs"],
        f"{path}.acceptance_criterion_refs",
        non_empty=True,
    )
    _closed_refs(
        basis_refs,
        f"{path}.basis_refs",
        declared_artifact_refs,
        "correction_request artifact references",
    )
    _closed_refs(
        observation_refs,
        f"{path}.observation_refs",
        declared_observation_refs,
        "correction_request.observation_refs",
    )
    _closed_refs(
        evidence_refs,
        f"{path}.evidence_refs",
        declared_evidence_refs,
        "correction_request.evidence_refs",
    )
    _closed_refs(
        acceptance_refs,
        f"{path}.acceptance_criterion_refs",
        set(acceptance_by_id),
        "correction_request.acceptance_criteria",
    )

    criteria = [acceptance_by_id[ref] for ref in acceptance_refs]
    if operation in {"add", "replace"}:
        if not any(
            criterion.kind == "path_equals"
            and criterion.target_path == target_path
            and criterion.has_expected
            and criterion.expected == after
            for criterion in criteria
        ):
            _fail(
                f"{path}.acceptance_criterion_refs",
                "must include path_equals for target_path with the requested after value",
            )
    elif operation == "remove":
        if not any(
            criterion.kind == "path_absent" and criterion.target_path == target_path
            for criterion in criteria
        ):
            _fail(
                f"{path}.acceptance_criterion_refs",
                "must include path_absent for target_path",
            )
    elif operation == "recompute":
        if not any(
            criterion.kind == "path_recomputed" and criterion.target_path == target_path
            for criterion in criteria
        ):
            _fail(
                f"{path}.acceptance_criterion_refs",
                "must include path_recomputed for target_path",
            )

    return CorrectionChange(
        id=_string(item["id"], f"{path}.id"),
        discrepancy_ref=discrepancy_ref,
        subject_kind=subject_kind,
        target_path=target_path,
        operation=operation,
        reason=_string(item["reason"], f"{path}.reason"),
        basis_refs=tuple(sorted(basis_refs)),
        observation_refs=tuple(sorted(observation_refs)),
        evidence_refs=tuple(sorted(evidence_refs)),
        input_fields=tuple(sorted(input_fields)),
        acceptance_criterion_refs=tuple(sorted(acceptance_refs)),
        has_before=has_before,
        before=before,
        has_after=has_after,
        after=after,
    )


def _load_review_requirement(
    value: object,
    *,
    index: int,
    declared_discrepancy_refs: AbstractSet[str],
    declared_artifact_refs: AbstractSet[str],
) -> CorrectionReviewRequirement:
    path = f"correction_request.review_requirements[{index}]"
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={
            "id",
            "discrepancy_refs",
            "reviewer_role",
            "reason",
            "affected_paths",
            "basis_refs",
        },
    )
    discrepancy_refs = _string_list(
        item["discrepancy_refs"], f"{path}.discrepancy_refs", non_empty=True
    )
    basis_refs = _string_list(item["basis_refs"], f"{path}.basis_refs", non_empty=True)
    _closed_refs(
        discrepancy_refs,
        f"{path}.discrepancy_refs",
        declared_discrepancy_refs,
        "correction_request.discrepancy_refs",
    )
    _closed_refs(
        basis_refs,
        f"{path}.basis_refs",
        declared_artifact_refs,
        "correction_request artifact references",
    )
    affected_paths = tuple(
        sorted(
            _json_pointer(path_value, f"{path}.affected_paths[{item_index}]")
            for item_index, path_value in enumerate(
                _string_list(
                    item["affected_paths"], f"{path}.affected_paths", non_empty=True
                )
            )
        )
    )
    return CorrectionReviewRequirement(
        id=_string(item["id"], f"{path}.id"),
        discrepancy_refs=tuple(sorted(discrepancy_refs)),
        reviewer_role=_string(item["reviewer_role"], f"{path}.reviewer_role"),
        reason=_string(item["reason"], f"{path}.reason"),
        affected_paths=affected_paths,
        basis_refs=tuple(sorted(basis_refs)),
    )


def _load_output_contract(
    value: object,
    base_world_state: CorrectionWorldStateRef,
) -> CorrectionOutputContract:
    path = "correction_request.output_contract"
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={
            "artifact_id",
            "schema_version",
            "world_state_id",
            "minimum_revision",
            "preserve_immutable_paths",
            "require_semantic_fingerprint",
        },
    )
    if item["artifact_id"] != "geotask.world-state":
        _fail(f"{path}.artifact_id", "must equal 'geotask.world-state'")
    if item["schema_version"] != "0.1":
        _fail(f"{path}.schema_version", "must equal '0.1'")
    world_state_id = _string(item["world_state_id"], f"{path}.world_state_id")
    if world_state_id != base_world_state.world_state_id:
        _fail(
            f"{path}.world_state_id",
            "must equal base_world_state.world_state_id",
        )
    minimum_revision = _positive_integer(
        item["minimum_revision"], f"{path}.minimum_revision"
    )
    if minimum_revision <= base_world_state.revision:
        _fail(
            f"{path}.minimum_revision",
            "must be greater than base_world_state.revision",
        )
    preserve = _boolean(
        item["preserve_immutable_paths"], f"{path}.preserve_immutable_paths"
    )
    require_fingerprint = _boolean(
        item["require_semantic_fingerprint"], f"{path}.require_semantic_fingerprint"
    )
    if not preserve:
        _fail(f"{path}.preserve_immutable_paths", "must be true")
    if not require_fingerprint:
        _fail(f"{path}.require_semantic_fingerprint", "must be true")
    return CorrectionOutputContract(
        artifact_id="geotask.world-state",
        schema_version="0.1",
        world_state_id=world_state_id,
        minimum_revision=minimum_revision,
        preserve_immutable_paths=True,
        require_semantic_fingerprint=True,
    )


def _ensure_unique_artifact_refs(
    refs: Sequence[CorrectionArtifactRef | CorrectionWorldStateRef],
) -> None:
    ref_ids: set[str] = set()
    instance_ids: set[str] = set()
    for ref in refs:
        instance_id = (
            ref.world_state_id
            if isinstance(ref, CorrectionWorldStateRef)
            else ref.instance_id
        )
        if ref.ref_id in ref_ids:
            _fail("correction_request artifact references", f"duplicates ref_id {ref.ref_id!r}")
        if instance_id in instance_ids:
            _fail(
                "correction_request artifact references",
                f"duplicates instance identity {instance_id!r}",
            )
        ref_ids.add(ref.ref_id)
        instance_ids.add(instance_id)


def _load_unique_items(
    raw: object,
    path: str,
    loader,
) -> tuple[object, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    items: list[object] = []
    ids: set[str] = set()
    for index, value in enumerate(raw):
        item = loader(value, index)
        identifier = getattr(item, "id")
        if identifier in ids:
            _fail(f"{path}[{index}].id", f"duplicates id {identifier!r}")
        ids.add(identifier)
        items.append(item)
    return tuple(sorted(items, key=lambda item: getattr(item, "id")))


def load_correction_request(payload: Mapping[str, object]) -> CorrectionRequest:
    """Load and strictly validate one Correction Request v0.1 payload."""

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"correction_request"})
    body = _mapping(root["correction_request"], "correction_request")
    _exact_fields(
        body,
        "correction_request",
        required={
            "schema_id",
            "schema_version",
            "request_id",
            "created_at",
            "state",
            "reason",
            "base_world_state",
            "discrepancy_report_refs",
            "supporting_artifact_refs",
            "observation_refs",
            "evidence_refs",
            "discrepancy_refs",
            "changes",
            "review_requirements",
            "acceptance_criteria",
            "output_contract",
            "blocked_outputs",
            "blocked_actions",
            "resume_when",
            "next_action",
        },
    )
    if body["schema_id"] != CORRECTION_REQUEST_SCHEMA_ID:
        _fail(
            "correction_request.schema_id",
            f"must equal {CORRECTION_REQUEST_SCHEMA_ID!r}",
        )
    if body["schema_version"] != CORRECTION_REQUEST_SCHEMA_VERSION:
        _fail(
            "correction_request.schema_version",
            f"must equal {CORRECTION_REQUEST_SCHEMA_VERSION!r}",
        )

    created_at_text, created_at = _timestamp(
        body["created_at"], "correction_request.created_at"
    )
    base_world_state, base_as_of = _load_world_state_ref(body["base_world_state"])
    if created_at < base_as_of:
        _fail(
            "correction_request.created_at",
            "must not be earlier than base_world_state.as_of",
        )

    discrepancy_report_refs = _load_artifact_refs(
        body["discrepancy_report_refs"],
        "correction_request.discrepancy_report_refs",
        expected_artifact_id=DISCREPANCY_REPORT_ARTIFACT_ID,
        expected_schema_version=DISCREPANCY_REPORT_SCHEMA_VERSION,
        non_empty=True,
    )
    supporting_artifact_refs = _load_artifact_refs(
        body["supporting_artifact_refs"],
        "correction_request.supporting_artifact_refs",
    )
    _ensure_unique_artifact_refs(
        (base_world_state, *discrepancy_report_refs, *supporting_artifact_refs)
    )
    declared_report_refs = frozenset(item.ref_id for item in discrepancy_report_refs)
    declared_artifact_refs = frozenset(
        item.ref_id
        for item in (base_world_state, *discrepancy_report_refs, *supporting_artifact_refs)
    )

    observation_refs = _string_list(
        body["observation_refs"], "correction_request.observation_refs"
    )
    evidence_refs = _string_list(
        body["evidence_refs"], "correction_request.evidence_refs"
    )
    discrepancy_refs = _load_discrepancy_refs(
        body["discrepancy_refs"], declared_report_refs
    )
    declared_discrepancy_refs = frozenset(item.id for item in discrepancy_refs)

    raw_acceptance = body["acceptance_criteria"]
    acceptance_criteria = _load_unique_items(
        raw_acceptance,
        "correction_request.acceptance_criteria",
        lambda value, index: _load_acceptance_criterion(
            value,
            index=index,
            declared_discrepancy_refs=declared_discrepancy_refs,
        ),
    )
    acceptance_by_id = {
        item.id: item for item in acceptance_criteria if isinstance(item, CorrectionAcceptanceCriterion)
    }

    changes = _load_unique_items(
        body["changes"],
        "correction_request.changes",
        lambda value, index: _load_change(
            value,
            index=index,
            declared_discrepancy_refs=declared_discrepancy_refs,
            declared_artifact_refs=declared_artifact_refs,
            declared_observation_refs=frozenset(observation_refs),
            declared_evidence_refs=frozenset(evidence_refs),
            acceptance_by_id=acceptance_by_id,
        ),
    )
    typed_changes = tuple(
        item for item in changes if isinstance(item, CorrectionChange)
    )
    for index, left in enumerate(typed_changes):
        for right in typed_changes[index + 1 :]:
            if _paths_overlap(left.target_path, right.target_path):
                _fail(
                    "correction_request.changes",
                    "change target paths must not duplicate or overlap: "
                    f"{left.target_path!r} and {right.target_path!r}",
                )
    review_requirements = _load_unique_items(
        body["review_requirements"],
        "correction_request.review_requirements",
        lambda value, index: _load_review_requirement(
            value,
            index=index,
            declared_discrepancy_refs=declared_discrepancy_refs,
            declared_artifact_refs=declared_artifact_refs,
        ),
    )
    typed_reviews = tuple(
        item
        for item in review_requirements
        if isinstance(item, CorrectionReviewRequirement)
    )
    typed_acceptance = tuple(
        item
        for item in acceptance_criteria
        if isinstance(item, CorrectionAcceptanceCriterion)
    )

    state = _enum(
        body["state"], "correction_request.state", CORRECTION_REQUEST_STATES
    )
    next_action = _enum(
        body["next_action"],
        "correction_request.next_action",
        CORRECTION_NEXT_ACTIONS,
    )
    if state == "required":
        if not changes:
            _fail("correction_request.changes", "state 'required' requires changes")
        if review_requirements:
            _fail(
                "correction_request.review_requirements",
                "state 'required' forbids review requirements",
            )
        if next_action != "materialize_successor_state":
            _fail(
                "correction_request.next_action",
                "state 'required' requires 'materialize_successor_state'",
            )
        if any(
            isinstance(item, CorrectionAcceptanceCriterion)
            and item.kind == "human_reviewed"
            for item in acceptance_criteria
        ):
            _fail(
                "correction_request.acceptance_criteria",
                "state 'required' forbids human_reviewed criteria",
            )
        changed_discrepancies = {
            item.discrepancy_ref for item in changes if isinstance(item, CorrectionChange)
        }
        missing_changes = sorted(declared_discrepancy_refs - changed_discrepancies)
        if missing_changes:
            _fail(
                "correction_request.changes",
                "state 'required' requires at least one change for every discrepancy_ref: "
                + ", ".join(missing_changes),
            )
    elif state == "need_review":
        if changes:
            _fail("correction_request.changes", "state 'need_review' forbids changes")
        if not review_requirements:
            _fail(
                "correction_request.review_requirements",
                "state 'need_review' requires review requirements",
            )
        if next_action != "human_review":
            _fail(
                "correction_request.next_action",
                "state 'need_review' requires 'human_review'",
            )
        if not any(
            isinstance(item, CorrectionAcceptanceCriterion)
            and item.kind == "human_reviewed"
            for item in acceptance_criteria
        ):
            _fail(
                "correction_request.acceptance_criteria",
                "state 'need_review' requires a human_reviewed criterion",
            )
    elif state == "blocked":
        if changes or review_requirements or acceptance_criteria:
            _fail(
                "correction_request",
                "state 'blocked' forbids changes, review requirements, and acceptance criteria",
            )
        if next_action != "none":
            _fail(
                "correction_request.next_action",
                "state 'blocked' requires 'none'",
            )

    blocked_outputs = _string_list(
        body["blocked_outputs"], "correction_request.blocked_outputs"
    )
    blocked_actions = _string_list(
        body["blocked_actions"], "correction_request.blocked_actions"
    )
    if not blocked_outputs and not blocked_actions:
        _fail(
            "correction_request",
            "must block at least one output or action until resume_when is satisfied",
        )

    if state == "required":
        resolved_discrepancies = {
            item.discrepancy_ref
            for item in typed_acceptance
            if item.kind == "discrepancy_resolved"
        }
        unresolved = sorted(declared_discrepancy_refs - resolved_discrepancies)
        if unresolved:
            _fail(
                "correction_request.acceptance_criteria",
                "state 'required' requires discrepancy_resolved for every discrepancy_ref: "
                + ", ".join(unresolved),
            )
        if not any(
            item.kind == "artifact_valid" and item.artifact_id == "geotask.world-state"
            for item in typed_acceptance
        ):
            _fail(
                "correction_request.acceptance_criteria",
                "state 'required' requires artifact_valid for 'geotask.world-state'",
            )
        rechecked_outputs = {
            output_ref
            for item in typed_acceptance
            if item.kind == "recheck_completed"
            for output_ref in item.output_refs
        }
        missing_rechecks = sorted(set(blocked_outputs) - rechecked_outputs)
        if missing_rechecks:
            _fail(
                "correction_request.acceptance_criteria",
                "every blocked_output requires recheck_completed before release: "
                + ", ".join(missing_rechecks),
            )
    elif state == "need_review":
        reviewed_discrepancies = {
            discrepancy_ref
            for item in typed_reviews
            for discrepancy_ref in item.discrepancy_refs
        }
        missing_reviews = sorted(declared_discrepancy_refs - reviewed_discrepancies)
        if missing_reviews:
            _fail(
                "correction_request.review_requirements",
                "state 'need_review' requires review coverage for every discrepancy_ref: "
                + ", ".join(missing_reviews),
            )
        criterion_roles = {
            item.reviewer_role
            for item in typed_acceptance
            if item.kind == "human_reviewed"
        }
        missing_roles = sorted(
            {item.reviewer_role for item in typed_reviews} - criterion_roles
        )
        if missing_roles:
            _fail(
                "correction_request.acceptance_criteria",
                "human_reviewed criteria must cover every required reviewer_role: "
                + ", ".join(missing_roles),
            )

    output_contract = _load_output_contract(body["output_contract"], base_world_state)

    return CorrectionRequest(
        request_id=_string(body["request_id"], "correction_request.request_id"),
        created_at=created_at_text,
        state=state,
        reason=_string(body["reason"], "correction_request.reason"),
        base_world_state=base_world_state,
        discrepancy_report_refs=discrepancy_report_refs,
        supporting_artifact_refs=supporting_artifact_refs,
        observation_refs=tuple(sorted(observation_refs)),
        evidence_refs=tuple(sorted(evidence_refs)),
        discrepancy_refs=discrepancy_refs,
        changes=typed_changes,
        review_requirements=typed_reviews,
        acceptance_criteria=typed_acceptance,
        output_contract=output_contract,
        blocked_outputs=tuple(sorted(blocked_outputs)),
        blocked_actions=tuple(sorted(blocked_actions)),
        resume_when=_string(body["resume_when"], "correction_request.resume_when"),
        next_action=next_action,
    )


def _resolve_discrepancy(
    ref: CorrectionDiscrepancyRef,
    reports: Mapping[str, DiscrepancyReport],
) -> DiscrepancyFinding:
    report = reports[ref.report_ref]
    by_id = {item.id: item for item in report.discrepancies}
    if ref.discrepancy_id not in by_id:
        _fail(
            f"correction_request.discrepancy_refs[{ref.id!r}]",
            f"discrepancy_id {ref.discrepancy_id!r} is absent from report {ref.report_ref!r}",
        )
    return by_id[ref.discrepancy_id]


def validate_correction_request_bindings(
    request: CorrectionRequest,
    base_world_state: WorldState,
    discrepancy_reports: Mapping[str, DiscrepancyReport],
    artifact_contents: Mapping[str, bytes],
) -> None:
    """Validate base-state, report, exact-byte, and bounded-scope bindings.

    This does not parse supporting artifacts, apply changes, generate a successor
    World State, evaluate acceptance criteria, resolve discrepancies, execute a
    recheck, release outputs, or authorize actions.
    """

    checks = (
        (
            "correction_request.base_world_state.world_state_id",
            request.base_world_state.world_state_id,
            base_world_state.world_state_id,
        ),
        (
            "correction_request.base_world_state.revision",
            request.base_world_state.revision,
            base_world_state.revision,
        ),
        (
            "correction_request.base_world_state.as_of",
            request.base_world_state.as_of,
            base_world_state.as_of,
        ),
        (
            "correction_request.base_world_state.semantic_fingerprint",
            request.base_world_state.semantic_fingerprint,
            base_world_state.semantic_fingerprint(),
        ),
    )
    for path, declared, actual in checks:
        if declared != actual:
            _fail(path, f"does not match bound World State: expected {actual!r}")

    expected_report_refs = {item.ref_id: item for item in request.discrepancy_report_refs}
    if set(discrepancy_reports) != set(expected_report_refs):
        missing = sorted(set(expected_report_refs) - set(discrepancy_reports))
        unknown = sorted(set(discrepancy_reports) - set(expected_report_refs))
        if missing:
            _fail(
                "discrepancy_reports",
                "missing report_ref values: " + ", ".join(missing),
            )
        if unknown:
            _fail(
                "discrepancy_reports",
                "contains unknown report_ref values: " + ", ".join(unknown),
            )

    created_at = _timestamp(request.created_at, "correction_request.created_at")[1]
    for ref_id, ref in expected_report_refs.items():
        report = discrepancy_reports[ref_id]
        if ref.instance_id != report.report_id:
            _fail(
                f"correction_request.discrepancy_report_refs[{ref_id!r}].instance_id",
                f"does not match report_id {report.report_id!r}",
            )
        report_world = report.world_state
        report_checks = (
            ("world_state_id", report_world.world_state_id, base_world_state.world_state_id),
            ("revision", report_world.revision, base_world_state.revision),
            ("as_of", report_world.as_of, base_world_state.as_of),
            (
                "semantic_fingerprint",
                report_world.semantic_fingerprint,
                base_world_state.semantic_fingerprint(),
            ),
        )
        for field, declared, actual in report_checks:
            if declared != actual:
                _fail(
                    f"discrepancy_reports[{ref_id!r}].world_state.{field}",
                    f"does not match correction base World State: expected {actual!r}",
                )
        report_recorded_at = _timestamp(
            report.recorded_at, f"discrepancy_reports[{ref_id!r}].recorded_at"
        )[1]
        if created_at < report_recorded_at:
            _fail(
                "correction_request.created_at",
                f"must not be earlier than report {ref_id!r} recorded_at",
            )

    expected_artifact_refs: dict[str, tuple[str, str]] = {
        request.base_world_state.ref_id: (
            request.base_world_state.content_sha256,
            request.base_world_state.artifact_id,
        )
    }
    for ref in (*request.discrepancy_report_refs, *request.supporting_artifact_refs):
        expected_artifact_refs[ref.ref_id] = (ref.content_sha256, ref.artifact_id)
    supplied_refs = set(artifact_contents)
    missing_artifacts = sorted(set(expected_artifact_refs) - supplied_refs)
    unknown_artifacts = sorted(supplied_refs - set(expected_artifact_refs))
    if missing_artifacts:
        _fail(
            "artifact_contents",
            "missing ref_id values: " + ", ".join(missing_artifacts),
        )
    if unknown_artifacts:
        _fail(
            "artifact_contents",
            "contains unknown ref_id values: " + ", ".join(unknown_artifacts),
        )
    for ref_id, (expected_digest, _artifact_id) in expected_artifact_refs.items():
        content = artifact_contents[ref_id]
        if not isinstance(content, bytes):
            _fail(f"artifact_contents[{ref_id!r}]", "must be bytes")
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected_digest:
            _fail(
                f"artifact_contents[{ref_id!r}]",
                f"SHA-256 mismatch: expected {expected_digest!r}, got {actual!r}",
            )

    report_observations = {
        ref
        for report in discrepancy_reports.values()
        for ref in report.observation_refs
    }
    report_evidence = {
        ref for report in discrepancy_reports.values() for ref in report.evidence_refs
    }
    missing_observations = sorted(set(request.observation_refs) - report_observations)
    if missing_observations:
        _fail(
            "correction_request.observation_refs",
            "not declared by bound Discrepancy Reports: "
            + ", ".join(missing_observations),
        )
    missing_evidence = sorted(set(request.evidence_refs) - report_evidence)
    if missing_evidence:
        _fail(
            "correction_request.evidence_refs",
            "not declared by bound Discrepancy Reports: " + ", ".join(missing_evidence),
        )

    resolved: dict[str, DiscrepancyFinding] = {}
    for ref in request.discrepancy_refs:
        finding = _resolve_discrepancy(ref, discrepancy_reports)
        resolved[ref.id] = finding
        if request.state == "required":
            if finding.state not in {"detected", "confirmed"}:
                _fail(
                    f"correction_request.discrepancy_refs[{ref.id!r}]",
                    "state 'required' needs a detected or confirmed discrepancy",
                )
            if finding.correction_scope.state != "allowed":
                _fail(
                    f"correction_request.discrepancy_refs[{ref.id!r}]",
                    "state 'required' needs correction_scope.state 'allowed'",
                )
        elif request.state == "need_review":
            if finding.correction_scope.state != "need_review":
                _fail(
                    f"correction_request.discrepancy_refs[{ref.id!r}]",
                    "state 'need_review' needs correction_scope.state 'need_review'",
                )
        elif request.state == "blocked":
            if finding.correction_scope.state not in {"blocked", "not_applicable"}:
                _fail(
                    f"correction_request.discrepancy_refs[{ref.id!r}]",
                    "state 'blocked' needs blocked or not_applicable correction scope",
                )

    for change in request.changes:
        finding = resolved[change.discrepancy_ref]
        mutable_paths = finding.correction_scope.mutable_paths
        immutable_paths = finding.correction_scope.immutable_paths
        if not any(_path_within(change.target_path, path) for path in mutable_paths):
            _fail(
                f"correction_request.changes[{change.id!r}].target_path",
                "is outside the discrepancy mutable_paths",
            )
        for immutable in immutable_paths:
            if _paths_overlap(change.target_path, immutable):
                _fail(
                    f"correction_request.changes[{change.id!r}].target_path",
                    f"overlaps immutable path {immutable!r}",
                )
        discrepancy_ref = next(
            item for item in request.discrepancy_refs if item.id == change.discrepancy_ref
        )
        if discrepancy_ref.report_ref not in change.basis_refs:
            _fail(
                f"correction_request.changes[{change.id!r}].basis_refs",
                "must include the bound Discrepancy Report ref",
            )
        unbound_observations = sorted(
            set(change.observation_refs) - set(finding.observation_refs)
        )
        if unbound_observations:
            _fail(
                f"correction_request.changes[{change.id!r}].observation_refs",
                "must be declared by the bound discrepancy finding: "
                + ", ".join(unbound_observations),
            )
        unbound_evidence = sorted(
            set(change.evidence_refs) - set(finding.evidence_refs)
        )
        if unbound_evidence:
            _fail(
                f"correction_request.changes[{change.id!r}].evidence_refs",
                "must be declared by the bound discrepancy finding: "
                + ", ".join(unbound_evidence),
            )
        if (
            change.target_path == finding.subject_path
            and finding.has_observed
            and change.operation in {"replace", "remove", "recompute"}
            and change.before != finding.observed
        ):
            _fail(
                f"correction_request.changes[{change.id!r}].before",
                "must equal the discrepancy observed value for the same subject_path",
            )

        path_exists, current_value = _resolve_world_state_path(
            base_world_state,
            change.target_path,
        )
        if change.operation == "add":
            if path_exists:
                _fail(
                    f"correction_request.changes[{change.id!r}].target_path",
                    "operation 'add' requires the target path to be absent from the base World State",
                )
        else:
            if not path_exists:
                _fail(
                    f"correction_request.changes[{change.id!r}].target_path",
                    "must exist in the base World State for this operation",
                )
            if change.before != current_value:
                _fail(
                    f"correction_request.changes[{change.id!r}].before",
                    "does not match the value at target_path in the base World State: "
                    f"expected {current_value!r}",
                )

    for review in request.review_requirements:
        for discrepancy_ref_id in review.discrepancy_refs:
            finding = resolved[discrepancy_ref_id]
            discrepancy_ref = next(
                item
                for item in request.discrepancy_refs
                if item.id == discrepancy_ref_id
            )
            if discrepancy_ref.report_ref not in review.basis_refs:
                _fail(
                    f"correction_request.review_requirements[{review.id!r}].basis_refs",
                    "must include every bound Discrepancy Report referenced by the review requirement",
                )
            scope_paths = (
                *finding.correction_scope.mutable_paths,
                *finding.correction_scope.immutable_paths,
            )
            for affected_path in review.affected_paths:
                if not any(
                    _path_within(affected_path, scope_path)
                    for scope_path in scope_paths
                ):
                    _fail(
                        f"correction_request.review_requirements[{review.id!r}].affected_paths",
                        f"path {affected_path!r} is outside the discrepancy correction scope",
                    )


def __all_public() -> list[str]:
    return [
        "CORRECTION_REQUEST_ARTIFACT_ID",
        "CORRECTION_REQUEST_SCHEMA_ID",
        "CORRECTION_REQUEST_SCHEMA_VERSION",
        "CORRECTION_REQUEST_FORMAT_VERSION",
        "CORRECTION_REQUEST_STATES",
        "CORRECTION_OPERATIONS",
        "CORRECTION_SUBJECT_KINDS",
        "CORRECTION_ACCEPTANCE_KINDS",
        "CORRECTION_NEXT_ACTIONS",
        "CorrectionRequestFormatError",
        "CorrectionArtifactRef",
        "CorrectionWorldStateRef",
        "CorrectionDiscrepancyRef",
        "CorrectionAcceptanceCriterion",
        "CorrectionChange",
        "CorrectionReviewRequirement",
        "CorrectionOutputContract",
        "CorrectionRequest",
        "load_correction_request",
        "validate_correction_request_bindings",
    ]


__all__ = __all_public()
