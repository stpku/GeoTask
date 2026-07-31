# GeoTask Target Specification Status

GeoTask maintains a broader system-level design draft in the development repository. That draft explores future model execution, Runtime orchestration, Domain Packs, governance, evaluation, and commercial integration.

It is intentionally separate from the public implemented profile.

## Authoritative Public Documents

For the current public Core, use:

1. [GeoTask Language and Execution Specification v1.0](geotask-language-spec-v1.0.md)
2. [GeoTask Agent Integration Profile v0.1](geotask-agent-integration-profile-v0.1.md)
3. [GeoTask Runtime Interface Profile v0.1](geotask-runtime-interface-profile-v0.1.md)
4. [GeoTask Artifact Registry v1.0](geotask-artifact-registry-v1.0.md) and `geotask inspect schemas`
5. machine-readable task, execution-result, control-result, Agent-report, Runtime-message, validation-report, and registry JSON Schemas
6. public source code and tests
7. [Operator Registry](../operator_registry.md)

These sources describe what the current repository can parse, validate, and execute. The implemented public object profile includes point, polyline, multi-polyline, polygon, rectangle, time interval, altitude interval, and feature collection objects; the polygon contract is one closed exterior ring without holes, and registered boundary contact counts as containment or intersection. The Runtime Interface currently covers offline Descriptor discovery, side-effect-free Request preflight, strict Runtime message validation, a three-way Descriptor/Request/Response exchange guard, one fail-closed read-only reference adapter, a public-safe external HTTP JSON transport Adapter, a paired loopback-only reference Endpoint, an independently buildable provider-neutral model Adapter package, and the first provider-specific OpenAI Responses package outside Core. The OpenAI package accepts an externally authenticated official SDK client and implements one no-retry, no-storage, strict Structured Outputs call with audit and truthfulness guards. Repository verification is fully offline; it does not prove account access, model availability, billing, quota, live-provider compatibility, production authorization, external evidence access, routing or cost governance, or production action execution.

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
