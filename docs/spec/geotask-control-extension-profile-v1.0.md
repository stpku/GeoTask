# GeoTask Control Extension Profile v1.0

Status: implemented public profile  
Profile identifier: `geotask.control`  
Profile version: `1.0`

## 1. Purpose

GeoTask Core keeps `extensions` open so that applications and Domain Packs can carry domain state without changing Core operators. Open mappings are useful for experimentation, but repeated control structures such as evidence requests, evidence conflicts, task gates, and three-valued decision rules need a stable contract once they are exchanged between tools.

The Control Extension Profile defines that contract. It standardises reusable workflow-control structures while deliberately leaving domain-specific state open. Fields such as `arrival_state`, `vehicle_envelope`, `energy_budget`, `ground_clearance_evidence`, or `dedup_rule` remain application data and are not owned by this profile.

## 2. Opt-in declaration

A document opts into strict validation by declaring:

```yaml
extensions:
  extension_profile:
    id: geotask.control
    version: "1.0"
```

Documents without `extension_profile` retain the original open-extension behaviour. This preserves compatibility with existing GeoTask v1.0 documents and private Domain Packs.

A declared `geotask.control/1.0` profile MUST contain at least one of:

- `decision_rule`
- `evidence_request`
- `evidence_conflict`
- `task_gate`

Unknown domain-level siblings remain allowed. Unknown fields inside the four control blocks are rejected.

## 3. `decision_rule`

`decision_rule` records an explicit composition rule without pretending that the expression itself is a registered Core operator.

```yaml
extensions:
  extension_profile:
    id: geotask.control
    version: "1.0"
  decision_rule:
    id: full_conflict
    logic: three_valued_and
    expression: route_intersects_zone AND altitude_conflict AND temporal_conflict
    unknown_policy: propagate
    expected_status: unverifiable
```

Required fields are `id`, `logic`, and `expression`. `unknown_policy` and `expected_status` are optional non-empty strings.

## 4. `evidence_request`

`evidence_request` converts an unverifiable assertion into an explicit request for missing evidence.

```yaml
extensions:
  extension_profile:
    id: geotask.control
    version: "1.0"
  evidence_request:
    id: verify-restricted-schedule
    trigger: temporal_conflict
    trigger_status: unverifiable
    reason: restricted_schedule_not_verified
    required_fields:
      - issuing_authority
      - effective_date
      - document_version
      - source_reference
      - verified_at
    blocked_outputs:
      - full_conflict
      - automatic_approval
    resume_when: restricted_schedule_verified == true
    next_action: request_evidence
```

`trigger` MUST reference an assertion in the same GeoTask document. `required_fields` and `blocked_outputs` MUST be non-empty lists of unique non-empty strings.

## 5. `evidence_conflict`

`evidence_conflict` records disagreement between at least two evidence-derived assertions and identifies what must be resolved before blocked outputs can resume.

```yaml
extensions:
  extension_profile:
    id: geotask.control
    version: "1.0"
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
    blocked_outputs:
      - full_conflict
      - automatic_approval
    resolution_required_fields:
      - authoritative_source
      - superseded_version
      - resolution_basis
      - resolved_at
    resume_when: evidence_conflict_resolved == true
    next_action: request_conflict_review
    expected_status: conflicted
```

`conflicting_assertions` MUST contain at least two unique assertion references. `source_refs` MUST contain at least two unique source identifiers.

## 6. `task_gate`

`task_gate` separates a verified situation from the action currently permitted by that situation.

```yaml
extensions:
  extension_profile:
    id: geotask.control
    version: "1.0"
  task_gate:
    status: blocked_pending_ground_clearance
    selected_action: hold_position_and_request_ground_clearance
    rejected_actions:
      - release_cargo_because_over_target
      - abort_delivery_mission
    blocked_outputs:
      - payload_release_command
      - automatic_drop_authorization
    required_controls:
      - retain_live_ground_clearance_evidence
      - maintain_safe_hover_position
      - reverify_clearance_before_release
    resume_when: ground_zone_clear == true AND clearance_evidence_age_seconds <= 15
    next_action: request_ground_clearance_and_reverify
    expected_status: verified_release_hold
```

Required fields are `status`, `selected_action`, `blocked_outputs`, `required_controls`, `resume_when`, and `next_action`. `rejected_actions` and `expected_status` are optional.

Domain measurements and result statistics MUST remain in sibling domain structures rather than being added as ad hoc `task_gate` fields. For example, `dispatch_task_count` belongs in a deduplication result structure, while the gate only records which dispatch action is permitted.

## 7. Validation behaviour

GeoTask Core validates the profile during `validate_document()` and `validate_canonical()`.

The profile adds two stable diagnostic codes:

- `unsupported_extension_profile`: the declared profile identifier or version is not implemented;
- `extension_profile_violation`: the declared profile violates a profile-level rule, such as an empty or duplicate control list.

Existing Core diagnostics are reused for structural issues:

- `missing_field`
- `unknown_field`
- `invalid_type`
- `invalid_reference`

Profile validation does not execute `resume_when` or expression strings. It validates their presence and structure. A Runtime or Domain Pack may implement expression evaluation, but it MUST NOT report that evaluation as a Core deterministic operator unless the relevant semantics are registered and executed.

## 8. Compatibility and evolution

The profile is opt-in. Omitting `extension_profile` keeps extensions open and avoids retroactive breakage. Producers should declare the profile once they rely on interoperable control structures.

A future incompatible contract will use a new version. Implementations MUST reject unsupported declared versions rather than silently interpreting them as `1.0`.
