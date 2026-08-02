# GeoTask Verification Session v0.1

Status: public experimental contract for the v0.5 Verifiable World-State Cycle.

A Verification Session is an immutable audit snapshot for one explicit World State. It binds the state to exact serialized task, execution-result, control-evaluation, State Transition, and discrepancy artifacts, then records the session outcome, action eligibility, and recheck triggers.

A valid Verification Session is not a workflow execution record. Validation does **not** validate the semantics of linked artifacts, execute tasks, evaluate controls, run rechecks, fetch evidence, verify external truth, materialize a World State, or authorize a real-world action.

## 1. Stable identity

- Artifact ID: `geotask.verification-session`
- Wrapper: `verification_session`
- Schema version: `0.1`
- JSON Schema: [`schemas/geotask-verification-session-v0.1.schema.json`](../../schemas/geotask-verification-session-v0.1.schema.json)
- Python loader: `load_verification_session(payload)`
- Binding validator: `validate_verification_session_bindings(session, world_state, artifact_contents)`
- Unified validation: `geotask artifact validate geotask.verification-session <verification-session.json>`

The Registry descriptor has no generation command. An Agent or Runtime may author the Session only after the referenced World State and serialized artifacts already exist. Core validates the audit contract but does not create, execute, or recompute the linked artifacts.

## 2. Session identity and outcome

Each Session contains:

| Field | Meaning |
|---|---|
| `session_id` | Stable identity of this audit snapshot |
| `recorded_at` | Time the Session record was written |
| `state` | Overall session state |
| `reason` | Human-readable explanation of the state |

`recorded_at` must include a timezone offset and must not precede the bound World State `as_of` time.

The v0.1 session states are:

- `verified`
- `contradicted`
- `blocked`
- `need_review`
- `unknown`
- `error`

A `blocked` Session must contain at least one blocked action eligibility. An `unknown` Session must contain at least one unknown action eligibility or unknown recheck trigger.

These consistency rules prevent obviously contradictory audit records. They do not independently prove that the stated outcome is operationally correct.

## 3. World State binding

The `world_state` reference contains:

| Field | Meaning |
|---|---|
| `world_state_id` | Stable World State identity |
| `revision` | Positive snapshot revision |
| `as_of` | Time represented by the snapshot |
| `semantic_fingerprint` | Deterministic World State semantic fingerprint |

`validate_verification_session_bindings()` compares these fields with one already loaded `WorldState` object. It also requires every Session-level `observation_ref` to be declared by that bound World State.

This proves that the Session names the exact normalized World State snapshot supplied by the caller. It does not prove that the snapshot is externally true or that it was produced correctly.

## 4. Exact serialized artifact references

The Session separates linked artifacts into five lists:

| List | Required artifact identity | Cardinality |
|---|---|---|
| `task_refs` | `geotask.document` / `1.0` | one or more |
| `execution_result_refs` | `geotask.execution-result` / `1.0` | one or more |
| `control_evaluation_refs` | `geotask.control-evaluation` / `1.0` | zero or more |
| `state_transition_refs` | `geotask.state-transition` / `0.1` | zero or more |
| `discrepancy_refs` | explicitly declared Artifact ID and version | zero or more |

Every artifact reference contains:

```json
{
  "ref_id": "transition-uav-recheck",
  "artifact_id": "geotask.state-transition",
  "schema_version": "0.1",
  "instance_id": "fictional-uav-separation-recheck-transition",
  "content_sha256": "..."
}
```

`ref_id` is unique across the complete Session. `instance_id` is unique within each artifact category. `content_sha256` is the lowercase SHA-256 digest of the exact raw bytes of the referenced file.

The binding validator accepts a mapping from `ref_id` to `bytes`. It rejects:

- missing referenced artifacts;
- undeclared extra artifacts;
- non-byte values;
- SHA-256 mismatches.

This exact-byte binding is intentionally distinct from semantic validation. Formatting changes to a referenced JSON or YAML file change its byte digest even when its parsed meaning is equivalent. Callers that need semantic guarantees must separately validate each linked artifact through its own registered loader or `geotask artifact validate` contract.

