"""Public-safe provider-neutral model Adapter skeleton for GeoTask."""

from .adapter import ProviderNeutralModelRuntimeAdapter
from .contracts import (
    DEFAULT_MODEL_REF,
    MODEL_ADAPTER_PACKAGE_VERSION,
    MODEL_RUNTIME_ID,
    MODEL_RUNTIME_VERSION,
    ModelAdapterConfig,
    ModelAdapterContractError,
    ProviderDiagnostic,
    StructuredModelInvocation,
    StructuredModelProvider,
    StructuredModelResult,
)
from .mock_provider import MockStructuredModelProvider

__version__ = MODEL_ADAPTER_PACKAGE_VERSION

__all__ = [
    "__version__",
    "DEFAULT_MODEL_REF",
    "MODEL_ADAPTER_PACKAGE_VERSION",
    "MODEL_RUNTIME_ID",
    "MODEL_RUNTIME_VERSION",
    "ModelAdapterConfig",
    "ModelAdapterContractError",
    "ProviderDiagnostic",
    "StructuredModelInvocation",
    "StructuredModelProvider",
    "StructuredModelResult",
    "MockStructuredModelProvider",
    "ProviderNeutralModelRuntimeAdapter",
]
