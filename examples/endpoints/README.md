# GeoTask Reference Runtime HTTP Endpoint

`reference_runtime_http_server.py` is a public-safe, independently hosted endpoint
for the GeoTask Runtime Interface. It completes the transport loop with
`examples/adapters/http_json_runtime_adapter.py` while keeping networking and
service hosting outside `geotask_core`.

The endpoint is a contract example, not a production Runtime. It dispatches only
to the public `FailClosedMockRuntime`, which performs read-only Artifact
validation and never calls a model, resolves external evidence, or executes an
action.

## Run locally

From the repository root:

```bash
python examples/endpoints/reference_runtime_http_server.py
```

The service listens at:

```text
http://127.0.0.1:8765/runtime
```

It can bind only to `127.0.0.1` or `localhost`. The public example deliberately
cannot listen on `0.0.0.0` or a remote interface.

To use another loopback port or a smaller request limit:

```bash
python examples/endpoints/reference_runtime_http_server.py \
  --host 127.0.0.1 \
  --port 8877 \
  --max-request-bytes 262144
```

Use the client workflow in
[`examples/adapters/README.md`](../adapters/README.md), setting the Adapter
endpoint to the URL printed by the service.

## Transport and Runtime-state boundary

The endpoint distinguishes malformed transport input from a valid Runtime
Request that the Runtime refuses:

| Situation | HTTP result | Runtime Response |
|---|---:|---|
| Supported, valid request | `200` | `completed` |
| Valid Request Artifact but unsupported operation or contract mismatch | `200` | structured `rejected` with no outputs or side effects |
| Invalid JSON, duplicate keys, non-finite numbers, invalid UTF-8, or invalid Request Artifact | `400` | none; `application/problem+json` |
| Request body exceeds the configured limit | `413` | none |
| Non-JSON media type | `415` | none |
| Wrong path | `404` | none |
| Method other than `POST` | `405` | none |

A transport failure must never be reinterpreted as Runtime state `failed`,
`blocked`, or `rejected`. Conversely, a valid Runtime rejection is carried in a
normal `200` transport response so the Adapter can strictly load and validate the
Runtime Response Artifact.

## Defensive behavior

The reference endpoint:

- accepts only `POST /runtime`;
- requires a fixed `Content-Length` and rejects chunked requests;
- accepts only UTF-8 `application/json` or `+json` bodies;
- rejects duplicate object keys and `NaN` / `Infinity` JSON values;
- rejects `Authorization`, `Proxy-Authorization`, `Cookie`, and `X-API-Key`
  headers so secrets are not accidentally sent to the public example;
- limits request size to 1 MiB by default;
- returns `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`;
- suppresses request-line logging so Runtime metadata is not echoed;
- does not expose online Descriptor discovery or a production-readiness endpoint;
- returns generic Problem details without echoing request bodies or credentials.

Descriptor discovery remains offline and file-based:

```bash
geotask runtime inspect \
  examples/core/runtime_reference_descriptor.json \
  --format json

geotask runtime check \
  examples/core/runtime_reference_descriptor.json \
  examples/core/runtime_validate_artifact_request.json \
  --format json
```

## Production boundary

A production service must implement authentication, authorization, TLS policy,
rate limiting, observability, durable idempotency, asynchronous job management,
audit persistence, and operational hardening in a separate Runtime package.
Those capabilities must not be copied into `geotask_core`, and any returned
Runtime Response must still satisfy the public Descriptor / Request / Response
exchange contract.

Run the endpoint and Adapter tests with:

```bash
python -m pytest \
  tests/test_http_json_runtime_adapter_example.py \
  tests/test_reference_runtime_http_endpoint_example.py \
  -q
```
