# GeoTask Core Distribution Boundary v0.1

**Status:** public release-governance contract  
**Date:** 2026-08-07

## 1. Purpose

The GeoTask source repository may contain work from more than one engineering line, but repository co-location does not transfer ownership.

```text
same repository != same product line
passing repository tests != Core ownership
public-safe Integration code != Core release artifact
```

The **GeoTask Core public export** is the release surface for Core-owned code, Reference Agent material, Core product/release tooling, and public architecture/governance contracts. It is not the distribution mechanism for Lowa Product or Lowa-GT Integration implementations.

## 2. Three-line distribution rule

- **GeoTask Core:** may enter the Core public export when it is Core-owned and satisfies Core release rules.
- **Lowa Product:** never enters the Core public export as business implementation, data, workflows, or authoritative state.
- **Lowa-GT Integration:** validation harnesses, Integration-specific fixtures, study protocols, baseline comparison code, handoff packages, and Integration tests remain outside the Core public export unless a later distribution explicitly targets the Integration line.

A public architecture document that defines a boundary between lines is not the same as an Integration implementation. Therefore the Core export may retain public governance contracts such as:

- `cross-line-promotion-gate-v0.1.md`;
- `lowa-gt-integration-contract-v0.1.md` as a boundary/interface contract.

It must not thereby absorb the implementation that validates that contract.

## 3. Current Core-export exclusions

The Core public export explicitly excludes at least:

```text
examples/integrations/**
tests/test_lowa_gt_shadow_fixture.py
tests/test_lowa_gt_shadow_batch.py
tests/test_lowa_gt_handoff_package.py
tests/test_lowa_gt_human_baseline_compare.py
docs/reference/lowa-gt-shadow-study-protocol-v0.1.md
docs/internal/**
docs/reports/**
```

The first four test files may continue to run in the full source-repository suite. Their passing result is Integration validation evidence, not Core conformance evidence.

## 4. Promotion does not happen through packaging

Moving an Integration capability into the Core public export is an ownership change if the capability becomes part of the Core compatibility/release promise. That cannot happen merely by adding a path to `.release/public-manifest.yaml`.

Before such a path is added as Core-owned capability, the Cross-Line Promotion Gate must return an explicit `PROMOTE` decision with the required second-system/industry reuse and Core-native verification evidence.

```text
Integration path added to Core export
    requires prior Promotion decision

Promotion decision
    is never inferred from export inclusion
```

## 5. Reference Agent is different

`examples/reference_agent/**` remains a Core Product Track asset because its purpose is to teach and verify the generic GeoTask development lifecycle with fictional public-safe data. It does not depend on a Lowa System of Record and does not claim low-altitude business authority.

This distinction is intentional:

```text
Reference Agent = Core-owned generic teaching/reference implementation
Lowa-GT shadow harness = Integration-owned industry validation implementation
```

## 6. Machine enforcement

`tests/test_core_distribution_boundary.py` verifies the real public manifest and requires:

1. Core governance contracts remain included;
2. Reference Agent remains included;
3. Integration implementation paths are not included or required;
4. Integration implementation paths are explicitly forbidden from the Core export.

The existing public-export verifier then checks the generated export itself.

The same ownership rule now applies one step earlier to the Git index. `.release/core-baseline-manifest.yaml` is a closed-set declaration of the intended Core/governance pre-RC batch. `.release/plan_core_baseline.py` classifies the real mixed dirty workspace against that declaration: exact Core paths are content-hashed, known Integration/internal paths are excluded, and any unclassified dirty path is a hard failure. The generated plan is bound to the current `HEAD` and can emit an exact pathspec for a later local executor without staging anything.

After the executor stages that pathspec, `.release/verify_core_commit_scope.py --baseline-plan ...` requires the staged path set, `HEAD`, and every staged blob SHA-256 to match the generated plan exactly. It also independently rejects Integration-owned harnesses, Lowa-GT shadow/handoff tests, Integration-specific internal notes, and Lowa-GT reports. The public Integration boundary contract, Cross-Line Promotion Gate, and this distribution contract remain allowed because they govern the boundary rather than implement the Integration line. Neither tool stages, unstages, commits, pushes, or publishes anything.

```text
source-repo co-location
    != classified Core baseline
    != exact staged Core ownership
    != Core public distribution
```

## 7. Non-negotiable outcome

A Core release may describe how Integration works and define the contracts Integration must obey. It must not silently turn Integration implementation into Core product surface.

This is the distribution-level equivalent of the architecture rule:

> **Integration validates; Core abstracts; Lowa owns business facts; cross-line ownership changes require an explicit Promotion Gate.**
