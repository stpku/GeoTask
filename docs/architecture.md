# GeoTask Core Architecture

## 1. Product Role

GeoTask is an explicit and verifiable spatiotemporal world model for AI agents.

```text
multimodal models and external systems observe the world
→ GeoTask represents objects, relations, state, evidence, and constraints
→ local providers verify world claims and maintain uncertainty/conflict
→ new observations update the affected world state
→ controls derive current action eligibility
```

The public Core does not replace a multimodal model, sensor stack, map platform, simulator, or production-control system. It provides public state specifications and interface contracts, a deterministic verification kernel, provenance, control semantics, identity-governance proposals, and the Artifact foundation used by Agents, external Runtimes, and Domain Packs.

"A verifiable spatiotemporal task protocol" remains correct as the current implementation form. Error detection, correction, and action gating are maintenance capabilities of the broader world model, not the complete product definition.

## 2. Four Architectural Planes

```text
┌────────────────────────────────────────────────────────────┐
│ 1. Perception and open-reasoning plane                      │
│ Models, sensors, maps, and systems produce observations    │
└─────────────────────────────┬──────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ 2. Explicit spatiotemporal world-state plane               │
│ Objects, identity, CRS, time, state, relations, evidence   │
└─────────────────────────────┬──────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ 3. Verification and state-evolution plane                   │
│ Operators, rules, providers, discrepancy, transition      │
└─────────────────────────────┬──────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ 4. Control and real-world action plane                      │
│ Eligibility, block, evidence, review, authorized action    │
└────────────────────────────────────────────────────────────┘
```

GeoTask Core currently implements foundational plane-2 specifications and interface contracts, including moving objects and discrete trajectories, Observation v0.1, World State v0.1, bounded Observation Merge v0.1 with caller-declared semantic-equality consolidation and complete explicit precedence for claims targeting the same path, State Transition v0.1 snapshot bindings, Verification Session v0.1 audit snapshots, Discrepancy Report v0.1 bounded-difference records, Correction Request v0.1 successor-state correction contracts, Impact Graph v0.1 source-bound impact DAGs, Recompute Derivation Result v0.1 source-bound deterministic value derivation, World State Materialization Result v0.1 bounded successor generation, and Incremental Reevaluation Result v0.1 bounded outcome records. Plane 3 now also contains trajectory identity candidates, exact-bound Trajectory Identity Adjudication, review-only Identity Merge Proposal Artifacts, non-executing Identity Merge Approval Records, bounded Object Graph Change Requests, and non-applying Object Graph Change Application Approval Records. The deterministic baseline and Provider assurance remain separate from plane-4 read-only control semantics. Automatic diff computation, bounded object-graph change application and application-result generation after approval, general object-graph mutation, resolution of ambiguous claims without a declared policy, expansion of the bounded derivation method registry, and automatic impact discovery and propagation execution remain target abstractions. External Runtimes and Domain Packs provide connectors, industry policy, predictive models, authoritative data, human review, approvals, and production actions.

## 3. Implemented Architecture

### 3.1 Deterministic execution kernel

The base execution path remains intentionally simple and reproducible:

```text
Document
→ parse
→ Canonical IR
→ validate
→ execute
→ GeotaskResult
```

#### Parse

Raw YAML is loaded with strict duplicate-key handling and structural checks. Version detection distinguishes legacy documents from native v1 documents.

Modules:

- `geotask_core.parser`
- `geotask_core.runner`

#### Canonicalize

Input is converted into one `CanonicalDocument`. Legacy aliases are normalized before downstream processing. The Canonical IR is the single source consumed by validation and execution.

Modules:

- `geotask_core.v1.canonicalizer`
- `geotask_core.v1.ir`
- `geotask_core.v1.enums`

#### Validate

Validation covers document identity, object structure, operator arity, references, execution order, output contracts, shared spatial contracts, extension profiles, provenance, and dependency consistency.

Modules:

- `geotask_core.v1.validator`
- `geotask_core.v1.extension_profiles`
- `geotask_core.v1.provenance`
- `geotask_core.v1.output_contract`

#### Execute

