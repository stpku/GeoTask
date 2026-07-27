# GeoTask Evidence, Conflict, Blocking, and Recovery

GeoTask examples use structured workflow extensions to handle missing evidence, conflicting evidence, blocked outputs, and resumable execution. These patterns live above Core claim execution and MUST NOT be confused with deterministic operator semantics.

## 1. Why Evidence Is Part of the Task

A spatial proposition can be geometrically valid but operationally unverifiable because a required schedule, authority, version, or source is missing. A reliable system should not silently replace missing evidence with a model guess.

Example:

```text
route intersection = true
altitude overlap = true
restricted schedule = unknown
```

The correct complete result is not automatically `true` or `false`. The task is `unverifiable` until the missing schedule evidence is supplied.

## 2. Evidence Request Pattern

Recommended structure:

```yaml
extensions:
  evidence_request:
    id: verify-restricted-schedule
    trigger: temporal_condition_unverifiable
    reason: restricted_schedule_not_verified
    required_fields:
      - issuing_authority
      - effective_date
      - start_time
      - end_time
      - document_version
      - source_reference
      - verified_at
    blocked_outputs:
      - full_conflict
      - automatic_approval
    resume_when: restricted_schedule_verified == true
    next_action: request_evidence
    expected_status: unverifiable
```

### 2.1 Required Fields

An evidence request SHOULD include:

| Field | Purpose |
|---|---|
| `id` | Stable request id. |
| `trigger` | Condition that created the request. |
| `reason` | Machine-readable explanation. |
| `required_fields` | Concrete evidence items needed to continue. |
| `blocked_outputs` | Results or actions that cannot be released. |
| `resume_when` | Explicit condition for resuming. |
| `next_action` | What the workflow should do now. |
| `expected_status` | Current workflow state. |

Avoid vague requests such as “provide more information.” Name the issuing authority, version, time interval, source reference, or other exact fields needed for recomputation.

## 3. Blocking Is Operational, Not Cosmetic

A warning banner is not a safety gate. If evidence is required for a decision, the dependent outputs MUST be blocked.

Example:

```yaml
blocked_outputs:
  - launch_clearance
  - automatic_dispatch
```

A blocked output MUST NOT be emitted through another field, fallback response, or model explanation. The system should record the block reason and expose the recovery path.

## 4. Resume Conditions

A resume condition should be testable:

```yaml
resume_when: available_range_km >= total_required_range_km
```

or:

```yaml
resume_when: evidence_conflict_resolved == true
```

A resume condition SHOULD identify the exact state change required. Avoid conditions such as `when_safe` unless `safe` is a separately computed and auditable proposition.

After the condition becomes true, dependent assertions SHOULD be recomputed. Do not simply change `blocked` to `approved` without rerunning the affected logic.

## 5. Conflicting Evidence

Two evidence items may each be authentic and verified while still making incompatible claims.

Example:

```text
Authority notice A: restricted 08:30–10:00
Operations bulletin B: restricted 09:30–11:00
Mission window: 08:00–09:00
```

Both documents may have valid source references and versions. Yet one produces temporal conflict `true` and the other `false`.

Correct state:

```text
source A = verified
source B = verified
cross-source consistency = conflicted
```

“Verified evidence” means each source passed its own checks. It does not mean all verified sources agree.

## 6. Conflict Review Pattern

```yaml
extensions:
  evidence_conflict:
    id: resolve-restricted-schedule-conflict
    subject: restricted_schedule
    conflict_type: incompatible_verified_sources
    conflicting_assertions:
      - temporal_conflict_authority_a
      - temporal_conflict_bulletin_b
    source_refs:
      - authority_notice_a
      - operations_bulletin_b
    compared_fields:
      - start_time
      - end_time
      - document_version
      - source_reference
    blocked_outputs:
      - full_conflict
      - automatic_approval
    resolution_required_fields:
      - authoritative_source
      - superseded_version
      - effective_schedule
      - resolution_basis
      - resolved_by
      - resolved_at
    resume_when: evidence_conflict_resolved == true
    next_action: request_conflict_review
    expected_status: conflicted
```

### 6.1 Why the System Must Not Pick a Source

Without an explicit authority or version rule, the system MUST NOT choose a source because it:

- was published later;
- has a more official-looking title;
- uses stronger wording;
- is more familiar to the model;
- produces the safer-looking answer.

