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

## 13. External HTTP Adapter example

The public repository includes `examples/adapters/http_json_runtime_adapter.py` as a non-normative transport example. It binds one caller-inspected `RuntimeDescriptor` to one HTTP or HTTPS endpoint and implements the structural `RuntimeAdapter` Protocol outside `geotask_core`.

The example preserves these boundaries:

- `describe()` is offline and returns only the Descriptor supplied by the caller;
- `submit()` performs exactly one explicit HTTP POST with a strict JSON Runtime Request;
- the endpoint must return a UTF-8 JSON Runtime Response with a 2xx transport status;
- HTTP failures remain transport errors and are not converted into `completed`, `rejected`, `blocked`, or `failed` Runtime states;
- redirects, embedded URL credentials, non-JSON bodies, non-finite JSON, and oversized responses fail closed;
- the adapter does not resolve `authorization_ref`, add secrets, retry, poll, call a model, fetch evidence, or execute a production action;
- callers still use `submit_runtime_request()` so the returned Response is strictly loaded and validated against both the inspected Descriptor and submitted Request.

This example proves the external transport seam without publishing a production Runtime implementation. Authentication, endpoint discovery, TLS policy, retries, asynchronous polling, observability, and production action logic belong in a separate adapter or Runtime package outside Core.

## 14. Reference HTTP Endpoint example

The public repository also includes `examples/endpoints/reference_runtime_http_server.py`, a non-normative loopback-only service that completes the transport path with the HTTP Adapter. It hosts only `FailClosedMockRuntime` and therefore supports only the Descriptor-advertised read-only Artifact validation operation.

The Endpoint preserves these rules:

- it binds only to `127.0.0.1` or `localhost` and accepts only `POST /runtime`;
- Descriptor discovery remains offline; the service exposes no Descriptor-fetch or production-readiness endpoint;
- strict JSON parsing rejects invalid UTF-8, non-finite values, duplicate object keys, non-object roots, and invalid Runtime Request Artifacts;
- fixed `Content-Length` and a configurable request-size limit are required; chunked bodies are rejected;
- credential-bearing headers are rejected and request-line logging is suppressed;
- malformed transport or Artifact input returns `application/problem+json` with a non-2xx HTTP status and no Runtime Response;
- a structurally valid Runtime Request that the reference Runtime refuses returns HTTP `200` with a contract-valid `rejected` Runtime Response;
- supported validation requests return HTTP `200` with a `completed` Runtime Response;
- responses are marked `no-store` and do not expose the Python runtime version.

This distinction is normative for the example boundary: transport failures must not be represented as Runtime states, while Runtime operation outcomes must remain inside a strictly loaded Runtime Response Artifact. The service is not remotely deployable by default and is not a production authentication, authorization, rate-limiting, audit, or action-execution implementation.

## 15. Provider-neutral model Adapter package skeleton

The public repository includes `examples/model_adapters/provider_neutral/` as a non-normative, independently buildable package skeleton for `geotask.runtime.execute-nonlocal`. It depends on the Runtime Interface planned for GeoTask Core `0.4.x`, but it is not part of the `geotask-core` distribution and is not published in this stage.

The package defines:

- non-secret Adapter configuration with stable Runtime, model, input Artifact, and output Artifact references;
- a structural `StructuredModelProvider` Protocol with explicit declarations for external calls, authorization, and audit support;
- provider-neutral invocation, diagnostic, and result dataclasses;
- a no-network Mock Provider;
- a Runtime Adapter that checks the Request contract and validates the registered input Artifact before provider invocation;
- explicit `model_only` / `executor=model` input gating and rejection of credential-like metadata keys before provider invocation;
- registered output Artifact validation and model-output truthfulness checks before returning `completed`;
- mapping of real external model calls to `side_effect=external_read`, opaque authorization references, `side_effects_executed`, and `audit_ref` without resolving credentials in Core or the public skeleton;
- a requirement that any provider declaring external calls also declare audit support, so an executed call can be represented truthfully.

The default Mock Provider advertises `implementation_kind=mock`, `side_effect=none`, `requires_authorization=false`, and `production_ready=false`. A separately implemented real provider may advertise `implementation_kind=external`, `side_effect=external_read`, external authorization, and audit support. The package contains no provider SDK, network client, credential resolver, prompt registry, model routing, token budget, cost governance, evidence connector, or production action logic.

A model-generated `geotask.execution-result` remains distinct from a verified result. Before accepting a provider output, the reference Adapter requires the output task ID to match the submitted document, `execution.mode=model_only`, `executor=model`, `deterministic=false`, and model-scoped or unverified assurance. A provider output that claims `verified`, `local_deterministic`, independent verification, human review, or deterministic execution is returned as `failed` with no output Artifact. Independent deterministic execution or another verifier must raise assurance in a separate workflow.

Provider-native exceptions are not converted into invented Runtime states. When a provider cannot return a trustworthy `StructuredModelResult`, the Adapter raises a generic contract error without exposing provider-native exception text or claiming whether an external operation succeeded.