Assertions are dispatched through registered operator contracts. The public deterministic baseline currently covers fourteen operators:

```text
distance_2d
point_to_line_distance_2d
line_intersects_rect
rect_contains_point
point_in_polygon
polygon_contains_point
multi_polyline_intersects_rect
time_overlap
altitude_overlap
trajectory_duration_seconds
trajectory_segment_metrics
trajectory_segment_classifications
trajectory_segment_acceleration_estimates
trajectory_identity_candidate
```

Modules:

- `geotask_core.v1.operator_contracts`
- `geotask_core.v1.executor`
- `geotask_core.ops`

#### Result

Each assertion becomes a `CheckResult`; all checks are aggregated into `GeotaskResult` with execution state, overall state, outputs, evidence references, and assurance metadata.

Modules:

- `geotask_core.v1.result`
- `geotask_core.v1.assurance`

### 3.2 Trust and control layer

The execution kernel answers deterministic assertions. The trust and control layer determines how those results may be used.

```text
Execution Result
+ explicit state
+ evidence/control profile
→ Control Evaluation
→ eligible / blocked / evidence required / conflicted
```

Implemented capabilities include:

- versioned control extension profiles;
- a finite control-expression language;
- three-valued and fail-closed control evaluation;
- explicit `blocked_outputs`, `resume_when`, and `next_action` semantics;
- strict source, evidence-binding, digest, timestamp, and audit metadata;
- read-only evidence recovery after a named resume condition becomes true.

Modules:

- `geotask_core.v1.control_expressions`
- `geotask_core.v1.control_evaluation`
- `geotask_core.v1.provenance`
- `geotask_core.v1.agent_integration`

A structurally valid Artifact is not automatically an approved operational result. Callers must inspect its workflow state, blocked outputs, evidence state, and action boundary.

### 3.3 Agent verification loop

The public Agent integration has already moved beyond a single execution call:

```text
model-generated draft
→ strict preparation
→ mechanical repair where allowed
→ structured revision request
→ bounded-path revision verification
→ retry preparation
→ local deterministic execution
→ control evaluation
→ evidence recovery when explicitly resumable
```

Modules:

- `geotask_core.v1.agent_generation`
- `geotask_core.v1.agent_artifacts`
- `geotask_core.v1.agent_integration`

The preparation layer never invents coordinates, evidence, object references, operators, domain rules, or authorizations. Mechanical fixes are limited to protocol-level repairs. A revision is accepted only when changed paths remain within the generated request and immutable paths remain untouched.

This is the implemented foundation of the future verification cycle. It is not yet a single first-class `VerificationSession` object.

### 3.4 Artifact and Schema plane

GeoTask publishes versioned machine-readable Artifacts instead of relying on undocumented in-memory coupling.

Implemented Artifacts include:

- task documents, execution results, and control evaluations;
- Observation, World State, Observation Merge Result, and State Transition;
- Verification Session, Discrepancy Report, Correction Request, and Impact Graph;
- Recompute Derivation Result, World State Materialization Result, and Incremental Reevaluation Result;
- Verification Provider Descriptor, Verification Request, Verification Response, and Assurance Profile;
- Trajectory Identity Adjudication, Identity Merge Proposal, Identity Merge Approval Record, Object Graph Change Request, and Object Graph Change Application Approval Record;
- Agent preparation, revision, retry, and evidence-recovery reports;
- Runtime descriptors, requests, and responses;
- Core benchmark and Artifact validation reports.

The Artifact Registry provides stable IDs, Schema IDs, versions, producer guidance, validation commands, and IDE file patterns. The installed Schema Bundle allows offline validation and integrity verification.

Modules:

- `geotask_core.v1.artifact_registry`
- `geotask_core.v1.artifact_validation`
- `geotask_core.v1.schema_bundle`
- `geotask_core.v1.serialized_validation`

### 3.5 Runtime boundary

The Runtime Interface separates public verification contracts from private execution infrastructure.

```text
Runtime Descriptor
→ offline request preflight
→ explicit submission by caller
→ Runtime Response
→ three-way contract validation
```

Core does not resolve credentials, discover private services, retry external calls, invoke hosted models by default, fetch evidence, or perform production actions.

