# GeoTask Documentation

[简体中文](README.md) | **English**

GeoTask documentation is organized around positioning, implemented contracts, end-to-end reference workflows, and future state-evolution extensions. The current public fact is an open verifiable spatiotemporal task protocol and deterministic Core for AI agents; a trusted world-state runtime is the near-term product direction, not a claim that every production capability already exists. The 42 public examples form the Capability Track, while product maturity is tracked separately as P0–P5. GT38–GT42 form one five-stage UAV identity-governance composite case.

## Start here

- [Architecture Manifesto v1](architecture_manifesto_v1.md) — freezes the current-fact / near-term-product / long-term-vision distinction and the Context, Tool Result, World State, Unknown, Impact, and action-boundary principles.
- [Reference Agent v0.1 specification](reference/reference-agent-v0.1.md) — defines the first end-to-end public Reference Agent: a fictional facility-assessment-update workflow with five positive/negative scenarios.
- [GeoTask ↔ Lowa-GT Integration Contract v0.1](reference/lowa-gt-integration-contract-v0.1.md) — defines Lowa-GT as the low-altitude business System of Record and GeoTask as the read-only-first trust-control layer; the committed S1 read-only exporter and S2 exact transport profile are now aligned.
- [Cross-Line Promotion Gate v0.1](reference/cross-line-promotion-gate-v0.1.md) — freezes the independence of GeoTask Core, Lowa Product, and Lowa-GT Integration: Integration validates candidates, Core owns generic abstraction, Lowa owns business facts, and capability ownership never crosses lines without an explicit Promotion decision.
- [Core Distribution Boundary v0.1](reference/core-distribution-boundary-v0.1.md) — applies the three-line split to release artifacts: repository co-location does not imply product ownership, so the Core public export retains governance contracts and the Reference Agent but excludes Lowa-GT Integration harnesses, study protocols, and Integration tests.
- [Product Architecture v0.2](product_architecture_v0_2.md), [Open Core Boundary v0.2](open_core_boundary_v0_2.md), and [Productization Roadmap v0.2](productization_roadmap_v0_2.md) — re-baseline forward planning at the real GT42 capability state and introduce the P0–P5 Product Track.
- [GeoTask White Paper v0.1](whitepaper/GeoTask_White_Paper_v0.1.md) — why agents need an explicit and verifiable spatiotemporal world model, how GeoTask differs from implicit neural world models, and where the current Core foundation ends before first-class state evolution. See the [build guide](whitepaper/README.md) for HTML, DOCX, and PDF commands.
- [White paper English abstract](whitepaper/GeoTask_White_Paper_v0.1.md#english-abstract) — a concise English entry point and terminology map inside the same non-normative white paper.
- [GeoTask Language and Execution Specification v1.0](spec/geotask-language-spec-v1.0.md) — the normative profile implemented by the current public Core.
- [GeoTask Execution Result v1.0](spec/geotask-result-v1.0.md) — the `GeotaskResult.to_dict()` contract, public result JSON Schema, and `geotask result validate` command.
- [GeoTask Observation v0.1](spec/geotask-observation-v0.1.md) — source-bound, timestamped claims with producer identity and declared uncertainty, without claiming truth or automatically updating a World State.
- [GeoTask World State v0.1](spec/geotask-world-state-v0.1.md) — one versioned snapshot of world objects, attributes, relations, validity, uncertainty, and closed Observation/Evidence references, without automatically merging Observations or materializing a later state.
- [GeoTask Observation Merge Result v0.1](spec/geotask-observation-merge-result-v0.1.md) — exact-byte bounded merge of complete explicit Observation claim mappings into existing attributes or relations; when multiple claims target one path, only caller-declared semantic-equality consolidation or complete explicit precedence may produce the canonical successor revision, without identity inference, invented precedence, source ranking, undeclared ambiguous-conflict resolution, or State Transition computation.
- [GeoTask State Transition v0.1](spec/geotask-state-transition-v0.1.md) — semantic-fingerprint bindings between before/after World State snapshots and Observation-supported path, relation, and eligibility changes, without calculating diffs, applying patches, or authorizing action.
- [GeoTask Verification Session v0.1](spec/geotask-verification-session-v0.1.md) — one immutable audit snapshot binding a World State to exact-byte task, result, control, transition, eligibility, and recheck references.
- [GeoTask Discrepancy Report v0.1](spec/geotask-discrepancy-report-v0.1.md) — exact World State/source bindings plus explicit discrepancies, downstream impact, and mutable/immutable correction scope without automatically comparing or correcting sources.
- [GeoTask Correction Request v0.1](spec/geotask-correction-request-v0.1.md) — one immutable base World State plus exact Discrepancy Reports, bounded successor-state changes, acceptance criteria, immutable-path preservation, and output/action gates without applying changes.
- [GeoTask Impact Graph v0.1](spec/geotask-impact-graph-v0.1.md) — a source-bound directed acyclic graph linking discrepancies and corrections to affected state paths, assertions, outputs, actions, and reevaluation targets without discovering or executing propagation.
- [GeoTask Recompute Derivation Result v0.1](spec/geotask-recompute-derivation-result-v0.1.md) — exact Observation/GeoTask source-path bindings and allowlisted deterministic methods that close every requested `recompute` value without arbitrary expressions, model calls, or state mutation.
- [GeoTask World State Materialization Result v0.1](spec/geotask-world-state-materialization-result-v0.1.md) — deterministic bounded successor generation from one immutable base state, one bound Correction Request, and explicit recompute values while preserving output/action gates.
- [GeoTask Incremental Reevaluation Result v0.1](spec/geotask-incremental-reevaluation-result-v0.1.md) — exact base/successor World State, Impact Graph, source-file, node, target, acceptance, discrepancy, and gate outcomes without executing reevaluation or authorizing action.
- [GeoTask Artifact Registry v1.0](spec/geotask-artifact-registry-v1.0.md) — `geotask inspect schemas` discovery for all thirty-two public Artifacts and thirty-three public JSON Schemas.
- [GeoTask Verification Provider Profile v0.1](spec/geotask-verification-provider-profile-v0.1.md) — read-only Provider Descriptors, Verification Requests, Verification Responses, Assurance Profiles, exact bindings, and fail-closed assurance evaluation.
- [GeoTask Trajectory and Moving Object Profile v0.1](spec/geotask-trajectory-profile-v0.1.md) — identity/position separation, strictly ordered timezone-aware samples, adjacent-segment metrics, caller-declared classifications, identity candidates, adjudication, review-only merge proposals, approval records, bounded object-graph change requests, application approval records, and the GT33–GT42 non-prediction/non-execution boundary.
- [GeoTask Trajectory Identity Adjudication v0.1](spec/geotask-trajectory-identity-adjudication-v0.1.md) — exact GT37 candidate, Request, Profile, Provider, and Response bindings that may recommend merge review without mutating the object graph.
- [GeoTask Identity Merge Proposal v0.1](spec/geotask-identity-merge-proposal-v0.1.md) — one exact GT38 adjudication plus caller-declared canonical-subject selection, rationale, and approval roles produce a bounded proposal with alias preservation and a reversal plan, without approval or execution.
- [GeoTask Identity Merge Approval Record v0.1](spec/geotask-identity-merge-approval-record-v0.1.md) — one exact GT39 proposal plus one decision per required role produces approved, rejected, or evidence-required state without applying the merge.
- [GeoTask Object Graph Change Request v0.1](spec/geotask-object-graph-change-request-v0.1.md) — exact GT39 proposal and GT40 approval-record bytes derive one closed trajectory reference rewrite, retained alias, application preconditions, acceptance criteria, and rollback requirements without authorizing or applying a change.
- [GeoTask Object Graph Change Application Approval Record v0.1](spec/geotask-object-graph-change-application-approval-record-v0.1.md) — exact GT41 request bytes plus one decision per caller-declared application-approval role produce approved, rejected, or evidence-required state; all-role approval only makes a later bounded application Artifact eligible.
- [English Terminology Guide](terminology.en.md) — standard English terms, Chinese mappings, and stable machine identifiers.
- [GeoTask Artifact Validation v1.0](spec/geotask-artifact-validation-v1.0.md) — one `geotask artifact validate` entry point for validating all thirty-two registered public Artifacts, including trajectory identity adjudication, identity merge proposals, approval records, object-graph change requests, application approval records, world-state, Agent, Runtime, Verification Provider, benchmark, and validation-report contracts.
- [GeoTask Versioned Payload Validation v1.0](spec/geotask-versioned-payload-validation-v1.0.md) — shared strict loading, schema metadata, diagnostics, and text/JSON reports for execution and control results.
- [GeoTask Control Extension Profile v1.0](spec/geotask-control-extension-profile-v1.0.md) — versioned validation for evidence requests, evidence conflicts, decision rules, and task gates.
- [GeoTask Control Expression Language v1.0](spec/geotask-control-expression-language-v1.0.md) — the safe finite grammar, three-valued logic, comparison semantics, and public parser/evaluator API.
- [GeoTask Control Evaluation Result v1.0](spec/geotask-control-evaluation-v1.0.md) — read-only binding of assertion results and explicit domain state into gate status, unknown identifiers, and still-blocked outputs.
- [GeoTask Agent Integration Profile v0.1](spec/geotask-agent-integration-profile-v0.1.md) — the four model-neutral tools, mechanical preparation of generated drafts, guarded revision-diff retries, registered Agent report Artifacts, unknown/blocked handling, and deterministic re-execution after evidence recovery.
- [GeoTask Runtime Interface Profile v0.1](spec/geotask-runtime-interface-profile-v0.1.md) — Descriptor, Request, Response, authorization, idempotency, audit, and side-effect boundaries between Core and an external Runtime, plus public-safe HTTP Adapter, loopback Endpoint, provider-neutral model Adapter, and the first OpenAI Responses provider package.
- [GeoTask Core Agent Skill](../skills/geotask-core/SKILL.md) — directly injectable model instructions and safety boundaries for Agent integrations.
- [VS Code Schema association example](../.vscode/settings.json) — binds local GeoTask files to the repository JSON Schema.
- [Quickstart](tutorials/quickstart.md) — install, validate, execute, inspect, and extend a first task.
- [Reference Agent end-to-end tutorial](tutorials/reference-agent.md) — run the rev1→rev2→Discrepancy/Correction/Impact→rev3→Control lifecycle without reading GT01–GT42 first, then modify a developer-supplied scenario input.
- [P1 unfamiliar-developer activation protocol](reference/developer-activation-protocol-v0.1.md) — a standardized 30-minute exercise for first replay, custom input, three-revision comprehension, and `eligible != executed`; the anonymized result template, observer-only runbook, and `tools/summarize_developer_activation.py` make the first real trials machine-auditable, while P1 activation validation remains pending until those external results actually exist.
- [Second-System Validation Protocol v0.1](reference/second-system-validation-protocol-v0.1.md) — turns the independent-reuse requirement for Core Promotion into a concrete evidence package. The first scout candidate is neutral dependency relation state; `tools/evaluate_core_promotion_candidate.py` can only return `defer` or `eligible_for_gate_review`, never `PROMOTE`.
- [Verification Quality Benchmark v0.1](reference/verification-quality-benchmark-v0.1.md) — measures fixed fictional Reference Agent error detection, missed errors, false blocking, bounded correction, impact scope, and side-effect boundaries; its 100% fixture result is explicitly not a real-world safety or cross-domain accuracy claim.
- [0.4.0 release-scope contract freeze](reference/p2-release-contract-freeze-v0.4.md) — machine-checks package/CLI names, 14 operators, 32 Artifact IDs, and 33 Schemas without claiming that 0.4.0 has been released.
- [0.4.0 installation and migration matrix](reference/install-migration-matrix-v0.4.md) — separates declared Python support, configured CI coverage, and clean-room evidence actually executed during P2 hardening.
- [Core 0.4.0 RC Readiness Gate v0.1](reference/core-0.4-rc-readiness-v0.1.md) — machine-audits target-version metadata, final wheel/sdist, the 33-Schema Bundle, executed Python 3.10–3.13 CI evidence, public export, and Reference Agent replay; this gate was satisfied before the 0.4.0 release on 2026-08-08 and remains the release-evidence contract for that candidate.
- [GT01–GT20 Cookbook](cookbook/gt01-gt20.md) — progressive examples from distance calculation to evidence governance, object-specific feasibility, emergency dispatch, equipment capability, and high-risk action gating.
- [GT21–GT28 World-State Cycle Cookbook](cookbook/gt21-gt28.md) — Observation conflict, snapshots, state change, impact, bounded correction, incremental reevaluation, and action eligibility.
- [GT38–GT42 UAV Identity-Governance Composite Case](cookbook/gt38-gt42-uav-identity-governance.md) — one concrete inspection-drone re-identification story spanning evidence adjudication, merge proposal, proposal approval, change request, and application approval.
- [v0.4.0 Core Productization and Reference Agent release notes](release_v0_4_0.md)
- [v0.3.0 Agent Integration release notes](release_v0_3_0.md) — adds generated-task preparation, guarded revision, evidence recovery, four Agent report Artifacts, and unified validation across eight Artifacts and nine Schemas.
- [v0.2.0 artifact-contract release notes](release_v0_2_0.md) — adds the Artifact Registry, offline Schema Bundle, unified Artifact validation, and validation-report self-validation.
- [v0.1.1 PyPI hotfix release notes](release_v0_1_1.md) — fixes package/runtime version consistency and records clean-environment installation verification.
- [v0.1.0 Public Preview release notes](release_v0_1_0.md) — fixed-version capabilities, assets, and verification status.
- [Public roadmap](../ROADMAP.md) — planned protocol, Core, tooling, and ecosystem directions.
- [中文快速入门](tutorials/quickstart.zh-CN.md), [GT01—GT20中文案例手册](cookbook/gt01-gt20.zh-CN.md), and [GT21—GT28世界状态循环案例手册](cookbook/gt21-gt28.zh-CN.md).

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

- [Architecture](architecture.md)
- [Design Principles](design_principles.md)
- [Evaluation Specification](eval_spec.md)
- [Normalizer v0.2 Design](normalizer_v0_2_design.md)
- [Operator Registry](operator_registry.md)
- [English Terminology Guide](terminology.en.md)
- [Security](../SECURITY.md)

## Public and private boundary

The public repository defines general-purpose task representation, deterministic operators, validation, result assurance, examples, and conformance tests. Industry rules, customer data, approval thresholds, model credentials, commercial routing, and patent-sensitive optimization remain outside the public Core. Public documentation describes only open contracts, developer interfaces, and safety boundaries.
