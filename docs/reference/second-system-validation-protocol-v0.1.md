# GeoTask Second-System Validation Protocol v0.1

**Status:** public validation protocol; no second-system result recorded yet
**Date:** 2026-08-09
**Purpose:** turn the Core Promotion Gate requirement for independent reuse into an executable, reviewable validation step without promoting Lowa-specific semantics into Core.

## 1. Why this protocol exists

The first real Lowa-GT integration has demonstrated that some candidate abstractions are useful in one production-shaped industry workflow. That is not enough for GeoTask Core promotion.

The Cross-Line Promotion Gate requires independent reuse in a second system or industry before a candidate may enter Core. A second fixture of the same Lowa workflow does not count.

This protocol defines what evidence must exist before a candidate can even be submitted for a Core Promotion Gate review.

## 2. First candidate to scout

The first candidate selected for second-system scouting is the neutral dependency relation state:

```text
matched
changed
not_declared
unverifiable
```

This candidate is selected because the problem is not inherently low-altitude-specific: a derived result may depend on named upstream artifacts or inputs, and a verifier may need to determine whether the dependency still matches the current referenced material.

This selection is **not** a Core Promotion decision. The candidate remains `DEFER` until real independent reuse evidence exists and every Core gate condition is reviewed.

## 3. What the second system must demonstrate

The second system must be independently owned from Lowa Product and must have its own authoritative business state. It may be in another industry or an independently governed system with a materially different domain workflow.

The validation must show a real need to answer all of the following without importing Lowa terminology:

1. What upstream dependency did a derived result declare?
2. What current upstream material is being compared against that declaration?
3. Can the relation be determined as `matched`, `changed`, `not_declared`, or `unverifiable`?
4. When evidence is missing or ambiguous, does the verifier fail closed rather than inventing equivalence?
5. Can the decision be replayed from stable identifiers and content evidence?
6. Does the verifier remain read-only with respect to the second system's authoritative state?

## 4. Evidence package

A valid second-system package must contain:

- an anonymized system identifier and owner line;
- a short problem statement in that system's own language;
- at least one real derived-result/dependency pair or equivalent source-owned record;
- the current referenced upstream material or a stable hash/reference that can be independently checked;
- at least one `matched` case;
- at least one non-matching or non-provable case (`changed`, `not_declared`, or `unverifiable`);
- deterministic replay instructions;
- explicit side-effect assertions showing the validation did not mutate authoritative state;
- a statement of what domain semantics are intentionally excluded from the candidate abstraction.

Synthetic examples may be used to build tooling, but they do **not** satisfy the independent-reuse gate.

## 5. Required separation from Lowa

The second-system evidence must not qualify merely by changing names in a Lowa fixture. At minimum:

- it must not use Lowa AssessmentRecord or report-publication semantics as its source of truth;
- it must not reuse the Lowa database as the authoritative system;
- it must not depend on Lowa-only thresholds, workflow states, or low-altitude policy facts;
- its owner must be able to explain the dependency problem without reference to the Lowa implementation.

## 6. Machine pre-review

Use `docs/reference/core-promotion-candidate-template.yaml` to create a candidate record and run:

```bash
python3 tools/evaluate_core_promotion_candidate.py candidate.yaml --format json
```

The machine result is intentionally limited to:

- `defer` — evidence or one or more Core entry conditions are missing;
- `eligible_for_gate_review` — the record is complete enough for an explicit architecture review.

The tool never returns `PROMOTE`. A human/reviewable Promotion Gate decision remains mandatory.

## 7. Gate conditions checked by the pre-review

For promotion into Core, the record must explicitly support all seven Cross-Line Promotion Gate conditions:

1. industry-neutral semantics;
2. real independent reuse evidence from a second system/industry;
3. deterministic, fail-closed, replayable behavior;
4. no System-of-Record capture;
5. no hidden side-effect expansion;
6. Core-native public-safe verification;
7. explicit compatibility/migration impact review.

The machine tool checks record completeness and declared evidence references. It does not independently prove that a human claim is true.

## 8. Current status

```text
Candidate: dependency relation state
First-system evidence: Lowa-GT Integration exists
Second-system evidence: NOT YET RECORDED
Core primitive added: NO
Automatic promotion: IMPOSSIBLE
Current formal outcome: DEFER
```

Until a real second-system package exists, the correct architectural action is to keep the candidate outside Core.
