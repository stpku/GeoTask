# GeoTask Documentation

[简体中文](README.md) | **English**

GeoTask documentation is organized by purpose. Start with the white paper for the overall idea, then use the implemented language specification and tutorials for engineering work.

## Start here

- [GeoTask White Paper v0.1](whitepaper/GeoTask_White_Paper_v0.1.md) — why GeoTask exists, its architecture, trust model, application patterns, and public boundary. See the [build guide](whitepaper/README.md) for HTML, DOCX, and PDF commands.
- [GeoTask Language and Execution Specification v1.0](spec/geotask-language-spec-v1.0.md) — the normative profile implemented by the current public Core.
- [Quickstart](tutorials/quickstart.md) — install, validate, execute, inspect, and extend a first task.
- [GT01–GT16 Cookbook](cookbook/gt01-gt16.md) — progressive examples from distance calculation to evidence governance, object-specific feasibility, emergency dispatch, and live environment state.
- [v0.1.1 PyPI hotfix release notes](release_v0_1_1.md) — fixes package/runtime version consistency and records clean-environment installation verification.
- [v0.1.0 Public Preview release notes](release_v0_1_0.md) — fixed-version capabilities, assets, and verification status.
- [Public roadmap](../ROADMAP.md) — planned protocol, Core, tooling, and ecosystem directions.
- [中文快速入门](tutorials/quickstart.zh-CN.md) and [中文案例手册](cookbook/gt01-gt16.zh-CN.md).

## Reference

- [Operator Registry](operator_registry.md)
- [Status and Assurance Model](reference/status-model.md)
- [Evidence, Conflict, Blocking, and Recovery](reference/evidence-and-recovery.md)
- [CLI Usage](cli_usage.md)
- [Architecture](architecture.md)
- [Operator Extension Guide](operator-guide.md)
- [JSON Schema](../schemas/geotask-v1.0.schema.json)

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
