# GeoTask Productization Roadmap v0.1

## Overview

This roadmap defines the path from open-source Core to commercial platform across five phases. Each phase has clear deliverables, commercial value, patent actions, and acceptance criteria.

---

## Phase 0 — Core + Normalizer + Verifier + Deterministic Evidence

**Status: Done**

| Aspect | Detail |
|--------|--------|
| Goal | Establish the lightweight spatial task representation, deterministic operators, normalizer, verifier, and reproducible patent evidence |
| Input | Spatial task format design, LLM output samples, patent strategy |
| Output | `src/geotask_core/` with parser, 6 operators, normalizer, verifier, CLI, evaluator; `patent_evidence/` with 3 evidence versions (v0.1.1, v0.2, v0.3); `benchmarks/` with encoding benchmarks; 406 passing tests |
| Commercial value | Foundation for all subsequent commercialization; reproducible evidence for patent prosecution; open-source adoption vehicle |
| Patent action | First patent filed covering spatial task representation, object-operator-proposition binding, deterministic verification, and output normalization |
| Public boundary | All Core code is MIT-licensed and publicly available. Patent evidence structure is public; filing details are private. |
| Acceptance criteria | `pytest` passes 406 tests; `geotask validate`, `geotask run`, `geotask normalize`, `geotask eval` CLI commands work; benchmark v0.1 and v0.2 produce reproducible results; Core v0.3 covers all 6 operators with unified status hierarchy |

**Key deliverables already completed:**

- `src/geotask_core/ops.py` — 6 deterministic spatial operators
- `src/geotask_core/normalizer.py` — Multi-operator normalizer with error detection
- `src/geotask_core/verifier.py` — Verifier with unified status hierarchy
- `src/geotask_core/result_schema.py` — Status/reason constants
- `benchmarks/encoding_v0_1/` and `benchmarks/encoding_v0_2/` — Encoding benchmarks
- `patent_evidence/` — 3 evidence versions with attorney delivery files
- `docs/` — Design principles, format spec, eval spec, patent boundary, open source boundary

---

## Phase 1 — Runtime Contracts + Mock Runtime + Domain Pack Protocol + Product/Patent Boundary

**Status: Current**

| Aspect | Detail |
|--------|--------|
| Goal | Define the Runtime and Domain Pack architecture, establish contracts and protocols, create mock implementations for testing, and document the product/patent boundary |
| Input | Core v0.3 stable codebase, product architecture v0.1 (this document set), patent portfolio status |
| Output | Product architecture documentation (this document set); Runtime contract definitions (Python Protocol classes); Mock Runtime for integration testing; Domain Pack protocol specification; ADR documents for key architecture decisions |
| Commercial value | Enables parallel development of Runtime and Domain Packs; establishes clear IP boundaries; creates framework for investor and partner communication |
| Patent action | Review existing filings against product architecture; identify gaps for continuation filings; document patent-sensitive boundaries in all architecture docs |
| Public boundary | Architecture documentation, ADRs, and contract definitions may be public. Mock Runtime is public. Real Runtime implementation is private. |
| Acceptance criteria | All 8 architecture documents created with substantive content; Runtime Protocol classes defined; at least one mock Domain Pack demonstrates the protocol; existing 406 tests still pass; no patent-sensitive algorithms disclosed in public docs |

**Key deliverables for this phase:**

- `docs/product_architecture_v0_1.md` — Product layers, execution flow, deployment topology
- `docs/productization_roadmap_v0_1.md` — This roadmap
- `docs/open_core_commercial_runtime_boundary.md` — Boundary table
- `docs/domain_pack_architecture.md` — Domain Pack specification
- `docs/architecture_decisions/ADR-001` through `ADR-004` — Architecture decision records

---

## Phase 2 — Private Runtime MVP

**Status: Planned**

| Aspect | Detail |
|--------|--------|
| Goal | Build a functional private Runtime that wraps Core, connects to at least one model provider, and produces auditable spatial reasoning results |
| Input | Core v0.3 stable, Runtime contracts from Phase 1, model provider API access |
| Output | Private Runtime repository with: model provider adapter (at least one provider), authorized data connector framework, token budget planner, runtime trace and audit log, cost guard with per-request limits, task registry for tracking spatial tasks |
| Commercial value | First deployable commercial component; enables pilot projects with early customers; demonstrates end-to-end spatial reasoning with governance |
| Patent action | File continuation patents covering encoding strategy selection, token budget optimization, and model routing methods as implemented in Runtime |
| Public boundary | Runtime SDK contracts and mock interfaces remain public for ecosystem development. All implementation code, prompt templates, model routing logic, and cost optimization algorithms are private. |
| Acceptance criteria | Runtime can accept a GeoTask YAML task, invoke a model provider, normalize the response using Core, verify using Core operators, and return an audited result; token budget planner allocates budgets within configurable limits; cost guard enforces per-request and per-tenant limits; all operations produce immutable audit records; Core tests still pass unmodified |

