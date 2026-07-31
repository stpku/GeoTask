# GeoTask Examples

This directory contains public-safe Core examples and separate domain-pack
examples. Core examples use fictional local coordinates and generic intervals.
They do not encode domain-specific approval logic, regulatory thresholds, or
patent-sensitive workflows.

## Public-Safe Core Examples

- `examples/core/minimal_valid.yaml`: minimal point distance example.
- `examples/core/time_altitude_overlap.yaml`: generic time and altitude interval
  overlap example.
- `examples/core/v1_polygon_multi_polyline.yaml`: native v1 polygon containment and
  grouped-route rectangle intersection with explicit closed-boundary semantics.
- `examples/core/v1_cross_task_space_contract.yaml`: three native v1 tasks sharing one
  CRS, coordinate order, horizontal/vertical unit, vertical datum, and closed-boundary contract.
- `examples/core/assertions_expected_results.yaml`: schema example for optional
  `assertions` and `expected_results` sections.
- `examples/core/multi_constraint_conflict.yaml`: three deterministic assertions
  combined by an explicit public-safe `AND` decision rule.
- `examples/core/unverifiable_constraint.yaml`: two verified assertions and one
  unverifiable required condition combined with three-valued unknown propagation.
- `examples/core/agent_generated_distance_draft.yaml`: a fictional native v1 draft with
  mechanical protocol omissions repaired by `geotask agent prepare` before deterministic execution.
- `examples/core/agent_generated_distance_blocked.yaml`: a generated draft with an unregistered
  operator and unknown object binding; Core emits a revision request but selects no candidate.
- `examples/core/agent_generated_distance_revised.yaml`: the explicit Agent revision of that blocked
  draft, which passes `geotask agent retry` changed-path verification and produces the deterministic five-meter result.
- `examples/core/evidence_request_plan.yaml`: an unverifiable required condition
  converted into a structured evidence request with blocked outputs and a resume condition.
- `examples/core/evidence_request_verified_state.yaml`: fictional complete evidence used by
  `geotask agent recover` to satisfy GT08's resume condition and rerun the temporal assertion.
- `examples/core/runtime_reference_descriptor.json`: the public fail-closed Runtime capability
  descriptor used for offline discovery and request-contract checks.
- `examples/core/runtime_validate_artifact_request.json`: a public Runtime Request that asks the
  fail-closed reference adapter to validate one embedded GeoTask Document without model calls,
  external credentials, or side effects.
- `examples/adapters/http_json_runtime_adapter.py`: a public-safe external HTTP JSON transport
  adapter that keeps Descriptor discovery offline, performs one explicit POST, strictly loads the
  Runtime Response, and leaves credentials, retries, models, and production actions outside Core.
- `examples/adapters/README.md`: the external Adapter workflow, transport/error boundary, and
  production-extension guidance.
- `examples/endpoints/reference_runtime_http_server.py`: a loopback-only HTTP Runtime service
  that accepts strict Runtime Request JSON, dispatches only to the fail-closed reference Runtime,
  and returns validated Runtime Responses without credentials, model calls, or production actions.
- `examples/endpoints/README.md`: the endpoint startup workflow, HTTP/Runtime-state distinction,
  defensive transport behavior, and production-service boundary.
- `examples/model_adapters/provider_neutral/`: an independently buildable provider-neutral model
  Adapter package skeleton with non-secret configuration, a structural Provider Protocol, a
  no-network Mock Provider, registered input/output Artifact validation, model-truthfulness guards,
  and Descriptor/Request/mock-result examples. It contains no real provider SDK or credentials.
- `examples/model_adapters/openai_responses/`: the first provider-specific integration package. It
  accepts an externally authenticated official OpenAI SDK client, performs one no-retry Responses API
  call with strict Structured Outputs and `store=false`, preserves audit references, and still routes
  the nested result through registered Artifact and model-truthfulness validation.
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
- `examples/core/rescue_robot_shortest_route_hazard.yaml`: a 120-meter shortest route crosses
  a 120°C hazard beyond the robot's 80°C limit, while a 260-meter detour remains executable.
- `examples/core/uav_arrival_ground_clearance_release.yaml`: a UAV reaches the authorized drop
  zone and altitude, but a responder only 10 meters from the impact point blocks payload release.
- `examples/core/vehicle_green_light_downstream_blockage.yaml`: a green signal is valid, but only
  4 meters of downstream storage remain for a vehicle envelope requiring 6.8 meters.
- `examples/geotask_core_lite.yaml`: legacy Core lite example used by tests.
- `examples/basic_distance.yaml`: basic distance example.
- `examples/route_zone_intersection.yaml`: line and rectangle intersection
  example.

## Domain-Pack Examples

Files under `examples/domain_packs/` are not public-safe Core examples. They are
kept separate to avoid mixing Core documentation with domain-specific material.
