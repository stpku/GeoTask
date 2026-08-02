# GeoTask World State Materialization Result v0.1

Status: implemented public Artifact and bounded Core operation  
Artifact ID: `geotask.world-state-materialization-result`  
Schema version: `0.1`  
JSON Schema: [`schemas/geotask-world-state-materialization-result-v0.1.schema.json`](../../schemas/geotask-world-state-materialization-result-v0.1.schema.json)

## 1. Purpose

World State Materialization Result v0.1 records the deterministic application of one required Correction Request to one immutable base World State. It binds the exact base bytes, the exact Correction Request bytes, and the exact generated successor bytes while recording every applied change and preserving all blocked outputs and actions for later reevaluation.

The public operation is `materialize_successor_world_state()`. It is intentionally narrower than a generic patch engine:

- the base World State must already exist and pass strict loading;
- the Correction Request must already pass its explicit binding validator;
- `add`, `replace`, and `remove` values come only from the request;
- every `recompute` value must be supplied explicitly by change ID;
- Core never guesses, predicts, retrieves, or derives a recomputed value;
- the successor is a new revision and the base snapshot is never modified;
- Observation and Evidence reference sets are preserved in v0.1;
- outputs and actions remain blocked until a separate Incremental Reevaluation Result closes them.

## 2. Operation inputs

`materialize_successor_world_state()` requires:

1. one loaded base `geotask.world-state`;
2. one loaded `geotask.correction-request` in state `required` with `next_action=materialize_successor_state`;
3. all Discrepancy Reports and exact source bytes required by Correction Request binding validation;
4. the exact Correction Request bytes;
5. one JSON-safe value for every `recompute` change, keyed by change ID;
6. explicit successor `as_of`, `materialized_at`, and result `created_at` timestamps.

The operation rejects missing or additional recompute keys. It also rejects non-finite values and any value that cannot be represented safely in JSON.

## 3. Causal time contract

The required order is:

```text
base World State
    → Correction Request
    → successor as_of
    → successor materialized_at
    → materialization result created_at
    → later reevaluation
```

The successor cannot precede the base snapshot or Correction Request. Materialization cannot precede successor `as_of`, and the result cannot precede materialization.

## 4. Identity-based change application

Changes use the same identity-based JSON Pointer profile as Correction Request v0.1. Object and attribute list positions are never used as stable identities. Typical paths are:

```text
/objects/<object-id>/attributes/<attribute-name>/value
/relations/<relation-id>/value
```

The operation applies exactly the request's declared changes:

- `add`: target must not exist; `after` comes from the request;
- `replace`: target must exist and equal `before`; `after` comes from the request;
- `remove`: target must exist and equal `before`; the field is removed;
- `recompute`: target must exist and equal `before`; `after` comes from the caller's explicit `recomputed_values[change_id]`.

Array insertion is not supported in v0.1. Intrinsic identity and provenance fields remain forbidden by the Correction Request contract.

## 5. Successor-state confinement

The generated successor must satisfy the Correction Request output contract:

- same `world_state_id` required by the request;
- revision at least `max(base revision + 1, minimum_revision)`;
- valid World State v0.1 structure and time windows;
- all changed semantic leaf paths contained by requested target paths;
- base Observation and Evidence reference sets preserved exactly;
- blocked outputs and actions preserved for later reevaluation.

A request that introduces new Observation or Evidence references is not materializable by v0.1. That requires a separate Observation-merging and provenance-update operation rather than silently expanding the base snapshot's trust set.

## 6. Result Artifact

The `world_state_materialization_result` wrapper contains:

- `materialization_id`, timestamps, state, and reason;
- exact base World State reference;
- exact Correction Request reference;
- exact successor World State reference;
- one `applied_changes` entry for every request change;
- preserved Observation and Evidence references;
- preserved blocked outputs and actions;
- `next_action=reevaluate_successor_state`;
- explicit operational boundary booleans.

Each applied change copies the request's target path, operation, basis references, Observation references, Evidence references, input fields, and acceptance-criterion references. Its `before` and `after` values must match the exact base and successor snapshots.

## 7. Exact-byte binding validator

`validate_world_state_materialization_result_bindings()` requires exactly three byte entries:

1. base World State;
2. Correction Request;
3. successor World State.

It verifies SHA-256 values, strict-loads all three byte sequences, and requires the parsed objects to equal the separately supplied objects. It then checks complete change coverage, request field copying, before/after values, output-contract compliance, provenance preservation, and path confinement.

A result cannot combine an in-memory object from one source with hash-valid bytes from another.

## 8. Validation layers

The layers are intentionally separate:

1. JSON Schema validation;
2. strict result loading;
3. exact-byte and semantic binding validation;
4. actual Core materialization execution;
5. later incremental reevaluation;
6. output release or action authorization by an external authority.

Generic `geotask artifact validate` receives only the result payload. It therefore reports the following as false:

```text
base_world_state_binding_verified
correction_request_binding_verified
successor_world_state_binding_verified
changes_applied
successor_world_state_materialized
reevaluation_executed
outputs_released
external_truth_verified
action_authorized
action_executed
```

A structurally valid result is not proof that materialization was executed. Execution proof requires the explicit binding validator with the three exact source byte sequences.

## 9. Operational boundaries

World State Materialization v0.1 does **not**:

- discover or author a Correction Request;
- compare source evidence;
- calculate missing recompute values;
- call a model, Provider, sensor, map service, or external API;
- merge new Observations;
- expand the evidence trust set;
- mutate the base snapshot;
- run Impact Graph propagation;
- execute incremental reevaluation;
- evaluate all acceptance criteria;
- resolve a discrepancy by itself;
- release an output;
- verify external truth;
- authorize or execute a real-world action.

The result schema forces `reevaluation_executed`, `outputs_released`, `external_truth_verified`, `action_authorized`, and `action_executed` to `false`.

## 10. Public example

[`examples/core/world_state_materialization_result_uav_recheck.json`](../../examples/core/world_state_materialization_result_uav_recheck.json) records the bounded generation of UAV World State revision 3 from revision 2 and the bound Correction Request. The operation applies two explicit recompute values while preserving route identity, provenance references, the blocked continuation output, and the blocked automatic action.

The exact generated successor is:

[`examples/core/world_state_uav_separation_successor.json`](../../examples/core/world_state_uav_separation_successor.json)

The later Incremental Reevaluation Result consumes that exact successor and remains the separate contract that evaluates targets, acceptance criteria, discrepancy resolution, output release, and action eligibility.
