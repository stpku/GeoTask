# GeoTask Productization Roadmap v0.2

**Date:** 2026-08-07  
**Supersedes for forward planning:** `productization_roadmap_v0_1.md`  
**Strategic source:** `docs/internal/GeoTask_长期战略_计划与落地须知_v1.0.md`

## 1. Why v0.2

The v0.1 roadmap was written before the public repository completed the Agent integration, World-State Cycle, Verification Provider contracts, dynamic trajectory/identity governance and the current Artifact/Schema surface. It also treated a private Runtime, multiple Domain Packs and Marketplace as near-linear planned phases.

v0.2 re-baselines productization around repository reality at GT42 and introduces a separate Product Track. Capability count is no longer used as a proxy for product maturity.

## 2. Two tracks

### Capability Track — GT

GT cases prove individual protocol/Core capabilities. GT01–GT42 are technical evidence, not a maturity scale.

GT43 and later are paused unless Reference Agent or real industry integration exposes a missing generic primitive.

### Product Track — P

| Stage | Name | Primary proof |
|---|---|---|
| P0 | Architecture Definition | positioning and boundaries are stable and non-contradictory |
| P1 | Reference Agent | an external developer can understand and replay one end-to-end workflow |
| P2 | Core Product | public contracts, registry, benchmark, packaging and migration experience are product-grade |
| P3 | Industry Integration | one real industry system reuses Core without duplicating business truth |
| P4 | Ecosystem Validation | independent teams build reusable validated extensions |
| P5 | Commercial Validation | real customers pull private governance/support capabilities |

## 3. Current state — 2026-08-07

### Capability baseline

The public repository already includes, among other capabilities:

- Agent Integration Profile and registered Agent artifacts;
- Runtime Interface Profile and read-only reference Runtime/adapter work;
- Observation, World State, bounded merge, transition, discrepancy, correction, impact, recompute/materialization and incremental reevaluation artifacts;
- Verification Provider contracts and assurance profiles;
- Control Evaluation and explicit action boundaries;
- dynamic trajectory segment, stop/move/gap and acceleration operators;
- object identity candidate/adjudication, merge proposal/approval and bounded graph-change request/application approval;
- public Artifact Registry and schema distribution;
- deterministic operator benchmark coverage.

### Product baseline

GeoTask has completed the first **P0 architecture re-baseline** and the **P1 Reference Agent implementation/developer-material gate**. External unfamiliar-developer activation is still pending, so P1 adoption is not yet declared validated. P3 industry preparation has also started: the Lowa-GT authoritative model has been read-only reviewed and the GeoTask-side S0 fictional shadow-contract fixture is implemented and tested; the next industry gate is a Lowa-side read-only exporter.

What is still unproven:

- external unfamiliar-developer activation in a bounded time;
- a real Lowa-GT read-only exporter and shadow run against authoritative business state;
- quantified verification quality beyond functional correctness/performance;
- measured human-review benefit on the planned real-site shadow sample;
- real commercial pull for private governance/runtime capabilities.

## 4. P0 — Architecture Definition

### Deliverables

- `docs/architecture_manifesto_v1.md`;
- long-term strategy source under `docs/internal/`;
- `docs/open_core_boundary_v0_2.md` explicit Open Core / Open Protocol boundary;
- Reference Agent v0.1 specification;
- GeoTask↔Lowa-GT Integration Contract v0.1;
- public README and ROADMAP aligned to current/near-term/long-term positioning.

### Gate

No major repository document should imply that:

- GT34 is still the next capability;
- Core supports only the original six operators/object set;
- Runtime/world-state/provider artifacts do not exist at all;
- GT count equals product maturity;
- Marketplace/multi-tenant billing is an immediate milestone;
- `eligible` means a production action occurred.

## 5. P1 — Reference Agent

### Public reference scenario

Fictional low-altitude facility assessment update:

```text
new evidence
→ bounded state update
→ verify missing/stale/conflicting evidence
→ bounded impact
→ bounded recomputation/reevaluation
→ human review/control gate
→ report update eligible
→ no automatic publication/action
```

