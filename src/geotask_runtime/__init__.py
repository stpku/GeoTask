"""GeoTask Runtime v0.1 — private orchestration and governance layer.

THIS IS A SKELETON / INTERFACE DEFINITION.
The Runtime layer is a FUTURE capability. Current implementations are mocks.

GeoTask Runtime is NOT open source. These interfaces define the contract
between public Core and private Runtime/Domain Pack components.
"""

__version__ = "0.1.0-mock"

from geotask_runtime.contracts import (
    EncodingType,
    TaskStatus,
    TaskRequest,
    TaskContext,
    EncodingPlan,
    ModelRequest,
    TokenUsage,
    ModelResponse,
    VerificationPlan,
    RuntimeEvent,
    GovernedTaskResult,
)

__all__ = [
    "__version__",
    "EncodingType",
    "TaskStatus",
    "TaskRequest",
    "TaskContext",
    "EncodingPlan",
    "ModelRequest",
    "TokenUsage",
    "ModelResponse",
    "VerificationPlan",
    "RuntimeEvent",
    "GovernedTaskResult",
]
