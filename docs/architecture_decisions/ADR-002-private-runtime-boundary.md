# ADR-002: Runtime Must Remain Private

**Date:** 2025-06-18
**Status:** Accepted
**Deciders:** GeoTask maintainers

---

## Context

With Core released under MIT license, we must decide the licensing and visibility of the Runtime layer. The Runtime contains model orchestration, token budget planning, encoding strategy selection, governance logic, and cost control — the components that transform Core from a format library into a commercial spatial reasoning platform.

Three options were evaluated:

- **Open Runtime**: Release Runtime under MIT alongside Core
- **Open-core with Runtime add-ons**: Release a basic Runtime under MIT, sell premium features as add-ons
- **Private Runtime**: Keep all Runtime code proprietary

---

## Decision

**Runtime must remain private and proprietary.**

The Runtime SDK contracts (Python Protocol classes) and mock Runtime implementation may be public to enable ecosystem development and Domain Pack testing. All implementation code is private.

---

## Rationale

### Commercial value concentration

The commercial value of GeoTask is not in the format (Core) — it is in the intelligence layer that connects the format to models, data, and governance. Specifically:

| Runtime Capability | Why It Must Be Private |
|-------------------|----------------------|
| Encoding strategy selection | Patent-sensitive method for choosing spatial task encoding |
| Token budget planning | Patent-sensitive optimization for allocating token budgets |
| Model routing and consensus | Patent-sensitive method for multi-model spatial reasoning |
| Prompt registry | Competitive advantage built through extensive iteration |
| Cost control logic | Revenue protection mechanism |
| Governance and audit | Compliance differentiator for enterprise customers |
| Task orchestration | Core product logic enabling multi-step spatial reasoning |

### Patent protection

Several Runtime methods are covered by existing or planned patent filings. Publishing these methods would:

- Create prior art that weakens future patent applications
- Enable competitors to implement covered methods before patents are granted
- Complicate patent prosecution by blurring the disclosure boundary

Keeping Runtime private preserves clean patent prosecution paths.

### Risks of opening Runtime

| Risk | Severity | Description |
|------|----------|-------------|
| Revenue loss | High | Competitors deploy equivalent systems using open Runtime code |
| Patent weakening | High | Published code creates prior art for competing filings |
| Support burden | Medium | Open Runtime attracts users who expect free commercial-grade support |
| Quality dilution | Medium | External contributions may not meet production governance requirements |
| Security exposure | Medium | Governance and audit logic under public scrutiny may reveal exploitable patterns |

### How open Core + private Runtime protects commercial value while enabling community adoption

| Goal | Mechanism |
|------|-----------|
| Community adoption | Core is MIT-licensed, lightweight, and self-contained. Developers can evaluate, integrate, and extend the format. |
| Ecosystem growth | Public Runtime SDK contracts and mock Runtime enable third-party tool development without exposing implementation. |
| Commercial protection | All orchestration, optimization, and governance logic is private. Competitors must independently engineer equivalent capabilities. |
| Patent strategy | Core disclosure is controlled and deliberate. Runtime methods remain undisclosed, preserving filing options. |
| Customer trust | Enterprise customers know the governance layer is proprietary and maintained by the GeoTask team, not crowd-sourced. |

---

## Consequences

### Positive

- Commercial value is protected behind a clear boundary
- Patent prosecution is not complicated by premature disclosure
- Enterprise customers have confidence in proprietary governance
- Core community is not burdened with Runtime complexity

### Negative

- Third-party integrators cannot inspect Runtime implementation
- Domain Pack developers must work against SDK contracts without seeing internals
- Open-source community may perceive the boundary as restrictive
- Runtime bugs reported by customers may be harder to reproduce without sharing code

### Mitigations

- Comprehensive Runtime SDK documentation with examples
- Mock Runtime implementation for Domain Pack development and testing
- Clear escalation path for community-reported issues that involve Runtime
- Transparent changelog for Runtime releases (without disclosing implementation details)

---

## References

- [`docs/patent_boundary.md`](../patent_boundary.md)
- [`docs/open_core_commercial_runtime_boundary.md`](../open_core_commercial_runtime_boundary.md)
- [`docs/product_architecture_v0_1.md`](../product_architecture_v0_1.md)
- [ADR-001: Three-Layer Architecture](ADR-001-core-runtime-domain-pack.md)
