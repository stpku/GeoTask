# GeoTask Product Architecture v0.2

**Date:** 2026-08-07  
**Forward-looking architecture source:** aligned with `architecture_manifesto_v1.md` and `productization_roadmap_v0_2.md`.

## 1. Positioning

GeoTask separates current public capability from product direction:

- **Current public fact:** open verifiable spatiotemporal task protocol and deterministic Core for AI agents;
- **Near-term product target:** a trusted world-state runtime reference implementation composed from the existing public Evidence, World State, Provider, Impact, Control and Artifact contracts;
- **Long-term vision:** reusable trusted task/state infrastructure for high-consequence physical-world agents.

## 2. Architecture layers

```text
Application / Agent
        ↓
Industry system or Reference Agent
        ↓
GeoTask Trust/Runtime layer
  - Snapshot / State
  - Evidence / Verification
  - Dependency / Impact
  - Evidence Request
  - Control Evaluation
  - Artifact / Replay
        ↓
GeoTask Core deterministic contracts
        ↓
Providers / Operators / external systems
```

The architecture is not a claim that all layers already exist as a production-grade commercial runtime.

## 3. GeoTask Core

Core owns generic, open contracts and deterministic semantics:

- task/object/claim expression;
- world-state and observation artifacts;
- deterministic operators;
- evidence and verification-provider contracts;
- discrepancy/correction/impact/recompute/materialization artifacts;
- control evaluation and action-boundary semantics;
- artifact/schema registry and offline validation;
- replayable public examples and SDK/CLI surfaces.

Core remains fail-closed and does not require industry databases or private rules.

## 4. Reference Agent

The Reference Agent is the first product proof, not a commercial runtime.

It demonstrates:

```text
Proposal
→ bounded World State Snapshot
→ Verification
→ Evidence Request / Conflict
→ successor state / State Delta
→ bounded Impact
→ bounded reevaluation
→ Control Evaluation
→ Artifact Replay
```

The first public scenario is a fictional facility-assessment update. It uses no live regulatory or production data.

## 5. Industry integration

Industry systems own their domain business truth and workflows.

When a system already has a System of Record, GeoTask must not create a second authoritative database. The integration pattern is:

```text
Industry System of Record
→ bounded read-only projection / references
→ GeoTask verification + impact + control
→ read-only result bundle
→ industry workflow decides whether to write, rescore, approve or publish
```

Lowa-GT is the first reference industry integration.

## 6. Lowa-GT relationship

Lowa-GT owns low-altitude facility/resource data, evidence, assessment, decision, review, report and real database writes. GeoTask owns generic trust-control semantics.

The first integration slice is evidence/assessment/report validity in read-only shadow mode—not flight control or a new low-altitude world-model database.

The three lines stay independent: Lowa Product owns business facts, Lowa-GT Integration validates real-boundary behavior and candidate abstractions, and GeoTask Core owns industry-neutral abstractions. Integration success does not itself transfer ownership into either product line.

See `reference/lowa-gt-integration-contract-v0.1.md` and `reference/cross-line-promotion-gate-v0.1.md`.

## 7. Extension ecosystem

The ecosystem may eventually include:

- Verification Providers;
- Operators;
- Artifacts/Schemas;
- Packs;
- Adapters/connectors;
- third-party decision-assurance capabilities.

Extensions may contribute capability, but not bypass trust governance. They must declare evidence, method/version, scope, validity, failure conditions, uncertainty and dependencies.

The progression is:

```text
Contract → Pack → Registry → Partner Validation → Open Developer Platform → Marketplace if demand exists
```

A public Marketplace is not a near-term architecture requirement.

## 8. Commercial / private capabilities

Private or enterprise capabilities are triggered by real customer demand and may include:

- private Artifact/Capability Registry;
- credentials and private connectors;
- identity/access and approval workflow;
- audit retention/export;
- provider/rule governance;
- deployment hardening;
- long-term compatibility/support.

The project must not assume multi-tenancy, billing or a generic model-routing platform are required before customers demonstrate that need.

## 9. Data and action boundaries

### Core

- no production System of Record;
- no implicit network truth fetch;
- no undeclared source precedence;
- no arbitrary recompute code inside deterministic paths;
- no production report publication;
- no real-world action execution.

### Industry/application layer

- owns authoritative business state;
- performs approved database writes;
- performs human review/approval workflow;
- performs report publication or real external actions when explicitly authorized.

### Critical invariant

```text
eligible != authorized != released != sent != executed
```

## 10. Explicit Promotion Gate for cross-line capability transfer

A low-altitude or other industry-specific feature does not enter Core merely because it works in one integration. Any proposed cross-line ownership transfer must first create a reviewable Promotion Candidate and end in an explicit `PROMOTE`, `KEEP_LOCAL`, `DEFER`, or `REJECT` decision under the Cross-Line Promotion Gate.

Promotion into Core additionally requires:

1. industry-neutral semantics;
2. demonstrated reuse in at least one second independent system/industry;
3. deterministic/fail-closed/replayable behavior compatible with Core;
4. no requirement for Core to own the domain System of Record;
5. Core-native public-safe verification without a live Lowa dependency;
6. explicit public compatibility/migration impact.

Consuming a released Core contract from Integration is dependency use, not promotion. Copying or re-owning Integration/Lowa semantics in Core is promotion and cannot bypass this Gate.

## 11. Product maturity

Product maturity is tracked separately from GT capability numbering:

- P0 Architecture Definition;
- P1 Reference Agent;
- P2 Core Product;
- P3 Industry Integration;
- P4 Ecosystem Validation;
- P5 Commercial Validation.

At the current GT42 capability baseline, GeoTask remains in P0→P1 transition until the complete Reference Agent and external-use evidence exist.