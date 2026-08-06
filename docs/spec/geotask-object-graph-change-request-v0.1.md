# GeoTask Object Graph Change Request v0.1

## 1. Status and purpose

GeoTask Object Graph Change Request v0.1 is the public, machine-verifiable contract used by GT41. Its stable Artifact ID is `geotask.object-graph-change-request`, its wrapper key is `object_graph_change_request`, and its JSON Schema is `schemas/geotask-object-graph-change-request-v0.1.schema.json`.

The Artifact converts one exact GT39 Identity Merge Proposal and one exact GT40 Identity Merge Approval Record into a bounded request for external application review. It does not apply the requested change. The distinction is deliberate:

- GT39 proposes one identity-merge rewrite;
- GT40 records whether every required role approved that proposal;
- GT41 describes the exact object-graph operation that may be reviewed for application;
- a later external application and post-application validation remain separate.

A structurally valid GT41 request therefore means “the approved scope has been expressed as a closed change request,” not “the object graph has changed.”

## 2. Required source bindings

The builder consumes the original UTF-8 JSON bytes of:

1. one `geotask.identity-merge-proposal` v0.1 Artifact; and
2. one `geotask.identity-merge-approval-record` v0.1 Artifact.

The request records SHA-256 digests for both exact byte sequences. The approval record must itself bind the same proposal ID and exact proposal digest. Insignificant byte changes therefore invalidate exact replay even when parsed JSON values remain equivalent.

The source proposal must be `ready_for_review`, preserve aliases, contain exactly one proposed `subject_ref` rewrite and one inverse rollback operation, and keep all mutation, publication, authorization, and execution flags false.

The source approval record must have:

- `aggregate_decision = approved`;
- `proposal_approval_complete = true`;
- `change_request_eligible = true`;
- `next_action = prepare_identity_merge_change_request`;
- every required role in `approved_roles`;
- no rejected or evidence-required roles; and
- all mutation, publication, authorization, and execution flags false.

## 3. Request structure

The serialized root contains one `object_graph_change_request` object with `request_version = 0.1`.

### 3.1 Identity and source references

The request includes:

- `change_request_id` and timezone-aware `created_at`;
- `source_proposal_ref` with Artifact ID, proposal ID, and exact-byte SHA-256;
- `source_approval_record_ref` with Artifact ID, approval-record ID, and exact-byte SHA-256;
- the proposal's existing `canonical_subject_ref`, `merge_subject_ref`, `object_class`, and exactly two affected trajectory references.

Core does not invent a new canonical identity or widen the source scope.

### 3.2 Closed change operation

GT41 contains exactly one `change_operations` item:

- `operation_kind = replace_subject_ref`;
- `target_object_kind = trajectory`;
- `target_path = /subject_ref`;
- `before_subject_ref` equals the proposal's merge subject;
- `after_subject_ref` equals the proposal's canonical subject; and
- `state = requested`.

For the fixed fictional case, the operation requests that `track_beta` change from `provisional_beta` to `provisional_alpha`. The operation is only requested; it is not applied by Core.

### 3.3 Alias preservation

`retained_aliases` contains exactly the alias declaration inherited from GT39. The merge subject remains an auditable alias of the canonical subject, and its source trajectory scope cannot be expanded. Alias deletion and new-identity creation are outside this contract.

### 3.4 Preconditions

The request records seven ordered preconditions. Exact proposal binding, exact approval-record binding, completed approval, and rollback availability are verified while the request is built. Canonical-subject availability, the current target binding, and absence of active withdrawal conditions require a separate application-time check.

A `verified` precondition is not an authorization to apply the change. A `requires_application_check` precondition must be evaluated by the external application workflow against its current authoritative state.

### 3.5 Acceptance criteria

Five pending criteria constrain any later application:

1. only the requested `subject_ref` rewrite is applied;
2. the retained alias is preserved;
3. no undeclared object-graph path changes;
4. post-application binding validation passes; and
5. the rollback plan remains available.

GT41 records these criteria but does not evaluate them because no application occurs in this Artifact.

### 3.6 Rollback plan

The rollback plan contains exactly one inverse operation restoring the original trajectory `subject_ref`. It requires alias-history preservation, post-rollback validation, and separate rollback authorization. `rollback_executed` must remain false.

## 4. States and action boundary

A valid request has:

- `request_state = ready_for_application_review`;
- `request_reason = approved_identity_merge_supports_bounded_object_graph_change_request`;
- `application_review_required = true`; and
- `next_action = request_object_graph_change_application_approval`.

The following must remain false:

- `application_authorized`;
- `change_applied`;
- `identity_merge_performed`;
- `subject_refs_mutated`;
- `object_graph_mutated`;
- `world_state_updated`;
- `production_output_released`;
- `action_authorized`; and
- `action_executed`.

The closed `blocked_operations` set prevents unreviewed application, undeclared path mutation, alias deletion, identity creation, World State update, production release, and action execution.

## 5. Validation levels

### 5.1 JSON Schema validation

The public JSON Schema validates the serialized shape, constants, item counts, and fixed false/true boundaries.

### 5.2 Strict semantic loading

`load_object_graph_change_request()` additionally enforces cross-field semantics, including the single trajectory `/subject_ref` operation, exact before/after subject roles, retained alias scope, ordered preconditions and acceptance criteria, inverse rollback, and all non-execution flags.

### 5.3 Exact binding replay

`validate_object_graph_change_request_bindings()` rebuilds the request from the supplied exact GT39 and GT40 bytes and requires semantic equality with the serialized GT41 Artifact. This is the authoritative public binding check.

### 5.4 Generic Artifact validation

`geotask artifact validate geotask.object-graph-change-request <file>` validates the registered Schema and strict serialized semantics. Generic validation intentionally reports proposal and approval-record bindings as unverified because the source bytes are not supplied to that command.

## 6. Non-goals

Object Graph Change Request v0.1 does not:

- discover identity equivalence;
- choose a canonical subject;
- approve an identity-merge proposal;
- submit or authorize itself;
- read an authoritative production object graph;
- apply a rewrite or create a successor World State;
- delete an alias or create a new identity;
- release production output; or
- authorize or execute a real-world action.

These boundaries preserve the GeoTask principle that a proposal, an approval record, a change request, application authorization, application execution, and post-change verification are distinct auditable stages.
