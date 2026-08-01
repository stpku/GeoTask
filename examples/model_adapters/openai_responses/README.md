# GeoTask OpenAI Responses Adapter

This directory contains the first provider-specific model integration for the
GeoTask Runtime Interface. It is an independent Python package built on top of
the provider-neutral model Adapter skeleton and the official OpenAI Python SDK.
It is not part of `geotask-core`.

Distribution name:

```text
geotask-openai-responses-adapter
```

Current package contract:

```text
geotask-provider-neutral-model-adapter>=0.1.0,<0.2.0
openai>=2.46.0,<3.0.0
```

The package is a verified public integration example and is not published to
PyPI in this stage.

## Security boundary

The public package never reads an environment variable, resolves a raw key, or
constructs an authenticated client. Private startup code constructs the official
OpenAI client and binds that client object to an opaque Runtime
`authorization_ref` through `StaticOpenAIClientResolver`.

```text
private startup code
        ↓ constructs authenticated OpenAI client
StaticOpenAIClientResolver
        ↓ opaque authorization_ref only
OpenAIResponsesStructuredProvider
        ↓ one Responses API call
StructuredModelResult
        ↓
ProviderNeutralModelRuntimeAdapter
        ↓
GeoTask Runtime Response
```

Raw authentication material must never enter:

- GeoTask Runtime Descriptor, Request, or Response Artifacts;
- `authorization_ref`;
- Runtime metadata or diagnostics;
- model references;
- audit references;
- public source code or tests.

## Runtime contract

The generated Descriptor advertises:

```text
runtime_id: geotask.openai.responses
operation_id: geotask.runtime.execute-nonlocal
input: geotask.document × 1
output: geotask.execution-result × 1
implementation_kind: external
side_effect: external_read
requires_authorization: true
audit_supported: true
synchronous: true
production_ready: false
```

The Descriptor and Request examples are under `examples/` and can be validated
offline before any client is resolved.

## Responses API behavior

The Provider performs one synchronous `client.responses.create(...)` call with:

- a caller-selected model snapshot;
- explicit instructions that prohibit verified or deterministic claims;
- the complete GeoTask Document as text input;
- strict JSON Schema output;
- a fixed outer object containing only `artifact_json`;
- response storage disabled;
- truncation disabled;
- SDK retries disabled through `with_options(max_retries=0)`;
- no tools, conversation state, provider metadata, or production actions.

The outer Structured Outputs schema intentionally contains one string field. The
string holds the serialized `geotask.execution-result` Artifact. This preserves
a small strict schema supported by the provider while allowing GeoTask Core to
apply the complete registered Artifact Schema and semantic validation to the
inner document.

```text
OpenAI strict JSON Schema envelope
        ↓ artifact_json string
strict duplicate/non-finite JSON rejection
        ↓
registered geotask.execution-result validation
        ↓
model-output truthfulness guard
```

A response is accepted only when:

- the OpenAI response state is `completed`;
- `output_text` is one strict JSON object;
- the object contains exactly `artifact_json`;
- the nested JSON has an object root;
- the registered output Artifact is valid;
- the provider-neutral truthfulness checks pass.

Duplicate object keys, `NaN`, `Infinity`, missing output, incomplete responses,
invalid Artifacts, and deceptive assurance claims fail closed.

## Audit and failure semantics

A successful SDK response uses the public SDK `_request_id` and response ID in
the Runtime audit reference:

```text
openai://responses/<request-id>/<response-id>
```

When an exception occurs before a server request ID is available, the Adapter
uses a deterministic client-side request identifier derived from the Runtime
request and idempotency key. This records that an external call was attempted
without inventing a server acknowledgement.

Provider exceptions are converted to generic diagnostics. Exception messages are
never copied into Runtime output. HTTP-like status codes `408`, `409`, `429`, and
`5xx`, plus timeout or connection exception classes, are classified as
retryable. The Adapter itself never retries.

## Pinned models

`OpenAIResponsesConfig` requires a model identifier ending in `YYYY-MM-DD` by
default. This keeps the Runtime Descriptor stable while making model behavior an
explicit deployment choice.

A non-pinned alias requires an explicit override:

```python
OpenAIResponsesConfig(
    model="your-reviewed-model-alias",
    require_pinned_model=False,
)
```

The override is a compatibility decision, not a production-readiness signal.

## Private startup example

The authentication step remains outside the public package:

```python
import json
from pathlib import Path

from openai import OpenAI
from geotask_core import submit_runtime_request
from geotask_openai_responses_adapter import (
    OPENAI_AUTHORIZATION_REF,
    OpenAIResponsesConfig,
    StaticOpenAIClientResolver,
    build_openai_responses_runtime_adapter,
)

root = Path.cwd()
client = OpenAI()  # Authenticated by private server-side OpenAI SDK configuration.
resolver = StaticOpenAIClientResolver(OPENAI_AUTHORIZATION_REF, client)
adapter = build_openai_responses_runtime_adapter(
    OpenAIResponsesConfig(model="gpt-5-2025-08-07"),
    resolver,
)
request_payload = json.loads(
    (
        root
        / "examples/model_adapters/openai_responses/examples/openai_runtime_request.json"
    ).read_text(encoding="utf-8")
)
response = submit_runtime_request(adapter, request_payload)
print(response.to_dict())
```

The example model is illustrative. Deployments must select a pinned model
snapshot available to their own OpenAI project and run compatibility evaluations
before use.

## Offline verification

No live OpenAI call is performed by repository tests:

```bash
python -m pytest tests/test_openai_responses_model_adapter_example.py -q
```

After building the Core, provider-neutral, and OpenAI Adapter wheels, the offline
installed-package smoke can also be run with the isolated Python environment:

```bash
python examples/model_adapters/openai_responses/examples/installed_smoke.py \
  --repository-root .
```

The smoke script imports the installed packages, submits the example Runtime
Request through an SDK-shaped fake client, checks `store=false`, no-retry client
options, one provider call, and an audit-bound `completed` response. It reports
`live_request_executed=false`.

The tests use a fake official-SDK-shaped client and verify:

- independent package metadata and license distribution;
- Descriptor and Request Artifact validation;
- exact `responses.create` request options;
- disabled storage, tools, conversation state, and retries;
- strict outer and nested JSON parsing;
- server and client-side audit references;
- authorization and resolver failure before an API call;
- retry classification without automatic retry;
- provider exception detail suppression;
- rejection of deceptive `verified` and deterministic output.

## Build

```bash
python -m build examples/model_adapters/openai_responses \
  --outdir openai-adapter-dist
python -m twine check openai-adapter-dist/*
```

Do not publish this package before GeoTask Core v0.4.0 and the provider-neutral
Adapter package are tagged and independently released.

## Official interface references

The implementation follows the OpenAI Responses API, Structured Outputs,
official Python SDK request-ID behavior, and server-side key-management guidance:

- https://platform.openai.com/docs/api-reference/responses
- https://platform.openai.com/docs/guides/structured-outputs
- https://github.com/openai/openai-python
- https://platform.openai.com/docs/api-reference/authentication