Module:

- `geotask_core.v1.runtime_interface`

External adapters may implement model calls or other operations, but their outputs remain bound to declared Artifact contracts, authorization references, side-effect classes, audit capabilities, and truthfulness constraints.

### 3.6 Public conformance and performance gate

The public Core benchmark executes fixed fictional cases through production parsing, canonicalization, validation, execution, and result serialization. It covers all fourteen deterministic operators, including discrete trajectory duration, adjacent-segment metrics, caller-declared segment classifications, bounded scalar acceleration estimates, and boundary-sample identity candidates, replay hashes, result round trips, and evidence propagation.

Modules:

- `geotask_core.v1.core_benchmark_contract`
- `geotask_core.v1.core_benchmark_cases`
- `geotask_core.v1.core_benchmark`
- `geotask_core.v1.core_benchmark_report`
- `geotask_core.v1.core_benchmark_cli`

Performance values are local regression observations only. They are not cross-hardware rankings, production service levels, or model-quality measurements.

## 4. Current End-to-End Flows

### 4.1 Direct deterministic execution

```text
Task Document
→ Canonical IR
→ Validation
→ Local Operators
→ Execution Result
```

### 4.2 Evidence-gated decision

```text
Task Document
→ Execution Result
→ Control Context
→ Control Evaluation
→ eligible / blocked / request evidence
```

### 4.3 Agent correction and retry

```text
Model Draft
→ Preparation Report
→ Revision Request
→ Bounded Revision
→ Revision Verification
→ Retry Report
→ Deterministic Result
```

### 4.4 Evidence recovery

```text
Blocked Result
→ declared evidence request
→ supplied evidence state
→ resume-condition evaluation
→ affected deterministic assertion rerun
→ final control evaluation
```

### 4.5 Identity governance proposal, approval, change request, and application approval

```text
Trajectory identity candidate
→ exact-bound Provider evidence adjudication
→ caller selects one existing canonical subject
→ bounded Identity Merge Proposal
→ explicit decision for every required proposal-approval role
→ Identity Merge Approval Record
→ exact-bound Object Graph Change Request
→ one closed subject_ref rewrite + retained alias + rollback plan
→ explicit decision for every caller-declared application-approval role
→ Object Graph Change Application Approval Record
→ later bounded application Artifact may become eligible
```

These flows are implemented independently. Users currently assemble them through related Artifacts and CLI commands. The identity-governance flow now records proposal approval, derives one bounded change request with preconditions and acceptance criteria, and records application-approval completion. It still stops before Core application authorization, object-graph mutation, `subject_ref` rewrite, World State update, publication, authorization, or execution.

## 5. Target Evolution: Verifiable World-State Cycle

The next architectural step is an upward world-state composition layer, not a rewrite of the execution kernel.

```text
Observation
→ bounded Observation Merge
→ successor World State
→ State Transition record
→ relation and claim verification
→ discrepancy / uncertainty detection
→ bounded correction or evidence request
→ state transition
→ affected-claim analysis
→ incremental recheck
→ action eligibility
→ next observation
→ repeat
```

Observation v0.1 carries source-bound, timestamped world claims with producer identity, evidence references, declared uncertainty, validity windows, and optional supersession links. Its validation does not verify truth or update a World State.

World State v0.1 is implemented as a public world-model Artifact. It records one versioned, point-in-time snapshot of objects, attributes, relations, validity, uncertainty, and closed Observation/Evidence references. Its validation does not ingest Observations, fetch evidence, verify external truth, materialize a later state, rerun tasks, or change action eligibility.

Observation Merge Result v0.1 is implemented as the bounded snapshot-update contract. It binds exact base World State, Observation, and successor bytes; requires a complete explicit mapping from every Observation claim to an existing attribute or relation; supports only caller-declared `require_equal` consolidation or complete `explicit_precedence` when multiple claims target the same path; and deterministically emits one canonical successor revision with an auditable resolution record. It does not infer identity, create missing objects or relations, invent precedence, rank sources, resolve an undeclared ambiguous conflict, calculate a State Transition, verify external truth, release outputs, or authorize action.

