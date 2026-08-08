# GeoTask Cross-Line Promotion Gate v0.1

**Status:** architecture-governance contract  
**Date:** 2026-08-07  
**Scope:** GeoTask Core, Lowa Product, and Lowa-GT Integration

## 1. Purpose

GeoTask Core, Lowa Product, and Lowa-GT Integration are three independent lines with different ownership:

- **GeoTask Core** owns industry-neutral contracts, deterministic semantics, fail-closed verification, replay, and reusable public abstractions.
- **Lowa Product** owns low-altitude business facts, authoritative records, domain workflows, product UI, human operations, reports, and real writes/actions.
- **Lowa-GT Integration** owns validation of whether existing Core capabilities and candidate abstractions work against Lowa-shaped reality without collapsing the two systems into one codebase or one System of Record.

The Integration line is a validation boundary. It is not a staging branch from which code automatically flows into Core or Lowa.

## 2. Promotion invariant

> **Cross-line capability ownership never changes implicitly. Every ownership transfer requires an explicit Promotion Gate decision.**

Normal dependency use is not promotion. For example, Integration may consume a released Core Artifact contract without a Promotion Gate because Core still owns that contract. Promotion occurs when a capability, schema, semantic rule, implementation responsibility, or public compatibility commitment is proposed to move from one line into another line's owned surface.

A successful Integration experiment creates evidence for a **Promotion Candidate**. It does not create a Core feature by itself.

## 3. What must pass the Gate

A Promotion Gate is required before any of the following becomes owned by another line:

- a new Core public contract, schema, Artifact type, operator, registry entry, SDK/CLI surface, or compatibility promise derived from Integration or Lowa work;
- domain behavior copied from Lowa into Core or re-labelled as generic without independent abstraction evidence;
- Integration-only validation logic converted into a production Lowa capability;
- a responsibility for authoritative state, write-back, approval, report publication, or real action moved across line boundaries;
- a shared component whose ownership would otherwise become ambiguous.

Pure read-only fixtures, adapters, compatibility tests, and references may remain in Integration without promotion as long as their ownership and non-authoritative status stay explicit.

## 4. Promotion Candidate record

Before a Gate decision, the candidate must record at least:

1. **source line** and **target line**;
2. the concrete problem exposed by the source-line work;
3. evidence showing the capability is needed and what the current workaround/cost is;
4. the proposed ownership after promotion;
5. the proposed public/private contract surface;
6. dependencies, failure conditions, side-effect boundary, and compatibility impact;
7. what source-line logic or data is explicitly **not** being promoted.

The record should live in an architecture decision or equivalent reviewable document. Chat discussion, a passing test, or a successful demo is not a Promotion decision.

## 5. Additional Gate for promotion into GeoTask Core

A candidate may enter Core only when all of the following are satisfied:

1. **Industry-neutral semantics:** the abstraction is expressible without Lowa-specific business objects, thresholds, workflow names, database tables, or low-altitude policy facts.
2. **Independent reuse evidence:** the abstraction is independently useful in at least one second system or industry, not merely a second fixture of the same Lowa workflow.
3. **Core behavior:** the behavior can remain deterministic where claimed, fail closed on missing/conflicting inputs, and produce replayable artifacts or results.
4. **No System-of-Record capture:** Core does not become authoritative for the domain's business state.
5. **No hidden side-effect expansion:** promotion does not turn verification eligibility into write, approval, publication, command, or execution authority.
6. **Core-native verification:** public-safe tests and fixtures demonstrate the abstraction without requiring a live Lowa database, private credentials, or Lowa-only runtime behavior.
7. **Compatibility is explicit:** public naming, schema/version impact, migration needs, and failure behavior are reviewed before the capability is added to Core.

Passing only the first Lowa-GT Integration is therefore insufficient for Core promotion.

## 6. Gate outcomes

Every Gate review ends with one explicit outcome:

- **PROMOTE:** ownership moves to the target line under the approved contract and compatibility plan;
- **KEEP_LOCAL:** capability remains owned by the source line and may continue to be consumed through the existing boundary;
- **DEFER:** evidence is insufficient; the candidate remains experimental and no target-line commitment is created;
- **REJECT:** the proposed ownership transfer conflicts with architecture, safety, or product boundaries.

Silence or merged Integration code is never interpreted as `PROMOTE`.

## 7. Lowa Product acceptance remains separate

This Core repository can define the cross-line governance rule, but it does not approve Lowa Product changes. A capability validated by Lowa-GT Integration that is intended to become a Lowa Product feature must still pass Lowa's own product, data, review, deployment, and write-safety acceptance process.

Likewise, a Core Promotion decision does not authorize Lowa production adoption, and a Lowa production decision does not authorize a Core abstraction.

## 8. Relationship to P0-P5 and GT

- **GT Capability Track** proves individual public capabilities; it is not a Promotion mechanism.
- **P3 Industry Integration** may generate Promotion Candidates and reuse evidence.
- **P4 Ecosystem Validation** provides especially strong independent-reuse evidence for Core candidates.
- A new GT number, a P3 success, or an Integration benchmark never bypasses the Promotion Gate.

## 9. Non-negotiable summary

```text
Lowa Product owns business facts.
Lowa-GT Integration validates boundaries and candidates.
GeoTask Core owns generic abstractions.

validation != promotion
consumption != ownership transfer
promotion requires an explicit Gate decision
eligible != executed
```
