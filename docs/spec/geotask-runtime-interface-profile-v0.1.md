# GeoTask Runtime Interface Profile v0.1

- **Profile ID:** `geotask.runtime-interface`
- **Profile version:** `0.1`
- **Status:** Public preview
- **Applies to:** GeoTask Core-compatible external Runtime implementations

## 1. Purpose

The Runtime Interface Profile defines the public boundary between the open GeoTask Core and an independently implemented Runtime. It enables clients to discover a Runtime's declared capabilities, submit an explicit operation request, receive a versioned response, and validate all three messages offline.

The profile publishes contracts, not a production Runtime implementation. It does not expose or prescribe model routing, token budgets, encoding strategy selection, prompt construction, connector credentials, data-source governance, approval policy, or production action logic.

## 2. Responsibility boundary

### GeoTask Core

Core owns:

- the public Artifact Registry and Schema Bundle;
- strict parsing and offline validation of Runtime Descriptor, Request, and Response Artifacts;
- deterministic local execution and read-only control evaluation already defined by Core;
- the fail-closed reference Runtime used only for contract testing.

Core does not:

- import the private `geotask_runtime` package;
- store or resolve connector credentials;
- call hosted models through the reference Runtime;
- authenticate external evidence;
- execute approvals or production actions;
- infer an authorization reference;
- claim that a mock implementation is production ready.

### External Runtime

A production Runtime may own:

- model/provider routing and inference policy;
- token and cost governance;
- external data and evidence connectors;
- credential and authorization enforcement;
- asynchronous job management;
- audit persistence;
- approved external side effects.

An external Runtime must implement the public `RuntimeAdapter` structural Protocol and preserve the message contracts in this profile.

## 3. Registered Artifacts

The profile registers three public Artifacts:

| Artifact ID | Wrapper | Schema version | Purpose |
|---|---|---:|---|
| `geotask.runtime-descriptor` | `runtime_descriptor` | `0.1` | Advertise identity, operations, side effects, authorization, and audit capability. |
| `geotask.runtime-request` | `runtime_request` | `0.1` | Submit registered input Artifacts and an explicit expected-output contract. |
| `geotask.runtime-response` | `runtime_response` | `0.1` | Return state, output Artifacts, diagnostics, audit reference, retryability, and side-effect declaration. |

All three can be validated without connecting to a Runtime:

```bash
geotask artifact validate geotask.runtime-descriptor runtime-descriptor.json
geotask artifact validate geotask.runtime-request runtime-request.json
geotask artifact validate geotask.runtime-response runtime-response.json
```

Artifact validity is separate from operation success. A truthful `rejected`, `blocked`, or `failed` Runtime Response can still be a valid serialized Artifact.

## 4. RuntimeAdapter Protocol

A compatible adapter structurally provides:

```python
class RuntimeAdapter(Protocol):
    def describe(self) -> RuntimeDescriptor: ...
    def submit(self, request: RuntimeRequest) -> RuntimeResponse: ...
```

The public SDK does not require inheritance from a concrete base class. A caller should inspect `describe()` before constructing a request and must not assume that a standard operation is supported merely because the operation ID is defined by this profile.

## 5. Runtime Descriptor

A Runtime Descriptor declares:

- `runtime_id` and `runtime_version`;
- `implementation_kind`: `mock` or `external`;
- whether the implementation is production ready;
- named capabilities;
- supported operations;
- allowed input Artifact IDs and explicit `min_input_artifacts` / `max_input_artifacts` cardinality;
- output Artifact contracts;
- side-effect class: `none`, `external_read`, or `external_write`;
- authorization requirements;
- synchronous/asynchronous behavior;
- audit support;
- whether credentials are managed externally;
- whether any external side effect is permitted.

A mock implementation must set `production_ready=false`. A descriptor that sets `external_side_effects_allowed=false` must not advertise operations with external reads or writes. Any `external_write` operation must require authorization.

The public reference descriptor is available through:

```bash
geotask runtime inspect --format json
geotask runtime inspect --profile --format json
geotask runtime inspect <runtime-descriptor.json> --format json
```

The file form performs strict offline discovery of any public Runtime Descriptor. It does not connect to the named Runtime, resolve credentials, submit a request, or execute a side effect.

## 6. Runtime Request

A Runtime Request contains:

- `request_id`;
- target `runtime_id`;
- explicit `operation_id`;
- one or more registered input Artifacts;
- expected output Artifact IDs;
- optional opaque `authorization_ref`;
- caller-provided `idempotency_key`;
- JSON metadata.

The request carries an authorization reference only. It must never contain a password, private key, bearer token, or connector credential. Core does not create, resolve, or approve authorization references.

The caller is responsible for selecting an operation from the inspected descriptor and constructing a request consistent with its input, output, authorization, and side-effect contract. The public `validate_runtime_request_contract(descriptor, request)` helper performs this comparison without submitting the request or executing a side effect.