### Deliverables

- fixed fictional artifact bundle;
- one-command or documented replay entrypoint;
- five scenarios: success, missing evidence, conflict, stale evidence, contradiction;
- deterministic tests;
- developer tutorial and experience page.

### Gate

A developer unfamiliar with GT01–GT42 can install GeoTask, replay the chain, change one declared input and explain why the output changed.

## 6. P2 — Core Product

### Deliverables

- public object/Artifact/Schema/CLI naming freeze for the release scope;
- Artifact/Capability Registry developer experience;
- Verification Quality Benchmark covering error detection, missed error, false blocking, correction success and bounded impact scope;
- installation and migration matrix;
- clean wheel/sdist/schema-bundle verification;
- Reference Agent runs from an installed package;
- machine-auditable 0.4 RC readiness with clean-worktree and exact-HEAD evidence binding.

### 0.4.0 release gate

Do not publish 0.4.0 solely because of calendar date. Release only after the P1 reference workflow is installable/replayable and the quality benchmark covers more than performance/conformance. The final decision is audited by `reference/core-0.4-rc-readiness-v0.1.md` / `.release/verify_rc_readiness.py`: the exact candidate must have a clean worktree, evidence bound to the current Git `HEAD`, executed Python 3.10–3.13 CI, final 0.4.0 wheel/sdist + 33-Schema Bundle verification, public-export verification/scan, and Reference Agent replay. `pending` is not release authorization.

## 7. P3 — Lowa-GT industry reference integration

The first real integration is not flight control. It mirrors the Reference Agent's evidence/assessment/report chain.

### First slice

One facility receives new evidence or an updated evidence bundle. In read-only/shadow mode GeoTask determines:

- which claims/assessment outputs/report sections are affected;
- what is contradicted, conflicted or unverifiable;
- whether a human-approved rescore/report refresh is required or eligible;
- what remains explicitly unperformed.

### Gate

- zero unauthorized writes;
- deterministic replay for the same snapshot;
- bounded impact does not spread to unrelated facilities/sections;
- conclusions trace to source/time/version/hash where available;
- humans understand what changed and why;
- measured comparison against current review baseline.

## 8. P4 — Partner/Ecosystem Validation

Do not start with a public Marketplace.

Progression:

```text
Contract → Pack → Registry → Partner Validation → Open Developer Platform → Marketplace (only if demand exists)
```

Suggested triggers:

- at least two independently maintained reusable extensions before designing a broader Hub;
- multiple stable packs and/or paid deployments before Marketplace investment;
- every third-party capability remains subject to GeoTask trust/control semantics.

## 9. P5 — Enterprise / Commercial Validation

Enterprise capabilities are customer-pull driven. Candidate capabilities include private Artifact/Capability Registry, identity/access, audit retention, approval workflow, provider/rule governance, private connectors, deployment hardening and long-term compatibility/support.

No separate large Enterprise platform should be built before real customer demand demonstrates the need.

## 10. Resource priority for the next 90 days

1. Reference Agent and Lowa-GT shadow-integration preparation;
2. architecture/tutorial/developer experience derived from the same end-to-end chain;
3. verification quality benchmark and release readiness;
4. partner/customer validation.

Do not create separate narratives and separate demo architectures for each workstream.

## 11. Stop/defer list

- GT43 merely for sequence continuity;
- GeoTask Hub / Marketplace before external extension demand;
- second production model provider before the first path is stable;
- multiple industry packs in parallel;
- real-time takeoff authorization as the first Lowa-GT integration;
- certification claims;
- automatic production write-back/rescore/report publication by Core;
- multi-tenant billing as a near-term product gate.

## 12. Commercial principle

The open Core establishes standards, reproducibility and adoption. Commercial value, when pulled by real customers, comes from governed integration, private data/connectors, industry packs, review/approval workflows, audit/operations and long-term support—not from artificially crippling the open Core.