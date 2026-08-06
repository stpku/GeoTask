# GeoTask Trajectory and Moving Object Profile v0.1

Status: implemented public profile  
Reference cases: GT33–GT41
Scope: discrete observations, adjacent-sample metrics, caller-declared classifications, bounded scalar acceleration estimates, boundary-sample identity candidates, exact-bound external identity adjudication, review-only identity-merge proposals, non-executing approval records, and bounded object-graph change requests

## Purpose

This profile separates moving-object identity from timestamped spatial observations. It prevents a static polyline from silently standing in for a trajectory and prevents a short observation sequence from being reinterpreted as interpolation, prediction, map matching, or action authorization.

## Moving object

A `moving_object` declares identity only:

```yaml
uav_alpha:
  type: moving_object
  object_class: uav
  identity: fictional-uav-alpha
```

Required fields:

- `object_class`: non-empty caller-declared class;
- `identity`: non-empty caller-declared stable identity.

Position, time, velocity, prediction, and command state do not belong inside the moving object. Unknown fields fail closed.

## Trajectory

A `trajectory` binds explicit observations to one moving object:

```yaml
uav_alpha_track:
  type: trajectory
  subject_ref: uav_alpha
  interpolation: none
  samples:
    - observed_at: "2026-08-05T08:00:00+08:00"
      coordinates: [0, 0]
    - observed_at: "2026-08-05T08:05:00+08:00"
      coordinates: [30, 40]
```

The contract requires:

- `subject_ref` resolves to a declared `moving_object`;
- `interpolation` is exactly `none`;
- at least two samples;
- each sample contains only `observed_at` and `coordinates`;
- `observed_at` is timezone-aware ISO 8601/RFC3339;
- sample times are strictly increasing;
- coordinates are exactly two finite numbers in document coordinate order.

## Deterministic operators

`trajectory_duration_seconds(trajectory)` returns the elapsed seconds between the first and last explicit sample.

`trajectory_segment_metrics(trajectory)` returns one ordered record for every adjacent explicit sample pair. Each record binds the start/end sample indexes, timestamps, and coordinates, then reports:

- `duration_seconds`;
- `distance_in_horizontal_unit`, inherited from the document Space contract;
- `average_speed_in_horizontal_units_per_second`.

The segment operator does not treat average speed as instantaneous velocity and does not interpolate, smooth, resample, predict, map match, verify external truth, publish output, deliver commands, authorize action, or execute action.

`trajectory_segment_classifications(trajectory, parameters...)` extends each adjacent segment with one state from the closed vocabulary `stationary_candidate`, `moving_observed`, `observation_gap`, or `unverifiable`. The caller must explicitly provide:

- `stationary_radius_in_horizontal_unit`, a finite non-negative distance in the document horizontal unit;
- `minimum_stationary_duration_seconds`, a finite positive duration;
- `maximum_observation_gap_seconds`, a finite positive duration;
- `allow_observation_gap`, a boolean that decides whether an excessive interval may be labeled `observation_gap`.

A segment becomes `stationary_candidate` only when its distance is within the declared radius and its duration reaches the declared minimum. A duration above the maximum gap becomes `observation_gap` only when gap marking is allowed; otherwise the segment is `unverifiable`. All other valid segments are `moving_observed`. Core does not select default thresholds, infer lost link or anomaly, prove continuous stationary motion, or interpolate inside a gap.

`trajectory_segment_acceleration_estimates(trajectory, parameters...)` builds one record for every adjacent pair of trajectory segments. The caller must explicitly provide `representative_time_method: segment_midpoint` and a finite positive `maximum_observation_gap_seconds`. Each segment-average speed is bound to its temporal midpoint; scalar acceleration is `(next_average_speed - prior_average_speed) / (next_midpoint_time - prior_midpoint_time)`. When either participating segment exceeds the declared maximum gap, the transition state is `unverifiable` and both speed change and acceleration are `null`. The operator does not claim instantaneous or vector acceleration, infer direction change, interpolate or smooth observations, predict future position, or authorize action.

`trajectory_identity_candidate(first_trajectory, second_trajectory, parameters...)` compares only the first trajectory's final explicit sample with the second trajectory's first explicit sample. The caller must declare a finite positive `maximum_identity_gap_seconds`, a finite non-negative `maximum_identity_distance_in_horizontal_unit`, and boolean `require_same_object_class`. A positive boundary gap above the declared maximum returns `unverifiable` before class or distance evaluation. Otherwise, a required class mismatch or excessive boundary distance returns `different_object_candidate`; a class-compatible boundary within both limits returns `same_object_candidate`. The result preserves both trajectory refs, subject refs, object classes, boundary samples, time gap, distance, and policy. It never merges identities, mutates `subject_ref`, proves real-world identity, interpolates a path, predicts motion, publishes, authorizes, or executes action.

GT38 adds the registered `geotask.trajectory-identity-adjudication` Artifact. It binds the exact GT37 execution result to one Verification Request, one caller-authored Assurance Profile, and matching Provider Descriptor/Verification Response pairs. The policy may produce `same_object_confirmed`, `different_objects_confirmed`, or `unresolved`, and may recommend merge review, keeping identities separate, or requesting more evidence. Even a confirmed same-object adjudication preserves both provisional subjects and leaves external truth verification, identity merge, `subject_ref` mutation, publication, authorization, and execution false. See [Trajectory Identity Adjudication v0.1](geotask-trajectory-identity-adjudication-v0.1.md).

