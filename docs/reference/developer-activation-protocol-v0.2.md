# GeoTask P1 External Developer Activation Protocol v0.2

**Status:** candidate external-validation protocol  
**Date:** 2026-08-13  
**Scope:** first-use Product Activation and bounded-control comprehension  

## 1. Purpose

This protocol tests whether a developer who did not follow GeoTask's implementation history can independently discover, run, modify, and correctly interpret the public Reference Agent.

v0.2 intentionally separates **first-use Product Activation** from **Advanced Architecture Comprehension**. It lowers terminology burden, not verification or control standards.

A passing record never means production authorization, real-world truth, or action execution.

## 2. Historical compatibility

`developer-activation-protocol-v0.1.md` remains immutable as the interpretation baseline for all v0.1 participant records.

v0.2 does **not** reinterpret v0.1 evidence. Records MUST declare both:

```yaml
schema_version: "0.2"
protocol_version: "0.2"
```

The aggregation tool rejects unsupported or mixed protocol versions in one report.

## 3. Participant eligibility

A qualifying participant must be a real external developer who:

- did not implement the tested GeoTask activation flow;
- did not follow the detailed GT01–GT42 implementation history;
- is not an automated test, scripted demo, repository author acting as a participant, or implementation Agent;
- is represented only by an anonymized alias in the public evidence record.

At least **3 qualifying participants** are required before v0.2 can validate P1 external activation.

## 4. Exercise structure

### Phase A — 0–5 minutes: discover the value and entry point

The participant starts from the public README/Quickstart without an observer explaining internal Artifact names.

Record whether the participant can find the entry point without help.

The participant should be able to explain, in ordinary language:

> A new fact changes the current world state; only affected conclusions should be reconsidered; technical eligibility does not mean a real action was authorized or executed.

### Phase B — target by 15 minutes: Product Activation

The participant should:

1. materialize the installed Reference Agent;
2. replay the fixed `success` scenario;
3. modify one real scenario input without changing GeoTask Core source;
4. replay the custom scenario and observe a deterministic output change.

Record `product_activation_completed_at` when these product-activation tasks are complete. The derived `product_activation_completed_within_15_minutes` metric is diagnostic evidence, **not an independent pass/fail gate**.

### Phase C — by 30 minutes: bounded-control comprehension

The participant should explain, in their own words:

- **bounded impact:** a changed fact should trigger reassessment only where a dependency exists rather than unconditional whole-world recomputation;
- **action boundary:** `eligible != authorized != executed`;
- **fail-closed intuition:** unknown, stale, conflicted, or contradicted evidence must not be silently converted into a convenient positive Boolean.

The exact `rev1 → rev2 → rev3` lifecycle is still recorded, but is an **Advanced Comprehension metric**, not a first-activation blocking gate in v0.2.

## 5. Observer intervention

Observers may rescue a blocked session only after recording a `help_event` containing:

- elapsed minute;
- issue observed;
- intervention provided.

Observers must not silently correct a participant record to create a passing outcome.

If the fixed Reference Agent cannot run because of a reproducible repository defect, record:

```yaml
first_replay_succeeded: false
first_replay_failure_repository_defect: true
repository_defects:
  - "...specific reproducible defect..."
```

A defect override can satisfy only the fixed-replay availability check; the defect still creates a required follow-up.

## 6. v0.2 aggregation gate

For `N` valid v0.2 participants, define:

```text
T = ceil(2N / 3)
```

The core quantitative gate passes only when all four conditions hold:

1. `N >= 3`;
2. every participant either runs the fixed Reference Agent successfully or has a documented repository-defect override;
3. at least `T` participants successfully run a custom scenario without changing Core source;
4. at least `T` **same participants** demonstrate both:
   - `understood_bounded_impact = true`, and
   - `understood_eligible_not_executed = true`.

The following remain metrics, not independent v0.2 blocking gates:

- `product_activation_completed_within_15_minutes`;
- `completed_within_30_minutes`;
- `entrypoint_found_without_help`;
- `understood_rev1_rev2_rev3`;
- `understood_unknown_not_false`.

They remain important for product and documentation improvement.

## 7. Follow-up rule

Even when the quantitative gate passes, the decision is `validated_with_followups` if any of the following exists:

- the same normalized confusion point appears for at least 2 participants;
- any repository defect is recorded;
- any documentation gap is recorded.

Otherwise the decision is `validated`.

If any core gate fails, the decision is `not_yet_validated`.

## 8. Required record bundle

Use `developer-activation-result-template-v0.2.yaml` and the v0.2 observer runbook. Aggregate only real records with:

```bash
python tools/summarize_developer_activation.py participant-01.yaml participant-02.yaml participant-03.yaml
```

The aggregator selects semantics from the declared record version. Do not mix v0.1 and v0.2 records in one report.

## 9. Decision boundary

```text
Product Activation validated
        !=
Advanced Architecture Comprehension complete
        !=
Real-world truth established
        !=
Action authorized
        !=
Action executed
```

A v0.2 PASS therefore means only:

> **At least three real unfamiliar developers produced auditable evidence that the public first-use path is runnable and modifiable, and at least two thirds understood bounded impact together with the action boundary.**