**Key deliverables for this phase:**

- Model provider adapter with at least DeepSeek and OpenAI support
- Authorized data connector framework with at least one reference connector
- Token budget planner with configurable strategy *(patent-sensitive — implementation private)*
- Runtime trace system producing immutable audit records
- Cost guard with per-request and per-tenant budget enforcement
- Task registry for lifecycle tracking of spatial tasks

---

## Phase 3 — Industry MVP

**Status: Planned**

| Aspect | Detail |
|--------|--------|
| Goal | Deliver the first industry-specific Domain Packs running on Runtime, validated with pilot customers |
| Input | Runtime MVP from Phase 2, industry partner requirements, domain expertise |
| Output | Three Domain Packs: LowAlt Site Precheck Pack, Facility Siting Pack, Network Spatial Optimization Pack; each with industry object models, rules, task templates, and data connector implementations |
| Commercial value | First revenue-generating deployments; industry-specific differentiation; customer reference cases |
| Patent action | File industry application patents covering specific spatial task workflows in low-altitude operations, facility siting, and network optimization |
| Public boundary | Generic toy Domain Pack examples remain public. All industry object models, rules, scoring logic, customer data adapters, and proprietary templates are private. |
| Acceptance criteria | Each Domain Pack passes industry-specific acceptance tests; at least one pilot customer validates each pack in a real-world scenario; Domain Packs plug into Runtime via the protocol defined in Phase 1; audit trail captures full provenance for each industry task |

**Key deliverables for this phase:**

- **LowAlt Site Precheck Pack**: Airspace clearance, obstacle analysis, regulatory buffer evaluation, takeoff/landing site scoring
- **Facility Siting Pack**: Multi-criteria site selection, proximity constraint evaluation, environmental compliance checks, accessibility scoring
- **Network Spatial Optimization Pack**: Coverage analysis, facility placement optimization, route planning with spatial constraints, capacity-distance tradeoff evaluation

---

## Phase 4 — Commercial Platform

**Status: Planned**

| Aspect | Detail |
|--------|--------|
| Goal | Scale from pilot deployments to a multi-tenant commercial platform with self-service capabilities |
| Input | Runtime MVP, validated Domain Packs, customer feedback from Phase 3 pilots |
| Output | API/SDK for third-party integration; tenant isolation with per-tenant configuration; comprehensive audit log with export and compliance reporting; usage quota and billing system; Domain Pack marketplace for third-party pack distribution; private deployment option for regulated industries |
| Commercial value | Recurring SaaS revenue; third-party ecosystem revenue share; enterprise license deals for on-premise deployment |
| Patent action | Review portfolio coverage across all platform capabilities; file system patents for multi-tenant spatial task orchestration and domain pack marketplace architecture |
| Public boundary | Core remains MIT-licensed. Public SDK documentation and integration guides. All platform code, tenant management, billing, marketplace, and deployment automation are private. |
| Acceptance criteria | Multi-tenant platform serves concurrent customers with isolated data and configuration; API/SDK enables third-party applications to submit tasks and retrieve results; audit log meets enterprise compliance requirements (retention, export, access control); usage quota system accurately tracks and limits per-tenant consumption; at least one third-party Domain Pack is distributed via marketplace; private deployment package passes security review for regulated industry requirements |

**Key deliverables for this phase:**

- REST/gRPC API with versioned endpoints and SDK for Python, TypeScript
- Tenant isolation: per-tenant config, data separation, model provider keys
- Audit log: immutable, exportable, compliance-ready (SOC2 alignment)
- Usage quota: per-tenant token budgets, rate limits, overage policies
- Domain Pack marketplace: registration, versioning, access control, revenue sharing
- Private deployment: Helm charts, air-gapped support, customer-managed keys

---

## Phase Summary

| Phase | Name | Status | Core Change | Runtime Change | Domain Pack Change |
|-------|------|--------|-------------|----------------|-------------------|
| 0 | Core + Evidence | Done | 6 operators, normalizer, verifier, CLI | None | None |
| 1 | Architecture + Contracts | Current | No code change | Contract definitions, mock | Protocol definition |
| 2 | Private Runtime MVP | Planned | No code change | Full implementation | Mock pack for testing |
| 3 | Industry MVP | Planned | Possible operator additions | Connector + governance enhancements | 3 production packs |
| 4 | Commercial Platform | Planned | Stable | Multi-tenant, API, billing | Marketplace |

---

*Document version: v0.1 | Date: 2025-06-18 | Status: Initial roadmap definition*
