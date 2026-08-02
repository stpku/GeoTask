# GeoTask Examples

This directory contains public-safe Core examples and separate domain-pack
examples. Core examples use fictional local coordinates and generic intervals.
They do not encode domain-specific approval logic, regulatory thresholds, or
patent-sensitive workflows.

## Public-Safe Core Examples

- `examples/core/minimal_valid.yaml`: minimal point distance example.
- `examples/core/v1_point_to_line_distance_minimal.en.yaml`: directly runnable English
  example covering a four-meter point-to-line distance and the zero-distance on-line boundary case.
- `examples/core/v1_point_to_line_distance_minimal.zh-CN.yaml`: the matching Chinese
  example with identical objects, assertions, and deterministic expected results.
- `examples/core/time_altitude_overlap.yaml`: generic time and altitude interval
  overlap example.
- `examples/core/v1_polygon_multi_polyline.yaml`: native v1 point-first polygon containment and
  grouped-route rectangle intersection with explicit closed-boundary semantics.
- `examples/core/v1_polygon_contains_point.yaml`: container-first polygon containment with
  interior, boundary, and exterior points and deterministic expected results.
- `examples/core/v1_cross_task_space_contract.yaml`: three native v1 tasks sharing one
  CRS, coordinate order, horizontal/vertical unit, vertical datum, and closed-boundary contract.
- `examples/core/v1_provenance_evidence_audit.yaml`: fictional source records, strict
  evidence-to-assertion bindings, authoring audit metadata, and propagated result evidence refs.
- `examples/core/observation_uav_delay.json`: fictional source-bound UAV delay Observation with
  producer identity, evidence, validity, uncertainty, and no truth or state-update claim.
- `examples/core/world_state_uav_separation.json`: fictional World State v0.1 revision 1 with two
  UAV objects, versioned attributes and relations, as-of validity, uncertainty, and closed references.
- `examples/core/world_state_uav_separation_recheck.json`: the paired fictional revision 2 snapshot,
  where a later telemetry Observation changes delay and temporal separation to sixty seconds.
- `examples/core/state_transition_uav_separation_recheck.json`: State Transition v0.1 binding both
  snapshot fingerprints and recording two state changes plus one blocked eligibility change, without
  calculating the diff, applying changes, materializing state, or authorizing action.
- `examples/core/verification_session_uav_execution_result.json`: deterministic GT16 execution result
  with fixed timestamps for exact-byte Verification Session binding.
- `examples/core/verification_session_uav_recheck.json`: Verification Session v0.1 binding World State
  revision 2, the GT16 task, its result, and the State Transition by semantic fingerprint and raw SHA-256,
  while recording blocked/eligible outputs and one satisfied recheck trigger without executing the recheck.
- `examples/core/discrepancy_report_uav_recheck.json`: Discrepancy Report v0.1 binding the later World State
  and four exact source Artifacts, recording a 120-to-60-second relation mismatch, a stale historical result,
  confirmed downstream impact, mutable telemetry-derived paths, and immutable route/result paths without
  comparing sources, applying corrections, or authorizing action.
- `examples/core/correction_request_uav_recheck.json`: Correction Request v0.1 binding World State revision 2,
  the corresponding Discrepancy Report, and the GT16 task, requesting two bounded recomputations for a successor
  snapshot with revision at least 3 while preserving route identity/geometry and keeping continuation blocked
  until the successor state is valid and the affected temporal output has been rechecked.
- `examples/core/impact_graph_uav_recheck.json`: Impact Graph v0.1 binding the same World State, Discrepancy Report,
  and Correction Request into an eight-node, nine-edge directed acyclic graph from the confirmed discrepancy through
  two correction changes and affected state paths to the temporal assertion, blocked continuation output, blocked
  route action, and two explicit reevaluation targets without discovering or executing propagation.
- `examples/core/world_state_uav_separation_successor.json`: canonical World State revision 3 emitted by bounded Core
  materialization; route identity and geometry remain unchanged while the two requested mutable values are re-materialized.
- `examples/core/world_state_materialization_result_uav_recheck.json`: World State Materialization Result v0.1 binding
  the exact base state, Correction Request, and generated successor bytes, with complete applied-change coverage and all
  output/action gates preserved for later reevaluation.
- `examples/core/incremental_reevaluation_uav_execution_result.json`: deterministic reevaluation execution result with
  fixed timestamps and four verified GT16 checks, including the recomputed `temporal_conflict=false` assertion.
- `examples/core/incremental_reevaluation_result_uav_recheck.json`: Incremental Reevaluation Result v0.1 binding the
  base and successor World States, Impact Graph, Correction Request, Discrepancy Report, and execution result; it closes
  all eight node outcomes, two targets, five acceptance criteria, one discrepancy, one released output, and one action
  that is eligible but still externally unauthorized and unexecuted.
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
