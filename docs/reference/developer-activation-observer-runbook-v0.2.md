# GeoTask External Developer Activation Observer Runbook v0.2

Use this runbook only with `developer-activation-protocol-v0.2.md` and `developer-activation-result-template-v0.2.yaml`.

## 1. Before the session

- Confirm the participant qualifies as an unfamiliar real external developer under the v0.2 protocol.
- Assign an anonymized alias such as `tester-01`.
- Start from the public GeoTask material; do not provide private implementation history.
- Prepare a fresh environment that can install the public package.
- Do not pre-fill success values in the result template.

## 2. Start the clock

Record `started_at` immediately before the participant begins from the public entry point.

Do not teach Artifact names first. The participant should initially see the same onboarding path a normal developer sees.

## 3. Observe 0–5 minute discovery

Record whether the participant finds the relevant Quickstart/Reference Agent entry point without help.

Do not fail the session merely because a participant does not know internal terms. The relevant observation is whether they can state the value story in ordinary language: a changed fact changes state, affects dependent conclusions, and does not itself authorize a real action.

## 4. Observe Product Activation

The participant should independently:

1. materialize the Reference Agent;
2. run the fixed `success` scenario;
3. change one real scenario input without changing Core source;
4. replay the custom scenario and identify a deterministic result change.

When these steps are complete, record `product_activation_completed_at` immediately.

The template contains `product_activation_completed_within_15_minutes`; set it from the observed timestamps. The aggregator recomputes it and rejects inconsistent records.

**Do not stop a valid session at minute 15.** The 15-minute result is a product metric, not a standalone v0.2 pass/fail condition.

## 5. Observe 15–30 minute comprehension

Ask the participant to explain, without requiring exact protocol vocabulary:

### Bounded impact

A passing explanation must communicate that a changed fact should invalidate/recompute dependent conclusions rather than blindly recomputing or silently overwriting everything.

Set `understood_bounded_impact: true` only when that idea is clear.

### Action boundary

A passing explanation must distinguish technical eligibility from authorization and actual execution.

Set `understood_eligible_not_executed: true` only when the participant understands that:

```text
eligible != authorized != executed
```

### Advanced metrics

Also record, without making either one a v0.2 first-activation blocker:

- `understood_rev1_rev2_rev3`;
- `understood_unknown_not_false`.

These support longitudinal analysis and Advanced Comprehension follow-up.

## 6. Help events

If observer help is necessary, first record:

```yaml
help_events:
  - minute: <elapsed minute>
    issue: "<what blocked the participant>"
    intervention: "<exact help provided>"
```

Do not erase a help event after the participant succeeds.

## 7. Repository defect handling

If the fixed replay fails because the repository/package is reproducibly defective:

- set `first_replay_succeeded: false`;
- set `first_replay_failure_repository_defect: true`;
- add at least one specific `repository_defects` entry.

Never use the defect override for user error, environment misunderstanding, or an unverified suspicion.

A defect remains a product follow-up even when it satisfies the fixed-replay availability check.

## 8. Close the session

Record `completed_at` when the observation session ends and set `completed_within_30_minutes` from the timestamps. The aggregator recomputes this flag.

Complete:

- `confusion_points`;
- `documentation_gaps`;
- `participant_summary`;
- `observer_notes`.

Do not include personally identifying information.

## 9. Aggregate only after real sessions exist

Example:

```bash
python tools/summarize_developer_activation.py \
  participant-01.yaml participant-02.yaml participant-03.yaml \
  --format markdown
```

Do not combine v0.1 and v0.2 records in the same aggregation run.

Automated tests may verify the aggregator, but they **never count as external participants**.
