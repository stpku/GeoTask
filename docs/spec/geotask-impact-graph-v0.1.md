# GeoTask Impact Graph v0.1

Status: public experimental contract for the v0.5 Verifiable World-State Cycle.

An Impact Graph is an immutable, source-bound description of how one confirmed or potential change may affect World State paths, assertions, outputs, actions, bounded corrections, and later reevaluation work. It converts the local impact declarations embedded in Discrepancy Reports and Correction Requests into one explicit directed graph that can be inspected and validated before any incremental reevaluation is attempted.

A valid Impact Graph does **not** discover impact, execute propagation, apply a correction, materialize a successor World State, rerun a task, evaluate a target, release an output, verify external truth, or authorize an action.

## 1. Stable identity

- Artifact ID: `geotask.impact-graph`
- Wrapper: `impact_graph`
- Schema version: `0.1`
- JSON Schema: [`schemas/geotask-impact-graph-v0.1.schema.json`](../../schemas/geotask-impact-graph-v0.1.schema.json)
- Python loader: `load_impact_graph(payload)`
- Binding validator: `validate_impact_graph_bindings(graph, world_state, discrepancy_reports, correction_requests, artifact_contents)`
- Unified validation: `geotask artifact validate geotask.impact-graph <impact-graph.json>`

The Registry descriptor intentionally has no generation command. Impact analysis must be performed explicitly by an Agent or Runtime. Core validates the submitted graph and its exact bindings; it does not infer missing dependencies.

## 2. Bound source snapshot and Artifacts

Every graph binds one immutable World State using:

- `world_state_id`;
- `revision`;
- `as_of`;
- semantic fingerprint;
- exact raw-byte SHA-256 digest.

Additional `artifact_refs` bind exact Discrepancy Reports, Correction Requests, and optional supporting Artifacts. At least one `geotask.discrepancy-report` is required. Discrepancy Report and Correction Request references are pinned to schema version `0.1`.

Binding validation verifies:

1. World State identity, revision, time, and semantic fingerprint;
2. exact raw bytes for the World State and every referenced Artifact;
3. Discrepancy Report and Correction Request instance identity;
4. every report and request binding to the same World State snapshot;
5. graph recording time not preceding any bound report or request;
6. every declared source entity against the exact bound Artifact.

Exact-byte binding identifies serialized inputs. It does not prove their external truth or independently validate every supporting Artifact's semantics.

## 3. Source entities

`entity_refs` create stable local identities for entities contained inside bound Artifacts:

| Kind | Source Artifact | Resolved entity |
|---|---|---|
| `discrepancy` | Discrepancy Report | one discrepancy finding |
| `correction_change` | Correction Request | one requested change |
| `acceptance_criterion` | Correction Request | one acceptance criterion |
| `review_requirement` | Correction Request | one review requirement |

Entity-backed nodes must use the local entity reference as their `identity`. This prevents graph nodes from silently pointing to similarly named entities in another report or request.

## 4. Node model

Impact Graph v0.1 supports these node kinds:

- `world_state_path`;
- `discrepancy`;
- `correction_change`;
- `acceptance_criterion`;
- `review_requirement`;
- `assertion`;
- `output`;
- `action`;
- `artifact`.

Every node records:

- stable local `id`;
- kind and identity;
- impact state;
- reason;
- one or more exact Artifact basis references;
- an entity reference when the node is backed by a source entity.

Node identities are unique within each kind. World State path nodes use identity-based JSON Pointers rather than array indexes. Artifact nodes identify an exact declared `artifact_ref`.

Supported node states are:

| State | Meaning |
|---|---|
| `root` | declared source of graph propagation |
| `affected` | downstream item is affected |
| `blocked` | output or action remains blocked |
| `requires_recheck` | assertion or output must be reevaluated |
| `unknown` | impact cannot yet be determined |

Only nodes listed in `root_node_refs` may use `root`, and every declared root must use it. Root state is limited to discrepancy, correction-change, World State path, or Artifact nodes. A blocked node must be an output or action; `requires_recheck` is limited to assertion or output nodes. Entity-backed nodes must include their exact source Artifact in `basis_refs`.

## 5. Directed acyclic graph

Edges form a finite directed acyclic graph. v0.1 rejects:

- self loops;
- duplicate edge identities;
- duplicate kind/source/target triples;
- cycles;
- nodes not reachable from a declared root;
- incoming edges to declared root nodes;
- unresolved node or Artifact references.

Supported edge kinds are:

| Kind | Declared meaning |
|---|---|
| `changes` | a Correction Request change targets a World State path |
| `invalidates` | a discrepancy invalidates a subject or declared impact target |
| `affects` | one affected item propagates impact to another |
| `blocks` | an assertion or output blocks an output or action |
| `requires` | a discrepancy requires a correction change, or a change/review requires a criterion |
| `requires_recheck` | an affected item requires an assertion or output reevaluation |
| `guards` | an acceptance criterion guards release of an output or action |

Edge state is `confirmed`, `potential`, or `unknown`. Every edge must share at least one declared basis reference with both its source and target nodes. Confirmed edges cannot connect unknown nodes. A structural graph may declare potential or unknown propagation, but it may not promote such edges to confirmed without a source basis.

## 6. Binding-level semantic checks

`validate_impact_graph_bindings()` resolves graph nodes and checks important edge shapes against the bound source Artifacts:

