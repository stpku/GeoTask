# ADR-004: Patent and Open Source Boundary

**Date:** 2025-06-18
**Status:** Accepted
**Deciders:** GeoTask maintainers

---

## Context

GeoTask Core is released under the MIT License. The GeoTask patent portfolio covers methods for spatial task representation, object-operator-proposition binding, deterministic verification of LLM spatial output, and output normalization. Additional filings are planned for Runtime methods including encoding strategy selection, token budget planning, and model routing.

We must define how the MIT license on Core interacts with patent rights, and establish clear guidelines for contributors and users.

See [`patent_boundary.md`](../patent_boundary.md) for the existing patent boundary documentation.

---

## Decision

The MIT license on Core covers the **software code and documentation**. Patent rights on the **underlying methods** are retained separately. These are distinct legal instruments that operate independently.

---

## What Open-Sourcing Core Does NOT Do

### 1. Does not waive patent rights

Publishing Core under MIT grants a copyright license to use, copy, modify, and distribute the code. It does **not** grant a patent license. Patent rights on the spatial task representation method, object-operator-proposition binding, deterministic verification, and output normalization are retained.

The MIT License text does not contain a patent grant clause. This is a deliberate choice consistent with the distinction between copyright and patent law.

### 2. Does not open commercial modules

Open-sourcing Core does not open:
- GeoTask Runtime (private, proprietary)
- Domain Pack implementations (private, proprietary)
- Production deployment configurations
- Customer-specific configurations
- Internal prompt engineering artifacts

These components exist in separate private repositories and are not covered by Core's MIT License.

### 3. Does not limit future filings

The patent portfolio is designed to grow with the product:

| Filing Timeline | Scope |
|----------------|-------|
| Filed (Phase 0) | Spatial task representation, object-operator-proposition binding, deterministic verification, output normalization |
| Planned (Phase 2) | Encoding strategy selection, token budget planning, model routing *(Runtime methods)* |
| Planned (Phase 3) | Industry-specific spatial task workflows *(Domain Pack methods)* |
| Planned (Phase 4) | Multi-tenant spatial task orchestration, domain pack marketplace |

Core open-sourcing does not constitute prior art for Runtime or Domain Pack methods because those methods are not implemented in or disclosed through Core.

### 4. Does not create an implied patent license

Users of GeoTask Core under MIT receive:
- Right to use, copy, modify, and distribute the Core code
- No patent license for the methods described in patent filings

Users who implement the spatial task representation method independently (not using Core code) may still need a patent license if their implementation falls within patent claims.

---

## Guidelines for Contributors

### What contributors CAN submit to Core

- New spatial object types (e.g., polygon, circle, 3D point)
- New deterministic operators that are general-purpose and not patent-sensitive
- Bug fixes and performance improvements to existing Core modules
- Documentation improvements and example files
- Test cases and benchmark expansions
- CLI enhancements

### What contributors must NOT submit to Core

| Prohibited Content | Reason |
|-------------------|--------|
| Runtime orchestration logic | Private commercial module |
| Model calling or API integration code | Belongs in Runtime |
| Encoding strategy or token budget algorithms | Patent-sensitive |
| Industry-specific rules or object models | Belongs in Domain Packs |
| Customer data, configurations, or case studies | Confidential |
| Unreleased algorithm descriptions | May compromise patent filings |
| Prompt templates or prompt engineering artifacts | Competitive advantage |
| Attorney work product or filing details | Attorney-client privilege |

### Contributor checklist

Before submitting a pull request to Core, contributors should verify:

1. The change contains only general-purpose, domain-agnostic code
2. No patent-sensitive algorithms are introduced or disclosed
3. No proprietary data, customer information, or confidential material is included
4. No Runtime or Domain Pack dependencies are introduced
5. The change does not reference or depend on external APIs, databases, or model providers
6. All new code is compatible with the MIT License

---

## Interaction Between MIT License and Patent Portfolio

| Aspect | MIT License (Copyright) | Patent Portfolio |
|--------|------------------------|-----------------|
| What it covers | Source code, documentation, examples | Methods, systems, processes |
| What it grants | Right to use, copy, modify, distribute code | Nothing (separate license required) |
| Scope | Core repository only | All GeoTask methods regardless of repository |
| Revocability | Irrevocable once granted | Standard patent enforcement |
| Geographic scope | Worldwide (copyright) | Per-jurisdiction (patent filings) |

---

## Consequences

### Positive

- Clear legal separation between copyright license and patent rights
- Contributors understand what they can and cannot submit
- Users understand what they receive and what they do not
- Future patent filings are not compromised by Core open-sourcing
- Community adoption is enabled without commercial capability leakage

### Negative

- Some users may misunderstand the patent reservation
- Perception risk: "open source but with patents" may deter some adopters
- Requires ongoing review to ensure patent-sensitive content does not leak into Core

### Mitigations

- `patent_boundary.md` and this ADR provide clear documentation
- Code review policy includes patent-sensitivity check
- Contributor guidelines are explicit about prohibited content
- Legal FAQ will be added to documentation as community questions arise

---

## References

- [`docs/patent_boundary.md`](../patent_boundary.md)
- [`docs/open_source_boundary.md`](../open_source_boundary.md)
- [`docs/open_core_commercial_runtime_boundary.md`](../open_core_commercial_runtime_boundary.md)
- [ADR-001: Three-Layer Architecture](ADR-001-core-runtime-domain-pack.md)
- [ADR-002: Private Runtime Boundary](ADR-002-private-runtime-boundary.md)
