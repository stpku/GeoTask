# GeoTask Runtime Adapter Examples

This directory contains public-safe transport examples for the GeoTask Runtime
Interface. These files are not part of the `geotask-core` Python package and do
not implement a production Runtime.

## HTTP JSON Runtime Adapter

`http_json_runtime_adapter.py` binds an already inspected `RuntimeDescriptor` to
one HTTP or HTTPS endpoint. It demonstrates the first real external transport
boundary for the public `RuntimeAdapter` Protocol:

```text
Runtime Descriptor file
        ↓ offline strict load
HttpJsonRuntimeAdapter.describe()
        ↓ no network activity
Runtime Request
        ↓ one HTTP POST
independently hosted Runtime endpoint
        ↓ Runtime Response JSON
strict response load
        ↓
Descriptor / Request / Response three-way validation
```

The example deliberately does not:

- fetch or trust a Descriptor from the endpoint;
- accept embedded URL credentials or add authorization headers;
- resolve `authorization_ref`;
- retry, poll asynchronous jobs, or persist idempotency keys;
- call a model, connector, evidence service, or production action;
- convert HTTP failures into GeoTask Runtime states;
- live inside or add networking dependencies to `geotask_core`.

### Required workflow

First inspect and validate the Descriptor and Request offline:

```bash
geotask runtime inspect examples/core/runtime_reference_descriptor.json --format json
geotask artifact validate \
  geotask.runtime-descriptor \
  examples/core/runtime_reference_descriptor.json \
  --format json
geotask artifact validate \
  geotask.runtime-request \
  examples/core/runtime_validate_artifact_request.json \
  --format json
geotask runtime check \
  examples/core/runtime_reference_descriptor.json \
  examples/core/runtime_validate_artifact_request.json \
  --format json
```

Start the paired public-safe endpoint in a separate terminal:

```bash
python examples/endpoints/reference_runtime_http_server.py
```

Then construct the transport adapter outside Core and submit through the public
SDK helper:

```python
import json
from pathlib import Path

from geotask_core import (
    load_runtime_descriptor,
    submit_runtime_request,
)
from http_json_runtime_adapter import HttpJsonRuntimeAdapter

root = Path(__file__).resolve().parents[2]
descriptor_payload = json.loads(
    (root / "examples/core/runtime_reference_descriptor.json").read_text(
        encoding="utf-8"
    )
)
request_payload = json.loads(
    (root / "examples/core/runtime_validate_artifact_request.json").read_text(
        encoding="utf-8"
    )
)

adapter = HttpJsonRuntimeAdapter(
    descriptor=load_runtime_descriptor(descriptor_payload),
    endpoint="http://127.0.0.1:8765/runtime",
)
response = submit_runtime_request(adapter, request_payload)
print(response.to_dict())
```

The endpoint must return a UTF-8 JSON `geotask.runtime-response` Artifact with a
2xx HTTP transport status. The Adapter rejects redirects, duplicate object keys,
non-finite JSON values, non-JSON media types, and oversized responses before Core
contract validation. Operation outcomes such as `completed`, `rejected`,
`blocked`, or `failed` belong in the Runtime Response body. HTTP transport
failure remains a `RuntimeTransportError` and is never reinterpreted as a Runtime
operation result. See the paired
[`reference endpoint`](../endpoints/README.md) for the server-side boundary.

### Production boundary

A production adapter may add authentication, TLS policy, observability, retries,
asynchronous polling, and endpoint discovery in a separate package. Those
features must remain outside `geotask_core`, and the returned Response must still
pass the public Descriptor / Request / Response exchange validation.