Those heuristics may be valid only when encoded as an authorized rule and supported by evidence.

### 6.2 Conflict Resolution Output

A conflict decision SHOULD record:

- `authoritative_source`
- `superseded_version`
- `effective_schedule` or effective content
- `resolution_basis`
- `resolved_by`
- `resolved_at`

The result must be traceable and replayable.

## 7. Resource and Capability Gates

Evidence patterns generalize to other feasibility gates.

### 7.1 Energy Margin

```yaml
mission_gate:
  status: blocked
  reason: insufficient_range_after_required_reserve
  blocked_outputs:
    - launch_clearance
    - automatic_dispatch
  selected_action: request_recharge_or_replan
  resume_when: available_range_km >= total_required_range_km
  next_action: recover_energy_margin
```

### 7.2 Clearance Margin

```yaml
passage_gate:
  status: blocked
  reason: insufficient_lateral_clearance
  blocked_outputs:
    - autonomous_passage
    - full_speed_entry
  selected_action: request_alternate_route_or_controlled_passage
  resume_when: available_width_m >= required_envelope_width_m or controlled_passage_authorized == true
  next_action: recover_clearance_margin
```

The same pattern applies:

```text
explicit requirement
+ measured or computed capability
→ gap
→ blocked outputs
→ recovery action
→ resume condition
→ recomputation
```

## 8. Action Contracts

A useful next action is more than a label. It SHOULD carry enough information to execute or route the task.

Robot wait example:

```yaml
selected_action: robot_b_wait
proceed_robot: robot_a
wait_robot: robot_b
hold_at: robot_b_holding_point
wait_duration_minutes: 4
revised_entry_time: "08:36"
revised_exit_time: "08:41"
resume_when: robot_a_cleared_corridor == true and current_time >= "08:36"
next_action: coordinate_passage
```

An action contract SHOULD identify:

- actor;
- target or resource;
- location;
- start/end time or duration;
- policy basis;
- blocked alternatives;
- resume or completion condition;
- expected status.

## 9. Three-Valued Composition

For a required `AND` rule:

| A | B | A AND B |
|---|---|---|
| true | true | true |
| false | any | false |
| unknown | true | unknown |
| unknown | unknown | unknown |

For a required `OR` rule:

| A | B | A OR B |
|---|---|---|
| true | any | true |
| false | false | false |
| unknown | false | unknown |
| unknown | unknown | unknown |

`unknown` represents an unverifiable proposition, not a third business answer. A task may map unknown to an evidence request or review action.

## 10. Provenance Rules

Evidence fields SHOULD record:

- source id or reference;
- issuing authority or owner;
- version;
- effective time;
- retrieved or observed time;
- verification method;
- verifier;
- hash or immutable locator when available.

A model summary of a document is not equivalent to the original source. Preserve the original source reference and mark the summary as model-generated.

## 11. Security and Public Boundary

Public examples may demonstrate evidence and recovery structure using fictional data. Real regulatory decisions, customer thresholds, internal source rankings, private connectors, and production approval logic should remain in a Domain Pack or private Runtime.

Do not commit:

- real credentials;
- confidential notices;
- customer identifiers;
- private approval matrices;
- patent-sensitive optimization rules not cleared for publication.

## 12. Validation Checklist

- [ ] Is the missing or conflicting subject explicit?
- [ ] Are required fields concrete and testable?
- [ ] Are unsafe outputs actually blocked?
- [ ] Is the next action executable or routable?
- [ ] Is the resume condition machine-testable?
- [ ] Will dependent calculations be rerun after recovery?
- [ ] Are provenance and assurance recorded separately?
- [ ] Does a human review identify the reviewer and time?
- [ ] Are domain-sensitive rules kept outside Core?

## 13. Examples

- `examples/core/unverifiable_constraint.yaml`
- `examples/core/evidence_request_plan.yaml`
- `examples/core/evidence_conflict_review.yaml`
- `examples/core/robot_corridor_coordination.yaml`
- `examples/core/uav_energy_reserve.yaml`
- `examples/core/vehicle_clearance_envelope.yaml`

## 14. Related Documents

- [Status and Assurance Model](status-model.md)
- [Language and Execution Specification](../spec/geotask-language-spec-v1.0.md)
- [GT01–GT13 Cookbook](../cookbook/gt01-gt13.md)
- [White Paper](../whitepaper/GeoTask_White_Paper_v0.1.md)
