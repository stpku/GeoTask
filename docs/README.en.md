# GeoTask Documentation

[简体中文](README.md) | **English**

GeoTask documentation is organized from world-model positioning to implemented contracts and future state-evolution extensions. Start with the white paper to understand the explicit and verifiable spatiotemporal world model, then use the specifications and tutorials to distinguish the current public foundation from roadmap abstractions.

## Start here

- [GeoTask White Paper v0.1](whitepaper/GeoTask_White_Paper_v0.1.md) — why agents need an explicit and verifiable spatiotemporal world model, how GeoTask differs from implicit neural world models, and where the current Core foundation ends before first-class state evolution. See the [build guide](whitepaper/README.md) for HTML, DOCX, and PDF commands.
- [White paper English abstract](whitepaper/GeoTask_White_Paper_v0.1.md#english-abstract) — a concise English entry point and terminology map inside the same non-normative white paper.
- [GeoTask Language and Execution Specification v1.0](spec/geotask-language-spec-v1.0.md) — the normative profile implemented by the current public Core.
- [GeoTask Execution Result v1.0](spec/geotask-result-v1.0.md) — the `GeotaskResult.to_dict()` contract, public result JSON Schema, and `geotask result validate` command.
- [GeoTask Observation v0.1](spec/geotask-observation-v0.1.md) — source-bound, timestamped claims with producer identity and declared uncertainty, without claiming truth or automatically updating a World State.
- [GeoTask World State v0.1](spec/geotask-world-state-v0.1.md) — one versioned snapshot of world objects, attributes, relations, validity, uncertainty, and closed Observation/Evidence references, without automatically merging Observations or materializing a later state.
- [GeoTask Observation Merge Result v0.1](spec/geotask-observation-merge-result-v0.1.md) — exact-byte bounded merge of complete explicit Observation claim mappings into existing attributes or relations, producing one canonical successor revision without identity inference, conflict resolution, or State Transition computation.
- [GeoTask State Transition v0.1](spec/geotask-state-transition-v0.1.md) — semantic-fingerprint bindings between before/after World State snapshots and Observation-supported path, relation, and eligibility changes, without calculating diffs, applying patches, or authorizing action.
- [GeoTask Verification Session v0.1](spec/geotask-verification-session-v0.1.md) — one immutable audit snapshot binding a World State to exact-byte task, result, control, transition, eligibility, and recheck references.
- [GeoTask Discrepancy Report v0.1](spec/geotask-discrepancy-report-v0.1.md) — exact World State/source bindings plus explicit discrepancies, downstream impact, and mutable/immutable correction scope without automatically comparing or correcting sources.
- [GeoTask Correction Request v0.1](spec/geotask-correction-request-v0.1.md) — one immutable base World State plus exact Discrepancy Reports, bounded successor-state changes, acceptance criteria, immutable-path preservation, and output/action gates without applying changes.
- [GeoTask Impact Graph v0.1](spec/geotask-impact-graph-v0.1.md) — a source-bound directed acyclic graph linking discrepancies and corrections to affected state paths, assertions, outputs, actions, and reevaluation targets without discovering or executing propagation.
- [GeoTask Recompute Derivation Result v0.1](spec/geotask-recompute-derivation-result-v0.1.md) — exact Observation/GeoTask source-path bindings and allowlisted deterministic methods that close every requested `recompute` value without arbitrary expressions, model calls, or state mutation.
- [GeoTask World State Materialization Result v0.1](spec/geotask-world-state-materialization-result-v0.1.md) — deterministic bounded successor generation from one immutable base state, one bound Correction Request, and explicit recompute values while preserving output/action gates.
- [GeoTask Incremental Reevaluation Result v0.1](spec/geotask-incremental-reevaluation-result-v0.1.md) — exact base/successor World State, Impact Graph, source-file, node, target, acceptance, discrepancy, and gate outcomes without executing reevaluation or authorizing action.
- [GeoTask Artifact Registry v1.0](spec/geotask-artifact-registry-v1.0.md) — `geotask inspect schemas` discovery for all twenty-three public Artifacts, their schemas, versions, and operating commands.
- [GeoTask Artifact Validation v1.0](spec/geotask-artifact-validation-v1.0.md) — one `geotask artifact validate` entry point for validating all twenty-three registered public Artifacts, including Observation, World State, Observation Merge Result, State Transition, Verification Session, Discrepancy Report, Correction Request, Impact Graph, Recompute Derivation Result, World State Materialization Result, Incremental Reevaluation Result, Agent reports, Runtime messages, the Core benchmark report, and validation reports themselves, by stable Artifact ID.
- [GeoTask Versioned Payload Validation v1.0](spec/geotask-versioned-payload-validation-v1.0.md) — shared strict loading, schema metadata, diagnostics, and text/JSON reports for execution and control results.
- [GeoTask Control Extension Profile v1.0](spec/geotask-control-extension-profile-v1.0.md) — versioned validation for evidence requests, evidence conflicts, decision rules, and task gates.
- [GeoTask Control Expression Language v1.0](spec/geotask-control-expression-language-v1.0.md) — the safe finite grammar, three-valued logic, comparison semantics, and public parser/evaluator API.
- [GeoTask Control Evaluation Result v1.0](spec/geotask-control-evaluation-v1.0.md) — read-only binding of assertion results and explicit domain state into gate status, unknown identifiers, and still-blocked outputs.
- [GeoTask Agent Integration Profile v0.1](spec/geotask-agent-integration-profile-v0.1.md) — the four model-neutral tools, mechanical preparation of generated drafts, guarded revision-diff retries, registered Agent report Artifacts, unknown/blocked handling, and deterministic re-execution after evidence recovery.
- [GeoTask Runtime Interface Profile v0.1](spec/geotask-runtime-interface-profile-v0.1.md) — Descriptor, Request, Response, authorization, idempotency, audit, and side-effect boundaries between Core and an external Runtime, plus public-safe HTTP Adapter, loopback Endpoint, provider-neutral model Adapter, and the first OpenAI Responses provider package.
- [GeoTask Core Agent Skill](../skills/geotask-core/SKILL.md) — directly injectable model instructions and safety boundaries for Agent integrations.
- [VS Code Schema association example](../.vscode/settings.json) — binds local GeoTask files to the repository JSON Schema.
- [Quickstart](tutorials/quickstart.md) — install, validate, execute, inspect, and extend a first task.
- [GT01–GT20 Cookbook](cookbook/gt01-gt20.md) — progressive examples from distance calculation to evidence governance, object-specific feasibility, emergency dispatch, equipment capability, and high-risk action gating.
- [v0.3.0 Agent Integration release notes](release_v0_3_0.md) — adds generated-task preparation, guarded revision, evidence recovery, four Agent report Artifacts, and unified validation across eight Artifacts and nine Schemas.
- [v0.2.0 artifact-contract release notes](release_v0_2_0.md) — adds the Artifact Registry, offline Schema Bundle, unified Artifact validation, and validation-report self-validation.
- [v0.1.1 PyPI hotfix release notes](release_v0_1_1.md) — fixes package/runtime version consistency and records clean-environment installation verification.
- [v0.1.0 Public Preview release notes](release_v0_1_0.md) — fixed-version capabilities, assets, and verification status.
- [Public roadmap](../ROADMAP.md) — planned protocol, Core, tooling, and ecosystem directions.
- [中文快速入门](tutorials/quickstart.zh-CN.md) and [中文案例手册](cookbook/gt01-gt20.zh-CN.md).

## Reference

- [Operator Registry](operator_registry.md)
- [Status and Assurance Model](reference/status-model.md)
- [Evidence, Conflict, Blocking, and Recovery](reference/evidence-and-recovery.md)
- [CLI Usage](cli_usage.md)
- [Architecture](architecture.md)
- [Operator Extension Guide](operator-guide.md)
- Machine-readable schemas: [artifact registry](../schemas/geotask-artifact-registry-v1.0.schema.json), [artifact validation report](../schemas/geotask-artifact-validation-v1.0.schema.json), [Agent evidence-recovery report](../schemas/geotask-agent-integration-v0.1.schema.json), [task document](../schemas/geotask-v1.0.schema.json), [execution result](../schemas/geotask-result-v1.0.schema.json), and [control evaluation result](../schemas/geotask-control-evaluation-v1.0.schema.json)

## Specification layers

GeoTask intentionally separates three documentation layers:

1. **Implemented public profile.** `spec/geotask-language-spec-v1.0.md` describes fields and semantics that the current public Core can parse, validate, canonicalize, and execute.
2. **System-level target direction.** [Target Specification Status](spec/target-specification-status.md) explains how broader Runtime, Domain Pack, governance, and future protocol designs relate to the implemented public profile. It is not a statement that every planned feature is already implemented.
3. **Legacy compatibility.** [Format Specification](format_spec.md) and [Legacy YAML Schema](geotask_yaml_schema.md) document earlier `0.x`/`v0.1-lite` formats that remain useful for migration and backward compatibility.

When documents differ, the current source code, tests, implemented v1.0 specification, and machine-readable schema are authoritative for the public Core.

## Design and boundary documents

- [Design Principles](design_principles.md)
- [Evaluation Specification](eval_spec.md)
- [Normalizer v0.2 Design](normalizer_v0_2_design.md)
- [Open Source Boundary](open_source_boundary.md)
- [Open Core / Commercial Runtime Boundary](open_core_commercial_runtime_boundary.md)
- [Product Architecture v0.1](product_architecture_v0_1.md)
- [ADR-001: Core, Runtime, and Domain Pack](architecture_decisions/ADR-001-core-runtime-domain-pack.md)
- [ADR-002: Private Runtime Boundary](architecture_decisions/ADR-002-private-runtime-boundary.md)
- [ADR-003: Domain Pack Contract](architecture_decisions/ADR-003-domain-pack-plugin-contract.md)
- [ADR-004: Patent and Open Source Boundary](architecture_decisions/ADR-004-patent-and-open-source-boundary.md)

## Public and private boundary

The public repository defines general-purpose task representation, deterministic operators, validation, result assurance, examples, and conformance tests. Industry rules, customer data, approval thresholds, model credentials, commercial routing, and patent-sensitive optimization remain outside the public Core. See [ADR-004](architecture_decisions/ADR-004-patent-and-open-source-boundary.md) and [Open Core Boundary](open_core_commercial_runtime_boundary.md).