- `changes` must be `correction_change → world_state_path`, and the path must exactly equal the request change target;
- `invalidates` must start from a discrepancy and target that finding's subject, affected path, assertion, output, action, or basis Artifact;
- `requires` from discrepancy to correction change must resolve through the Correction Request's local discrepancy reference to the same report and finding;
- `requires` from correction change to acceptance criterion must use a criterion named by that change and the same Correction Request;
- review requirement and human-review criterion roles and source requests must match;
- `affects` is limited to path/artifact propagation into paths, assertions, outputs, or actions, plus assertion-to-output/action and output-to-action propagation;
- `blocks` must originate from a discrepancy, assertion, or output and terminate at an explicitly blocked output or action;
- `requires_recheck` must originate from a path, discrepancy, correction change, or Artifact and terminate at a `requires_recheck` or blocked assertion/output node;
- `guards` must bind one acceptance criterion to an output or action gated by the same Correction Request;
- source-entity edges must include the exact bound Discrepancy Report or Correction Request references in their edge bases;
- affected paths, assertions, outputs, and actions must be grounded in bound reports or requests;
- blocked and recheck targets must be declared by the bound source Artifacts.

This is validation of an already assembled graph. It is not automatic dependency discovery, static program analysis, or execution tracing.

## 7. Reevaluation targets

`reevaluation_targets` identify the work whose outcomes may be recorded by an Incremental Reevaluation Result v0.1 Artifact. Each target records:

- the graph node to reevaluate;
- state: `required`, `blocked`, `not_required`, or `unknown`;
- input node references;
- prerequisite node references;
- exact Artifact basis references;
- a reason.

Input and prerequisite nodes must be strict ancestors of the target node and the two sets must be disjoint. Target state must agree with node state: `blocked` targets point to blocked nodes, `required` targets point to affected or `requires_recheck` nodes, `unknown` targets point to unknown nodes, and `not_required` cannot conceal blocked, unknown, or recheck-required nodes. A blocked target must name at least one prerequisite. These rules ensure the target's declared dependency chain is represented in the DAG rather than written only in prose.

Impact Graph validation does not execute a target. A future Reevaluation Result must separately prove which target was run, which exact inputs were used, and what result was produced.

## 8. Output and action gates

`blocked_outputs` and `blocked_actions` must exactly enumerate all output and action nodes with `impact_state=blocked`; each listed item must have a matching blocked graph node, and no blocked node may be omitted.

This prevents a graph from claiming a blocked operational result without representing it in the propagation chain or from hiding a blocked node outside the top-level gate inventory. Conversely, writing a blocked node or edge does not itself enforce a production system gate. Runtime control and authorization remain external.

## 9. Aggregate graph state

v0.1 defines four graph states:

| State | Contract rule |
|---|---|
| `mapped` | no potential, unknown, or blocked impact remains |
| `partial` | at least one potential or unknown node, edge, or target exists, with no blocked target |
| `blocked` | at least one blocked target, output, or action exists |
| `unknown` | every reevaluation target is unknown and none is blocked |

The aggregate state is checked against the detailed graph. It cannot be used to conceal a blocked or unknown node.

## 10. Deterministic semantic fingerprint

`ImpactGraph.semantic_fingerprint()` canonicalizes:

- Artifact references by `ref_id`;
- entity references, nodes, edges, and reevaluation targets by `id`;
- root, basis, input, prerequisite, blocked-output, and blocked-action arrays;
- JSON object keys.

Equivalent graphs with different collection ordering produce the same lowercase SHA-256 fingerprint. The fingerprint is not a signature, authority statement, proof of graph completeness, or proof that propagation was executed.

## 11. Validation layers

Impact Graph v0.1 separates:

1. **Graph structure valid** — strict loading or unified Artifact validation succeeded.
2. **World State and Artifact bindings verified** — identity and exact raw bytes matched.
3. **Source entities and edge semantics verified** — graph references matched report/request contents.
4. **Impact computed or propagation executed** — an explicit analysis or engine traversed dependencies.
5. **Corrections applied and successor state materialized** — a separate authorized workflow produced a new snapshot.
6. **Reevaluation executed** — affected assertions and outputs were rerun against exact inputs.
7. **outputs released or actions authorized** — external control and authorization permitted operational use.

Generic unified Artifact validation receives only the graph payload. It therefore explicitly reports false for binding verification, source-entity verification, edge-semantic verification, impact computation, propagation execution, correction application, successor-state materialization, reevaluation execution, output release, external truth, and action authorization.

## 12. Fictional UAV example

[`examples/core/impact_graph_uav_recheck.json`](../../examples/core/impact_graph_uav_recheck.json) binds:

- World State revision 2;
- the corresponding temporal-separation Discrepancy Report;
- the bounded Correction Request.

Its single discrepancy root reaches:

1. two successor-state recomputation changes;
2. the UAV-B delay path;
3. the dependent temporal-separation path;
4. the `temporal_conflict` assertion;
5. the blocked `continue_route_without_recheck` output;
6. the blocked `automatic_route_continuation` action.

The graph declares two reevaluation targets: the temporal assertion is required, while output release remains blocked until the correction changes and assertion recheck complete.

The example is fictional. It contains no live telemetry, real flight authorization, executed correction, successor World State, completed reevaluation, released output, or real-world action.
