# GeoTask P1 Developer Activation Observer Runbook v0.1

**Status:** ready for real external trials
**Date:** 2026-08-09
**Audience:** the observer/organizer, not the participant

## 1. Goal

Run the P1 unfamiliar-developer activation exercise without accidentally coaching the participant or converting a scripted demo into evidence.

The participant receives only the public GeoTask repository (or clean checkout), the top-level README, and normal access to links they discover from there. Do not hand them this observer runbook during the trial.

## 2. Before each trial

1. Confirm the participant has not followed the detailed GT01–GT42 implementation history.
2. Assign an anonymous alias such as `tester-01`.
3. Copy `docs/reference/developer-activation-result-template.yaml` to a private/local results directory outside the public repository history.
4. Replace the alias and start/end timestamp placeholders only with real observations.
5. Do not pre-fill success/comprehension booleans.
6. Start the 30-minute clock when the participant first opens the supplied starting material.

## 3. During the trial

Observe the five protocol tasks in order:

- find and run the Reference Agent;
- explain revision 1 → revision 2 → revision 3;
- explain why `report_update_eligible=true` does not mean a production report was refreshed;
- run one fail-closed scenario;
- modify one real input and rerun it.

Do not tell the participant which file implements the Reference Agent or which documentation page contains the answer unless an intervention is deliberately recorded as a `help_event`.

If intervention is unavoidable, record the minute, the issue, and the exact intervention. Do not erase the help event after the participant succeeds.

## 4. Recording evidence

For every boolean in the result template, record what actually happened. Do not infer a success because a command could have worked in principle.

A failed first replay may be classified as a repository defect only when a concrete defect is observed and recorded in `repository_defects`. Participant environment errors, local shell mistakes, and observer coaching are not repository defects.

Repeated confusion points should use consistent wording where possible so the aggregate tool can identify recurrence across participants.

## 5. After three or more trials

Run:

```bash
python3 tools/summarize_developer_activation.py \
  results/tester-01.yaml results/tester-02.yaml results/tester-03.yaml \
  --format markdown \
  --output developer-activation-report.md
```

Interpretation:

- `validated`: quantitative gate passed and no recorded defect/repeated confusion/documentation gap remains;
- `validated_with_followups`: quantitative gate passed but product follow-ups remain;
- `not_yet_validated`: one or more gate conditions failed;
- invalid evidence: fix the record only from the observer's real notes; never guess a missing result.

## 6. What the observer must not do

- do not count yourself, an implementation agent, CI, or a scripted demo as a participant;
- do not create synthetic participant records to reach three attempts;
- do not rewrite a participant's explanation into the expected terminology and then mark comprehension true;
- do not hide repeated confusion because the repository can be fixed later;
- do not interpret P1 activation success as P3 industry validation, Core Promotion, or production authorization.

Until real records close the gate, repository status remains:

> **P1 implementation and developer materials complete; external developer activation validation pending.**
