# GeoTask State Transition v0.1

Status: public experimental contract for the v0.5 Verifiable World-State Cycle.

A State Transition is an auditable record that binds one earlier World State snapshot to one later snapshot and declares which Observation references support explicit object, attribute, relation, and action-eligibility changes. It is not a patch executor, event bus, truth source, workflow engine, or authorization decision.

Validation proves only that the transition payload is structurally complete, internally consistent, time-ordered, reference-closed, JSON-safe, and bound to declared snapshot identities and fingerprints. It does **not** compare snapshot contents, calculate a diff, apply changes, materialize a new World State, fetch evidence, verify external truth, rerun a GeoTask, execute a control action, or authorize real-world action.

## 1. Stable identity

- Artifact ID: `geotask.state-transition`
- Wrapper: `state_transition`
- Schema version: `0.1`
- JSON Schema: [`schemas/geotask-state-transition-v0.1.schema.json`](../../schemas/geotask-state-transition-v0.1.schema.json)
- Python loader: `load_state_transition(payload)`
- Snapshot binding validator: `validate_state_transition_bindings(transition, from_state, to_state)`
- Unified validation: `geotask artifact validate geotask.state-transition <state-transition.json>`

The Registry descriptor has no generation command. A Runtime or Agent may author or materialize the record only after an explicit state comparison. Core validates the serialized contract but does not invent the changes.

## 2. Snapshot bindings

`from_state` and `to_state` each contain:

| Field | Meaning |
|---|---|
| `world_state_id` | Stable identity of the versioned world state |
| `revision` | Positive snapshot revision |
| `as_of` | Time represented by the snapshot |
| `semantic_fingerprint` | Deterministic SHA-256 of the normalized World State payload |

The two references must name the same `world_state_id`. `to_state.revision` must be greater than `from_state.revision`, and `to_state.as_of` must not be earlier than `from_state.as_of`.

`validate_state_transition_bindings()` checks both references against two already loaded `WorldState` objects. It compares state ID, revision, `as_of`, and semantic fingerprint. This proves cryptographic binding to those exact serialized snapshots; it does not prove that the declared path changes are complete or correct.

## 3. Transition time

- `occurred_at` records when the declared state change occurred. It must fall between the two snapshot `as_of` timestamps, inclusive.
- `recorded_at` records when the transition Artifact was written. It must not be earlier than `to_state.as_of`.

All timestamps must include an explicit timezone offset.

## 4. Reference closure

Top-level `observation_refs` must contain at least one Observation ID. Top-level `evidence_refs` may be empty.

Every state change and action-eligibility change carries its own `observation_refs` and `evidence_refs`. Nested references must be declared in the corresponding top-level arrays. This provides closure inside the Artifact without claiming that the referenced source was fetched, authenticated, or independently verified.

## 5. State changes

Each item in `changes` contains:

| Field | Meaning |
|---|---|
| `id` | Unique transition-local change identity |
| `kind` | `object`, `attribute`, or `relation` |
| `operation` | `add`, `replace`, or `remove` |
| `path` | Identity-based JSON Pointer into the conceptual World State |
| `before` / `after` | Explicit serialized values governed by the operation |
| `basis` | Observation-compatible basis vocabulary |
| `verification_status` | World State verification-status vocabulary |
| `reason` | Human-readable explanation |
| `observation_refs` | Non-empty supporting Observation references |
| `evidence_refs` | Supporting evidence references |

Operation rules are fail-closed:

- `add` requires `after` and forbids `before`;
- `replace` requires both `before` and `after`, and the values must differ;
- `remove` requires `before` and forbids `after`.

No two changes may use the same `id` or changed `path`.

## 6. Identity-based paths

State Transition v0.1 uses identity-based JSON Pointer paths rather than array positions. Examples:

```text
/objects/uav-b/attributes/delay_seconds/value
/relations/uav-temporal-separation/value
```

This is a logical addressing contract. It does not imply that the World State JSON arrays can be patched directly with a generic RFC 6902 implementation.

Path families are checked against `kind`:

- object changes target `/objects/<object-id>/...` outside the `attributes` branch;
- attribute changes target `/objects/<object-id>/attributes/<attribute-name>/...`;
- relation changes target `/relations/<relation-id>/...`.

Invalid JSON Pointer escapes, empty segments, root paths, trailing slashes, and kind/path mismatches are rejected.

## 7. Action eligibility changes

`action_eligibility_changes` records changes to named output or action-gate references. Each item contains:

- unique `id`;
- `output_ref`;
- `before` and `after`, each one of `eligible`, `blocked`, or `unknown`;
- reason;
- closed Observation and Evidence references.

`before` and `after` must differ, and one transition cannot change the same `output_ref` twice.

This records that an eligibility state changed; it does not execute an action, release an output, or replace a Control Evaluation Result.

## 8. Deterministic semantic fingerprint

`StateTransition.semantic_fingerprint()` canonicalizes:

- top-level Observation and Evidence references;
- state changes by `id`;
- action-eligibility changes by `id`;
- nested reference arrays;
- JSON object keys.

Equivalent payloads with different collection ordering produce the same lowercase SHA-256 fingerprint. The fingerprint supports replay and audit binding; it is not a digital signature or publisher attestation.

## 9. Unified validation boundary

A successful unified validation report includes counts, revisions, the transition fingerprint, and the following explicit boundaries:

```json
{
  "snapshot_bindings_verified": false,
  "changes_applied": false,
  "world_state_materialized": false,
  "external_truth_verified": false,
  "action_authorized": false
}
```

The generic `geotask artifact validate` command validates only the Transition payload itself. To verify its bindings, a caller must separately load the two World State snapshots and invoke `validate_state_transition_bindings()`.

## 10. Fictional example

[`examples/core/state_transition_uav_separation_recheck.json`](../../examples/core/state_transition_uav_separation_recheck.json) binds revision 1 and revision 2 of a fictional UAV separation state. A later fictional telemetry Observation changes one delay attribute from 40 to 60 seconds, changes one derived temporal-separation relation from 80 to 60 seconds, and records that continuing without another recheck becomes blocked.

The paired snapshots are:

- [`examples/core/world_state_uav_separation.json`](../../examples/core/world_state_uav_separation.json)
- [`examples/core/world_state_uav_separation_recheck.json`](../../examples/core/world_state_uav_separation_recheck.json)

The example contains no live telemetry, aviation authorization, regulatory threshold, or production action.
