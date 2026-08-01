"""Public State Transition v0.1 contract for auditable GeoTask state changes.

A State Transition binds one earlier World State snapshot to one later snapshot and
records which Observation references support explicit world-state path changes,
relation changes, and action-eligibility changes. Loading validates structure,
time and revision order, reference closure, change semantics, JSON safety, and a
deterministic semantic fingerprint. It does not compare snapshot contents,
automatically apply changes, materialize a World State, verify external truth,
rerun tasks, or authorize action.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Mapping, Sequence

from geotask_core.v1.observation import CLAIM_BASES
from geotask_core.v1.world_state import VERIFICATION_STATUSES, WorldState


STATE_TRANSITION_ARTIFACT_ID = "geotask.state-transition"
STATE_TRANSITION_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/geotask-state-transition-v0.1.schema.json"
)
STATE_TRANSITION_SCHEMA_VERSION = "0.1"
STATE_TRANSITION_FORMAT_VERSION = "0.1"

CHANGE_KINDS = frozenset({"object", "attribute", "relation"})
CHANGE_OPERATIONS = frozenset({"add", "replace", "remove"})
ACTION_ELIGIBILITY_STATES = frozenset({"eligible", "blocked", "unknown"})


class StateTransitionFormatError(ValueError):
    """Raised when a State Transition payload violates the public v0.1 contract."""


def _fail(path: str, message: str) -> None:
    raise StateTransitionFormatError(f"{path}: {message}")


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
    normalized = _string(value, path)
    if normalized not in allowed:
        _fail(path, "must be one of: " + ", ".join(sorted(allowed)))
    return normalized


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
        raise StateTransitionFormatError(
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
        return [_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    _fail(path, "must be a JSON-compatible value")


def _json_pointer(value: object, path: str, *, kind: str) -> str:
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

    if kind == "object":
        if len(segments) < 2 or segments[0] != "objects" or "attributes" in segments:
            _fail(path, "object changes must target /objects/<object-id>/...")
    elif kind == "attribute":
        if len(segments) < 4 or segments[0] != "objects" or segments[2] != "attributes":
            _fail(
                path,
                "attribute changes must target /objects/<object-id>/attributes/<name>/...",
            )
    elif kind == "relation":
        if len(segments) < 2 or segments[0] != "relations":
            _fail(path, "relation changes must target /relations/<relation-id>/...")
    return pointer


def _closed_refs(
    refs: tuple[str, ...],
    path: str,
    declared: frozenset[str],
    declaration_path: str,
) -> None:
    for index, ref in enumerate(refs):
        if ref not in declared:
            _fail(f"{path}[{index}]", f"must be declared in {declaration_path}: {ref!r}")


@dataclass(frozen=True)
class StateTransitionStateRef:
    world_state_id: str
    revision: int
    as_of: str
    semantic_fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "world_state_id": self.world_state_id,
            "revision": self.revision,
            "as_of": self.as_of,
            "semantic_fingerprint": self.semantic_fingerprint,
        }


@dataclass(frozen=True)
class StateTransitionChange:
    id: str
    kind: str
    operation: str
    path: str
    basis: str
    verification_status: str
    reason: str
    observation_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    has_before: bool
    before: object
    has_after: bool
    after: object

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "kind": self.kind,
            "operation": self.operation,
            "path": self.path,
            "basis": self.basis,
            "verification_status": self.verification_status,
            "reason": self.reason,
            "observation_refs": sorted(self.observation_refs),
            "evidence_refs": sorted(self.evidence_refs),
        }
        if self.has_before:
            payload["before"] = copy.deepcopy(self.before)
        if self.has_after:
            payload["after"] = copy.deepcopy(self.after)
        return payload


@dataclass(frozen=True)
class ActionEligibilityChange:
    id: str
    output_ref: str
    before: str
    after: str
    reason: str
    observation_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "output_ref": self.output_ref,
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
            "observation_refs": sorted(self.observation_refs),
            "evidence_refs": sorted(self.evidence_refs),
        }


@dataclass(frozen=True)
class StateTransition:
    transition_id: str
    occurred_at: str
    recorded_at: str
    from_state: StateTransitionStateRef
    to_state: StateTransitionStateRef
    observation_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    changes: tuple[StateTransitionChange, ...]
    action_eligibility_changes: tuple[ActionEligibilityChange, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "state_transition": {
                "schema_id": STATE_TRANSITION_SCHEMA_ID,
                "schema_version": STATE_TRANSITION_SCHEMA_VERSION,
                "transition_id": self.transition_id,
                "occurred_at": self.occurred_at,
                "recorded_at": self.recorded_at,
                "from_state": self.from_state.to_dict(),
                "to_state": self.to_state.to_dict(),
                "observation_refs": sorted(self.observation_refs),
                "evidence_refs": sorted(self.evidence_refs),
                "changes": [
                    item.to_dict() for item in sorted(self.changes, key=lambda item: item.id)
                ],
                "action_eligibility_changes": [
                    item.to_dict()
                    for item in sorted(
                        self.action_eligibility_changes, key=lambda item: item.id
                    )
                ],
            }
        }

    def semantic_fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint of the normalized transition."""

        raw = json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _load_state_ref(value: object, path: str) -> tuple[StateTransitionStateRef, datetime]:
    ref = _mapping(value, path)
    _exact_fields(
        ref,
        path,
        required={"world_state_id", "revision", "as_of", "semantic_fingerprint"},
    )
    as_of_text, as_of = _timestamp(ref["as_of"], f"{path}.as_of")
    return (
        StateTransitionStateRef(
            world_state_id=_string(ref["world_state_id"], f"{path}.world_state_id"),
            revision=_positive_integer(ref["revision"], f"{path}.revision"),
            as_of=as_of_text,
            semantic_fingerprint=_sha256(
                ref["semantic_fingerprint"], f"{path}.semantic_fingerprint"
            ),
        ),
        as_of,
    )


