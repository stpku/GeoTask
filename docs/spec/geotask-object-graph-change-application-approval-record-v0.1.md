# GeoTask Object Graph Change Application Approval Record v0.1

Status: implemented public contract  
Artifact ID: `geotask.object-graph-change-application-approval-record`  
Wrapper key: `object_graph_change_application_approval_record`  
JSON Schema: [`schemas/geotask-object-graph-change-application-approval-record-v0.1.schema.json`](../../schemas/geotask-object-graph-change-application-approval-record-v0.1.schema.json)  
Reference case: GT42

## 1. Purpose

Object Graph Change Application Approval Record v0.1 records whether one exact GT41 Object Graph Change Request has completed the caller-declared application-approval process. It separates four stages that must not be collapsed:

1. a change request exists;
2. application approvers record decisions;
3. a later bounded application Artifact may become eligible;
4. an external authorized system may eventually apply and verify the change.

A valid GT42 approval record therefore means only that the declared approval decisions are closed and auditable. It does not mean the change has been authorized by GeoTask Core, applied to an object graph, reflected in World State, published, or executed.

## 2. Exact source binding

The record binds the exact serialized bytes of one GT41 `geotask.object-graph-change-request` using:

- `artifact_id`;
- `change_request_id`;
- lowercase SHA-256 digest of the original bytes.

The source request must be `ready_for_application_review`, must request `request_object_graph_change_application_approval`, and must retain all GT41 non-application boundaries. Whitespace-only changes to the supplied source bytes change the digest and fail exact binding validation.

## 3. Caller-declared approval roles

The caller supplies a non-empty, unique ordered list of `required_approval_roles`. GeoTask Core does not discover an organization chart, infer legal authority, nominate reviewers, or decide which roles are sufficient for a real deployment.

For every declared role, the caller must provide exactly one decision containing:

- `approval_role`;
- `reviewer_ref`;
- `decision`;
- `rationale`;
- timezone-aware `decided_at`;
- zero or more `evidence_refs`.

The fixed GT42 example declares:

- `object_graph_change_owner`;
- `world_state_governance_reviewer`.

## 4. Decision states and aggregation

Each role decision is one of:

- `approved`;
- `rejected`;
- `evidence_required`.

Aggregation is deterministic and closed:

1. any `rejected` decision produces aggregate `rejected`;
2. otherwise, any `evidence_required` decision produces aggregate `evidence_required`;
3. only all-role approval produces aggregate `approved`.

An `evidence_required` decision must include at least one evidence reference. Missing roles, duplicate roles, undeclared roles, unsupported decisions, and inconsistent aggregate fields fail closed.

## 5. Approved outcome is eligibility, not application

When all required roles approve, the record sets:

```text
application_approval_complete: true
change_application_eligible: true
next_action: prepare_bounded_object_graph_change_application
```

It still requires:

```text
application_authorized: false
change_applied: false
identity_merge_performed: false
subject_refs_mutated: false
object_graph_mutated: false
world_state_updated: false
production_output_released: false
action_authorized: false
action_executed: false
```

The public contract therefore distinguishes:

> application approval complete ≠ application authorized ≠ change applied

A later Artifact must express the bounded application inputs, exact before/after state, applied scope, retained alias history, rollback capability, and acceptance results.

## 6. Rejected and evidence-required outcomes

A rejected aggregate produces:

```text
next_action: close_object_graph_change_request
change_application_eligible: false
```

An evidence-required aggregate produces:

```text
next_action: request_object_graph_change_application_evidence
change_application_eligible: false
```

Neither outcome permits partial application or undeclared path mutation.

## 7. Closed blocked operations

Every record preserves the fixed blocked-operation set:

- unapproved change application;
- undeclared path mutation;
- alias deletion;
- identity creation;
- World State update;
- production output release;
- action execution.

The record cannot be extended with an application command, arbitrary mutation path, hidden authorization flag, or side-effect instruction.

## 8. Validation layers

`load_object_graph_change_application_approval_record()` performs strict structural and semantic validation of serialized GT42 content.

`validate_object_graph_change_application_approval_record_bindings()` rebuilds the record from the exact supplied GT41 bytes and requires semantic equality. This is the authoritative public source-binding check.

`geotask artifact validate geotask.object-graph-change-application-approval-record <file>` validates the registered Schema and strict serialized semantics. Generic Artifact validation intentionally reports the GT41 binding as unverified because the source bytes are not supplied to that command.

## 9. GT42 fixed fictional case

GT42 binds `object_graph_change_request_gt41.json`. Both declared roles explicitly approve. The result is eligible for preparation of a later bounded application Artifact, while application authorization, reference mutation, object-graph mutation, World State update, publication, authorization, and execution all remain false.

## 10. Non-goals

Object Graph Change Application Approval Record v0.1 does not:

- prove that a reviewer has legal or organizational authority;
- authenticate identities or signatures;
- authorize GeoTask Core to execute a mutation;
- apply the GT41 operation;
- rewrite `subject_ref`;
- delete aliases or create identities;
- update an object graph or World State;
- evaluate GT41 post-application acceptance criteria;
- publish production output;
- authorize or execute external action.
