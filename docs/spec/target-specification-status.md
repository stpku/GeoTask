# GeoTask Target Specification Status

GeoTask maintains a broader system-level design draft in the development repository. That draft explores future model execution, Runtime orchestration, Domain Packs, governance, evaluation, and commercial integration.

It is intentionally separate from the public implemented profile.

## Authoritative Public Documents

For the current public Core, use:

1. [GeoTask Language and Execution Specification v1.0](geotask-language-spec-v1.0.md)
2. [Machine-readable JSON Schema](../../schemas/geotask-v1.0.schema.json)
3. public source code and tests
4. [Operator Registry](../operator_registry.md)

These sources describe what the current repository can parse, validate, and execute.

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
