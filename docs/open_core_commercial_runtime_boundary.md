# Open Core vs. Commercial Runtime Boundary

## Principle

**Open Core is not equivalent to open commercial capability. The commercial value resides in runtime orchestration, task planning, governance, domain packs, data integration, and operational workflow.**

**开源 Core 不等于开源商业能力。商业价值存在于运行时编排、任务规划、治理、行业包、数据集成和运营工作流中。**

This document defines what can be open-sourced and what must remain private at each product layer.

---

## Boundary Table

| Layer | Can Be Open Source | Must Remain Private / Commercial |
|-------|-------------------|----------------------------------|
| **Core** | Task schema and YAML format spec; 6 lightweight deterministic operators (`distance_2d`, `line_intersects_rect`, `point_to_line_distance_2d`, `rect_contains_point`, `time_overlap`, `altitude_overlap`); Parser (`src/geotask_core/parser.py`); Normalizer (`src/geotask_core/normalizer.py`); Verifier (`src/geotask_core/verifier.py`); Result schema and status machine (`src/geotask_core/result_schema.py`); CLI (`src/geotask_core/cli.py`); Evaluator (`src/geotask_core/evaluator.py`); Example YAML files; Design principles and format specification | No Core component is required to remain private. Core is fully open. |
| **Runtime** | SDK contract definitions (Python Protocol classes); Mock Runtime implementation for testing; Integration test fixtures; Architecture documentation and ADRs | Encoding strategy planner *(patent-sensitive)*; Token budget optimizer *(patent-sensitive)*; Model routing policy and multi-model consensus *(patent-sensitive)*; Prompt registry and prompt engineering templates; Cost control and quota enforcement logic; Governance and compliance logic; Audit trail implementation; Task orchestration engine; Verifiability triage logic; Data connector credential management |
| **Domain Pack** | Generic toy examples demonstrating the Domain Pack protocol; Domain Pack protocol specification; Example pack skeleton with no real industry rules | Industry-specific object models; Industry rules, safety margins, and regulatory thresholds; Customer-specific workflows and approval gates; Domain scoring models and risk algorithms; Private data source adapters and connectors; Proprietary report templates; Customer case configurations; Human review escalation rules |
| **Evidence** | Sanitized benchmark framework (`benchmarks/`); Benchmark runner scripts; Public benchmark results and methodology docs | Patent filing records and application numbers; Attorney communications and work product; Customer-specific evaluation cases; Confidential model output logs; Internal prompt engineering artifacts; Unreleased algorithm descriptions |

---

## Why This Boundary Matters

### For Adoption

Open Core enables:
- Developers evaluate GeoTask format without sales friction
- Researchers benchmark LLM spatial reasoning against deterministic ground truth
- Community contributes object types, operators, and integrations
- Ecosystem tools read/write GeoTask format using the open parser

### For Commercial Protection

Private Runtime and Domain Packs protect:
- Engineering investment in orchestration, governance, and optimization
- Patent-sensitive algorithms for encoding selection, token planning, and model routing
- Industry-specific domain expertise and data integration
- Customer relationships and deployment configurations

### For Patent Strategy

The boundary supports:
- Core open-sourcing does not constitute prior art disclosure for Runtime methods
- Runtime patents cover methods that are never published in Core
- Domain Pack application patents cover industry-specific workflows
- Clear separation enables independent filing timelines

---

## Boundary Enforcement

| Mechanism | Description |
|-----------|-------------|
| Separate repositories | Core, Runtime, and each Domain Pack live in separate repositories with separate access control |
| Code review policy | All Core PRs reviewed for accidental inclusion of commercial or patent-sensitive content |
| CI/CD checks | Automated checks verify Core has no imports from Runtime or Domain Pack modules |
| Documentation review | All public docs reviewed for patent-sensitive content before publication |
| Contributor guidelines | Contributors to Core must not include proprietary algorithms, industry rules, or customer data |

---

## Common Misunderstandings

| Misunderstanding | Reality |
|-----------------|---------|
| "Core is open, so everything is free" | Core is the format and verification engine. Commercial value is in orchestration and industry packs. |
| "MIT license means no IP protection" | MIT covers the code. Patents cover the methods. These are separate legal instruments. |
| "Open Core means competitors can replicate the product" | Competitors can replicate the format. They cannot replicate the Runtime orchestration, governance, or domain expertise without independent engineering. |
| "Domain Packs are just configuration files" | Domain Packs contain industry expertise, regulatory knowledge, scoring models, and data integration — significant engineering beyond configuration. |

---

## Relationship to Existing Docs

- [`open_source_boundary.md`](open_source_boundary.md) — Defines what is open source in the current repository
- [`patent_boundary.md`](patent_boundary.md) — Defines how patents interact with open source licensing
- [`design_principles.md`](design_principles.md) — Principle 1 ("Core Must Be Light") is the foundation of this boundary
- [`product_architecture_v0_1.md`](product_architecture_v0_1.md) — Full product architecture with layer definitions

---

*Document version: v0.1 | Date: 2025-06-18 | Status: Initial boundary definition*