The same preflight is available from the CLI:

```bash
geotask runtime check \
  <runtime-descriptor.json> \
  <runtime-request.json> \
  --format json
```

A successful check reports `submitted=false` and `side_effects_executed=false`. It is an offline compatibility result, not proof that the Runtime is reachable, authorized, trustworthy, or willing to execute the operation.

## 7. Runtime Response

A Runtime Response uses one of five states:

| State | Meaning |
|---|---|
| `accepted` | The request was accepted for asynchronous processing; no output or completed side effect is claimed yet. |
| `completed` | The operation completed and any declared output Artifacts are included. |
| `blocked` | A prerequisite is missing; no blocked side effect was executed. |
| `rejected` | The Runtime refused the request; no side effect was executed. |
| `failed` | Processing failed. The response records diagnostics and whether retry is appropriate. |

Cross-field rules include:

- `accepted` requires a positive `next_poll_after_ms` and cannot contain error diagnostics or outputs;
- a synchronous operation cannot return `accepted`;
- `completed` cannot be retryable or contain error diagnostics;
- a `completed` response must return exactly the output Artifact IDs requested and advertised by the operation;
- every returned output Artifact ID must be inside the request's expected-output contract;
- `blocked`, `rejected`, and `failed` require at least one error diagnostic;
- `blocked` and `rejected` require `side_effects_executed=false`;
- a request that violates the inspected Descriptor contract must receive a side-effect-free `rejected` response with no output Artifacts;
- an operation declared with `side_effect=none` cannot claim that side effects were executed;
- any response claiming `side_effects_executed=true` must include a non-empty `audit_ref` and the Descriptor must allow external side effects;
- a Runtime that declares `audit_supported=false` cannot return an `audit_ref`;
- request ID, Runtime ID, and operation ID returned by an adapter must match the submitted request and inspected descriptor.

The public `validate_runtime_response_contract(descriptor, request, response)` helper enforces these exchange rules. `submit_runtime_request()` invokes it after strict response loading, so a structurally valid but contract-inconsistent third-party response fails closed. Validation never repeats the Runtime operation or any external side effect.

## 8. Standard operation identifiers

The profile reserves these stable identifiers:

- `geotask.runtime.validate-artifact`
- `geotask.runtime.execute-nonlocal`
- `geotask.runtime.resolve-evidence`
- `geotask.runtime.execute-action`

Defining an identifier does not grant permission and does not imply support. Every Runtime must advertise the operations it actually supports. Production operations may add narrower namespaced identifiers while preserving the same request and response envelopes.

## 9. Fail-closed reference Runtime

GeoTask Core ships `FailClosedMockRuntime` with Runtime ID:

```text
geotask.reference.fail-closed
```

It supports only:

```text
geotask.runtime.validate-artifact
```

This operation accepts exactly one registered input Artifact (`min_input_artifacts=1`, `max_input_artifacts=1`), invokes the existing read-only, Registry-driven Core Artifact validator, and returns one `geotask.artifact-validation-report` output. The operation itself can complete even when the target Artifact is invalid; the nested validation report records `valid=false` and diagnostics.

The reference Runtime rejects:

- model or nonlocal execution;
- evidence resolution;
- production actions;
- a mismatched Runtime ID;
- an unexpected output contract;
- authorization references for its read-only operation;
- any request shape that violates the strict loader.

Every rejection records `side_effects_executed=false`. The reference Runtime is not a production Runtime and is not a substitute for an authorization, connector, or governance implementation.

Run the reference example:

```bash
geotask runtime mock examples/core/runtime_validate_artifact_request.json
```

Unsupported operations return a structured `rejected` response and CLI exit code `2`. Malformed Runtime Artifacts or CLI arguments return exit code `1`.

## 10. Idempotency and audit

The caller supplies a non-empty `idempotency_key`. A production Runtime is responsible for defining its storage duration, replay behavior, and collision policy. The public Core validates the field but does not persist requests or deduplicate them.

An `audit_ref` is opaque to Core. A production Runtime should use it to reference immutable or access-controlled audit evidence. Core validates only the presence and cross-field consistency of the reference; it does not fetch or authenticate the audit record.

## 11. Security and privacy

Runtime messages are public protocol Artifacts and may be logged, stored, or exchanged. Implementations must not place raw secrets in:

- `authorization_ref`;
- request metadata;
- diagnostics;
- `audit_ref`;
- embedded Artifacts unless those Artifact contracts explicitly permit the data.

Credential resolution and access control remain outside Core. A Runtime that performs an external write must require authorization, enforce it independently, and return an audit reference when a side effect was executed.

## 12. Compatibility

Profile `0.1` is a public-preview contract. Additive capabilities should be advertised through descriptors. Breaking changes to message fields, wrappers, states, or cross-field semantics require a new profile and Schema version.

GeoTask Document Schema `1.0`, Artifact Registry `1.0`, and Artifact Validation Report `1.0` remain independently versioned.
