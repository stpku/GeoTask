"""Build the OpenAI provider into the public GeoTask Runtime Adapter contract."""

from __future__ import annotations

from geotask_model_adapter_reference import (
    ModelAdapterConfig,
    ProviderNeutralModelRuntimeAdapter,
)

from .client import OpenAIClientResolver
from .config import (
    OPENAI_RUNTIME_ID,
    OPENAI_RUNTIME_VERSION,
    OpenAIResponsesConfig,
)
from .provider import OpenAIResponsesStructuredProvider


def build_openai_responses_runtime_adapter(
    config: OpenAIResponsesConfig,
    client_resolver: OpenAIClientResolver,
) -> ProviderNeutralModelRuntimeAdapter:
    """Return an external, authorized, audited ``execute-nonlocal`` Runtime Adapter."""

    provider = OpenAIResponsesStructuredProvider(
        config=config,
        client_resolver=client_resolver,
    )
    runtime_config = ModelAdapterConfig(
        runtime_id=OPENAI_RUNTIME_ID,
        runtime_version=OPENAI_RUNTIME_VERSION,
        title="GeoTask OpenAI Responses Runtime Adapter",
        model_ref=f"openai://responses/{config.model}",
        input_artifact_id="geotask.document",
        output_artifact_id="geotask.execution-result",
    )
    return ProviderNeutralModelRuntimeAdapter(provider, runtime_config)


__all__ = ["build_openai_responses_runtime_adapter"]
