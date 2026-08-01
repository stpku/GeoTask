# GeoTask World State v0.1

Status: public experimental contract for the v0.5 Verifiable World-State Cycle.

A World State is one explicit, versioned snapshot of the objects, attributes, and relations that an Agent or Runtime currently depends on at a declared time. It is a materialized state record, not a stream, database, hidden model representation, or automatic truth source.

World State validation proves only that the payload is structurally complete, internally consistent, reference-closed, time-consistent, JSON-safe, and traceable to its declared Observation and Evidence references. It does **not** ingest Observations, fetch evidence, authenticate sources, verify external truth, compute a State Transition, rerun a GeoTask, change action eligibility, or execute an action.

## Published identifiers

- Artifact ID: `geotask.world-state`
- wrapper key: `world_state`
- Schema version: `0.1`
- JSON Schema: `schemas/geotask-world-state-v0.1.schema.json`
- validation command:

  ```bash
  geotask artifact validate geotask.world-state <world-state.json> --format json
  ```

## Envelope

```json
{
  "world_state": {
    "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-world-state-v0.1.schema.json",
    "schema_version": "0.1",
    "world_state_id": "fictional-state",
    "revision": 1,
    "as_of": "2026-07-16T10:00:40+08:00",
    "materialized_at": "2026-07-16T10:00:42+08:00",
    "observation_refs": [],
    "evidence_refs": [],
    "objects": [],
    "relations": []
  }
}
```

`objects` must contain at least one world object. The other arrays are explicit even when empty so the snapshot boundary is machine-readable.

## Snapshot identity and time

- `world_state_id` identifies the logical state series.
- `revision` is an integer greater than or equal to one.
- `as_of` is the time represented by the snapshot.
- `materialized_at` is when this serialized snapshot was constructed and must not precede `as_of`.

Revision ordering is declared metadata only. v0.1 does not infer a predecessor, compare revisions, merge branches, or create a State Transition.

## Reference inventories

`observation_refs` and `evidence_refs` are unique, top-level inventories. Every nested object, attribute, or relation reference must be present in the corresponding inventory. Validation checks reference closure only; it does not fetch, authenticate, or validate the referenced content.

## World objects

Each object contains:

- `id`: unique object identity within the snapshot;
- `type`: explicit object type;
- `verification_status`;
- optional validity interval and uncertainty;
- nested Observation and Evidence references;
- `attributes`: zero or more named state values.

Attribute names must be unique within one object. An attribute contains a JSON-safe `value`, a claim `basis`, its own verification status, validity, uncertainty, and traceability.

## Relations

Each relation contains:

- unique `id` that does not collide with an object ID;
- `subject_ref` and `object_ref`, both resolving to objects in the same snapshot;
- explicit `predicate` and JSON-safe `value`;
- claim `basis`, verification status, validity, uncertainty, and traceability.

World State v0.1 does not infer reverse, symmetric, transitive, or spatial relations. A relation is present only when explicitly serialized.

## Verification status

Allowed values are:

- `asserted`
- `verified`
- `contradicted`
- `unverifiable`
- `need_data`
- `unknown`

`asserted`, `verified`, and `contradicted` require at least one nested `observation_ref` or `evidence_ref`. This is a traceability requirement, not proof that the status is correct. `unverifiable`, `need_data`, and `unknown` may remain without references when the absence of support is itself explicit.

## Claim basis

Attributes and relations reuse the Observation v0.1 basis vocabulary:

- `direct_observation`
- `model_inference`
- `derived`
- `external_assertion`
- `human_judgment`

Basis and verification status are independent. For example, a `model_inference` may be `asserted`, `contradicted`, or `verified` by a separately referenced result.

## Validity at the snapshot time

For every object, attribute, and relation:

- `valid_from`, when present, must not be later than `world_state.as_of`;
- `valid_until`, when present, must not be earlier than `world_state.as_of`;
- `valid_until` must not precede `valid_from`.

This ensures every serialized item is active at the represented snapshot time. Historical and future facts belong in other snapshots rather than inactive entries in the same snapshot.

## Uncertainty

World State uses the Observation v0.1 uncertainty forms:

- probability of error;
- confidence;
- standard deviation;
- interval width;
- qualitative `low`, `medium`, `high`, or `unknown`.

Probability and confidence are bounded to `[0, 1]`. Numeric uncertainty must be finite and non-negative. Qualitative uncertainty cannot declare a unit.

## Deterministic semantic fingerprint

The Python loader normalizes object, attribute, relation, Observation-reference, and Evidence-reference ordering before producing a SHA-256 semantic fingerprint. The unified Artifact Validation Report exposes this fingerprint so repeated validation of semantically identical ordering variants can be compared without treating the fingerprint as a signature or proof of source authenticity.

## Failure-closed conditions

Strict loading rejects, among other cases:

- unknown or missing fields;
- naive or inconsistent timestamps;
- empty object inventory;
- duplicate object IDs, relation IDs, or object attribute names;
- relation references to unknown objects;
- nested Observation or Evidence references absent from the top-level inventory;
- traceable statuses without any traceability reference;
- items not valid at `as_of`;
- non-finite or non-JSON values;
- invalid uncertainty metadata.

## Explicit non-goals

World State v0.1 does not:

- consume or merge Observation payloads;
- establish which Observation supersedes another;
- resolve conflicts between claims;
- calculate changed paths;
- produce a State Transition;
- build an Impact Graph;
- rerun affected assertions;
- evaluate or change action eligibility;
- authorize or execute `next_action`;
- prove that evidence, status, or world values are true.

Those behaviors belong to later State Transition, Verification Session, discrepancy, impact, and incremental-reevaluation contracts.

## Fictional example

`examples/core/world_state_uav_separation.json` materializes the fictional GT16 replay as a snapshot with two UAV objects, a direct delay Observation, a verified route-crossing relation, and a derived temporal-separation relation. The example contains no live telemetry, operational authorization, or real aviation data.
