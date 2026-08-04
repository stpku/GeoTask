# GeoTask Verification Provider Profile v0.1

## Status

Public, read-only interface profile for connecting independently implemented verification capabilities to GeoTask Core.

The profile defines four registered Artifacts:

1. `geotask.verification-provider-descriptor`
2. `geotask.verification-request`
3. `geotask.verification-response`
4. `geotask.assurance-profile`

It does not define a production Provider marketplace, credential store, network transport, billing model, regulatory rule set, or action executor.

## Design principle

A Provider may report what it observed or checked. It cannot decide that its own response is independently verified, cannot raise its own Assurance level, cannot release a production output, and cannot authorize or execute an action.

Independent Assurance is evaluated outside the Provider response against a caller-authored Assurance Profile.

## Verification Provider Descriptor

The Descriptor advertises:

- stable Provider identity and version;
- Provider type;
- supported capabilities and methods;
- declared independence group;
- reproducibility state;
- calibration state;
- validity window;
- audit and credential boundaries;
- an immutable `external_side_effects_allowed=false` boundary.

Supported Provider types are:

- `deterministic_operator`
- `rule_engine`
- `authoritative_data_provider`
- `sensor_data_provider`
- `local_predictive_model`
- `human_review`

A mock Provider must declare `production_ready=false`.

## Verification Request

A Request binds:

- one verification subject;
- exact input Artifact references and SHA-256 digests;
- one verification method;
- required capabilities;
- allowed Provider types;
- one exact Assurance Profile reference;
- a deadline;
- immutable no-side-effect and no-authorization flags.

Core validation does not submit the Request to a Provider.

## Verification Response

A Response binds exact serialized Request and Descriptor bytes. It records:

- Provider-local response state;
- one source-bound result and validity window;
- method and evidence references;
- assurance declarations copied from the bound Descriptor;
- diagnostics and completion time.

The following fields are always `false`:

- `independently_verified`
- `production_output_released`
- `action_authorized`
- `action_executed`

Binding validation rejects any response that changes its independence group, reproducibility, or calibration state relative to the Descriptor.

## Assurance Profile

The caller, not the Provider, authors the Assurance Profile. It declares:

- minimum Provider count;
- minimum independent-group count;
- accepted Provider types;
- freshness and maximum-age requirements;
- reproducibility requirements;
- calibration requirements;
- conflict policy;
- eligible and blocked outputs;
- blocked actions;
- the next action when Assurance is insufficient.

The public reference evaluator never invents Provider precedence and never averages conflicting values. When fresh, admissible, independently grouped Provider responses disagree, the result remains `unknown` or becomes `contradicted` according to the explicit profile policy.

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

## Security and commercial boundary

This public profile contains only contracts, strict validation, offline reference logic, and fictional examples. Production connectors, credentials, Provider governance, source-quality scoring, conflict arbitration policies, industry rules, customer workflows, output publication, and action execution belong outside GeoTask Core.
