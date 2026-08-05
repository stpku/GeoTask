# GeoTask Trajectory Identity Adjudication v0.1

Status: implemented public Artifact  
Reference case: GT38  
Artifact ID: `geotask.trajectory-identity-adjudication`

## Purpose

This Artifact records an auditable identity adjudication for two trajectory fragments without changing the object graph. It starts from one exact GT37 `trajectory_identity_candidate` execution result and binds one Verification Request, one caller-authored Assurance Profile, matching Verification Provider Descriptors, and matching Verification Responses.

The contract separates three questions:

1. Did deterministic boundary-sample rules produce a same-object or different-object candidate?
2. Did the caller-declared independent-evidence policy pass for an external identity verdict?
3. What review recommendation follows without letting Core merge identities or rewrite references?

## Exact inputs

The deterministic builder requires exact bytes for:

- one `geotask.execution-result` whose `identity_candidate` output preserves two distinct trajectory and subject references;
- one `geotask.verification-request` with `claim_type: trajectory_identity` and an exact SHA-256 binding to that execution result;
- one `geotask.assurance-profile` whose eligible output is `identity_merge_recommendation` and whose blocked outputs/actions include automatic merge and `subject_ref` mutation;
- one or more `geotask.verification-provider-descriptor` Artifacts;
- one matching `geotask.verification-response` per supplied Provider Descriptor.

Every response is checked against the exact Request and Descriptor bytes before assurance evaluation. Provider count, independent groups, freshness, reproducibility, calibration, allowed Provider types, and conflict behavior come from the caller-authored Assurance Profile. A Provider cannot self-assign the final adjudication state.

## Adjudication vocabulary

`adjudication_state` is one of:

- `same_object_confirmed`: the declared assurance policy passed and all usable responses support `same_object`;
- `different_objects_confirmed`: the declared assurance policy passed and all usable responses support `different_objects`;
- `unresolved`: evidence is insufficient, stale, ineligible, unknown, or conflicting.

`identity_merge_recommendation` is one of:

- `recommend_identity_merge_review`;
- `recommend_keep_separate`;
- `request_more_evidence`.

The recommendation is not an object mutation. `same_object_confirmed` only makes a bounded review recommendation eligible. It does not create a merged object, select a canonical identity, rewrite either trajectory, or publish a production identity update.

## Candidate alignment

The Artifact records whether the independent evidence result is:

- `aligned` with the GT37 candidate;
- `contradicted` by the adjudication;
- `not_comparable` because the original candidate was `unverifiable`;
- `unresolved` because the evidence policy did not reach a confirmed adjudication.

The original candidate and every Provider response remain retained. Contradictory evidence is not deleted or averaged.

## Generic validation and exact binding validation

`geotask artifact validate geotask.trajectory-identity-adjudication <file>` checks the JSON Schema and internal semantic consistency. Generic validation deliberately reports that source-byte bindings were not replayed.

`validate_trajectory_identity_adjudication_bindings(...)` rebuilds the adjudication from the exact candidate, Request, Profile, Descriptor, and Response bytes and requires semantic equality with the retained Artifact.

## Fail-closed behavior

Construction or loading fails when:

- the GT37 result lacks a structured `identity_candidate` output;
- the original candidate claims an identity merge or `subject_ref` mutation;
- the Request does not bind the exact candidate bytes;
- the Request, Profile, Descriptor, or Response references do not close;
- a Provider cannot accept the declared Request;
- a verified response returns an unsupported identity verdict;
- Provider and response sets differ;
- response-reference partitions are incomplete, overlapping, or inconsistent;
- adjudication state, recommendation, next action, and policy result disagree;
- any field claims Core verified external identity, merged identities, mutated references, released output, authorized action, or executed action.

## Non-execution boundary

The public Core does not fetch registry records, inspect real imagery, establish real-world identity truth, merge objects, choose a canonical identifier, rewrite `subject_ref`, publish production output, authorize a merge, or execute a merge. External systems or human governance may consume the recommendation under their own authorization and audit controls.

## Fixed GT38 files

- `examples/core/gt38_build_trajectory_identity_adjudication.py`
- `examples/core/assurance_profile_trajectory_identity_gt38.json`
- `examples/core/verification_provider_descriptor_asset_registry_gt38.json`
- `examples/core/verification_provider_descriptor_human_identity_reviewer_gt38.json`
- `examples/core/verification_request_trajectory_identity_gt38.json`
- `examples/core/verification_response_asset_registry_gt38.json`
- `examples/core/verification_response_human_identity_reviewer_gt38.json`
- `examples/core/trajectory_identity_adjudication_gt38.json`
- `examples/core/gt38_trajectory_identity_adjudication.json`
- `site/gt38/index.html`
