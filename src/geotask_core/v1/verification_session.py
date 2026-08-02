"""Public Verification Session v0.1 audit contract.

A Verification Session binds one World State snapshot to exact serialized task,
execution-result, control-evaluation, State Transition, and discrepancy artifacts.
It records action eligibility and recheck triggers as an immutable audit snapshot.
Loading validates structure, time order, reference closure, and deterministic
fingerprinting. Binding validation checks the World State identity/fingerprint and
raw SHA-256 digests of supplied artifact bytes. It does not validate linked
artifact semantics, execute tasks, evaluate controls, run rechecks, verify external
truth, materialize state, or authorize action.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Mapping, Sequence

from geotask_core.v1.state_transition import ACTION_ELIGIBILITY_STATES
from geotask_core.v1.world_state import WorldState


VERIFICATION_SESSION_ARTIFACT_ID = "geotask.verification-session"
VERIFICATION_SESSION_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/geotask-verification-session-v0.1.schema.json"
)
VERIFICATION_SESSION_SCHEMA_VERSION = "0.1"
VERIFICATION_SESSION_FORMAT_VERSION = "0.1"

VERIFICATION_SESSION_STATES = frozenset(
    {"verified", "contradicted", "blocked", "need_review", "unknown", "error"}
)
RECHECK_TRIGGER_STATES = frozenset({"armed", "satisfied", "dismissed", "unknown"})


class VerificationSessionFormatError(ValueError):
    """Raised when a Verification Session payload violates the v0.1 contract."""


def _fail(path: str, message: str) -> None:
    raise VerificationSessionFormatError(f"{path}: {message}")


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
        raise VerificationSessionFormatError(
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
class VerificationWorldStateRef:
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
class VerificationArtifactRef:
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
class VerificationActionEligibility:
    output_ref: str
    state: str
    reason: str
    basis_refs: tuple[str, ...]
    observation_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "output_ref": self.output_ref,
            "state": self.state,
            "reason": self.reason,
            "basis_refs": sorted(self.basis_refs),
            "observation_refs": sorted(self.observation_refs),
        }


@dataclass(frozen=True)
class VerificationRecheckTrigger:
    id: str
    condition: str
    state: str
    reason: str
    affected_output_refs: tuple[str, ...]
    basis_refs: tuple[str, ...]
    observation_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "condition": self.condition,
            "state": self.state,
            "reason": self.reason,
            "affected_output_refs": sorted(self.affected_output_refs),
            "basis_refs": sorted(self.basis_refs),
            "observation_refs": sorted(self.observation_refs),
        }


@dataclass(frozen=True)
class VerificationSession:
    session_id: str
    recorded_at: str
    state: str
    reason: str
    world_state: VerificationWorldStateRef
    observation_refs: tuple[str, ...]
    task_refs: tuple[VerificationArtifactRef, ...]
    execution_result_refs: tuple[VerificationArtifactRef, ...]
    control_evaluation_refs: tuple[VerificationArtifactRef, ...]
    state_transition_refs: tuple[VerificationArtifactRef, ...]
    discrepancy_refs: tuple[VerificationArtifactRef, ...]
    action_eligibility: tuple[VerificationActionEligibility, ...]
    recheck_triggers: tuple[VerificationRecheckTrigger, ...]

    def all_artifact_refs(self) -> tuple[VerificationArtifactRef, ...]:
        return (
            self.task_refs
            + self.execution_result_refs
            + self.control_evaluation_refs
            + self.state_transition_refs
            + self.discrepancy_refs
        )

    def to_dict(self) -> dict[str, object]:
        def refs(items: tuple[VerificationArtifactRef, ...]) -> list[dict[str, object]]:
            return [item.to_dict() for item in sorted(items, key=lambda item: item.ref_id)]

        return {
            "verification_session": {
                "schema_id": VERIFICATION_SESSION_SCHEMA_ID,
                "schema_version": VERIFICATION_SESSION_SCHEMA_VERSION,
                "session_id": self.session_id,
                "recorded_at": self.recorded_at,
                "state": self.state,
                "reason": self.reason,
                "world_state": self.world_state.to_dict(),
                "observation_refs": sorted(self.observation_refs),
                "task_refs": refs(self.task_refs),
                "execution_result_refs": refs(self.execution_result_refs),
                "control_evaluation_refs": refs(self.control_evaluation_refs),
                "state_transition_refs": refs(self.state_transition_refs),
                "discrepancy_refs": refs(self.discrepancy_refs),
                "action_eligibility": [
                    item.to_dict()
                    for item in sorted(self.action_eligibility, key=lambda item: item.output_ref)
                ],
                "recheck_triggers": [
                    item.to_dict()
                    for item in sorted(self.recheck_triggers, key=lambda item: item.id)
                ],
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


def _load_world_state_ref(
    value: object, path: str
) -> tuple[VerificationWorldStateRef, datetime]:
    ref = _mapping(value, path)
    _exact_fields(
        ref,
        path,
        required={"world_state_id", "revision", "as_of", "semantic_fingerprint"},
    )
    as_of_text, as_of = _timestamp(ref["as_of"], f"{path}.as_of")
    return (
        VerificationWorldStateRef(
            world_state_id=_string(ref["world_state_id"], f"{path}.world_state_id"),
            revision=_positive_integer(ref["revision"], f"{path}.revision"),
            as_of=as_of_text,
            semantic_fingerprint=_sha256(
                ref["semantic_fingerprint"], f"{path}.semantic_fingerprint"
            ),
        ),
        as_of,
    )


def _load_artifact_refs(
    value: object,
    path: str,
    *,
    expected_artifact_id: str | None,
    expected_schema_version: str | None,
    non_empty: bool,
    global_ref_ids: set[str],
) -> tuple[VerificationArtifactRef, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if non_empty and not value:
        _fail(path, "must contain at least one item")
    items: list[VerificationArtifactRef] = []
    local_instances: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        ref = _mapping(raw, item_path)
        _exact_fields(
            ref,
            item_path,
            required={
                "ref_id",
                "artifact_id",
                "schema_version",
                "instance_id",
                "content_sha256",
            },
        )
        ref_id = _string(ref["ref_id"], f"{item_path}.ref_id")
        artifact_id = _string(ref["artifact_id"], f"{item_path}.artifact_id")
        schema_version = _string(
            ref["schema_version"], f"{item_path}.schema_version"
        )
        instance_id = _string(ref["instance_id"], f"{item_path}.instance_id")
        if expected_artifact_id is not None and artifact_id != expected_artifact_id:
            _fail(
                f"{item_path}.artifact_id",
                f"must equal {expected_artifact_id!r}",
            )
        if (
            expected_schema_version is not None
            and schema_version != expected_schema_version
        ):
            _fail(
                f"{item_path}.schema_version",
                f"must equal {expected_schema_version!r}",
            )
        if ref_id in global_ref_ids:
            _fail(f"{item_path}.ref_id", f"duplicates ref_id {ref_id!r}")
        if instance_id in local_instances:
            _fail(f"{item_path}.instance_id", f"duplicates instance_id {instance_id!r}")
        global_ref_ids.add(ref_id)
        local_instances.add(instance_id)
        items.append(
            VerificationArtifactRef(
                ref_id=ref_id,
                artifact_id=artifact_id,
                schema_version=schema_version,
                instance_id=instance_id,
                content_sha256=_sha256(
                    ref["content_sha256"], f"{item_path}.content_sha256"
                ),
            )
        )
    return tuple(sorted(items, key=lambda item: item.ref_id))


def _load_action_eligibility(
    value: object,
    *,
    declared_artifact_refs: frozenset[str],
    declared_observation_refs: frozenset[str],
) -> tuple[VerificationActionEligibility, ...]:
    path = "verification_session.action_eligibility"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if not value:
        _fail(path, "must contain at least one item")
    items: list[VerificationActionEligibility] = []
    output_refs: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={"output_ref", "state", "reason", "basis_refs", "observation_refs"},
        )
        output_ref = _string(item["output_ref"], f"{item_path}.output_ref")
        if output_ref in output_refs:
            _fail(f"{item_path}.output_ref", f"duplicates output_ref {output_ref!r}")
        output_refs.add(output_ref)
        basis_refs = _string_list(
            item["basis_refs"], f"{item_path}.basis_refs", non_empty=True
        )
        observation_refs = _string_list(
            item["observation_refs"],
            f"{item_path}.observation_refs",
            non_empty=True,
        )
        _closed_refs(
            basis_refs,
            f"{item_path}.basis_refs",
            declared_artifact_refs,
            "verification_session artifact reference lists",
        )
        _closed_refs(
            observation_refs,
            f"{item_path}.observation_refs",
            declared_observation_refs,
            "verification_session.observation_refs",
        )
        items.append(
            VerificationActionEligibility(
                output_ref=output_ref,
                state=_enum(
                    item["state"], f"{item_path}.state", ACTION_ELIGIBILITY_STATES
                ),
                reason=_string(item["reason"], f"{item_path}.reason"),
                basis_refs=tuple(sorted(basis_refs)),
                observation_refs=tuple(sorted(observation_refs)),
            )
        )
    return tuple(sorted(items, key=lambda item: item.output_ref))


def _load_recheck_triggers(
    value: object,
    *,
    declared_artifact_refs: frozenset[str],
    declared_observation_refs: frozenset[str],
    declared_output_refs: frozenset[str],
) -> tuple[VerificationRecheckTrigger, ...]:
    path = "verification_session.recheck_triggers"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    items: list[VerificationRecheckTrigger] = []
    ids: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={
                "id",
                "condition",
                "state",
                "reason",
                "affected_output_refs",
                "basis_refs",
                "observation_refs",
            },
        )
        trigger_id = _string(item["id"], f"{item_path}.id")
        if trigger_id in ids:
            _fail(f"{item_path}.id", f"duplicates id {trigger_id!r}")
        ids.add(trigger_id)
        affected = _string_list(
            item["affected_output_refs"],
            f"{item_path}.affected_output_refs",
            non_empty=True,
        )
        basis_refs = _string_list(
            item["basis_refs"], f"{item_path}.basis_refs", non_empty=True
        )
        observation_refs = _string_list(
            item["observation_refs"],
            f"{item_path}.observation_refs",
            non_empty=True,
        )
        _closed_refs(
            affected,
            f"{item_path}.affected_output_refs",
            declared_output_refs,
            "verification_session.action_eligibility output_ref values",
        )
        _closed_refs(
            basis_refs,
            f"{item_path}.basis_refs",
            declared_artifact_refs,
            "verification_session artifact reference lists",
        )
        _closed_refs(
            observation_refs,
            f"{item_path}.observation_refs",
            declared_observation_refs,
            "verification_session.observation_refs",
        )
        items.append(
            VerificationRecheckTrigger(
                id=trigger_id,
                condition=_string(item["condition"], f"{item_path}.condition"),
                state=_enum(
                    item["state"], f"{item_path}.state", RECHECK_TRIGGER_STATES
                ),
                reason=_string(item["reason"], f"{item_path}.reason"),
                affected_output_refs=tuple(sorted(affected)),
                basis_refs=tuple(sorted(basis_refs)),
                observation_refs=tuple(sorted(observation_refs)),
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def load_verification_session(payload: Mapping[str, object]) -> VerificationSession:
    """Load and strictly validate one Verification Session v0.1 payload."""

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"verification_session"})
    body = _mapping(root["verification_session"], "verification_session")
    _exact_fields(
        body,
        "verification_session",
        required={
            "schema_id",
            "schema_version",
            "session_id",
            "recorded_at",
            "state",
            "reason",
            "world_state",
            "observation_refs",
            "task_refs",
            "execution_result_refs",
            "control_evaluation_refs",
            "state_transition_refs",
            "discrepancy_refs",
            "action_eligibility",
            "recheck_triggers",
        },
    )
    if body["schema_id"] != VERIFICATION_SESSION_SCHEMA_ID:
        _fail(
            "verification_session.schema_id",
            f"must equal {VERIFICATION_SESSION_SCHEMA_ID!r}",
        )
    if body["schema_version"] != VERIFICATION_SESSION_SCHEMA_VERSION:
        _fail(
            "verification_session.schema_version",
            f"must equal {VERIFICATION_SESSION_SCHEMA_VERSION!r}",
        )

    recorded_at_text, recorded_at = _timestamp(
        body["recorded_at"], "verification_session.recorded_at"
    )
    world_state, world_as_of = _load_world_state_ref(
        body["world_state"], "verification_session.world_state"
    )
    if recorded_at < world_as_of:
        _fail(
            "verification_session.recorded_at",
            "must not be earlier than world_state.as_of",
        )

    observation_refs = _string_list(
        body["observation_refs"],
        "verification_session.observation_refs",
        non_empty=True,
    )
    global_ref_ids: set[str] = set()
    task_refs = _load_artifact_refs(
        body["task_refs"],
        "verification_session.task_refs",
        expected_artifact_id="geotask.document",
        expected_schema_version="1.0",
        non_empty=True,
        global_ref_ids=global_ref_ids,
    )
    execution_result_refs = _load_artifact_refs(
        body["execution_result_refs"],
        "verification_session.execution_result_refs",
        expected_artifact_id="geotask.execution-result",
        expected_schema_version="1.0",
        non_empty=True,
        global_ref_ids=global_ref_ids,
    )
    control_evaluation_refs = _load_artifact_refs(
        body["control_evaluation_refs"],
        "verification_session.control_evaluation_refs",
        expected_artifact_id="geotask.control-evaluation",
        expected_schema_version="1.0",
        non_empty=False,
        global_ref_ids=global_ref_ids,
    )
    state_transition_refs = _load_artifact_refs(
        body["state_transition_refs"],
        "verification_session.state_transition_refs",
        expected_artifact_id="geotask.state-transition",
        expected_schema_version="0.1",
        non_empty=False,
        global_ref_ids=global_ref_ids,
    )
    discrepancy_refs = _load_artifact_refs(
        body["discrepancy_refs"],
        "verification_session.discrepancy_refs",
        expected_artifact_id="geotask.discrepancy-report",
        expected_schema_version="0.1",
        non_empty=False,
        global_ref_ids=global_ref_ids,
    )

    declared_artifact_refs = frozenset(global_ref_ids)
    declared_observation_refs = frozenset(observation_refs)
    action_eligibility = _load_action_eligibility(
        body["action_eligibility"],
        declared_artifact_refs=declared_artifact_refs,
        declared_observation_refs=declared_observation_refs,
    )
    declared_output_refs = frozenset(item.output_ref for item in action_eligibility)
    recheck_triggers = _load_recheck_triggers(
        body["recheck_triggers"],
        declared_artifact_refs=declared_artifact_refs,
        declared_observation_refs=declared_observation_refs,
        declared_output_refs=declared_output_refs,
    )

    state = _enum(body["state"], "verification_session.state", VERIFICATION_SESSION_STATES)
    if state == "blocked" and not any(
        item.state == "blocked" for item in action_eligibility
    ):
        _fail(
            "verification_session.state",
            "blocked requires at least one blocked action eligibility",
        )
    if state == "unknown" and not (
        any(item.state == "unknown" for item in action_eligibility)
        or any(item.state == "unknown" for item in recheck_triggers)
    ):
        _fail(
            "verification_session.state",
            "unknown requires an unknown action eligibility or recheck trigger",
        )

    eligibility_by_output = {item.output_ref: item.state for item in action_eligibility}
    for index, trigger in enumerate(recheck_triggers):
        if trigger.state == "satisfied" and not any(
            eligibility_by_output[output_ref] in {"blocked", "unknown"}
            for output_ref in trigger.affected_output_refs
        ):
            _fail(
                f"verification_session.recheck_triggers[{index}].state",
                "satisfied must affect at least one blocked or unknown output",
            )

    return VerificationSession(
        session_id=_string(body["session_id"], "verification_session.session_id"),
        recorded_at=recorded_at_text,
        state=state,
        reason=_string(body["reason"], "verification_session.reason"),
        world_state=world_state,
        observation_refs=tuple(sorted(observation_refs)),
        task_refs=task_refs,
        execution_result_refs=execution_result_refs,
        control_evaluation_refs=control_evaluation_refs,
        state_transition_refs=state_transition_refs,
        discrepancy_refs=discrepancy_refs,
        action_eligibility=action_eligibility,
        recheck_triggers=recheck_triggers,
    )


def validate_verification_session_bindings(
    session: VerificationSession,
    world_state: WorldState,
    artifact_contents: Mapping[str, bytes],
) -> None:
    """Validate snapshot identity and exact byte bindings for all session artifacts.

    This does not parse or semantically validate linked artifacts. Callers must run
    each registered artifact through its own loader or unified validator separately.
    """

    checks = (
        (
            "verification_session.world_state.world_state_id",
            session.world_state.world_state_id,
            world_state.world_state_id,
        ),
        (
            "verification_session.world_state.revision",
            session.world_state.revision,
            world_state.revision,
        ),
        (
            "verification_session.world_state.as_of",
            session.world_state.as_of,
            world_state.as_of,
        ),
        (
            "verification_session.world_state.semantic_fingerprint",
            session.world_state.semantic_fingerprint,
            world_state.semantic_fingerprint(),
        ),
    )
    for path, declared, actual in checks:
        if declared != actual:
            _fail(path, f"does not match bound World State: expected {actual!r}")

    missing_observations = sorted(
        set(session.observation_refs) - set(world_state.observation_refs)
    )
    if missing_observations:
        _fail(
            "verification_session.observation_refs",
            "not declared by bound World State: " + ", ".join(missing_observations),
        )

    expected_refs = {item.ref_id: item for item in session.all_artifact_refs()}
    supplied_refs = set(artifact_contents)
    missing = sorted(set(expected_refs) - supplied_refs)
    unknown = sorted(supplied_refs - set(expected_refs))
    if missing:
        _fail("artifact_contents", "missing ref_id values: " + ", ".join(missing))
    if unknown:
        _fail("artifact_contents", "contains unknown ref_id values: " + ", ".join(unknown))

    for ref_id, ref in expected_refs.items():
        content = artifact_contents[ref_id]
        if not isinstance(content, bytes):
            _fail(f"artifact_contents[{ref_id!r}]", "must be bytes")
        actual = hashlib.sha256(content).hexdigest()
        if actual != ref.content_sha256:
            _fail(
                f"artifact_contents[{ref_id!r}]",
                f"SHA-256 mismatch: expected {ref.content_sha256!r}, got {actual!r}",
            )


__all__ = [
    "VERIFICATION_SESSION_ARTIFACT_ID",
    "VERIFICATION_SESSION_SCHEMA_ID",
    "VERIFICATION_SESSION_SCHEMA_VERSION",
    "VERIFICATION_SESSION_FORMAT_VERSION",
    "VERIFICATION_SESSION_STATES",
    "RECHECK_TRIGGER_STATES",
    "VerificationSessionFormatError",
    "VerificationWorldStateRef",
    "VerificationArtifactRef",
    "VerificationActionEligibility",
    "VerificationRecheckTrigger",
    "VerificationSession",
    "load_verification_session",
    "validate_verification_session_bindings",
]
