"""OpenAI Responses API integration for the GeoTask Runtime Interface."""

from .client import (
    OpenAIClientResolutionError,
    OpenAIClientResolver,
    StaticOpenAIClientResolver,
)
from .config import (
    OPENAI_AUTHORIZATION_REF,
    OPENAI_RESPONSES_ADAPTER_VERSION,
    OPENAI_RUNTIME_ID,
    OPENAI_RUNTIME_VERSION,
    OpenAIProviderConfigurationError,
    OpenAIResponsesConfig,
)
from .provider import OpenAIResponsesStructuredProvider
from .runtime import build_openai_responses_runtime_adapter

__version__ = OPENAI_RESPONSES_ADAPTER_VERSION

__all__ = [
    "__version__",
    "OPENAI_AUTHORIZATION_REF",
    "OPENAI_RESPONSES_ADAPTER_VERSION",
    "OPENAI_RUNTIME_ID",
    "OPENAI_RUNTIME_VERSION",
    "OpenAIProviderConfigurationError",
    "OpenAIResponsesConfig",
    "OpenAIClientResolutionError",
    "OpenAIClientResolver",
    "StaticOpenAIClientResolver",
    "OpenAIResponsesStructuredProvider",
    "build_openai_responses_runtime_adapter",
]