def _load_change(
    value: object,
    *,
    index: int,
    declared_observation_refs: frozenset[str],
    declared_evidence_refs: frozenset[str],
) -> StateTransitionChange:
    path = f"state_transition.changes[{index}]"
    change = _mapping(value, path)
    _exact_fields(
        change,
        path,
        required={
            "id",
            "kind",
            "operation",
            "path",
            "basis",
            "verification_status",
            "reason",
            "observation_refs",
            "evidence_refs",
        },
        optional={"before", "after"},
    )
    kind = _enum(change["kind"], f"{path}.kind", CHANGE_KINDS)
    operation = _enum(change["operation"], f"{path}.operation", CHANGE_OPERATIONS)
    has_before = "before" in change
    has_after = "after" in change
    if operation == "add" and (has_before or not has_after):
        _fail(path, "add requires after and forbids before")
    if operation == "replace" and (not has_before or not has_after):
        _fail(path, "replace requires both before and after")
    if operation == "remove" and (not has_before or has_after):
        _fail(path, "remove requires before and forbids after")

    before = _json_value(change["before"], f"{path}.before") if has_before else None
    after = _json_value(change["after"], f"{path}.after") if has_after else None
    if operation == "replace" and before == after:
        _fail(path, "replace before and after must differ")

    observation_refs = _string_list(
        change["observation_refs"], f"{path}.observation_refs", non_empty=True
    )
    evidence_refs = _string_list(change["evidence_refs"], f"{path}.evidence_refs")
    _closed_refs(
        observation_refs,
        f"{path}.observation_refs",
        declared_observation_refs,
        "state_transition.observation_refs",
    )
    _closed_refs(
        evidence_refs,
        f"{path}.evidence_refs",
        declared_evidence_refs,
        "state_transition.evidence_refs",
    )

    return StateTransitionChange(
        id=_string(change["id"], f"{path}.id"),
        kind=kind,
        operation=operation,
        path=_json_pointer(change["path"], f"{path}.path", kind=kind),
        basis=_enum(change["basis"], f"{path}.basis", CLAIM_BASES),
        verification_status=_enum(
            change["verification_status"],
            f"{path}.verification_status",
            VERIFICATION_STATUSES,
        ),
        reason=_string(change["reason"], f"{path}.reason"),
        observation_refs=tuple(sorted(observation_refs)),
        evidence_refs=tuple(sorted(evidence_refs)),
        has_before=has_before,
        before=before,
        has_after=has_after,
        after=after,
    )


