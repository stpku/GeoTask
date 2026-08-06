# GeoTask Identity Merge Approval Record v0.1

Status: implemented public Artifact  
Artifact ID: `geotask.identity-merge-approval-record`  
Schema ID: `https://stpku.github.io/GeoTask/schemas/geotask-identity-merge-approval-record-v0.1.schema.json`  
Reference case: GT40

## Purpose

The Identity Merge Approval Record binds one exact GT39 Identity Merge Proposal to an explicit decision for every approval role declared by that proposal. It records whether each role approved, rejected, or requested more evidence, then derives one aggregate decision without applying the proposed merge.

The Artifact separates three stages that must not be collapsed:

```text
Identity Merge Proposal
→ Approval Record
→ later bounded change request
```

An approved record means only that the proposal may proceed to a separate change-request stage. It does not mutate an object graph, rewrite `subject_ref`, update World State, publish output, authorize action, or execute action.

## Source binding

`source_proposal_ref` contains:

- `artifact_id: geotask.identity-merge-proposal`;
- the exact source `proposal_id`;
- SHA-256 of the serialized proposal bytes.

Binding validation reloads the exact bytes, verifies the GT39 proposal contract, rebuilds the approval record, and requires semantic equality. Whitespace-only changes therefore invalidate the exact binding even when the JSON values remain equivalent.

## Approval decisions

Every role in the GT39 `required_approvals` array must appear exactly once in `approval_decisions`, in the same declared order. Each decision contains:

- `approval_role`;
- `reviewer_ref`;
- `decision`;
- `rationale`;
- timezone-aware `decided_at`;
- zero or more `evidence_refs`.

The closed decision vocabulary is:

- `approved`;
- `rejected`;
- `evidence_required`.

An `evidence_required` decision must contain at least one evidence reference describing the requested evidence target.

## Aggregate decision

The aggregate rule is deterministic and closed:

1. if any required role records `rejected`, the aggregate decision is `rejected`;
2. otherwise, if any required role records `evidence_required`, the aggregate decision is `evidence_required`;
3. otherwise all required roles have approved and the aggregate decision is `approved`.

Derived role lists must exactly match the individual decisions:

- `approved_roles`;
- `rejected_roles`;
- `evidence_required_roles`.

## Next action

| Aggregate decision | Approval complete | Change request eligible | Next action |
|---|---:|---:|---|
| `approved` | true | true | `prepare_identity_merge_change_request` |
| `rejected` | false | false | `close_identity_merge_proposal` |
| `evidence_required` | false | false | `request_identity_merge_evidence` |

`change_request_eligible=true` is not an execution authorization. It only permits preparation of a later bounded object-graph change request.

## Closed execution boundary

The record always keeps these operations blocked:

```text
identity_merge_execution
subject_ref_mutation
object_graph_mutation
world_state_update
production_output_release
action_execution
```

The following fields must remain false:

```text
identity_merge_performed
subject_refs_mutated
object_graph_mutated
world_state_updated
production_output_released
action_authorized
action_executed
```

## GT40 fixed case

GT40 binds `identity_merge_proposal_gt39.json`. The proposal requires two approval roles:

- `identity_governance_reviewer`;
- `world_state_maintainer`.

Two fictional reviewers approve the proposal. The aggregate decision becomes `approved`, `proposal_approval_complete` and `change_request_eligible` become true, and the next action becomes `prepare_identity_merge_change_request`.

No identity is merged. `track_beta` still references `provisional_beta`; the object graph and World State remain unchanged.

## Reference files

- `examples/core/identity_merge_proposal_gt39.json`
- `examples/core/identity_merge_approval_record_gt40.json`
- `examples/core/gt40_identity_merge_approval_record.json`
- `examples/core/gt40_build_identity_merge_approval_record.py`
- `schemas/geotask-identity-merge-approval-record-v0.1.schema.json`
- `site/gt40/index.html`
