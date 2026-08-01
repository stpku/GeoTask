# GeoTask Core Architecture

## 1. Product Role

GeoTask is the spatiotemporal error-detection, correction, and action-gating layer between open multimodal reasoning and local verification.

```text
multimodal model proposes
→ GeoTask structures the claim
→ local spatial/temporal methods verify it
→ discrepancies become bounded correction requests
→ controls decide whether an output is eligible, blocked, or waiting for evidence
```

The public Core does not replace a multimodal model, fetch real-world evidence, or execute production actions. It provides the public contracts and local deterministic baseline used by Agents, external Runtimes, and Domain Packs.

The original definition—"a verifiable spatiotemporal task protocol"—remains correct as the implementation form. The broader system value is the verification loop built on top of that protocol.

## 2. Four Architectural Planes

```text
┌────────────────────────────────────────────────────────────┐
│ 1. Open reasoning plane                                    │
│ Multimodal models interpret scenes, propose claims/plans   │
└─────────────────────────────┬──────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ 2. Spatiotemporal task plane                               │
│ Objects, CRS, coordinates, time, altitude, evidence, tasks │
└─────────────────────────────┬──────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ 3. Local verification and correction plane                 │
│ Deterministic operators, validation, comparison, retry     │
└─────────────────────────────┬──────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ 4. Control and action plane                                │
│ Block, request evidence, recheck, review, external action  │
└────────────────────────────────────────────────────────────┘
```

GeoTask Core implements the public contracts for planes 2 and 3 and the read-only control semantics of plane 4. External Runtimes and Domain Packs provide connectors, industry policy, nonlocal models, authoritative data, human review, and production actions.

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

Assertions are dispatched through registered operator contracts. The public deterministic baseline currently covers eight operators:

```text
distance_2d
point_to_line_distance_2d
line_intersects_rect
rect_contains_point
point_in_polygon
multi_polyline_intersects_rect
time_overlap
altitude_overlap
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

- task documents;
- execution results;
- control evaluations;
- Agent preparation, revision, retry, and evidence-recovery reports;
- Runtime descriptors, requests, and responses;
- Core benchmark reports;
- Artifact validation reports.

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

The public Core benchmark executes fixed fictional cases through production parsing, canonicalization, validation, execution, and result serialization. It covers all eight deterministic operators, replay hashes, result round trips, and evidence propagation.

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

These flows are implemented independently. Users currently assemble them through related Artifacts and CLI commands.

## 5. Target Evolution: Verification Cycle

The next architectural step is an upward composition layer, not a rewrite of the execution kernel.

```text
Proposal
→ task materialization
→ local verification
→ discrepancy detection
→ correction request
→ bounded revision
→ affected-assertion analysis
→ incremental recheck
→ action gate
→ new state
→ repeat
```

Planned public abstractions:

| Planned abstraction | Purpose | Reuses existing capability |
|---|---|---|
| `VerificationSession` | Bind proposal, task, results, controls, discrepancies, revisions, and state transitions | Artifact Registry, Agent reports, control evaluation |
| `DiscrepancyReport` | Explain which claim differs, why, impact, mutable scope, and immutable paths | execution result, evaluator, revision request |
| `CorrectionRequest` | Give an Agent an explicit bounded correction contract | Agent preparation and revision verification |
| `ImpactGraph` | Map changed object/state paths to assertions and outputs | object refs, assertion refs, output contracts |
| `ReevaluationResult` | Record preserved, invalidated, and recomputed findings | execution result and control evaluation |
| `Observation` | Carry multimodal observations with source, time, producer, uncertainty, and claim | provenance and evidence binding |
| `VerificationProvider` | Describe deterministic operators, rule engines, local predictive models, authoritative data, and human review | operator contracts and Runtime descriptors |

These names describe the target architecture only. They are not yet implemented public APIs and must not be presented as completed capabilities until code, Schemas, tests, and release notes exist.

## 6. Dynamic Recheck Without a Streaming Platform

Core does not need to embed Kafka, a stream processor, or a real-time database to support continuous verification semantics.

The intended public interaction is snapshot based:

```text
initial state
→ verification snapshot
→ changed state
→ impact analysis
→ local recheck
→ new gate state
```

A future high-level CLI may expose this as:

```text
geotask verify  --proposal ... --task ... --state ...
geotask recheck <verification-session> --state ...
```

Each call should remain local, explicit, reproducible, and Artifact-producing. Long-running monitoring and event delivery remain Runtime responsibilities.

GT16 demonstrates the intended semantics today through a fictional static replay: an initial 120-second separation is verified; a 40-second delay reduces the predicted separation to 80 seconds; the system preserves the still-valid findings, invalidates the assumption of permanent safety, and keeps action eligibility behind a 60-second recheck threshold.

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