def _load_action_eligibility_change(
    value: object,
    *,
    index: int,
    declared_observation_refs: frozenset[str],
    declared_evidence_refs: frozenset[str],
) -> ActionEligibilityChange:
    path = f"state_transition.action_eligibility_changes[{index}]"
    change = _mapping(value, path)
    _exact_fields(
        change,
        path,
        required={
            "id",
            "output_ref",
            "before",
            "after",
            "reason",
            "observation_refs",
            "evidence_refs",
        },
    )
    before = _enum(change["before"], f"{path}.before", ACTION_ELIGIBILITY_STATES)
    after = _enum(change["after"], f"{path}.after", ACTION_ELIGIBILITY_STATES)
    if before == after:
        _fail(path, "before and after must differ")

    observation_refs = _string_list(
        change["observation_refs"], f"{path}.observation_refs", non_empty=True
    )
    evidence_refs = _string_list(change["evidence_refs"], f"{path}.evidence_refs")
    _closed_refs(
        observation_refs,
        f"{path}.observation_refs",
        declared_observation_refs,
        "state_transition.observation_refs",
    )
    _closed_refs(
        evidence_refs,
        f"{path}.evidence_refs",
        declared_evidence_refs,
        "state_transition.evidence_refs",
    )
    return ActionEligibilityChange(
        id=_string(change["id"], f"{path}.id"),
        output_ref=_string(change["output_ref"], f"{path}.output_ref"),
        before=before,
        after=after,
        reason=_string(change["reason"], f"{path}.reason"),
        observation_refs=tuple(sorted(observation_refs)),
        evidence_refs=tuple(sorted(evidence_refs)),
    )


def load_state_transition(payload: Mapping[str, object]) -> StateTransition:
    """Load and strictly validate one State Transition v0.1 payload.

    Validation proves only that the transition record is structurally complete,
    internally consistent, reference-closed, time-ordered, JSON-safe, and bound to
    declared snapshot fingerprints. It does not compare snapshot contents, apply
    changes, materialize a state, verify external truth, or authorize action.
    """

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"state_transition"})
    body = _mapping(root["state_transition"], "state_transition")
    _exact_fields(
        body,
        "state_transition",
        required={
            "schema_id",
            "schema_version",
            "transition_id",
            "occurred_at",
            "recorded_at",
            "from_state",
            "to_state",
            "observation_refs",
            "evidence_refs",
            "changes",
            "action_eligibility_changes",
        },
    )
    if body["schema_id"] != STATE_TRANSITION_SCHEMA_ID:
        _fail("state_transition.schema_id", f"must equal {STATE_TRANSITION_SCHEMA_ID!r}")
    if body["schema_version"] != STATE_TRANSITION_SCHEMA_VERSION:
        _fail(
            "state_transition.schema_version",
            f"must equal {STATE_TRANSITION_SCHEMA_VERSION!r}",
        )

    occurred_at_text, occurred_at = _timestamp(
        body["occurred_at"], "state_transition.occurred_at"
    )
    recorded_at_text, recorded_at = _timestamp(
        body["recorded_at"], "state_transition.recorded_at"
    )
    from_state, from_as_of = _load_state_ref(
        body["from_state"], "state_transition.from_state"
    )
    to_state, to_as_of = _load_state_ref(body["to_state"], "state_transition.to_state")
    if from_state.world_state_id != to_state.world_state_id:
        _fail(
            "state_transition.to_state.world_state_id",
            "must equal from_state.world_state_id",
        )
    if to_state.revision <= from_state.revision:
        _fail(
            "state_transition.to_state.revision",
            "must be greater than from_state.revision",
        )
    if to_as_of < from_as_of:
        _fail("state_transition.to_state.as_of", "must not be earlier than from_state.as_of")
    if occurred_at < from_as_of or occurred_at > to_as_of:
        _fail(
            "state_transition.occurred_at",
            "must fall between from_state.as_of and to_state.as_of inclusive",
        )
    if recorded_at < to_as_of:
        _fail("state_transition.recorded_at", "must not be earlier than to_state.as_of")

    observation_refs = _string_list(
        body["observation_refs"],
        "state_transition.observation_refs",
        non_empty=True,
    )
    evidence_refs = _string_list(
        body["evidence_refs"], "state_transition.evidence_refs"
    )
    declared_observation_refs = frozenset(observation_refs)
    declared_evidence_refs = frozenset(evidence_refs)

    raw_changes = body["changes"]
    if not isinstance(raw_changes, Sequence) or isinstance(
        raw_changes, (str, bytes, bytearray)
    ):
        _fail("state_transition.changes", "must be an array")
    changes: list[StateTransitionChange] = []
    ids: set[str] = set()
    paths: set[str] = set()
    for index, raw_change in enumerate(raw_changes):
        change = _load_change(
            raw_change,
            index=index,
            declared_observation_refs=declared_observation_refs,
            declared_evidence_refs=declared_evidence_refs,
        )
        if change.id in ids:
            _fail(f"state_transition.changes[{index}].id", f"duplicates id {change.id!r}")
        if change.path in paths:
            _fail(
                f"state_transition.changes[{index}].path",
                f"duplicates changed path {change.path!r}",
            )
        ids.add(change.id)
        paths.add(change.path)
        changes.append(change)

    raw_eligibility_changes = body["action_eligibility_changes"]
    if not isinstance(raw_eligibility_changes, Sequence) or isinstance(
        raw_eligibility_changes, (str, bytes, bytearray)
    ):
        _fail("state_transition.action_eligibility_changes", "must be an array")
    eligibility_changes: list[ActionEligibilityChange] = []
    output_refs: set[str] = set()
    for index, raw_change in enumerate(raw_eligibility_changes):
        change = _load_action_eligibility_change(
            raw_change,
            index=index,
            declared_observation_refs=declared_observation_refs,
            declared_evidence_refs=declared_evidence_refs,
        )
        if change.id in ids:
            _fail(
                f"state_transition.action_eligibility_changes[{index}].id",
                f"duplicates id {change.id!r}",
            )
        if change.output_ref in output_refs:
            _fail(
                f"state_transition.action_eligibility_changes[{index}].output_ref",
                f"duplicates output_ref {change.output_ref!r}",
            )
        ids.add(change.id)
        output_refs.add(change.output_ref)
        eligibility_changes.append(change)

    if not changes and not eligibility_changes:
        _fail(
            "state_transition",
            "must contain at least one state change or action eligibility change",
        )

    return StateTransition(
        transition_id=_string(body["transition_id"], "state_transition.transition_id"),
        occurred_at=occurred_at_text,
        recorded_at=recorded_at_text,
        from_state=from_state,
        to_state=to_state,
        observation_refs=tuple(sorted(observation_refs)),
        evidence_refs=tuple(sorted(evidence_refs)),
        changes=tuple(sorted(changes, key=lambda item: item.id)),
        action_eligibility_changes=tuple(
            sorted(eligibility_changes, key=lambda item: item.id)
        ),
    )


