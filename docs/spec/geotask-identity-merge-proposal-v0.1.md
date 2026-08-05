# GeoTask Identity Merge Proposal v0.1

Status: implemented public Artifact  
Artifact ID: `geotask.identity-merge-proposal`  
Schema: [`schemas/geotask-identity-merge-proposal-v0.1.schema.json`](../../schemas/geotask-identity-merge-proposal-v0.1.schema.json)  
Reference case: GT39

## 1. Purpose

An identity adjudication may establish that independently bound evidence supports treating two provisional subjects as the same object. That conclusion still does not define which existing subject should remain canonical, which trajectory references would change, which identifiers must remain discoverable, which approvals are required, or how a later change could be reversed.

Identity Merge Proposal v0.1 records that missing governance layer. It turns one exact GT38 Trajectory Identity Adjudication into a bounded, review-only proposal containing:

- one caller-selected canonical subject reference;
- one existing merge subject reference;
- the exact two affected trajectories;
- one proposed `subject_ref` rewrite;
- one retained alias record;
- one proposed retired subject reference;
- explicit approval roles;
- closed blocking and withdrawal conditions;
- a deterministic reversal plan;
- explicit non-approval and non-execution boundaries.

The Artifact is a proposal, not a mutation command, State Transition, Correction Request, Runtime Request, authorization, or proof of real-world identity.

## 2. Source requirements

The builder accepts exact bytes for one registered `geotask.trajectory-identity-adjudication` Artifact. The source must strictly load and must declare:

```text
adjudication_state = same_object_confirmed
candidate_alignment = aligned
identity_merge_recommendation = recommend_identity_merge_review
next_action = review_identity_merge
candidate_binding_verified = true
verification_bindings_verified = true
independent_evidence_satisfied = true
```

The source must also preserve two distinct trajectory references and two distinct subject references of the same object class. Every source execution or mutation boundary must remain false.

A source that is unresolved, confirms different objects, contradicts the candidate, lacks exact bindings, or claims an identity merge already occurred fails closed.

## 3. Canonical-subject selection

The caller must choose `canonical_subject_ref` from the exact two existing subject references in the source adjudication. Version 0.1 does not allow:

- invention of a new canonical identity;
- selection of an unrelated subject;
- automatic ranking of the two subjects;
- use of Provider count, trajectory order, filename order, or arrival order as implicit precedence.

The non-selected existing subject becomes `merge_subject_ref`. It is proposed for retirement as a primary subject reference but must remain as a retained alias.

## 4. Bounded affected scope

`affected_trajectory_refs` must contain exactly the two source trajectories. Exactly one `proposed_subject_ref_rewrites` record is produced for the trajectory currently bound to `merge_subject_ref`:

```json
{
  "trajectory_ref": "track_beta",
  "current_subject_ref": "provisional_beta",
  "proposed_subject_ref": "provisional_alpha",
  "state": "proposed"
}
```

The other trajectory already refers to the selected canonical subject and therefore requires no rewrite record.

The proposal cannot add unrelated trajectories, objects, relations, attributes, observations, world-state paths, outputs, or actions.

## 5. Alias preservation

Version 0.1 requires one retained alias:

```json
{
  "alias_subject_ref": "provisional_beta",
  "canonical_subject_ref": "provisional_alpha",
  "source_trajectory_refs": ["track_beta"],
  "state": "retain_as_alias"
}
```

`proposed_retired_subject_refs` identifies a subject that may cease to act as the primary reference after a separately approved and executed change. It does not authorize deletion. `aliases_preserved` must be true, while `alias_deleted` and `new_identity_created` must be false.

## 6. Approval boundary

The caller supplies at least one unique approval role. Roles are opaque caller-declared identifiers; Core does not resolve people, organizations, permissions, credentials, or real approval state.

The proposal always declares:

```text
proposal_state = ready_for_review
review_action = review_identity_merge_proposal
next_action = request_identity_merge_approval
proposal_approved = false
```

Artifact validity therefore does not mean the proposal has been approved.

## 7. Blocking and withdrawal conditions

The required blocking conditions are closed and ordered:

1. `source_adjudication_changed`;
2. `contradictory_identity_evidence`;
3. `approval_missing`;
4. `affected_scope_changed`;
5. `reversal_plan_unavailable`.

The required withdrawal conditions are:

1. `source_adjudication_withdrawn`;
2. `different_objects_confirmed`;
3. `canonical_subject_unavailable`;
4. `merge_subject_reassigned`;
5. `identity_policy_boundary_changed`.

Removing or replacing any required condition fails closed.

## 8. Reversal plan

The proposal records the inverse of its one proposed rewrite. The reversal plan restores the original subject reference for the affected trajectory, preserves alias history, requires post-reversal validation, and declares `reversal_executed: false`.

The plan is an auditable prerequisite, not an executed rollback. Execution belongs to a later, separately authorized object-graph or World-State change workflow.

## 9. Strict loading and exact binding

`load_identity_merge_proposal()` validates the serialized structure and all internal invariants. It does not reread the source adjudication.

`validate_identity_merge_proposal_bindings()` rebuilds the proposal from the exact GT38 bytes plus the serialized caller choices and requires complete semantic equality. Even insignificant source-byte changes alter the SHA-256 binding and fail replay validation.

Generic validation:

```bash
geotask artifact validate \
  geotask.identity-merge-proposal \
  identity_merge_proposal_gt39.json
```

verifies Schema and strict internal semantics only. Its summary therefore reports `source_binding_verified: false`; callers must use explicit binding validation when exact source replay matters.

## 10. Mandatory non-execution boundary

Every valid v0.1 proposal must keep the following values false:

```text
new_identity_created
alias_deleted
proposal_approved
object_graph_mutated
identity_merge_performed
subject_refs_mutated
world_state_updated
production_output_released
action_authorized
action_executed
```

The Artifact does not:

- prove external identity truth;
- approve its own proposal;
- create or delete identities;
- rewrite any `subject_ref`;
- mutate an object graph;
- create a Correction Request or State Transition;
- update a World State;
- publish production output;
- authorize or execute an action.

## 11. Public API

```python
from geotask_core import (
    build_identity_merge_proposal,
    load_identity_merge_proposal,
    validate_identity_merge_proposal_bindings,
)
```

## 12. Reference files

- `examples/core/gt39_build_identity_merge_proposal.py`
- `examples/core/identity_merge_proposal_gt39.json`
- `examples/core/gt39_identity_merge_proposal.json`
- `site/gt39/index.html`
- `tests/v1/test_identity_merge_proposal_v0_6.py`
- `tests/test_gt39_identity_merge_proposal_case.py`
- `tests/test_gt39_experience_page.py`
