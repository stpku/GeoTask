# GeoTask Provider-Neutral Model Adapter Reference

This directory is an independent Python package skeleton for connecting the
GeoTask Runtime Interface v0.1 to a structured model provider. It is public-safe,
provider-neutral, and intentionally contains no real model SDK, network client,
credential resolver, API key, prompt registry, routing policy, token budget, or
production action logic.

The package is not part of `geotask-core`. Its distribution name is:

```text
geotask-provider-neutral-model-adapter
```

The package currently targets the forthcoming GeoTask Core `0.4.x` Runtime
Interface:

```text
geotask-core>=0.4.0,<0.5.0
```

It is a reference skeleton and is not published to PyPI in this stage.

## Package layout

```text
provider_neutral/
├── pyproject.toml
├── MANIFEST.in
├── LICENSE
├── README.md
├── examples/
│   ├── model_runtime_descriptor.json
│   ├── model_runtime_request.json
│   └── mock_model_execution_result.json
└── src/geotask_model_adapter_reference/
    ├── __init__.py
    ├── contracts.py
    ├── adapter.py
    └── mock_provider.py
```

## Responsibility boundary

The package owns only:

- a non-secret `ModelAdapterConfig`;
- a structural `StructuredModelProvider` Protocol;
- normalized provider invocation and result dataclasses;
- mapping between Runtime Request/Response and provider contracts;
- validation of the input GeoTask Artifact before provider invocation;
- validation of the output execution-result Artifact before returning
  `completed`;
- truthfulness checks preventing model output from claiming deterministic or
  independently verified assurance;
- a deterministic `MockStructuredModelProvider` with no network activity.

The package does not own:

- provider credentials or secret resolution;
- a hosted model SDK or HTTP client;
- prompt templates or prompt optimization;
- model selection, routing, consensus, fallback, or cost control;
- token accounting or budget allocation;
- external data and evidence connectors;
- production authorization, approval, or action execution;
- durable audit storage or idempotency persistence.

Those capabilities belong in a separately implemented provider integration or
private Runtime.

## Runtime operation

The default Mock Provider advertises:

```text
runtime_id: geotask.reference.provider-neutral-model
operation_id: geotask.runtime.execute-nonlocal
input: geotask.document × 1
output: geotask.execution-result × 1
side_effect: none
requires_authorization: false
synchronous: true
production_ready: false
```

A real provider implementation can declare:

```text
implementation_kind: external
side_effect: external_read
requires_authorization: true
external_side_effects_allowed: true
audit_supported: true
```

The public Adapter never resolves `authorization_ref`; it passes the opaque
reference to the provider implementation. Passwords, bearer tokens, private
keys, and provider API keys must not be placed in Runtime messages or
`model_ref`.

## Required processing sequence

```text
Runtime Descriptor
        ↓
Runtime Request contract preflight
        ↓
registered input Artifact validation
        ↓
StructuredModelInvocation
        ↓
StructuredModelProvider.invoke()
        ↓
StructuredModelResult
        ↓
registered output Artifact validation
        ↓
model-output truthfulness checks
        ↓
Runtime Response
        ↓
Descriptor / Request / Response validation
```

The provider is not invoked when the Runtime Request contract or input Artifact
is invalid. The reference Adapter also requires `execution.mode=model_only`, a
non-empty execution-step list whose steps use `executor=model`, and metadata
without credential-like keys. Secrets must be resolved only from the opaque
`authorization_ref` outside Core and outside this public package.

An implementation that declares `external_call=true` must also declare
audit support. This prevents a real model call from being executed without a
contractual way to return an audit reference.

## Output truthfulness guard

A structurally valid execution-result Artifact is not automatically a truthful
model result. Before returning `completed`, the Adapter additionally requires:

- output `task_id` equals the submitted GeoTask document ID;
- `execution.mode` is `model_only`;
- every check uses `executor=model`;
- every check declares `deterministic=false`;
- assurance remains `unverified`, `model_generated`, or
  `model_self_checked`;
- neither individual checks nor the overall result claim `verified`.

A model result that claims `local_deterministic`, independent verification,
human review, or deterministic execution fails closed with:

```text
state = failed
code = untruthful_model_output_claim
output_artifacts = []
```

Independent Core execution, another verifier, or human review may later raise
the assurance level through a separate workflow.

## Run the Mock Provider example

From the GeoTask repository root:

```python
import json
import sys
from pathlib import Path

root = Path.cwd()
package_root = root / "examples/model_adapters/provider_neutral"
sys.path.insert(0, str(root / "src"))
sys.path.insert(0, str(package_root / "src"))

from geotask_core import submit_runtime_request
from geotask_model_adapter_reference import (
    MockStructuredModelProvider,
    ProviderNeutralModelRuntimeAdapter,
)

examples = package_root / "examples"
request_payload = json.loads(
    (examples / "model_runtime_request.json").read_text(encoding="utf-8")
)
output_payload = json.loads(
    (examples / "mock_model_execution_result.json").read_text(encoding="utf-8")
)

provider = MockStructuredModelProvider.completed(output_payload)
adapter = ProviderNeutralModelRuntimeAdapter(provider)
response = submit_runtime_request(adapter, request_payload)

print(response.to_dict())
```

Expected properties:

```text
state = completed
side_effects_executed = false
audit_ref = null
output_artifact_id = geotask.execution-result
check.status = computed
check.assurance_level = model_generated
check.deterministic = false
```

## Implement an external provider

A provider implementation supplies four public capability attributes and one
method:

```python
from geotask_model_adapter_reference import (
    ProviderDiagnostic,
    StructuredModelInvocation,
    StructuredModelResult,
)


class MyExternalProvider:
    provider_id = "example.external-provider"
    external_call = True
    requires_authorization = True
    audit_supported = True

    def invoke(
        self,
        invocation: StructuredModelInvocation,
    ) -> StructuredModelResult:
        # Resolve invocation.authorization_ref outside GeoTask Core.
        # Call the provider with private implementation code.
        # Convert provider-native output to a registered GeoTask Artifact.
        output_payload = create_structured_geotask_result()
        return StructuredModelResult.completed(
            output_payload,
            external_call_executed=True,
            audit_ref="audit://immutable-provider-call-reference",
        )
```

The provider must not return provider-native response objects. It must normalize
its outcome to `StructuredModelResult` and preserve whether an external call was
executed. A completed real external call should carry an immutable or
access-controlled `audit_ref`.

If a provider cannot return a trustworthy structured result, the Adapter raises
a generic `ModelAdapterContractError` rather than inventing a Runtime state or
exposing provider-native exception details.

## Build the independent package

The package can be built without resolving its future Core dependency:

```bash
python -m build examples/model_adapters/provider_neutral \
  --outdir model-adapter-dist
python -m twine check model-adapter-dist/*
```

Do not publish this package before GeoTask Core v0.4.0 is tagged and the installed
Runtime Interface compatibility tests pass.

## Verification

Run the package contract tests from the repository root:

```bash
python -m pytest tests/test_provider_neutral_model_adapter_example.py -q
```

These tests cover:

- independent package metadata and Core packaging separation;
- Descriptor, Request, and output Artifact validation;
- Mock Provider completion without external calls;
- pre-provider rejection of invalid input and contract mismatch;
- failure closure for invalid and deceptive model output;
- opaque authorization and audit propagation for an external provider stub;
- generic exception handling without provider-detail leakage;
- absence of network and provider SDK imports in the public package.