State Transition v0.1 is implemented as a public audit Artifact. It binds an earlier and later World State by ID, revision, snapshot time, and deterministic semantic fingerprint, then records Observation-supported object, attribute, relation, and action-eligibility changes using identity-based paths. Core can validate those bindings against two loaded snapshots, but it does not calculate the diff, apply the declared changes, materialize a state, verify truth, rerun tasks, or authorize action.

Verification Session v0.1 is implemented as an immutable audit snapshot. It binds one World State semantic fingerprint to exact serialized task, execution-result, control-evaluation, State Transition, and Discrepancy Report references, then records action eligibility and recheck triggers. Core can verify the state binding and raw artifact SHA-256 digests, but linked artifact semantics and operational execution remain separate validation layers.

Discrepancy Report v0.1 is implemented as a public bounded-difference Artifact. It binds one World State and exact source bytes, records kind-specific expected/observed values, declares affected paths, assertions, outputs, and actions, and separates mutable from immutable correction scope. Core validates those declarations and bindings but does not compare sources, propagate impact, create a Correction Request, apply correction, materialize state, rerun tasks, or authorize action.

Correction Request v0.1 is implemented as a public successor-state contract. It binds one immutable base World State and exact Discrepancy Reports, constrains requested changes to mutable identity paths, preserves immutable paths, defines operation-specific acceptance criteria, requires a later World State revision, and keeps affected outputs/actions blocked. Core validates structure and explicit bindings but does not edit the base state, apply changes, materialize a successor, evaluate acceptance criteria, release outputs, or authorize action.

Impact Graph v0.1 is implemented as a public impact-topology contract. It binds one World State and exact Discrepancy Report/Correction Request bytes, resolves source entities, and represents discrepancies, correction changes, state paths, assertions, outputs, actions, and reevaluation targets as a finite directed acyclic graph. Core validates roots, reachability, cycles, reference closure, aggregate state, and key edge semantics against the bound source Artifacts. It does not discover dependencies, execute propagation, apply corrections, materialize a successor state, run reevaluation, release outputs, or authorize action.

Incremental Reevaluation Result v0.1 is implemented as the public bounded-outcome contract for that graph. It binds exact base and successor World States, the Impact Graph, Correction Requests, Discrepancy Reports, and execution results; covers every graph node and reevaluation target; evaluates request acceptance criteria; records discrepancy resolution; confines successor changes to requested paths; preserves immutable paths; and closes output and action gates. An output may be recorded as released and an action as eligible, but Core still forces action authorization and execution to remain false. The contract validates an already-authored result and does not execute reevaluation or generate the successor snapshot.

Recompute Derivation Result v0.1 implements the deterministic value step before materialization. It binds one exact base World State, one required Correction Request, and exact Observation/GeoTask Document bytes; covers every request `recompute` change exactly once; resolves named inputs through exact JSON Pointers; and evaluates only `copy_input`, numeric `subtract`, or `interval_gap_minus_delay_seconds`. It never evaluates arbitrary code, fetches evidence, calls a model or Provider, mutates state, runs reevaluation, releases outputs, verifies external truth, or authorizes actions.

World State Materialization Result v0.1 and `materialize_successor_world_state()` implement the bounded generation step between Correction Request and reevaluation. Core strictly validates request bindings, applies only the declared add/replace/remove values plus an explicit recompute-value map, emits a new immutable World State revision, and binds exact base/request/successor bytes. It does not merge new Observations, expand provenance, execute reevaluation, release outputs, verify external truth, or authorize actions.

Remaining planned public abstractions:

| Planned abstraction | Purpose | Reuses existing capability |
|---|---|---|
| `VerificationProvider` | Describe deterministic operators, rule engines, local predictive models, authoritative data, and human review | operator contracts and Runtime descriptors |

These names describe the target architecture only. They are not yet implemented public APIs and must not be presented as completed capabilities until code, Schemas, tests, and release notes exist.

## 6. World-State Updates Without a Streaming Platform

Core does not need to embed Kafka, a stream processor, or a real-time database to support explicit world-state evolution.

The intended public interaction is snapshot based:

