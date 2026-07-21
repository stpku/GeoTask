# ADR-001: Three-Layer Architecture — Core, Runtime, Domain Pack

**Date:** 2025-06-18
**Status:** Accepted
**Deciders:** GeoTask maintainers

---

## Context

GeoTask started as a single repository (`src/geotask_core/`) providing a lightweight spatial task representation format with deterministic operators, a normalizer, and a verifier. As the project moves toward commercialization, we need to decide how to structure the product architecture to support:

1. Open-source adoption of the spatial task format
2. Commercial orchestration and governance capabilities
3. Industry-specific vertical deployments

The current codebase (`src/geotask_core/`) contains the parser (`parser.py`), 6 deterministic operators (`ops.py`), normalizer (`normalizer.py`), verifier (`verifier.py`), runner (`runner.py`), evaluator (`evaluator.py`), result schema (`result_schema.py`), models (`models.py`), and CLI (`cli.py`). All 406 tests pass. The project has a first patent filed and three patent evidence versions.

We considered three structural approaches:

- **Monolith**: Everything in one repository with feature flags
- **Two-layer**: Core (open) + Everything Else (private)
- **Three-layer**: Core (open) + Runtime (private commercial) + Domain Pack (private industry-specific)

---

## Decision

We adopt a **three-layer architecture**: Core, Runtime, and Domain Pack.

### Core must stay light

Core is the spatial task format, deterministic operators, normalizer, verifier, and CLI. It has no network I/O, no model API calls, no database connections, and no domain-specific logic. Its only non-stdlib dependency is PyYAML.

This constraint follows Design Principle 1 from [`design_principles.md`](../design_principles.md): "Core Must Be Light."

Core stays light because:
- Light code is easy to audit, easy to trust, and easy to adopt
- LLM tool integration requires minimal dependency surfaces
- Patent evidence is strongest when the verified component is self-contained
- Community contributions are easier when the codebase is simple

### Runtime wraps Core

Runtime is a separate private codebase that imports Core as a dependency and adds:
- Model provider adapters (calling external LLM APIs)
- Task orchestration (multi-step decomposition, dependency resolution)
- Token budget planning and encoding strategy selection *(patent-sensitive)*
- Governance (audit trails, cost control, quota enforcement)
- Data connector framework (authorized external data sources)

Runtime wraps Core rather than modifying it because:
- Core's MIT license and simplicity drive adoption; Runtime's complexity would hinder it
- Commercial orchestration logic is the primary revenue source and must be protected
- Patent-sensitive algorithms in Runtime should never appear in the open Core
- Runtime can evolve independently on a faster release cadence

### Domain Pack extends Runtime

Domain Pack is an industry-specific plugin that implements the `DomainPackProtocol` and registers with Runtime. It provides industry objects, rules, templates, scoring, and data connectors.

Domain Pack extends Runtime rather than Core because:
- Industry logic requires Runtime's orchestration (model calls, governance, audit)
- Domain Packs need data connectors that Core deliberately does not provide
- Different industries evolve at different rates; plugin architecture enables independent versioning
- Customer-specific configurations must be isolated from the shared platform

---

## Consequences

### Positive

- Clear IP boundary: open Core creates adoption, private Runtime and Domain Packs create revenue
- Patent strategy alignment: Core methods are disclosed; Runtime methods are protected
- Independent scaling: Core, Runtime, and each Domain Pack can be developed, tested, and deployed independently
- Clean dependency graph: Core depends on nothing; Runtime depends on Core; Domain Pack depends on Runtime

### Negative

- Three-layer architecture adds integration complexity compared to a monolith
- Domain Pack developers must understand both the Runtime SDK and the Domain Pack Protocol
- Core feature requests that require Runtime capabilities must be carefully triaged to maintain the boundary
- Testing across layers requires mock Runtime and mock Domain Pack implementations

### Risks

- If Core becomes too minimal, it may not attract sufficient community interest
- If Runtime becomes too complex, deployment and maintenance costs may exceed commercial value
- Domain Pack Protocol must be stable enough for third-party developers but flexible enough for diverse industries

### Mitigations

- Core is extended incrementally (new operators, new object types) following Design Principle 5
- Runtime complexity is managed through clear internal modules and comprehensive integration tests
- Domain Pack Protocol uses Python Protocol classes for structural subtyping, allowing evolution without breaking existing packs

---

## References

- [`docs/design_principles.md`](../design_principles.md)
- [`docs/product_architecture_v0_1.md`](../product_architecture_v0_1.md)
- [`docs/open_source_boundary.md`](../open_source_boundary.md)