def validate_state_transition_bindings(
    transition: StateTransition,
    from_state: WorldState,
    to_state: WorldState,
) -> None:
    """Validate that a transition is cryptographically bound to two snapshots.

    This checks identity, revision, snapshot time, and deterministic semantic
    fingerprints only. It does not compute or validate the declared path changes.
    """

    checks = (
        (
            "state_transition.from_state.world_state_id",
            transition.from_state.world_state_id,
            from_state.world_state_id,
        ),
        (
            "state_transition.from_state.revision",
            transition.from_state.revision,
            from_state.revision,
        ),
        (
            "state_transition.from_state.as_of",
            transition.from_state.as_of,
            from_state.as_of,
        ),
        (
            "state_transition.from_state.semantic_fingerprint",
            transition.from_state.semantic_fingerprint,
            from_state.semantic_fingerprint(),
        ),
        (
            "state_transition.to_state.world_state_id",
            transition.to_state.world_state_id,
            to_state.world_state_id,
        ),
        (
            "state_transition.to_state.revision",
            transition.to_state.revision,
            to_state.revision,
        ),
        (
            "state_transition.to_state.as_of",
            transition.to_state.as_of,
            to_state.as_of,
        ),
        (
            "state_transition.to_state.semantic_fingerprint",
            transition.to_state.semantic_fingerprint,
            to_state.semantic_fingerprint(),
        ),
    )
    for path, declared, actual in checks:
        if declared != actual:
            _fail(path, f"does not match bound World State: expected {actual!r}")


__all__ = [
    "STATE_TRANSITION_ARTIFACT_ID",
    "STATE_TRANSITION_SCHEMA_ID",
    "STATE_TRANSITION_SCHEMA_VERSION",
    "STATE_TRANSITION_FORMAT_VERSION",
    "CHANGE_KINDS",
    "CHANGE_OPERATIONS",
    "ACTION_ELIGIBILITY_STATES",
    "StateTransitionFormatError",
    "StateTransitionStateRef",
    "StateTransitionChange",
    "ActionEligibilityChange",
    "StateTransition",
    "load_state_transition",
    "validate_state_transition_bindings",
]
