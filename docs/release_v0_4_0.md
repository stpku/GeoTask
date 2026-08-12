# GeoTask Core v0.4.0 Core Productization and Reference Agent Release

- **Release date:** 2026-08-08
- **Git tag:** `v0.4.0`
- **Package version:** `0.4.0`
- **Status:** local release-candidate identity; tag, push, GitHub Release, and PyPI publication are not performed by the RC preparation workflow

GeoTask Core v0.4.0 moves the public project from the v0.3 Agent-integration baseline into a productized, release-auditable Core with a concrete Reference Agent, explicit cross-line governance, a closed public distribution boundary, and machine-generated RC evidence. The release does not expand Core ownership merely because Lowa-GT Integration validates it: GeoTask Core, Lowa Product, and Lowa-GT Integration remain independent lines, and any ownership transfer still requires the explicit Promotion Gate.

## What this release establishes

### 1. Product architecture and explicit governance

- Architecture Manifesto v1 and Product Architecture/Roadmap v0.2 separate the GT Capability Track from P0–P5 product maturity.
- Cross-Line Promotion Gate v0.1 formalizes `PROMOTE`, `KEEP_LOCAL`, `DEFER`, and `REJECT` outcomes.
- Core Distribution Boundary v0.1 makes repository co-location different from Core ownership and different again from public release distribution.
- The public Lowa-GT Integration contract defines the boundary without absorbing Lowa business facts or Integration-specific validation assets into Core.

### 2. Reference Agent v0.1

The public Reference Agent demonstrates one complete fictional facility-assessment update:

```text
request
→ Observation / World State
→ deterministic verification
→ discrepancy / correction / impact artifacts
→ bounded reevaluation
→ control evaluation
```

Five fixed scenarios cover success, missing evidence, stale evidence, conflicting evidence, and contradiction. Deterministic replay and a verification-quality benchmark are included. The Reference Agent never performs a production write, refreshes a production report, authorizes a real action, or executes a real action.

### 3. Frozen public Core contract

The v0.4 release candidate preserves the current public capability baseline rather than adding a GT number for release bookkeeping:

- GT capability baseline remains through GT42;
- public deterministic Operator Registry remains 14 operators;
- public Schema Bundle contains 33 Schemas;
- release-contract freeze, install/migration matrix, structured operator inspection, and public artifact discovery are machine checked.

`eligible != authorized != released != sent != executed` remains a hard control invariant.

### 4. Release-grade distribution and evidence

The release tooling now includes:

- closed-set Core baseline classification and exact staging plan;
- staged Core Commit Scope Gate with HEAD/path/blob-hash binding;
- public-export boundary verification and sensitive-content scanning;
- local RC readiness auditing;
- machine-generated RC evidence shards and same-commit evidence merge;
- Python 3.10–3.13 CI evidence wiring without allowing one interpreter to attest for another;
- installed-package Reference Agent replay evidence.

The RC tooling is intentionally side-effect limited: it does not create a release tag, push a remote branch, publish PyPI artifacts, or infer a cross-line Promotion decision.

## Install

After the release is published, install the exact package version with:

```bash
python -m pip install --no-cache-dir geotask-core==0.4.0
geotask --help
geotask inspect operators
```

## Verification expectations

A final release candidate is expected to satisfy all locally executable checks for the exact candidate commit and artifacts. Multi-interpreter Python 3.10–3.13 execution evidence may still remain pending locally when those interpreters are unavailable; the readiness auditor must report that as `pending`, never fabricate a pass.

Artifact validity is not external-world truth, and release readiness is not authorization to perform a physical-world action.

---

## English summary

GeoTask Core v0.4.0 productizes the public Core around an auditable Reference Agent, explicit Core/Lowa/Integration ownership boundaries, closed-set distribution controls, and machine-generated release-candidate evidence. It keeps the GT42 capability baseline and the established control semantics rather than adding capabilities for release numbering. Lowa-GT remains an independent Integration validation line; passing Integration tests does not imply Core Promotion.
