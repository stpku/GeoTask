# GeoTask Examples

This directory contains public-safe Core examples and separate domain-pack
examples. Core examples use fictional local coordinates and generic intervals.
They do not encode domain-specific approval logic, regulatory thresholds, or
patent-sensitive workflows.

## Public-Safe Core Examples

- `examples/core/minimal_valid.yaml`: minimal point distance example.
- `examples/core/time_altitude_overlap.yaml`: generic time and altitude interval
  overlap example.
- `examples/core/assertions_expected_results.yaml`: schema example for optional
  `assertions` and `expected_results` sections.
- `examples/core/multi_constraint_conflict.yaml`: three deterministic assertions
  combined by an explicit public-safe `AND` decision rule.
- `examples/core/unverifiable_constraint.yaml`: two verified assertions and one
  unverifiable required condition combined with three-valued unknown propagation.
- `examples/core/evidence_request_plan.yaml`: an unverifiable required condition
  converted into a structured evidence request with blocked outputs and a resume condition.
- `examples/core/evidence_conflict_review.yaml`: two verified schedule sources whose
  incompatible results trigger a structured conflict review task.
- `examples/core/robot_corridor_coordination.yaml`: two warehouse robots whose routes
  and occupancy windows conflict in a single-capacity aisle, resolved by an explicit priority policy.
- `examples/core/robot_accessible_route.yaml`: a delivery robot with a 50-meter Euclidean
  distance but a 300-meter accessible route due to mobility and network constraints.
- `examples/core/uav_energy_reserve.yaml`: a UAV whose 8-kilometer direct route is illegal
  and whose 11-kilometer detour plus a 2-kilometer reserve exceeds its remaining range.
- `examples/core/vehicle_clearance_envelope.yaml`: an open road narrowed to 2.4 meters
  where an autonomous vehicle requires a 2.7-meter object-specific safety envelope.
- `examples/core/emergency_response_fastest_arrival.yaml`: two rescue teams where the
  nearest team arrives in 14 minutes while the farther team arrives in 8 minutes and meets the response deadline.
- `examples/core/robot_live_obstacle_stop.yaml`: an inspection robot whose static map is
  structurally passable while live perception detects a route-blocking pallet and verifies a safe stop point.
- `examples/core/uav_route_crossing_temporal_separation.yaml`: two UAV routes pass the same
  crossing point with overlapping altitudes but non-overlapping crossing windows and verified temporal separation.
- `examples/core/city_event_report_deduplication.yaml`: ten reports with one semantic,
  spatial, and temporal signature are merged into one dispatch task while all source evidence is retained.
- `examples/geotask_core_lite.yaml`: legacy Core lite example used by tests.
- `examples/basic_distance.yaml`: basic distance example.
- `examples/route_zone_intersection.yaml`: line and rectangle intersection
  example.

## Domain-Pack Examples

Files under `examples/domain_packs/` are not public-safe Core examples. They are
kept separate to avoid mixing Core documentation with domain-specific material.
