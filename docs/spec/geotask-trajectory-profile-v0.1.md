# GeoTask Trajectory and Moving Object Profile v0.1

Status: implemented public profile  
Reference cases: GT33–GT34
Scope: discrete observations and adjacent-sample metrics only

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

The segment operator does not treat average speed as instantaneous velocity and does not interpolate, smooth, resample, predict, map match, verify external truth, publish output, deliver commands, authorize action, or execute action. Acceleration and stop/move classification remain outside this profile version.

## Fail-closed behavior

Validation fails when:

- the subject is missing or is a static geometry;
- a timestamp lacks a timezone;
- timestamps are duplicated or out of order;
- a sample contains undeclared fields such as `predicted`;
- interpolation is anything other than `none`;
- a static `polyline` is supplied to the trajectory operator.

## Boundary

A valid trajectory proves only that the submitted discrete sequence is structurally valid and locally computable. It does not prove external identity, sensor authenticity, continuous real-world motion, production publication, command delivery, action authorization, or action execution.

## Reference files

- `examples/core/gt33_moving_object_trajectory.yaml`
- `examples/core/gt33_moving_object_trajectory_result.json`
- `examples/core/gt33_moving_object_trajectory.json`
- `examples/core/gt34_trajectory_segment_metrics.yaml`
- `examples/core/gt34_trajectory_segment_metrics_result.json`
- `examples/core/gt34_trajectory_segment_metrics.json`
- `site/gt33/index.html`
- `site/gt34/index.html`
