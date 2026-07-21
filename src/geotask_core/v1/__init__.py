"""GeoTask Core v1.0 — Canonical Intermediate Representation and tooling.

v1.0 represents a clean break from the v0.x prototype. The canonical IR
(ir.py) is the single source of truth for Parser, Validator, Executor,
and Result Builder.
"""

from geotask_core.v1.ir import (
    GeotaskVersion,
    GeotaskMetadata,
    SpaceCRS,
    SpaceDefinition,
    GeoObject,
    OperatorContract,
    Assertion,
    Task,
    ExecutionStep,
    ExecutionDefinition,
    VerificationDefinition,
    OutputContract,
    CanonicalDocument,
)
from geotask_core.v1.result import (
    CheckResult,
    ExecutionSummary,
    ResultSummary,
    OverallResult,
    GeotaskResult,
)

__all__ = [
    "GeotaskVersion",
    "GeotaskMetadata",
    "SpaceCRS",
    "SpaceDefinition",
    "GeoObject",
    "OperatorContract",
    "Assertion",
    "Task",
    "ExecutionStep",
    "ExecutionDefinition",
    "VerificationDefinition",
    "OutputContract",
    "CanonicalDocument",
    "CheckResult",
    "ExecutionSummary",
    "ResultSummary",
    "OverallResult",
    "GeotaskResult",
]
