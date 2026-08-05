# GeoTask Target Specification Status

GeoTask maintains a broader system-level design draft in the development repository. That draft explores future model execution, Runtime orchestration, Domain Packs, governance, evaluation, and commercial integration.

It is intentionally separate from the public implemented profile.

## Authoritative Public Documents

For the current public Core, use:

1. [GeoTask Language and Execution Specification v1.0](geotask-language-spec-v1.0.md)
2. [GeoTask Agent Integration Profile v0.1](geotask-agent-integration-profile-v0.1.md)
3. [GeoTask Runtime Interface Profile v0.1](geotask-runtime-interface-profile-v0.1.md)
4. [GeoTask Artifact Registry v1.0](geotask-artifact-registry-v1.0.md) and `geotask inspect schemas`
5. [GeoTask Observation v0.1](geotask-observation-v0.1.md)
6. [GeoTask World State v0.1](geotask-world-state-v0.1.md)
7. [GeoTask Observation Merge Result v0.1](geotask-observation-merge-result-v0.1.md)
8. [GeoTask State Transition v0.1](geotask-state-transition-v0.1.md)
9. [GeoTask Verification Session v0.1](geotask-verification-session-v0.1.md)
10. [GeoTask Discrepancy Report v0.1](geotask-discrepancy-report-v0.1.md)
11. [GeoTask Correction Request v0.1](geotask-correction-request-v0.1.md)
12. [GeoTask Impact Graph v0.1](geotask-impact-graph-v0.1.md)
13. [GeoTask Recompute Derivation Result v0.1](geotask-recompute-derivation-result-v0.1.md)
14. [GeoTask World State Materialization Result v0.1](geotask-world-state-materialization-result-v0.1.md)
15. [GeoTask Incremental Reevaluation Result v0.1](geotask-incremental-reevaluation-result-v0.1.md)
16. [GeoTask Core Conformance and Performance Benchmark v0.1](geotask-core-benchmark-v0.1.md)
17. [GeoTask Trajectory and Moving Object Profile v0.1](geotask-trajectory-profile-v0.1.md)
18. [GeoTask Trajectory Identity Adjudication v0.1](geotask-trajectory-identity-adjudication-v0.1.md)
19. [GeoTask Identity Merge Proposal v0.1](geotask-identity-merge-proposal-v0.1.md)
20. machine-readable task, Observation, World State, Observation Merge Result, State Transition, Verification Session, Discrepancy Report, Correction Request, Impact Graph, Recompute Derivation Result, World State Materialization Result, Incremental Reevaluation Result, Trajectory Identity Adjudication, Identity Merge Proposal, execution-result, control-result, Agent-report, Runtime-message, benchmark-report, validation-report, and registry JSON Schemas
21. public source code and tests
22. [Operator Registry](../operator_registry.md)

