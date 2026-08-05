"""Bounded identity-merge proposals derived from exact GT38 adjudication bytes.

The public Artifact selects one existing subject as the canonical subject, records
one bounded subject-reference rewrite, preserves the other subject as an alias,
and declares review, blocking, withdrawal, and reversal requirements. It never
approves or applies the proposal, mutates an object graph, updates World State,
releases production output, authorizes action, or executes action.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from geotask_core.v1.trajectory_identity_adjudication import (
    TRAJECTORY_IDENTITY_ADJUDICATION_ARTIFACT_ID,
    TrajectoryIdentityAdjudication,
    TrajectoryIdentityAdjudicationError,
    load_trajectory_identity_adjudication,
)


IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID = "geotask.identity-merge-proposal"
IDENTITY_MERGE_PROPOSAL_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-identity-merge-proposal-v0.1.schema.json"
)
IDENTITY_MERGE_PROPOSAL_SCHEMA_VERSION = "0.1"
IDENTITY_MERGE_PROPOSAL_FORMAT_VERSION = "0.1"

PROPOSAL_STATE = "ready_for_review"
PROPOSAL_REASON = "bound_same_object_adjudication_supports_bounded_merge_review"
REVIEW_ACTION = "review_identity_merge_proposal"
NEXT_ACTION = "request_identity_merge_approval"

BLOCKING_CONDITIONS = (
    "source_adjudication_changed",
    "contradictory_identity_evidence",
    "approval_missing",
    "affected_scope_changed",
    "reversal_plan_unavailable",
)
WITHDRAWAL_CONDITIONS = (
    "source_adjudication_withdrawn",
    "different_objects_confirmed",
    "canonical_subject_unavailable",
    "merge_subject_reassigned",
    "identity_policy_boundary_changed",
)


class IdentityMergeProposalError(ValueError):
    """Raised when an identity-merge proposal fails closed."""


def _fail(path: str, message: str) -> None:
    raise IdentityMergeProposalError(f"{path}: {message}")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _exact_fields(
    value: Mapping[str, object],
    path: str,
    *,
    required: set[str] | frozenset[str],
) -> None:
    actual = set(value)
    missing = sorted(set(required) - actual)
    unknown = sorted(actual - set(required))
    if missing:
        _fail(path, "missing required fields: " + ", ".join(missing))
    if unknown:
        _fail(path, "contains unknown fields: " + ", ".join(unknown))


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")
    return value


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        _fail(path, "must be boolean")
    return bool(value)


def _timestamp(value: object, path: str) -> str:
    text = _string(value, path)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise IdentityMergeProposalError(
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


def _string_tuple(
    value: object,
    path: str,
    *,
    minimum_items: int = 0,
) -> tuple[str, ...]:
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
    if len(result) < minimum_items:
        _fail(path, f"must contain at least {minimum_items} item(s)")
    return tuple(result)


def _hash_bytes(content: bytes) -> str:
    if not isinstance(content, bytes):
        _fail("adjudication_bytes", "must be bytes")
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


def _json_mapping_from_bytes(content: bytes, path: str) -> Mapping[str, object]:
    if not isinstance(content, bytes):
        _fail(path, "must be bytes")
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IdentityMergeProposalError(f"{path}: must contain UTF-8 JSON") from exc
    return _mapping(payload, path)


@dataclass(frozen=True)
class IdentityAdjudicationRef:
    artifact_id: str
    adjudication_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "adjudication_id": self.adjudication_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class SubjectRefRewriteProposal:
    trajectory_ref: str
    current_subject_ref: str
    proposed_subject_ref: str
    state: str = "proposed"

    def to_dict(self) -> dict[str, object]:
        return {
            "trajectory_ref": self.trajectory_ref,
            "current_subject_ref": self.current_subject_ref,
            "proposed_subject_ref": self.proposed_subject_ref,
            "state": self.state,
        }


@dataclass(frozen=True)
class RetainedAlias:
    alias_subject_ref: str
    canonical_subject_ref: str
    source_trajectory_refs: tuple[str, ...]
    state: str = "retain_as_alias"

    def to_dict(self) -> dict[str, object]:
        return {
            "alias_subject_ref": self.alias_subject_ref,
            "canonical_subject_ref": self.canonical_subject_ref,
            "source_trajectory_refs": list(self.source_trajectory_refs),
            "state": self.state,
        }


@dataclass(frozen=True)
class ReversalStep:
    trajectory_ref: str
    restore_subject_ref: str

    def to_dict(self) -> dict[str, object]:
        return {
            "trajectory_ref": self.trajectory_ref,
            "restore_subject_ref": self.restore_subject_ref,
        }


@dataclass(frozen=True)
class MergeReversalPlan:
    restore_subject_refs: tuple[ReversalStep, ...]
    preserve_alias_history: bool
    require_post_reversal_validation: bool
    reversal_executed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "restore_subject_refs": [item.to_dict() for item in self.restore_subject_refs],
            "preserve_alias_history": self.preserve_alias_history,
            "require_post_reversal_validation": self.require_post_reversal_validation,
            "reversal_executed": self.reversal_executed,
        }


@dataclass(frozen=True)
class IdentityMergeProposal:
    proposal_id: str
    created_at: str
    source_adjudication_ref: IdentityAdjudicationRef
    proposal_state: str
    proposal_reason: str
    proposal_rationale: str
    canonical_subject_ref: str
    merge_subject_ref: str
    object_class: str
    affected_trajectory_refs: tuple[str, ...]
    proposed_subject_ref_rewrites: tuple[SubjectRefRewriteProposal, ...]
    retained_aliases: tuple[RetainedAlias, ...]
    proposed_retired_subject_refs: tuple[str, ...]
    required_approvals: tuple[str, ...]
    blocking_conditions: tuple[str, ...]
    withdrawal_conditions: tuple[str, ...]
    reversal_plan: MergeReversalPlan
    review_action: str
    next_action: str
    source_binding_verified: bool
    scope_closed: bool
    aliases_preserved: bool
    new_identity_created: bool
    alias_deleted: bool
    proposal_approved: bool
    object_graph_mutated: bool
    identity_merge_performed: bool
    subject_refs_mutated: bool
    world_state_updated: bool
    production_output_released: bool
    action_authorized: bool
    action_executed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "identity_merge_proposal": {
                "proposal_version": IDENTITY_MERGE_PROPOSAL_FORMAT_VERSION,
                "proposal_id": self.proposal_id,
                "created_at": self.created_at,
                "source_adjudication_ref": self.source_adjudication_ref.to_dict(),
                "proposal_state": self.proposal_state,
                "proposal_reason": self.proposal_reason,
                "proposal_rationale": self.proposal_rationale,
                "canonical_subject_ref": self.canonical_subject_ref,
                "merge_subject_ref": self.merge_subject_ref,
                "object_class": self.object_class,
                "affected_trajectory_refs": list(self.affected_trajectory_refs),
                "proposed_subject_ref_rewrites": [
                    item.to_dict() for item in self.proposed_subject_ref_rewrites
                ],
                "retained_aliases": [item.to_dict() for item in self.retained_aliases],
                "proposed_retired_subject_refs": list(
                    self.proposed_retired_subject_refs
                ),
                "required_approvals": list(self.required_approvals),
                "blocking_conditions": list(self.blocking_conditions),
                "withdrawal_conditions": list(self.withdrawal_conditions),
                "reversal_plan": self.reversal_plan.to_dict(),
                "review_action": self.review_action,
                "next_action": self.next_action,
                "source_binding_verified": self.source_binding_verified,
                "scope_closed": self.scope_closed,
                "aliases_preserved": self.aliases_preserved,
                "new_identity_created": self.new_identity_created,
                "alias_deleted": self.alias_deleted,
                "proposal_approved": self.proposal_approved,
                "object_graph_mutated": self.object_graph_mutated,
                "identity_merge_performed": self.identity_merge_performed,
                "subject_refs_mutated": self.subject_refs_mutated,
                "world_state_updated": self.world_state_updated,
                "production_output_released": self.production_output_released,
                "action_authorized": self.action_authorized,
                "action_executed": self.action_executed,
            }
        }

    def semantic_fingerprint(self) -> str:
        return _semantic_fingerprint(self.to_dict())


def _validate_source_adjudication(
    adjudication: TrajectoryIdentityAdjudication,
) -> None:
    if adjudication.adjudication_state != "same_object_confirmed":
        _fail(
            "source adjudication.adjudication_state",
            "must be 'same_object_confirmed'",
        )
    if adjudication.candidate_alignment != "aligned":
        _fail("source adjudication.candidate_alignment", "must be 'aligned'")
    if adjudication.identity_merge_recommendation != "recommend_identity_merge_review":
        _fail(
            "source adjudication.identity_merge_recommendation",
            "must be 'recommend_identity_merge_review'",
        )
    if adjudication.next_action != "review_identity_merge":
        _fail("source adjudication.next_action", "must be 'review_identity_merge'")
    if not adjudication.candidate_binding_verified:
        _fail("source adjudication.candidate_binding_verified", "must be true")
    if not adjudication.verification_bindings_verified:
        _fail("source adjudication.verification_bindings_verified", "must be true")
    if not adjudication.independent_evidence_satisfied:
        _fail("source adjudication.independent_evidence_satisfied", "must be true")
    for field in (
        "external_identity_verified_by_core",
        "identity_merge_performed",
        "subject_refs_mutated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        if getattr(adjudication, field):
            _fail(f"source adjudication.{field}", "must be false")
    pair = adjudication.identity_pair
    if pair.first_object_class != pair.second_object_class:
        _fail("source adjudication.identity_pair", "object classes must match")
    if pair.first_subject_ref == pair.second_subject_ref:
        _fail("source adjudication.identity_pair", "subject refs must remain distinct")
    if pair.first_trajectory_ref == pair.second_trajectory_ref:
        _fail("source adjudication.identity_pair", "trajectory refs must be distinct")


def build_identity_merge_proposal(
    *,
    proposal_id: str,
    created_at: str,
    adjudication_bytes: bytes,
    canonical_subject_ref: str,
    proposal_rationale: str,
    required_approvals: Sequence[str],
) -> IdentityMergeProposal:
    """Build a bounded, review-only identity-merge proposal from exact GT38 bytes."""

    proposal_id = _string(proposal_id, "proposal_id")
    created_at = _timestamp(created_at, "created_at")
    canonical_subject_ref = _string(
        canonical_subject_ref, "canonical_subject_ref"
    )
    proposal_rationale = _string(proposal_rationale, "proposal_rationale")
    approval_tuple = _string_tuple(
        required_approvals, "required_approvals", minimum_items=1
    )

    payload = _json_mapping_from_bytes(adjudication_bytes, "adjudication_bytes")
    try:
        adjudication = load_trajectory_identity_adjudication(payload)
    except TrajectoryIdentityAdjudicationError as exc:
        raise IdentityMergeProposalError(str(exc)) from exc
    _validate_source_adjudication(adjudication)

    pair = adjudication.identity_pair
    subject_refs = (pair.first_subject_ref, pair.second_subject_ref)
    if canonical_subject_ref not in subject_refs:
        _fail(
            "canonical_subject_ref",
            "must select one existing subject_ref from the source adjudication",
        )
    merge_subject_ref = (
        pair.second_subject_ref
        if canonical_subject_ref == pair.first_subject_ref
        else pair.first_subject_ref
    )
    trajectory_subject_pairs = (
        (pair.first_trajectory_ref, pair.first_subject_ref),
        (pair.second_trajectory_ref, pair.second_subject_ref),
    )
    rewrites = tuple(
        SubjectRefRewriteProposal(
            trajectory_ref=trajectory_ref,
            current_subject_ref=subject_ref,
            proposed_subject_ref=canonical_subject_ref,
        )
        for trajectory_ref, subject_ref in trajectory_subject_pairs
        if subject_ref != canonical_subject_ref
    )
    if len(rewrites) != 1:
        _fail("proposed_subject_ref_rewrites", "must contain exactly one rewrite")
    aliases = (
        RetainedAlias(
            alias_subject_ref=merge_subject_ref,
            canonical_subject_ref=canonical_subject_ref,
            source_trajectory_refs=tuple(
                trajectory_ref
                for trajectory_ref, subject_ref in trajectory_subject_pairs
                if subject_ref == merge_subject_ref
            ),
        ),
    )
    reversal_plan = MergeReversalPlan(
        restore_subject_refs=tuple(
            ReversalStep(
                trajectory_ref=item.trajectory_ref,
                restore_subject_ref=item.current_subject_ref,
            )
            for item in rewrites
        ),
        preserve_alias_history=True,
        require_post_reversal_validation=True,
        reversal_executed=False,
    )

    return IdentityMergeProposal(
        proposal_id=proposal_id,
        created_at=created_at,
        source_adjudication_ref=IdentityAdjudicationRef(
            artifact_id=TRAJECTORY_IDENTITY_ADJUDICATION_ARTIFACT_ID,
            adjudication_id=adjudication.adjudication_id,
            content_sha256=_hash_bytes(adjudication_bytes),
        ),
        proposal_state=PROPOSAL_STATE,
        proposal_reason=PROPOSAL_REASON,
        proposal_rationale=proposal_rationale,
        canonical_subject_ref=canonical_subject_ref,
        merge_subject_ref=merge_subject_ref,
        object_class=pair.first_object_class,
        affected_trajectory_refs=(
            pair.first_trajectory_ref,
            pair.second_trajectory_ref,
        ),
        proposed_subject_ref_rewrites=rewrites,
        retained_aliases=aliases,
        proposed_retired_subject_refs=(merge_subject_ref,),
        required_approvals=approval_tuple,
        blocking_conditions=BLOCKING_CONDITIONS,
        withdrawal_conditions=WITHDRAWAL_CONDITIONS,
        reversal_plan=reversal_plan,
        review_action=REVIEW_ACTION,
        next_action=NEXT_ACTION,
        source_binding_verified=True,
        scope_closed=True,
        aliases_preserved=True,
        new_identity_created=False,
        alias_deleted=False,
        proposal_approved=False,
        object_graph_mutated=False,
        identity_merge_performed=False,
        subject_refs_mutated=False,
        world_state_updated=False,
        production_output_released=False,
        action_authorized=False,
        action_executed=False,
    )


def _load_source_ref(value: object, path: str) -> IdentityAdjudicationRef:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={"artifact_id", "adjudication_id", "content_sha256"},
    )
    artifact_id = _string(body["artifact_id"], f"{path}.artifact_id")
    if artifact_id != TRAJECTORY_IDENTITY_ADJUDICATION_ARTIFACT_ID:
        _fail(
            f"{path}.artifact_id",
            f"must be {TRAJECTORY_IDENTITY_ADJUDICATION_ARTIFACT_ID!r}",
        )
    return IdentityAdjudicationRef(
        artifact_id=artifact_id,
        adjudication_id=_string(body["adjudication_id"], f"{path}.adjudication_id"),
        content_sha256=_sha256(body["content_sha256"], f"{path}.content_sha256"),
    )


def _load_rewrites(value: object, path: str) -> tuple[SubjectRefRewriteProposal, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    result: list[SubjectRefRewriteProposal] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        body = _mapping(item, item_path)
        _exact_fields(
            body,
            item_path,
            required={
                "trajectory_ref",
                "current_subject_ref",
                "proposed_subject_ref",
                "state",
            },
        )
        state = _string(body["state"], f"{item_path}.state")
        if state != "proposed":
            _fail(f"{item_path}.state", "must be 'proposed'")
        result.append(
            SubjectRefRewriteProposal(
                trajectory_ref=_string(
                    body["trajectory_ref"], f"{item_path}.trajectory_ref"
                ),
                current_subject_ref=_string(
                    body["current_subject_ref"], f"{item_path}.current_subject_ref"
                ),
                proposed_subject_ref=_string(
                    body["proposed_subject_ref"], f"{item_path}.proposed_subject_ref"
                ),
                state=state,
            )
        )
    if len(result) != 1:
        _fail(path, "must contain exactly one rewrite")
    return tuple(result)


def _load_aliases(value: object, path: str) -> tuple[RetainedAlias, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    result: list[RetainedAlias] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        body = _mapping(item, item_path)
        _exact_fields(
            body,
            item_path,
            required={
                "alias_subject_ref",
                "canonical_subject_ref",
                "source_trajectory_refs",
                "state",
            },
        )
        state = _string(body["state"], f"{item_path}.state")
        if state != "retain_as_alias":
            _fail(f"{item_path}.state", "must be 'retain_as_alias'")
        result.append(
            RetainedAlias(
                alias_subject_ref=_string(
                    body["alias_subject_ref"], f"{item_path}.alias_subject_ref"
                ),
                canonical_subject_ref=_string(
                    body["canonical_subject_ref"],
                    f"{item_path}.canonical_subject_ref",
                ),
                source_trajectory_refs=_string_tuple(
                    body["source_trajectory_refs"],
                    f"{item_path}.source_trajectory_refs",
                    minimum_items=1,
                ),
                state=state,
            )
        )
    if len(result) != 1:
        _fail(path, "must contain exactly one retained alias")
    return tuple(result)


def _load_reversal_plan(value: object, path: str) -> MergeReversalPlan:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path,
        required={
            "restore_subject_refs",
            "preserve_alias_history",
            "require_post_reversal_validation",
            "reversal_executed",
        },
    )
    raw_steps = body["restore_subject_refs"]
    if not isinstance(raw_steps, Sequence) or isinstance(
        raw_steps, (str, bytes, bytearray)
    ):
        _fail(f"{path}.restore_subject_refs", "must be an array")
    steps: list[ReversalStep] = []
    for index, item in enumerate(raw_steps):
        item_path = f"{path}.restore_subject_refs[{index}]"
        step = _mapping(item, item_path)
        _exact_fields(
            step,
            item_path,
            required={"trajectory_ref", "restore_subject_ref"},
        )
        steps.append(
            ReversalStep(
                trajectory_ref=_string(
                    step["trajectory_ref"], f"{item_path}.trajectory_ref"
                ),
                restore_subject_ref=_string(
                    step["restore_subject_ref"], f"{item_path}.restore_subject_ref"
                ),
            )
        )
    if len(steps) != 1:
        _fail(f"{path}.restore_subject_refs", "must contain exactly one step")
    result = MergeReversalPlan(
        restore_subject_refs=tuple(steps),
        preserve_alias_history=_boolean(
            body["preserve_alias_history"], f"{path}.preserve_alias_history"
        ),
        require_post_reversal_validation=_boolean(
            body["require_post_reversal_validation"],
            f"{path}.require_post_reversal_validation",
        ),
        reversal_executed=_boolean(
            body["reversal_executed"], f"{path}.reversal_executed"
        ),
    )
    if not result.preserve_alias_history:
        _fail(f"{path}.preserve_alias_history", "must be true")
    if not result.require_post_reversal_validation:
        _fail(f"{path}.require_post_reversal_validation", "must be true")
    if result.reversal_executed:
        _fail(f"{path}.reversal_executed", "must be false")
    return result


def load_identity_merge_proposal(
    payload: Mapping[str, object],
) -> IdentityMergeProposal:
    """Strictly load one serialized identity-merge proposal Artifact."""

    root = _mapping(payload, "Identity Merge Proposal")
    _exact_fields(root, "artifact root", required={"identity_merge_proposal"})
    body = _mapping(root["identity_merge_proposal"], "identity_merge_proposal")
    required = {
        "proposal_version",
        "proposal_id",
        "created_at",
        "source_adjudication_ref",
        "proposal_state",
        "proposal_reason",
        "proposal_rationale",
        "canonical_subject_ref",
        "merge_subject_ref",
        "object_class",
        "affected_trajectory_refs",
        "proposed_subject_ref_rewrites",
        "retained_aliases",
        "proposed_retired_subject_refs",
        "required_approvals",
        "blocking_conditions",
        "withdrawal_conditions",
        "reversal_plan",
        "review_action",
        "next_action",
        "source_binding_verified",
        "scope_closed",
        "aliases_preserved",
        "new_identity_created",
        "alias_deleted",
        "proposal_approved",
        "object_graph_mutated",
        "identity_merge_performed",
        "subject_refs_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    }
    _exact_fields(body, "identity_merge_proposal", required=required)
    if body["proposal_version"] != IDENTITY_MERGE_PROPOSAL_FORMAT_VERSION:
        _fail(
            "identity_merge_proposal.proposal_version",
            f"must be {IDENTITY_MERGE_PROPOSAL_FORMAT_VERSION!r}",
        )
    result = IdentityMergeProposal(
        proposal_id=_string(body["proposal_id"], "identity_merge_proposal.proposal_id"),
        created_at=_timestamp(body["created_at"], "identity_merge_proposal.created_at"),
        source_adjudication_ref=_load_source_ref(
            body["source_adjudication_ref"],
            "identity_merge_proposal.source_adjudication_ref",
        ),
        proposal_state=_string(
            body["proposal_state"], "identity_merge_proposal.proposal_state"
        ),
        proposal_reason=_string(
            body["proposal_reason"], "identity_merge_proposal.proposal_reason"
        ),
        proposal_rationale=_string(
            body["proposal_rationale"], "identity_merge_proposal.proposal_rationale"
        ),
        canonical_subject_ref=_string(
            body["canonical_subject_ref"],
            "identity_merge_proposal.canonical_subject_ref",
        ),
        merge_subject_ref=_string(
            body["merge_subject_ref"], "identity_merge_proposal.merge_subject_ref"
        ),
        object_class=_string(
            body["object_class"], "identity_merge_proposal.object_class"
        ),
        affected_trajectory_refs=_string_tuple(
            body["affected_trajectory_refs"],
            "identity_merge_proposal.affected_trajectory_refs",
            minimum_items=2,
        ),
        proposed_subject_ref_rewrites=_load_rewrites(
            body["proposed_subject_ref_rewrites"],
            "identity_merge_proposal.proposed_subject_ref_rewrites",
        ),
        retained_aliases=_load_aliases(
            body["retained_aliases"], "identity_merge_proposal.retained_aliases"
        ),
        proposed_retired_subject_refs=_string_tuple(
            body["proposed_retired_subject_refs"],
            "identity_merge_proposal.proposed_retired_subject_refs",
            minimum_items=1,
        ),
        required_approvals=_string_tuple(
            body["required_approvals"],
            "identity_merge_proposal.required_approvals",
            minimum_items=1,
        ),
        blocking_conditions=_string_tuple(
            body["blocking_conditions"],
            "identity_merge_proposal.blocking_conditions",
            minimum_items=1,
        ),
        withdrawal_conditions=_string_tuple(
            body["withdrawal_conditions"],
            "identity_merge_proposal.withdrawal_conditions",
            minimum_items=1,
        ),
        reversal_plan=_load_reversal_plan(
            body["reversal_plan"], "identity_merge_proposal.reversal_plan"
        ),
        review_action=_string(
            body["review_action"], "identity_merge_proposal.review_action"
        ),
        next_action=_string(body["next_action"], "identity_merge_proposal.next_action"),
        source_binding_verified=_boolean(
            body["source_binding_verified"],
            "identity_merge_proposal.source_binding_verified",
        ),
        scope_closed=_boolean(
            body["scope_closed"], "identity_merge_proposal.scope_closed"
        ),
        aliases_preserved=_boolean(
            body["aliases_preserved"], "identity_merge_proposal.aliases_preserved"
        ),
        new_identity_created=_boolean(
            body["new_identity_created"],
            "identity_merge_proposal.new_identity_created",
        ),
        alias_deleted=_boolean(
            body["alias_deleted"], "identity_merge_proposal.alias_deleted"
        ),
        proposal_approved=_boolean(
            body["proposal_approved"], "identity_merge_proposal.proposal_approved"
        ),
        object_graph_mutated=_boolean(
            body["object_graph_mutated"],
            "identity_merge_proposal.object_graph_mutated",
        ),
        identity_merge_performed=_boolean(
            body["identity_merge_performed"],
            "identity_merge_proposal.identity_merge_performed",
        ),
        subject_refs_mutated=_boolean(
            body["subject_refs_mutated"],
            "identity_merge_proposal.subject_refs_mutated",
        ),
        world_state_updated=_boolean(
            body["world_state_updated"],
            "identity_merge_proposal.world_state_updated",
        ),
        production_output_released=_boolean(
            body["production_output_released"],
            "identity_merge_proposal.production_output_released",
        ),
        action_authorized=_boolean(
            body["action_authorized"],
            "identity_merge_proposal.action_authorized",
        ),
        action_executed=_boolean(
            body["action_executed"], "identity_merge_proposal.action_executed"
        ),
    )

    if result.proposal_state != PROPOSAL_STATE:
        _fail("identity_merge_proposal.proposal_state", f"must be {PROPOSAL_STATE!r}")
    if result.proposal_reason != PROPOSAL_REASON:
        _fail("identity_merge_proposal.proposal_reason", f"must be {PROPOSAL_REASON!r}")
    if result.review_action != REVIEW_ACTION:
        _fail("identity_merge_proposal.review_action", f"must be {REVIEW_ACTION!r}")
    if result.next_action != NEXT_ACTION:
        _fail("identity_merge_proposal.next_action", f"must be {NEXT_ACTION!r}")
    if result.canonical_subject_ref == result.merge_subject_ref:
        _fail("identity_merge_proposal", "canonical and merge subject refs must differ")
    if len(result.affected_trajectory_refs) != 2:
        _fail("identity_merge_proposal.affected_trajectory_refs", "must contain exactly two refs")
    rewrite = result.proposed_subject_ref_rewrites[0]
    if rewrite.trajectory_ref not in result.affected_trajectory_refs:
        _fail("identity_merge_proposal.proposed_subject_ref_rewrites", "trajectory must be in affected scope")
    if rewrite.current_subject_ref != result.merge_subject_ref:
        _fail("identity_merge_proposal.proposed_subject_ref_rewrites", "current subject must equal merge_subject_ref")
    if rewrite.proposed_subject_ref != result.canonical_subject_ref:
        _fail("identity_merge_proposal.proposed_subject_ref_rewrites", "proposed subject must equal canonical_subject_ref")
    alias = result.retained_aliases[0]
    if alias.alias_subject_ref != result.merge_subject_ref:
        _fail("identity_merge_proposal.retained_aliases", "alias must equal merge_subject_ref")
    if alias.canonical_subject_ref != result.canonical_subject_ref:
        _fail("identity_merge_proposal.retained_aliases", "canonical ref mismatch")
    if alias.source_trajectory_refs != (rewrite.trajectory_ref,):
        _fail("identity_merge_proposal.retained_aliases", "must bind the rewritten trajectory only")
    if result.proposed_retired_subject_refs != (result.merge_subject_ref,):
        _fail("identity_merge_proposal.proposed_retired_subject_refs", "must contain only merge_subject_ref")
    if result.blocking_conditions != BLOCKING_CONDITIONS:
        _fail("identity_merge_proposal.blocking_conditions", "must match the required closed set")
    if result.withdrawal_conditions != WITHDRAWAL_CONDITIONS:
        _fail("identity_merge_proposal.withdrawal_conditions", "must match the required closed set")
    reversal = result.reversal_plan.restore_subject_refs[0]
    if reversal.trajectory_ref != rewrite.trajectory_ref:
        _fail("identity_merge_proposal.reversal_plan", "trajectory must mirror the proposed rewrite")
    if reversal.restore_subject_ref != rewrite.current_subject_ref:
        _fail("identity_merge_proposal.reversal_plan", "restore subject must match the original subject")
    for field in ("source_binding_verified", "scope_closed", "aliases_preserved"):
        if not getattr(result, field):
            _fail(f"identity_merge_proposal.{field}", "must be true")
    for field in (
        "new_identity_created",
        "alias_deleted",
        "proposal_approved",
        "object_graph_mutated",
        "identity_merge_performed",
        "subject_refs_mutated",
        "world_state_updated",
        "production_output_released",
        "action_authorized",
        "action_executed",
    ):
        if getattr(result, field):
            _fail(f"identity_merge_proposal.{field}", "must be false")
    return result


def validate_identity_merge_proposal_bindings(
    proposal: IdentityMergeProposal,
    *,
    adjudication_bytes: bytes,
) -> None:
    """Rebuild from exact GT38 bytes and require semantic equality."""

    rebuilt = build_identity_merge_proposal(
        proposal_id=proposal.proposal_id,
        created_at=proposal.created_at,
        adjudication_bytes=adjudication_bytes,
        canonical_subject_ref=proposal.canonical_subject_ref,
        proposal_rationale=proposal.proposal_rationale,
        required_approvals=proposal.required_approvals,
    )
    if rebuilt.to_dict() != proposal.to_dict():
        _fail(
            "identity_merge_proposal",
            "does not match the proposal rebuilt from exact bound adjudication bytes",
        )


__all__ = [
    "IDENTITY_MERGE_PROPOSAL_ARTIFACT_ID",
    "IDENTITY_MERGE_PROPOSAL_SCHEMA_ID",
    "IDENTITY_MERGE_PROPOSAL_SCHEMA_VERSION",
    "IDENTITY_MERGE_PROPOSAL_FORMAT_VERSION",
    "BLOCKING_CONDITIONS",
    "WITHDRAWAL_CONDITIONS",
    "IdentityMergeProposalError",
    "IdentityAdjudicationRef",
    "SubjectRefRewriteProposal",
    "RetainedAlias",
    "ReversalStep",
    "MergeReversalPlan",
    "IdentityMergeProposal",
    "build_identity_merge_proposal",
    "load_identity_merge_proposal",
    "validate_identity_merge_proposal_bindings",
]
