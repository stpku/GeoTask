# GeoTask Verification Provider Profile v0.1

## Status

Public profile for read-only Verification Providers that connect GeoTask Core to external deterministic operators, rule engines, authoritative data services, sensors, local predictive models, and human review systems.

This profile defines contracts and validation only. It does not fetch external truth, invoke a Provider, publish production output, authorize an action, or execute side effects.

## Interface

- Interface ID: `geotask.verification-provider`
- Interface version: `0.1`
- Public Artifacts:
  - `geotask.verification-provider-descriptor`
  - `geotask.verification-request`
  - `geotask.verification-response`
  - `geotask.assurance-profile`

## Provider types

- `deterministic_operator`
- `rule_engine`
- `authoritative_data_provider`
- `sensor_data_provider`
- `local_predictive_model`
- `human_review`

A Provider Descriptor declares one Provider identity, version, type, capability set, supported methods, independence group, reproducibility, calibration state, validity window, audit support, and side-effect boundary.

A Provider never self-assigns Assurance. Its Descriptor and Response declare facts about its own implementation and output. A separate caller-authored Assurance Profile decides whether multiple bound results satisfy the required provider count, independence, freshness, reproducibility, calibration, and conflict policy.

## Provider Descriptor

A Provider Descriptor records:

- stable Provider identity and version;
- Provider type and implementation kind;
- declared capabilities and verification methods;
- independence group;
- reproducibility and calibration state;
- descriptor validity and audit support;
- whether credentials are managed outside Core;
- an explicit no-side-effect boundary.

Mock Providers cannot declare themselves production-ready. Public Provider descriptors cannot allow external side effects.

## Verification Request

A Verification Request binds:

- one explicit claim and validity window;
- exact input Artifact references and SHA-256 digests;
- one verification method;
- required capabilities;
- allowed Provider types;
- one exact Assurance Profile digest;
- a deadline;
- no-side-effect and no-action-authorization flags.

Core validates whether a Descriptor can accept a Request. It does not submit the Request.

## Verification Response

A Verification Response binds:

- the exact Request bytes;
- the exact Provider Descriptor bytes;
- one response state and typed result;
- evidence references;
- the Descriptor's declared independence group, reproducibility, and calibration state;
- diagnostics and completion time.

The Response must keep all of these fields false:

- `independently_verified`
- `production_output_released`
- `action_authorized`
- `action_executed`

The response's Assurance declarations must exactly match the Descriptor. A Provider cannot invent a new independence group or upgrade its own calibration or reproducibility state in a response.

## Assurance Profile

The caller-authored Assurance Profile declares:

- minimum Provider count;
- minimum independent groups;
- allowed Provider types;
- freshness requirements;
- accepted reproducibility and calibration states;
- conflict policy;
- eligible output;
- blocked outputs and actions;
- next action when Assurance is insufficient.

Profile v0.1 compares exact typed result values. It does not average values, infer source precedence, apply undeclared majority voting, or discard a minority result.

A successful Assurance evaluation may make one declared output eligible. It never publishes that output, authorizes an action, or executes an action. Blocked actions remain blocked even after Assurance succeeds.

## CLI

```bash
geotask provider inspect --profile --format json
geotask provider inspect provider-descriptor.json
geotask provider check provider-descriptor.json verification-request.json
geotask provider validate verification-response.json \
  --request verification-request.json \
  --descriptor provider-descriptor.json
```

All commands are read-only. They do not submit requests, fetch external evidence, invoke a network service, publish production output, authorize action, or execute side effects.

## GT29 reference case

GT29 uses fictional data:

- mock authoritative weather service: `8 meter_per_second`;
- mock onsite sensor: `13 meter_per_second`;
- mission limit: `12 meter_per_second`.

Both responses are fresh and individually valid, and they belong to two declared independence groups. Their values conflict, so the Assurance result is `unknown`. Weather verification, automatic takeoff authorization, and the takeoff command remain blocked. The next action is to request a third independent weather verification.

## GT30 reference case

GT30 adds a third fictional independent source: a mobile wind lidar also reports `13 meter_per_second`. All three responses are fresh, reproducible, calibration-compatible, and independently grouped, but the usable result set still contains both `8` and `13`.

Assurance Profile v0.1 does not declare majority voting and does not silently discard a minority source. A two-to-one split therefore remains `unknown`, with explicit weather adjudication as the next action.

## GT31 reference case

GT31 adds a fictional human-review Provider after the GT30 conflict. The Request binds the three original responses, the GT30 Assurance Profile and evaluation, and one fictional context-evidence packet. The review keeps all three responses and records that the two `13 meter_per_second` readings are valid local-test-flow observations but are not applicable to the mission-corridor ambient-wind claim.

The human Response is still unable to self-assign Assurance or action authority. A separate Assurance evaluation makes `weather_condition_verified` eligible for the scoped claim. The existing takeoff Control Evaluation remains independent and keeps automatic takeoff authorization and the takeoff command blocked by five missing authorizations. Weather eligibility therefore does not imply production release, authorization, command emission, or action execution.

## GT32 reference case

GT32 keeps the GT31 weather result and reuses the existing GT28 control expression. Five fictional caller-supplied authorization records arrive one at a time: airspace, operator, departure site, weather release, and mission authorization. The reference builder reevaluates the same finite control profile after each cumulative arrival, reducing unknown identifiers from five to zero without inferring a missing authorization from any other record.

Until the fifth record arrives, automatic takeoff authorization and the takeoff command remain blocked. After all five explicit values are true, the Control Evaluation state becomes `satisfied` and both outputs become `eligible`. Eligibility still does not mean production publication, command delivery, real-world authorization, or flight execution; all of those fields remain false and belong to an external Runtime.

## Security and commercial boundary

This public profile contains only contracts, strict validation, offline reference logic, and fictional examples. Production connectors, credentials, Provider governance, source-quality scoring, conflict arbitration policies, industry rules, customer workflows, output publication, and action execution belong outside GeoTask Core.