GT39 adds the registered `geotask.identity-merge-proposal` Artifact. It accepts one exact GT38 adjudication only when the source confirms the same object, aligns with the GT37 candidate, recommends merge review, and preserves every non-execution boundary. The caller must select one of the two existing subject refs as `canonical_subject_ref`; Core proposes exactly one bounded rewrite for the other trajectory, retains the non-canonical subject as an alias, records approval roles plus closed blocking and withdrawal conditions, and provides the inverse rewrite as a reversal plan. The proposal never creates a new identity, deletes an alias, approves itself, mutates an object graph or World State, publishes, authorizes, or executes an update. See [Identity Merge Proposal v0.1](geotask-identity-merge-proposal-v0.1.md).

GT40 adds the registered `geotask.identity-merge-approval-record` Artifact. It binds one exact GT39 proposal and requires one explicit `approved`, `rejected`, or `evidence_required` decision for every declared approval role. Any rejection takes precedence; otherwise any evidence request blocks completion; only all-role approval makes a later bounded change request eligible. Even then, the record does not merge identity, rewrite `subject_ref`, mutate the object graph or World State, publish, authorize, or execute an update. See [Identity Merge Approval Record v0.1](geotask-identity-merge-approval-record-v0.1.md).

GT41 adds the registered `geotask.object-graph-change-request` Artifact. It binds the exact GT39 proposal and exact GT40 all-role approval record, derives exactly one trajectory `/subject_ref` rewrite from the approved scope, preserves the non-canonical subject as an alias, records seven application preconditions and five pending acceptance criteria, and carries the inverse rewrite as a rollback operation. The request still requires separate application approval and does not authorize or apply the change, mutate `subject_ref`, the object graph, or World State, publish, authorize, or execute an update. See [Object Graph Change Request v0.1](geotask-object-graph-change-request-v0.1.md).

## Fail-closed behavior

Validation fails when:

- the subject is missing or is a static geometry;
- a timestamp lacks a timezone;
- timestamps are duplicated or out of order;
- a sample contains undeclared fields such as `predicted`;
- interpolation is anything other than `none`;
- a static `polyline` is supplied to the trajectory operator;
- any GT35 threshold is missing, non-finite, negative where non-negative is required, non-positive where positive is required, or has the wrong type;
- undeclared classification parameters are present;
- GT36 omits either the midpoint method or maximum-gap parameter, uses a method other than `segment_midpoint`, or declares a non-finite/non-positive maximum gap;
- GT37 omits any identity-candidate parameter, declares an invalid time/distance/class policy, reuses the same trajectory ref twice, or places the second trajectory boundary at or before the first trajectory boundary;
- GT38 cannot close exact candidate/request/profile/provider/response references, the Assurance Profile does not block automatic merge and reference mutation, evidence conflicts or is insufficient, response partitions disagree with verdicts, or any field claims Core merged identities, rewrote `subject_ref`, published, authorized, or executed an update;
- GT39 selects a canonical subject outside the exact GT38 pair, expands the affected trajectory scope, omits alias preservation, changes the closed blocking or withdrawal conditions, lacks a reversible inverse rewrite, or claims that the proposal was approved, applied, published, authorized, or executed;
- GT40 omits or duplicates a required approval role, accepts an undeclared role or decision, records `evidence_required` without an evidence reference, derives an aggregate decision that disagrees with role decisions, or claims that approval applied the merge, rewrote references, changed the object graph or World State, published, authorized, or executed an update;
- GT41 receives a non-approved or mismatched GT40 record, expands the GT39 operation scope, changes the trajectory `/subject_ref` target, deletes the retained alias, alters the closed precondition or acceptance-criterion sets, provides an incomplete inverse rollback, or claims that the request was authorized, applied, published, or executed.

## Boundary

A valid trajectory proves only that the submitted discrete sequence is structurally valid and locally computable. It does not prove external identity, sensor authenticity, continuous real-world motion, production publication, command delivery, action authorization, or action execution.

## Reference files

- `examples/core/gt33_moving_object_trajectory.yaml`
- `examples/core/gt33_moving_object_trajectory_result.json`
- `examples/core/gt33_moving_object_trajectory.json`
- `examples/core/gt34_trajectory_segment_metrics.yaml`
- `examples/core/gt34_trajectory_segment_metrics_result.json`
- `examples/core/gt34_trajectory_segment_metrics.json`
- `examples/core/gt35_trajectory_stop_move_gap.yaml`
- `examples/core/gt35_trajectory_stop_move_gap_result.json`
- `examples/core/gt35_trajectory_stop_move_gap.json`
- `examples/core/gt36_trajectory_acceleration.yaml`
- `examples/core/gt36_trajectory_acceleration_result.json`
- `examples/core/gt36_trajectory_acceleration.json`
- `examples/core/gt37_trajectory_identity_candidate.yaml`
- `examples/core/gt37_trajectory_identity_candidate_result.json`
- `examples/core/gt37_trajectory_identity_candidate.json`
- `examples/core/trajectory_identity_adjudication_gt38.json`
- `examples/core/gt38_trajectory_identity_adjudication.json`
- `docs/spec/geotask-trajectory-identity-adjudication-v0.1.md`
- `examples/core/identity_merge_proposal_gt39.json`
- `examples/core/gt39_identity_merge_proposal.json`
- `docs/spec/geotask-identity-merge-proposal-v0.1.md`
- `examples/core/identity_merge_approval_record_gt40.json`
- `examples/core/gt40_identity_merge_approval_record.json`
- `docs/spec/geotask-identity-merge-approval-record-v0.1.md`
- `examples/core/object_graph_change_request_gt41.json`
- `examples/core/gt41_object_graph_change_request.json`
- `docs/spec/geotask-object-graph-change-request-v0.1.md`
- `site/gt33/index.html`
- `site/gt34/index.html`
- `site/gt35/index.html`
- `site/gt36/index.html`
- `site/gt37/index.html`
- `site/gt38/index.html`
- `site/gt39/index.html`
- `site/gt40/index.html`
- `site/gt41/index.html`
