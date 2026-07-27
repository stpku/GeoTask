# GeoTask Documentation

GeoTask documentation is organized by purpose. Start with the white paper for the overall idea, then use the implemented language specification and tutorials for engineering work.

## Start Here

- [GeoTask White Paper v0.1](whitepaper/GeoTask_White_Paper_v0.1.md) — why GeoTask exists, its architecture, trust model, application patterns, and public boundary. See the [build guide](whitepaper/README.md) for HTML, DOCX, and PDF commands.
- [GeoTask Language and Execution Specification v1.0](spec/geotask-language-spec-v1.0.md) — the normative profile implemented by the current public repository.
- [Quickstart](tutorials/quickstart.md) — install, validate, execute, inspect, and extend a first task.
- [GT01–GT13 Cookbook](cookbook/gt01-gt13.md) — progressive examples from distance calculation to evidence governance and object-specific feasibility.

## Reference

- [Operator Registry](operator_registry.md)
- [Status and Assurance Model](reference/status-model.md)
- [Evidence, Conflict, Blocking, and Recovery](reference/evidence-and-recovery.md)
- [CLI Usage](cli_usage.md)
- [Architecture](architecture.md)
- [Operator Extension Guide](operator-guide.md)
- [JSON Schema](../schemas/geotask-v1.0.schema.json)

## Specification Layers

GeoTask intentionally separates three documentation layers:

1. **Implemented public profile.** `docs/spec/geotask-language-spec-v1.0.md` describes fields and semantics that the current public Core can parse, validate, canonicalize, and execute.
2. **System-level target direction.** [Target Specification Status](spec/target-specification-status.md) explains how broader Runtime, Domain Pack, governance, and future protocol designs relate to the implemented public profile. It is not a statement that every planned feature is already implemented.
3. **Legacy compatibility.** `format_spec.md` and `geotask_yaml_schema.md` document earlier `0.x`/`v0.1-lite` formats that remain useful for migration and backward compatibility.

When documents differ, the current source code, tests, implemented v1.0 specification, and machine-readable schema are authoritative for the public Core.

## Public and Private Boundary

The public repository defines general-purpose task representation, deterministic operators, validation, result assurance, examples, and conformance tests. Industry rules, customer data, approval thresholds, model credentials, commercial routing, and patent-sensitive optimization remain outside the public Core. See [ADR-004](architecture_decisions/ADR-004-patent-and-open-source-boundary.md) and [Open Core Boundary](open_core_commercial_runtime_boundary.md).
