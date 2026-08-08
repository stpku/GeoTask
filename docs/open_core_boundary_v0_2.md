# GeoTask Open Core / Open Protocol Boundary v0.2

**Date:** 2026-08-07  
**Purpose:** forward-looking boundary aligned with the current GT42 capability baseline and the P0–P5 Product Track.

## 1. Principle

GeoTask should not create commercial value by artificially weakening the open Core. The public Core and protocols should remain strong enough to define, validate, replay and extend trusted spatiotemporal task/state contracts.

Commercial value, when real customers pull it, comes from governed integration, private data/connectors, proprietary industry packs, operational review/approval workflow, deployment hardening, audit operations and long-term support.

## 2. Remains open

The project intends to keep the following public and reusable:

- Task/Object/Claim language and schemas;
- deterministic Core operators and verification semantics;
- World State / Observation / transition and correction artifacts;
- Evidence Request and Verification Provider contracts;
- Dependency / Impact / bounded recomputation and reevaluation contracts;
- Control Evaluation / action-boundary semantics;
- Artifact/Schema Registry and offline validation;
- Agent Integration and public Runtime Interface contracts;
- public-safe mock/reference adapters and endpoints;
- Operator/Provider/Artifact extension SDKs and contracts;
- Reference Agent and fictional replayable examples;
- public quality/conformance benchmark methodology.

## 3. Belongs outside Core

The following should normally stay in industry systems, private packs or customer deployments rather than being copied into Core:

- authoritative customer/business databases;
- real industry rules, thresholds and scoring models;
- private or licensed data;
- customer-specific evidence ranking and approval policies;
- credentials and production data connectors;
- proprietary report templates and workflows;
- production database writes and publication operations;
- customer-specific audit retention, access-control and deployment configuration;
- patent-sensitive optimization implementations that are not required for open protocol interoperability.

## 4. Enterprise is demand-triggered

Potential private/enterprise capabilities include:

- Private Artifact/Capability Registry;
- identity/access and approval workflow;
- provider/rule governance;
- audit retention/export;
- private connectors and credential governance;
- deployment hardening and long-term compatibility/support.

Do not build a large separate Enterprise platform before real customer demand exists.

## 5. Ecosystem boundary

Third-party providers/operators/packs may contribute capability, but they do not gain the right to bypass GeoTask verification or announce final truth/authorization.

A trustworthy extension must declare, as applicable:

- Claim/output;
- evidence/provenance;
- method and version;
- applicable scope;
- validity/freshness;
- failure conditions;
- uncertainty;
- dependencies;
- side-effect/action boundary.

## 6. Marketplace is deferred

The ecosystem progression is:

```text
Contract → Pack → Registry → Partner Validation → Open Developer Platform → Marketplace if demand exists
```

A public Marketplace is not a current milestone. It should be considered only after independently maintained reusable extensions and real transaction/deployment demand exist.

## 7. Cross-line Promotion Gate

A capability built for Lowa-GT or another industry does not automatically become Core. Lowa Product, Lowa-GT Integration and GeoTask Core retain separate ownership: business facts stay in Lowa Product, validation/candidate evidence stays in Integration, and generic abstractions stay in Core.

Any ownership transfer across these lines requires the explicit [`Cross-Line Promotion Gate v0.1`](reference/cross-line-promotion-gate-v0.1.md). A successful Integration test is not a promotion decision. Promotion into Core requires:

1. industry-neutral semantics;
2. reuse in at least a second independent system/industry;
3. deterministic/fail-closed/replayable behavior compatible with Core;
4. no requirement for Core to own the industry System of Record;
5. Core-native public-safe verification independent of live Lowa infrastructure;
6. explicit compatibility and migration review.

Normal consumption of an existing Core contract does not change ownership and therefore is not promotion. Moving a schema, semantic rule, implementation responsibility or public compatibility commitment between lines does.

## 8. Non-negotiable boundary

Open or private, no component may silently collapse:

```text
supported/verified
→ eligible
→ authorized
→ released
→ sent
→ executed
```

Each transition requires explicit semantics and, where applicable, an external workflow/action record.