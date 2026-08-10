# GeoTask Reference Agent v0.1 — Facility Assessment Update

This is the first public end-to-end Reference Agent implementation defined by [`docs/reference/reference-agent-v0.1.md`](../../../docs/reference/reference-agent-v0.1.md).

It is **not GT43**. GT01–GT42 remain the Capability Track; this example belongs to the P1 Product Track and composes existing public GeoTask capabilities into one lifecycle.

## Question

A fictional low-altitude facility already has a current obstacle-clearance assessment and decision report. New map evidence arrives. The Agent must determine:

- whether the new evidence is usable, missing, stale, or conflicting;
- whether the obstacle position can enter a successor World State;
- which assessment dependency must be recomputed;
- which unrelated assessment sections remain reusable;
- whether the report refresh is eligible;
- what still has **not** happened in the production world.

All data in this directory is fictional.

## Replay

After installing GeoTask Core, the shortest activation path is:

```bash
geotask agent demo --output ./geotask-reference-agent
cd geotask-reference-agent
```

This verifies the packaged Reference Agent bundle, materializes a developer-owned copy, and replays `success` without fetching external truth or authorizing an action.

From a source checkout, the canonical example remains directly runnable:

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py --scenario success --check-expected
```

Available fixed scenarios:

```text
success
missing_evidence
conflicting_evidence
stale_evidence
contradicted
```

For example:

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py --scenario conflicting_evidence --check-expected
```

The script also works when `geotask-core` is installed as a package.

## Lifecycle

```text
natural-language request
→ structured GeoTask proposal/task
→ bounded baseline World State
→ map Observation(s)
→ freshness/conflict resolution
→ deterministic distance_2d recomputation
→ bounded successor state when evidence is usable
→ declared bounded impact graph
→ Control Evaluation
→ report_update_eligible or blocked/unknown
→ production_report_refreshed = false
→ action_executed = false
```

The replay now uses the existing registered World-State Cycle contracts rather than inventing a parallel workflow. When fresh evidence is accepted it first materializes an **observation-state** snapshot that updates only the obstacle position while intentionally leaving the old assessment stale. It then creates and validates a registered `geotask.discrepancy-report`, `geotask.correction-request`, and `geotask.impact-graph` bundle before materializing the reevaluated successor. Human approval remains a separate Control Evaluation concern because the public `Correction Request state=required` contract intentionally separates deterministic correction from review workflow.

The small `impact_scope` summary remains in the Reference Agent output as a developer-facing explanation of affected and reused business concepts; the registered `impact_graph` inside `registered_impact_bundle` is the normative Core artifact for the bounded correction chain.

## Scenario semantics

| Scenario | Evidence state | Verification | Control | Successor | Report update |
|---|---|---|---|---|---|
| `success` | fresh and unambiguous | `satisfied` | `satisfied` | materialized | eligible only |
| `missing_evidence` | absent | `unverifiable` | `unknown` | not materialized | blocked |
| `conflicting_evidence` | fresh but conflicting | `conflicted` | `unknown` | not materialized | blocked |
| `stale_evidence` | outside declared validity | `unverifiable` | `unknown` | not materialized | blocked |
| `contradicted` | fresh and unambiguous | `contradicted` | `blocked` | materialized | blocked |

`conflicted` is a Reference Agent lifecycle state. The underlying public Core still preserves its existing Artifact/status contracts; this example does not add a new Core enum merely to label the orchestration state.

## Bounded impact

Only this dependency chain is declared affected:

```text
mapped-obstacle-01.position_xy
→ obstacle_distance_m
→ assessment-FAC-001.obstacle_clearance_pass
→ report-v4.safety.obstacle_clearance
→ review:FAC-001:obstacle-clearance
```

The following are explicitly reused:

- `assessment-FAC-001.accessibility_score`;
- `assessment-FAC-001.service_capability_score`;
- `report-v4.operator_summary`.

This is intentional: GeoTask should not turn one evidence change into an implicit global rescore.

## Safety boundary

Every scenario keeps the following false:

```text
production_write_performed
production_report_refreshed
action_authorized
action_executed
```

Even the success scenario means only that an **external industry workflow may perform a later write if its own authority explicitly approves it**. The Reference Agent itself does not perform that write.