These sources describe what the current repository can parse, validate, and execute. The implemented public object profile includes point, polyline, multi-polyline, polygon, rectangle, time interval, altitude interval, feature collection, moving-object, and trajectory objects; the polygon contract is one closed exterior ring without holes, and the trajectory contract binds strictly increasing timezone-aware 2D samples to one moving object with `interpolation=none`. All tasks in one document share one fail-closed space contract: planar operators accept only local Cartesian or identified projected CRS with `[x, y]` coordinate order, Core performs no CRS transformation or unit conversion, distance and altitude units must match the document contract, compared altitude datums must agree, and boundary-sensitive operators require `boundary_semantics=closed`. Pure temporal tasks do not consume the planar CRS. Documents may additionally declare strict source, evidence-binding, and authoring-audit metadata; valid assertion bindings propagate to result `evidence_refs` without source retrieval or assurance promotion. Observation v0.1 validates source-bound world claims without asserting truth. World State v0.1 validates one versioned point-in-time snapshot with strict reference closure, as-of validity, uncertainty, and a deterministic semantic fingerprint. Observation Merge Result v0.1 binds exact base/Observation/successor bytes, requires complete explicit claim-to-existing-target mappings, supports only caller-declared `require_equal` or complete `explicit_precedence` policies when multiple claims target the same path, and deterministically emits one successor revision without identity inference, invented precedence, source ranking, undeclared ambiguous-conflict resolution, or State Transition computation. State Transition v0.1 binds two snapshot fingerprints and validates Observation-supported object, attribute, relation, and action-eligibility change records. Verification Session v0.1 binds one World State semantic fingerprint to exact serialized task, result, control, transition, and Discrepancy Report artifacts, then records action eligibility and recheck triggers. Discrepancy Report v0.1 binds exact source bytes and records kind-specific differences, declared impact, and mutable/immutable correction scope. Correction Request v0.1 binds an immutable base World State and exact Discrepancy Reports, constrains successor-state changes and acceptance criteria, preserves immutable paths, and keeps affected outputs/actions gated. Impact Graph v0.1 binds the same World State to exact reports and requests, resolves source entities, and validates a directed acyclic impact topology from discrepancies and corrections to affected paths, assertions, outputs, actions, and reevaluation targets. Recompute Derivation Result v0.1 binds exact base/request/source bytes, covers every request `recompute` change, resolves exact Observation or GeoTask Document paths, and evaluates a small deterministic method allowlist into a complete materializer value map. World State Materialization Result v0.1 and the bounded materializer bind exact base/request/successor bytes and apply only requested changes, using the explicit recompute-value map while preserving provenance and gates. Incremental Reevaluation Result v0.1 binds exact base/successor snapshots, the Impact Graph, Correction Requests, Discrepancy Reports, and execution results; covers every graph node and target; evaluates declared acceptance criteria; verifies discrepancy outcomes, requested-path confinement, immutable-path preservation, and output/action gate closure; and keeps action authorization and execution false. Trajectory Identity Adjudication v0.1 binds one exact identity candidate, Verification Request, Assurance Profile, and matching Provider Descriptors and Responses to confirmed-same, confirmed-different, or unresolved evidence outcomes while preserving both original subjects. Identity Merge Proposal v0.1 accepts only an exact confirmed-same adjudication, requires the caller to select one existing canonical subject, scopes exactly one proposed `subject_ref` rewrite, retains the other subject as an alias, records approval roles plus closed blocking and withdrawal conditions, and supplies an inverse reversal plan while keeping approval, object-graph mutation, World State update, publication, authorization, and execution false. These contracts do not automatically calculate diffs, compare sources, infer undeclared identity, approve or apply identity-merge proposals, resolve ambiguous claim conflicts without a declared policy, create missing state during Observation Merge, expand the bounded derivation method registry, discover or execute impact propagation, execute tasks or rechecks, verify external truth, authorize an action, or execute an action. Generic Artifact validation does not prove any linked binding or operational outcome; the explicit binding validators require the supplied source objects and exact bytes. Artifact Registry discovery includes portable IDE file patterns for every public Schema. The public Core benchmark runs fixed fictional cases through production Parser, Canonical IR, Validator, Executor, and Result contracts, covering all fourteen deterministic operators, including discrete trajectory duration, adjacent-segment metrics, caller-declared segment classifications, bounded scalar acceleration estimates, and boundary-sample identity candidates, with replay hashes and a local-only p95 regression guardrail; it does not support cross-hardware performance claims. The Runtime Interface currently covers offline Descriptor discovery, side-effect-free Request preflight, strict Runtime message validation, a three-way Descriptor/Request/Response exchange guard, one fail-closed read-only reference adapter, a public-safe external HTTP JSON transport Adapter, a paired loopback-only reference Endpoint, an independently buildable provider-neutral model Adapter package, and the first provider-specific OpenAI Responses package outside Core. The OpenAI package accepts an externally authenticated official SDK client and implements one no-retry, no-storage, strict Structured Outputs call with audit and truthfulness guards. Repository verification is fully offline; it does not prove account access, model availability, billing, quota, live-provider compatibility, production authorization, external evidence access, routing or cost governance, or production action execution.

## Why the Target Draft Is Separate

A target architecture may describe capabilities before they are implemented, including:

- hosted model execution;
- connector and human executors;
- hybrid and shadow-comparison orchestration;
- Domain Pack policy;
- commercial routing and cost governance;
- broader evidence and review workflows.

Those concepts are useful for architecture planning, but they MUST NOT be presented as completed public Core capabilities until code, tests, schemas, and release notes support them.

## Disclosure Boundary

The public documentation explains stable interfaces, general workflow patterns, and safe extension points. It does not require publication of:

- customer-specific rules or data;
- model credentials and commercial routing;
- private Runtime implementation;
- confidential approval policies;
- patent-sensitive methods not cleared for disclosure.

This separation allows the public language and Core to evolve transparently without treating every internal architecture proposal as a public commitment.
