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
7. [GeoTask State Transition v0.1](geotask-state-transition-v0.1.md)
8. [GeoTask Verification Session v0.1](geotask-verification-session-v0.1.md)
9. [GeoTask Discrepancy Report v0.1](geotask-discrepancy-report-v0.1.md)
10. [GeoTask Core Conformance and Performance Benchmark v0.1](geotask-core-benchmark-v0.1.md)
11. machine-readable task, Observation, World State, State Transition, Verification Session, Discrepancy Report, execution-result, control-result, Agent-report, Runtime-message, benchmark-report, validation-report, and registry JSON Schemas
12. public source code and tests
13. [Operator Registry](../operator_registry.md)

These sources describe what the current repository can parse, validate, and execute. The implemented public object profile includes point, polyline, multi-polyline, polygon, rectangle, time interval, altitude interval, and feature collection objects; the polygon contract is one closed exterior ring without holes. All tasks in one document share one fail-closed space contract: planar operators accept only local Cartesian or identified projected CRS with `[x, y]` coordinate order, Core performs no CRS transformation or unit conversion, distance and altitude units must match the document contract, compared altitude datums must agree, and boundary-sensitive operators require `boundary_semantics=closed`. Pure temporal tasks do not consume the planar CRS. Documents may additionally declare strict source, evidence-binding, and authoring-audit metadata; valid assertion bindings propagate to result `evidence_refs` without source retrieval or assurance promotion. Observation v0.1 validates source-bound world claims without asserting truth. World State v0.1 validates one versioned point-in-time snapshot with strict reference closure, as-of validity, uncertainty, and a deterministic semantic fingerprint. State Transition v0.1 binds two snapshot fingerprints and validates Observation-supported object, attribute, relation, and action-eligibility change records. Verification Session v0.1 binds one World State semantic fingerprint to exact serialized task, result, control, transition, and Discrepancy Report artifacts, then records action eligibility and recheck triggers. Discrepancy Report v0.1 binds exact source bytes and records kind-specific differences, declared impact, and mutable/immutable correction scope. These contracts do not automatically calculate diffs, compare sources, merge observations, validate every linked artifact semantic, propagate impact, create or apply corrections, execute tasks or rechecks, materialize a later state, verify external truth, or authorize action. Artifact Registry discovery includes portable IDE file patterns for every public Schema. The public Core benchmark runs fixed fictional cases through production Parser, Canonical IR, Validator, Executor, and Result contracts, covering all nine deterministic operators with replay hashes and a local-only p95 regression guardrail; it does not support cross-hardware performance claims. The Runtime Interface currently covers offline Descriptor discovery, side-effect-free Request preflight, strict Runtime message validation, a three-way Descriptor/Request/Response exchange guard, one fail-closed read-only reference adapter, a public-safe external HTTP JSON transport Adapter, a paired loopback-only reference Endpoint, an independently buildable provider-neutral model Adapter package, and the first provider-specific OpenAI Responses package outside Core. The OpenAI package accepts an externally authenticated official SDK client and implements one no-retry, no-storage, strict Structured Outputs call with audit and truthfulness guards. Repository verification is fully offline; it does not prove account access, model availability, billing, quota, live-provider compatibility, production authorization, external evidence access, routing or cost governance, or production action execution.

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