```text
initial WorldState
→ auditable VerificationSession
→ new Observation
→ bounded Observation Merge
→ successor WorldState
→ StateTransition
→ impact analysis
→ local recheck
→ updated WorldState and action eligibility
```

The public CLI now exposes two high-level, read-only bundle checks:

```text
geotask verify <verification-session.json> \
  --state <world-state.json> \
  --observation <observation.json> ... \
  --bind <ref-id>=<artifact-file> ...

geotask recheck <incremental-reevaluation-result.json> \
  --bind <ref-id>=<artifact-file> ...
```

`geotask verify` strictly validates one already-authored Verification Session,
its bound World State, the exact declared Observation set, and every referenced
registered Artifact before checking the Session's World State fingerprint and raw
content hashes. `geotask recheck` strictly validates one already-authored
Incremental Reevaluation Result and its complete base/successor World State,
Impact Graph, Correction Request, Discrepancy Report, and execution-result bundle
before checking the declared outcome semantics and exact byte bindings.

Both calls remain local, explicit, reproducible, and fail closed on missing,
duplicate, extra, semantically invalid, or hash-mismatched inputs. They produce
command reports rather than new normative Artifacts. They do not ingest a live
stream, infer identity, invent a conflict policy, resolve an undeclared ambiguous
conflict, discover impact, execute a task or control profile, perform reevaluation,
materialize a state, release an external output, authorize an action, or execute
an action. Long-running
observation delivery, storage, monitoring, and external action remain Runtime
responsibilities.

GT16 demonstrates the intended semantics today through a fictional static replay: an initial WorldState contains a 120-second separation; a new telemetry Observation records a 40-second delay; the predicted relation changes to 80 seconds; the system preserves still-valid spatial findings, invalidates the assumption of permanent safety, and keeps action eligibility behind a 60-second recheck threshold.

## 7. Assurance Model

The current compatibility field is a single ordered `AssuranceLevel`:

| Level | Meaning |
|---|---|
| `unverified` | no verification |
| `model_generated` | model-produced and unchecked |
| `model_self_checked` | checked only by the same model |
| `local_deterministic` | verified by a local deterministic operator |
| `model_local_agreement` | model and local result agree |
| `independent_cross_verified` | independent verification recorded |
| `human_reviewed` | human review recorded |

This ordering remains useful for compatibility but does not capture every future trust dimension. Local predictive models, stale evidence, calibration, reproducibility, independent verification, and human review are not interchangeable.

A future multidimensional assurance profile should add explicit fields such as source, method, reproducibility, independence, evidence freshness, calibration identity, and human review while retaining the current level as a compatibility summary.

## 8. Dependency Direction

Dependencies flow inward toward data contracts and deterministic primitives:

```text
CLI / runner / Agent integration / Runtime interface
  → Artifact and control services
  → parser / canonicalizer / validator / executor
  → operator contracts / IR / enums / deterministic ops
```

Key rules:

- `ir.py` and `enums.py` are leaf contracts;
- deterministic operators do not call models or networks;
- Core never imports private Runtime orchestration or Domain Packs;
- Artifact validation does not repeat production actions;
- control evaluation does not execute `next_action`;
- Agent repair does not invent missing domain facts;
- Runtime submission is explicit and remains outside normal validation.

## 9. Public and Private Boundary

Public Core contains:

- language and Artifact contracts;
- Canonical IR;
- deterministic spatial and temporal operators;
- validation and result assembly;
- provenance and evidence bindings;
- control evaluation;
- Agent preparation, bounded revision, retry, and evidence recovery;
- Artifact Registry and offline Schema Bundle;
- Runtime message contracts and fail-closed reference behavior;
- conformance and local regression benchmarks.

External Runtime or Domain Packs contain:

- multimodal model inference;
- customer or regulatory data;
- authoritative data connectors;
- local predictive-model serving;
- industry-specific rules and calibration;
- identity, credentials, authorization, and audit infrastructure;
- human-review operations;
- production actions and long-running monitoring.

This boundary allows GeoTask to become a verification and correction layer without turning the public Core into a hosted model platform or an operational control system.
