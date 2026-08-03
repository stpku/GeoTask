# GeoTask Observation Merge Result v0.1

## 1. Purpose

`geotask.observation-merge-result` records one bounded, deterministic merge of exact `geotask.observation` artifacts into one immutable base `geotask.world-state` snapshot.

The contract closes a specific world-model gap: a valid Observation can describe a newer claim, while a World State remains an explicit point-in-time snapshot. Observation Merge v0.1 applies those claims to declared existing targets and emits a new World State revision plus an immutable result that binds the exact input and output bytes.

It is not an identity-resolution engine, conflict-resolution engine, state-diff engine, impact engine, workflow runner, or action authorization mechanism.

## 2. Binding model

One result binds:

- one immutable base `geotask.world-state` by ID, revision, `as_of`, `materialized_at`, semantic fingerprint, and raw-byte SHA-256;
- one or more exact `geotask.observation` artifacts by Observation ID, timestamps, and raw-byte SHA-256;
- one explicit claim-to-target mapping for every supplied Observation claim;
- one generated successor `geotask.world-state` by ID, revision, timestamps, semantic fingerprint, and raw-byte SHA-256;
- one before/after application record for every mapped claim.

`validate_observation_merge_result_bindings` replays the merge over the supplied exact bytes and requires the generated canonical successor bytes and result semantics to match the declared Artifact.

## 3. Supported target scope

Observation Merge v0.1 supports two target forms:

| Target kind | Identity JSON Pointer | Meaning |
|---|---|---|
| `attribute` | `/objects/<object-id>/attributes/<attribute-name>` | Replace one existing object attribute from a claim whose `subject_ref` equals the object ID and whose `predicate` equals the attribute name. |
| `relation` | `/relations/<relation-id>` | Replace one existing relation from a claim whose `subject_ref`, `predicate`, and `object_ref` exactly match the existing relation identity. |

The target path is an identity path, not an array index path. This keeps the mapping stable when canonical ordering changes.

v0.1 does not create objects, create attributes, create relations, delete state, or change object/relation identity.

## 4. Complete claim coverage

Every claim in every supplied Observation must be mapped exactly once. A merge fails closed when:

- a claim has no mapping;
- a mapping references an unknown Observation or claim;
- the same claim is mapped more than once;
- two claims target the same state path;
- a target object, attribute, or relation does not already exist;
- a target identity disagrees with the claim identity.

This rule prevents a caller from silently dropping inconvenient claims or applying multiple competing values to one target in an order-dependent way.

## 5. Claim projection

For an accepted attribute claim, the successor attribute is projected as:

- the existing attribute `name`;
- the claim `value`;
- the claim `basis`;
- `verification_status: asserted`;
- `valid_from` equal to the claim-level `observed_at`, or the parent Observation `observed_at` when the claim omits it;
- optional claim `valid_until` and `uncertainty`;
- `observation_refs` containing the source Observation ID;
- `evidence_refs` copied from the claim.

For an accepted relation claim, the successor relation preserves the existing relation ID and uses the claim subject, predicate, object, value, basis, validity, uncertainty, Observation references, and evidence references. Its `verification_status` is also `asserted`.

Observation Merge never promotes a claim to `verified`. External truth verification remains a separate responsibility.

## 6. Snapshot semantics

A successful merge:

- preserves the base `world_state_id`;
- sets the successor revision to exactly `base revision + 1`;
- requires successor `as_of` not to precede the base `as_of`;
- requires every Observation and effective claim time not to be later than successor `as_of`;
- requires every Observation `received_at` not to be later than successor `materialized_at`;
- preserves base top-level Observation and evidence references;
- adds the supplied Observation IDs and claim evidence references;
- rejects a merge when all supplied Observation IDs are already declared by the base snapshot.

The last rule prevents a caller from producing a meaningless new revision from no newly declared Observation input.

## 7. Result contract

Each `applied_claims` entry records:

- deterministic `application_id` as `<observation-id>#<claim-id>`;
- source `observation_ref` and `claim_id`;
- explicit target path and target kind;
- `state: applied`;
- the complete target value before merge;
- the complete target value after merge.

The aggregate result state is `completed`. `next_action` is `compute_state_transition`, because the merge only materializes the successor snapshot. It does not calculate or assert what changed across snapshots as a State Transition Artifact.

## 8. Validation levels

Generic Artifact validation proves only:

- JSON Schema validity;
- strict loader validity;
- internal reference closure;
- timestamp and revision constraints;
- required false operational boundary flags;
- deterministic semantic fingerprinting.

Generic validation deliberately reports base binding, Observation binding, claim-target binding, replay, and successor binding as false.

Explicit binding validation additionally proves:

- exact base World State bytes;
- exact Observation bytes;
- complete claim mapping;
- exact target identity and before value;
- deterministic successor projection;
- exact canonical successor bytes;
- exact result semantics after replay.

## 9. Safety boundary

Observation Merge v0.1 does not:

- discover object or relation identity;
- merge ambiguous or conflicting claims;
- choose claim precedence;
- create missing objects, attributes, or relations;
- verify external evidence or claim truth;
- compute a State Transition;
- discover or propagate impact;
- run incremental reevaluation;
- release outputs;
- authorize or execute actions.

Accordingly, these result fields are required to remain `false`: `state_transition_computed`, `impact_propagation_executed`, `reevaluation_executed`, `outputs_released`, `external_truth_verified`, `action_authorized`, and `action_executed`.

## 10. Reference example

`examples/core/observation_merge_result_uav_recheck.json` binds:

- `examples/core/world_state_uav_separation.json` as revision 1;
- `examples/core/observation_uav_b_delay_recheck.json` as the newer telemetry Observation;
- `/objects/uav-b/attributes/delay_seconds` as the explicit target;
- `examples/core/world_state_uav_separation_observation_merged.json` as revision 2.

The merge changes `uav-b.delay_seconds` from 40 to 60 and preserves the dependent `uav-temporal-separation` relation at 80. That preserved stale derived value is intentional: Observation Merge does not replace State Transition calculation, impact discovery, recompute derivation, or incremental reevaluation.