## 5. Observation reference closure

Top-level `observation_refs` must contain at least one Observation identity.

Every action eligibility and recheck trigger carries non-empty `observation_refs`. Nested Observation references must be declared in the Session-level inventory. During explicit binding validation, the Session-level inventory must also be a subset of the bound World State Observation inventory.

Reference closure proves only that the identifiers are internally connected. It does not fetch, authenticate, or verify an Observation source.

## 6. Action eligibility

Each `action_eligibility` item contains:

| Field | Meaning |
|---|---|
| `output_ref` | Stable output or action-gate identity |
| `state` | `eligible`, `blocked`, or `unknown` |
| `reason` | Explanation of the eligibility state |
| `basis_refs` | References to linked artifacts in this Session |
| `observation_refs` | Supporting Observation identities |

`output_ref` values must be unique. Every `basis_ref` must resolve to one declared artifact reference.

Action eligibility is an audited claim. Loading or binding a Session does not release an output, call a downstream system, or authorize an action.

## 7. Recheck triggers

Each `recheck_triggers` item contains:

- unique `id`;
- explicit textual `condition`;
- trigger state: `armed`, `satisfied`, `dismissed`, or `unknown`;
- `reason`;
- one or more `affected_output_refs`;
- one or more artifact `basis_refs`;
- one or more `observation_refs`.

Affected outputs must be declared in `action_eligibility`. A `satisfied` trigger must affect at least one output currently recorded as `blocked` or `unknown`.

The condition is an audit statement in v0.1. Core does not parse or evaluate it, schedule work, execute a recheck, or change an output eligibility state.

## 8. Deterministic semantic fingerprint

`VerificationSession.semantic_fingerprint()` canonicalizes:

- Observation references;
- all artifact-reference lists by `ref_id`;
- action eligibility by `output_ref`;
- recheck triggers by `id`;
- nested reference arrays;
- JSON object keys.

Equivalent Session payloads with different collection ordering produce the same lowercase SHA-256 fingerprint. The fingerprint supports replay and audit comparison; it is not a digital signature, publisher identity, or external attestation.

## 9. Four distinct validation layers

Verification Session v0.1 deliberately separates four claims:

1. **Session structure valid** — `load_verification_session()` or unified Artifact validation succeeded.
2. **Bindings verified** — `validate_verification_session_bindings()` matched the World State and exact referenced bytes.
3. **Linked artifact semantics verified** — each task, result, control, transition, or discrepancy artifact passed its own validator.
4. **Operational work executed** — tasks, controls, rechecks, evidence retrieval, state materialization, or actions were actually performed by an authorized Runtime.

Success at one layer never implies success at a later layer.

Generic unified validation receives only the Session payload, so a successful report explicitly returns:

```json
{
  "world_state_binding_verified": false,
  "artifact_bindings_verified": false,
  "linked_artifact_semantics_verified": false,
  "tasks_executed": false,
  "controls_evaluated": false,
  "rechecks_executed": false,
  "external_truth_verified": false,
  "world_state_materialized": false,
  "action_authorized": false
}
```

## 10. Fictional example

[`examples/core/verification_session_uav_recheck.json`](../../examples/core/verification_session_uav_recheck.json) binds:

- World State revision 2;
- the fictional GT16 task document;
- a deterministic execution result;
- the fictional UAV State Transition v0.1 record.

It records that continuing without another review is blocked, continuing with active monitoring remains eligible, and a sixty-second temporal-separation recheck trigger is satisfied.

The exact referenced files are:

- [`examples/core/uav_route_crossing_temporal_separation.yaml`](../../examples/core/uav_route_crossing_temporal_separation.yaml)
- [`examples/core/verification_session_uav_execution_result.json`](../../examples/core/verification_session_uav_execution_result.json)
- [`examples/core/state_transition_uav_separation_recheck.json`](../../examples/core/state_transition_uav_separation_recheck.json)
- [`examples/core/world_state_uav_separation_recheck.json`](../../examples/core/world_state_uav_separation_recheck.json)

The example is fictional. It contains no live telemetry, regulatory decision, flight authorization, production recheck, or real-world action.
