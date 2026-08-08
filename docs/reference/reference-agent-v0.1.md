# GeoTask Reference Agent v0.1 Specification

**Status:** P1 implementation + developer materials complete; external developer activation validation pending  
**Date:** 2026-08-07  
**Public scenario:** fictional low-altitude facility assessment update  
**Executable example:** `examples/reference_agent/facility_assessment_update/`  
**Tutorials:** `docs/tutorials/reference-agent.zh-CN.md` / `docs/tutorials/reference-agent.md`  
**Experience page:** `site/reference-agent/`  
**Product quality benchmark:** `docs/reference/verification-quality-benchmark-v0.1.md`  
**Purpose:** prove the complete GeoTask development pattern with existing public Core artifacts, not create another isolated GT case.

The executable slice covers the five fixed scenarios, deterministic `distance_2d` replay, developer-supplied scenario files, strict Observation/World State loading, an immutable revision-1 baseline, revision-2 observation state, registered Discrepancy/Correction/Impact artifacts, bounded revision-3 reevaluation, Evidence Request behavior, and Control Evaluation. Code, tests, public-export integration, tutorial, and experience page are present. P1 is not yet declared fully validated until unfamiliar external developers complete the documented activation exercise and the observed time/confusion points are recorded.

## 1. Goal

The first Reference Agent demonstrates one end-to-end chain:

```text
new observation / evidence
→ explicit world-state update
→ conflict, freshness, missing-evidence and identity checks
→ bounded impact identification
→ bounded recomputation / reevaluation
→ human review or approval gate
→ output becomes eligible for update
→ no automatic publication and no real-world action
```

This Reference Agent is the P1 product gate. GT case count is not an acceptance criterion.

## 2. Scenario

A fictional low-altitude facility already has a current evidence bundle, assessment and decision report. A new webpage observation, map-derived fact or human review result arrives.

The Agent must answer:

> What changed, which claims and assessment outputs are affected, what remains unknown or conflicting, what must be reviewed, and whether the report is eligible to be refreshed?

The public scenario uses only fictional data and does not connect to a production low-altitude system.

## 3. Responsibilities

### Agent

The Agent may:

- interpret the user request;
- propose a structured task;
- select declared public artifacts and providers;
- explain the resulting verification state;
- request missing evidence through an explicit Evidence Request artifact.

The Agent must not:

- declare an external tool result to be true without verification;
- invent source precedence;
- convert missing evidence to `false`;
- enlarge the impact scope beyond declared dependencies;
- publish a report or claim that a real action occurred.

### GeoTask Core

Core is responsible for deterministic structure, binding and semantic validation using public contracts already present in the repository, including World State, Observation, Verification Provider, Impact Graph, incremental reevaluation and Control Evaluation artifacts.

Core does not fetch production evidence, mutate a production database, publish a production report or execute a real-world action.

## 4. Required lifecycle

### Step 1 — Proposal

Input is a natural-language request to reassess one fictional facility after new evidence arrives. The Agent produces a structured proposal/task. Proposal is not World State.

### Step 2 — Trusted snapshot

Build or load a bounded World State snapshot that contains only the objects and attributes required for this facility-assessment update.

Each relevant fact must preserve source/evidence references, validity and version information according to existing public contracts.

### Step 3 — Verification

Evaluate declared conditions. Required public outcomes include at least:

- `satisfied` / equivalent verified state;
- `contradicted`;
- `unverifiable` for missing or stale evidence;
- explicit conflict when independently valid inputs disagree and no resolution policy is declared.

Unknown must never be silently coerced to false.

### Step 4 — Evidence request

When a required condition is unverifiable, emit an explicit request that states:

- what evidence is missing;
- why it is needed;
- which output(s) remain blocked;
- what condition allows reevaluation to resume.

### Step 5 — State delta / successor state

New evidence must produce a bounded successor state or existing bounded materialization artifact. The baseline snapshot remains immutable.

### Step 6 — Impact

Use an explicit finite dependency/impact graph. The Reference Agent must identify only the affected claim, assessment section, decision/report output and review target. Unrelated facility facts and unrelated report sections must remain reusable.

### Step 7 — Bounded recomputation / reevaluation

Recompute only allowlisted deterministic values and reevaluate only declared affected targets. No arbitrary Python execution, model execution or hidden global recomputation is allowed inside Core.

### Step 8 — Human gate

If the resulting report may be refreshed only after human review, Control Evaluation must explicitly keep the production operation blocked until the required approval/review condition is satisfied.

### Step 9 — Eligible is not executed

Even when all declared conditions pass, the final public artifact must distinguish at least:

```text
report_update_eligible = true
production_report_refreshed = false
action_executed = false
```

### Step 10 — Replay

A fixed artifact bundle must reproduce the same verification, impact and control result byte-for-byte or semantically according to the existing deterministic artifact contracts.

## 5. Minimum scenario matrix

The implementation must ship at least five fixed scenarios.

| Scenario | Trigger | Expected top-level behavior |
|---|---|---|
| success | fresh compatible evidence; all declared conditions satisfied | update eligible; not published/executed |
| missing evidence | required source/evidence absent | `unverifiable`; Evidence Request emitted |
| conflicting evidence | two valid independent sources disagree; no resolution policy | conflict / unresolved; no invented precedence |
| stale evidence | evidence exists but validity/freshness fails | `unverifiable`; affected output blocked |
| explicit contradiction | verified evidence proves one required condition false | blocked / contradicted |

## 6. Suggested repository layout

```text
examples/reference_agent/facility_assessment_update/
  README.md
  request.txt
  task.yaml
  world_state_before.json
  observations/
  evidence/
  impact_graph.json
  control_evaluation.json
  scenarios/
    success/
    missing_evidence/
    conflicting_evidence/
    stale_evidence/
    contradicted/
  replay.py
  quality_benchmark.py

tests/
  test_reference_agent_facility_assessment_update.py
  test_reference_agent_quality_benchmark.py
```

The implementation may reuse existing artifact files from `examples/core/` where appropriate; duplication should be minimized.

## 7. Acceptance criteria

P1 v0.1 is complete only when:

1. one command or documented script replays the full fixed bundle;
2. all five scenarios pass deterministic tests;
3. every critical conclusion can be traced to exact evidence/version references;
4. missing/conflicting/stale evidence fails closed;
5. impact scope excludes unrelated facts and outputs;
6. no automatic publication, database write or real-world action exists;
7. a developer unfamiliar with the GT sequence can understand the lifecycle without reading GT01–GT42 first.

## 8. Non-goals

v0.1 does not:

- connect to live Lowa-GT production data;
- create a new low-altitude database or world-model System of Record;
- implement real regulatory approval;
- automatically rescore or publish a production report;
- add GT43 merely to represent this scenario;
- introduce Marketplace, multi-tenant billing or a second production model provider.

## 9. Relationship to existing GT capabilities

The Reference Agent composes existing capabilities rather than replacing them. In particular it should reuse the already published Evidence Request, World State Cycle, Verification Provider, Impact/Recompute, Control Evaluation, dynamic object and identity-governance primitives where they are genuinely required.

New Core primitives are added only if implementation exposes a generic gap that cannot be expressed with existing public contracts.