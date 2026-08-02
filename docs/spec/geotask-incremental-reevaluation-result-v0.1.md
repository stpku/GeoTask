# GeoTask Incremental Reevaluation Result v0.1

Status: implemented public Artifact  
Artifact ID: `geotask.incremental-reevaluation-result`  
Wrapper: `incremental_reevaluation_result`  
Schema version: `0.1`  
JSON Schema: [`schemas/geotask-incremental-reevaluation-result-v0.1.schema.json`](../../schemas/geotask-incremental-reevaluation-result-v0.1.schema.json)

## 1. Purpose

An Incremental Reevaluation Result is an immutable, bounded record of what happened after one exact Impact Graph was reevaluated against an explicit successor World State. It closes the public audit chain from a base World State, Discrepancy Reports, Correction Requests, and an Impact Graph to node outcomes, reevaluation-target outcomes, acceptance-criterion outcomes, discrepancy resolution, output gates, and action eligibility.

A valid Artifact does **not** itself prove that Core executed a task, discovered impact, generated or materialized the successor World State, released an external output, verified external truth, authorized an action, or executed an action. Generic Artifact validation checks only the authored structure. The separate binding validator checks exact bytes and declared semantics against supplied source objects.

## 2. Public API

```python
from geotask_core import (
    load_incremental_reevaluation_result,
    validate_incremental_reevaluation_result_bindings,
)
```

CLI validation:

```bash
geotask artifact validate geotask.incremental-reevaluation-result \
  examples/core/incremental_reevaluation_result_uav_recheck.json
```

## 3. Exact source bindings

The result binds:

- one immutable base World State;
- one later successor World State with the same `world_state_id` and a greater revision;
- one exact Impact Graph;
- every Correction Request and Discrepancy Report referenced by that graph;
- one or more exact execution results used as reevaluation evidence.

Every reference carries an instance identity and SHA-256 digest of the exact serialized bytes. `validate_incremental_reevaluation_result_bindings()` requires the supplied byte map to match the declared reference set exactly and rejects stale, substituted, omitted, or additional files. It then strictly reloads every World State, Impact Graph, Correction Request, Discrepancy Report, and execution result from those bytes and requires the reloaded objects to equal the separately supplied objects. This prevents an object from one source being combined with the hash-valid bytes of another.

The successor reference additionally carries its semantic fingerprint. This separates byte identity from World State semantics and prevents a result from silently pointing to a different snapshot with the same display name. Bound reevaluation executions must finish after successor materialization and no later than result recording, preserving the causal order `successor snapshot → reevaluation → result`.

## 4. Node results

`node_results` covers every Impact Graph node exactly once. Supported result states are:

| State | Meaning |
|---|---|
| `preserved` | the previous and current values are equal |
| `recomputed` | a bounded value or assertion was recomputed |
| `resolved` | a discrepancy, criterion, or review requirement was resolved |
| `invalidated` | the previous value is no longer present or valid |
| `released` | an output node passed its declared release gates |
| `eligible` | an action node may proceed to separate external authorization |
| `blocked` | the node remains blocked |
| `failed` | reevaluation failed |
| `unknown` | the result cannot yet be determined |

World State path results are checked against the exact base and successor snapshots. Correction-change results are checked against the target paths and operations declared by the bound Correction Request. Recomputed assertion nodes must bind exactly one matching assertion check in the supplied execution results.

## 5. Target results

`target_results` covers every `reevaluation_target` in the Impact Graph exactly once. A target points to its graph node and one node result, must cite the exact Impact Graph in `basis_refs`, and preserves the graph target identity. A completed target must reference a completed node outcome; blocked, failed, and unknown targets must reference matching node states. `not_required` is valid only when the graph target was already not required and the node result was preserved.

Target coverage is separate from graph-node coverage. This prevents a result from claiming that the graph was handled while silently skipping a declared reevaluation target.

## 6. Acceptance criteria

`acceptance_results` covers every acceptance criterion from every bound Correction Request exactly once. The binding validator evaluates the declared criterion against supplied objects:

- `path_equals` compares the successor path with the declared value;
- `path_absent` requires the successor path to be absent;
- `path_recomputed` requires both the correction-change node and World State path node to be recomputed;
- `artifact_valid` requires the bound successor World State to pass the strict public loader and fingerprint binding;
- `discrepancy_resolved` requires the corresponding discrepancy outcome to be resolved;
- `recheck_completed` requires the affected output node to be released and its graph target to be completed;
- `human_reviewed` requires a resolved review-requirement node.

The authored `satisfied` or `failed` state must equal the evaluated state. Writing `satisfied` in JSON is not sufficient. Each acceptance result must cite its Correction Request and explicitly reference every supporting graph-node and reevaluation-target result used by the criterion; supporting outcomes cannot exist only elsewhere in the document.

## 7. Discrepancy results

`discrepancy_results` covers every local discrepancy reference in every Correction Request exactly once. A resolved discrepancy must have a matching resolved discrepancy node in the Impact Graph. For World State subject paths, the successor value must agree with the observed value and must not retain the stale discrepant expected value.

## 8. Successor-state confinement

The binding validator compares flattened object and relation leaves between the base and successor World States. Every changed leaf must fall under a path explicitly requested by a Correction Request. All immutable paths inherited from the bound Discrepancy Reports must remain unchanged.

This is a fail-closed successor-state check. It does not apply a patch or generate the successor. It validates a successor that has already been authored or materialized elsewhere.

## 9. Output and action gates

`output_gates` covers every output blocked by the bound Correction Requests. A released output requires:

- a matching Impact Graph output node with node result `released`;
- only completed reevaluation targets for that exact output;
- every acceptance result from the gating Correction Request;
- all linked acceptance results to be satisfied.

Blocked and unknown gates must likewise identify matching node states and an explicit blocked, failed, or unknown target/criterion cause.

`action_gates` covers every action blocked by the requests. An eligible action must include every output gate from the same Correction Request, all of those outputs must be released, and all request acceptance results must be satisfied. In v0.1, `authorized` and `executed` are always `false`. Eligibility is only a Core-level handoff state; authorization and execution remain responsibilities of an external Runtime or human authority.

## 10. Aggregate state and next action

The result state is derived from contained outcomes:

- any failed node, target, or criterion produces `failed`;
- any blocked gate, blocked outcome, or unresolved discrepancy produces `blocked`;
- mixed successful and unknown outcomes produce `partial`;
- only unknown outcomes produce `unknown`;
- otherwise the result is `completed`.

`completed` requires `next_action=none`. Partial or failed results require `continue_reevaluation`. Unknown results require `request_evidence` or `human_review`. Blocked results cannot declare `none`.

## 11. Example

[`examples/core/incremental_reevaluation_result_uav_recheck.json`](../../examples/core/incremental_reevaluation_result_uav_recheck.json) binds the fictional UAV separation base state, revision-3 successor state, Impact Graph, Discrepancy Report, Correction Request, and a reevaluation execution result. It records eight graph-node outcomes, two completed targets, five satisfied acceptance criteria, one resolved discrepancy, one released output, and one eligible but unauthorized and unexecuted action.

The example demonstrates the intended distinction:

```text
output released
→ action eligible
→ external authorization still required
→ action not executed by GeoTask Core
```

## 12. Explicit non-capabilities

Incremental Reevaluation Result v0.1 does not:

- discover impact;
- generate an Impact Graph;
- execute reevaluation;
- call a model or provider;
- apply Correction Request changes;
- generate or materialize a successor World State;
- retrieve external evidence;
- prove external truth;
- release an output in a production system;
- authorize an action;
- execute an action.
