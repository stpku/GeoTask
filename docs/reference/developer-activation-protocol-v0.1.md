# GeoTask P1 Developer Activation Protocol v0.1

**Status:** ready for external use; no external results recorded yet  
**Date:** 2026-08-07  
**Target:** unfamiliar developers who have not followed the GT01–GT42 implementation history

## 1. Purpose

This protocol validates a Product Track question that automated tests cannot answer:

> Can a developer who is unfamiliar with GeoTask independently install or open the project, run the Reference Agent, change one real input, and correctly explain why the resulting state changed?

Passing the repository test suite is necessary but does not count as external developer activation.

## 2. Sample

Use at least three unfamiliar developers where practical. They should not receive a walkthrough of GT01–GT42 before the exercise.

Record only a participant alias such as `tester-01`; do not collect unnecessary personal information.

## 3. Time box

Target: **30 minutes per participant** from first opening the instructions to completing the explanation task.

The time box is an evaluation target, not a promise that every new user must finish within 30 minutes.

## 4. Starting material

Give the participant only:

1. either the public `geotask-core` install instruction or the public GeoTask repository URL;
2. `README.md` or `README.en.md`;
3. permission to use the linked documentation normally.

Do not tell them which source files implement the Reference Agent unless they find the links themselves. A pip-installed participant should not need a source checkout merely to discover and start the exercise.

## 5. Tasks

### Task A — Find and run the Reference Agent

The participant should find the Product Track Reference Agent and successfully activate it from an installed package:

```bash
geotask agent demo --output ./geotask-reference-agent
cd geotask-reference-agent
```

A source-checkout participant may run the canonical `replay.py` directly instead. In either path, the first successful replay must be the same deterministic `success` scenario.

Record:

- time to find the entry point;
- time to first successful replay;
- installation/environment errors;
- documentation pages opened before success.

### Task B — Explain the three-state lifecycle

Without being given the answer, ask:

> Why are there revision 1, revision 2, and revision 3 instead of directly changing the final assessment?

A satisfactory explanation should distinguish:

- revision 1: immutable baseline;
- revision 2: accepted Observation updates the obstacle fact while the old assessment remains stale;
- registered Discrepancy/Correction/Impact artifacts identify and bound the required reevaluation;
- revision 3: only affected assessment values are recomputed.

Exact terminology is not required if the semantics are correct.

### Task C — Explain the action boundary

Ask:

> The success scenario says `report_update_eligible=true`. Has the production report been refreshed?

The participant should answer **no** and be able to point to:

```text
production_write_performed = false
production_report_refreshed = false
action_authorized = false
action_executed = false
```

Treat an answer that equates `eligible` with real execution as a critical comprehension failure.

### Task D — Run one fail-closed scenario

Let the participant choose one:

```text
missing_evidence
conflicting_evidence
stale_evidence
contradicted
```

Ask them to explain why the system did not simply return the most convenient Boolean answer.

### Task E — Modify one input

The participant should copy `scenarios/success.json`, change the scenario ID and obstacle coordinates from `[70, 0]` to `[60, 0]`, remove the fixed `expected` block, then run from the materialized workspace:

```bash
python replay.py --scenario-file <their-file>.json
```

They should identify that:

```text
distance_m = 60.0
observation_state_revision = 2
successor_revision = 3
report_update_eligible = true
production_report_refreshed = false
```

This tests whether the project is modifiable rather than merely demonstrable.

## 6. Result fields

Use `docs/reference/developer-activation-result-template.yaml` as the participant-record template and `docs/reference/developer-activation-observer-runbook-v0.1.md` as the observer-only procedure. Keep participant aliases anonymous and record real timestamps with explicit timezone offsets.

For each participant record:

```yaml
schema_version: "0.1"
protocol_version: "0.1"
participant_alias: tester-01
started_at: <timestamp-with-timezone>
completed_at: <timestamp-with-timezone>
completed_within_30_minutes: true|false

entrypoint_found_without_help: true|false
first_replay_succeeded: true|false
custom_scenario_succeeded: true|false

understood_rev1_rev2_rev3: true|false
understood_unknown_not_false: true|false
understood_bounded_impact: true|false
understood_eligible_not_executed: true|false

# Set this only when a failed first replay is attributable to a documented
# repository/product defect rather than participant or environment error.
first_replay_failure_repository_defect: true|false
repository_defects:
  - "..."

help_events:
  - minute: 0
    issue: "..."
    intervention: "..."

confusion_points:
  - "..."

documentation_gaps:
  - "..."

participant_summary: "..."
observer_notes: "..."
```

The aggregate tool recomputes the 30-minute result from `started_at` and `completed_at`; a hand-entered `completed_within_30_minutes` value that disagrees with the timestamps is rejected. A failed first replay counts as a documented repository defect only when `first_replay_failure_repository_defect=true` and at least one concrete `repository_defects` entry exists.

## 7. Aggregate gate

Do not mark P1 external activation as validated merely because one technically experienced participant succeeds.

A recommended initial gate is:

- at least 3 unfamiliar participants attempted the exercise;
- all can run the fixed Reference Agent or every failure has a documented repository defect;
- at least 2/3 can modify and run a custom scenario without source-code changes;
- at least 2/3 correctly explain rev1→rev2→rev3 and `eligible != executed`;
- any repeated confusion point is converted into a documentation, CLI, packaging, or output-shape issue before P1 is declared validated.

After real participant records exist, aggregate them with:

```bash
python3 tools/summarize_developer_activation.py \
  results/tester-01.yaml results/tester-02.yaml results/tester-03.yaml \
  --format markdown \
  --output developer-activation-report.md
```

The tool is intentionally fail-closed:

- fewer than three participant records returns `not_yet_validated`;
- the two-thirds threshold is computed as `ceil(2 * attempted / 3)`;
- lifecycle comprehension and `eligible != executed` must both be correct for the same participant to count toward that comprehension threshold;
- automated tests and implementation agents never increment the participant count;
- repeated confusion points, repository defects, or documentation gaps yield `validated_with_followups` rather than silently reporting a clean validation;
- malformed or internally inconsistent participant records are rejected rather than guessed or repaired.

CLI exit codes are `0` for `validated` or `validated_with_followups`, `2` for `not_yet_validated`, and `1` for invalid evidence records.

This is a product-learning gate, not a statistical benchmark.

## 8. What does not count

The following do **not** independently close this gate:

- the author running the tutorial;
- an implementation Agent running the tests;
- `pytest` passing;
- a scripted demo;
- GitHub stars, views, or article reads;
- a participant who already followed the detailed GT implementation history.

## 9. Output

After the first three trials, produce one bounded report containing:

- anonymized individual result records;
- aggregate completion and comprehension results;
- repeated friction points;
- repository changes made in response;
- a final decision: `validated`, `validated_with_followups`, or `not_yet_validated`.

Until that report exists, the correct repository status remains:

> **P1 implementation and developer materials complete; external developer activation validation pending.**
