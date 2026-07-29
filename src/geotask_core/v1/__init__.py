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
from geotask_core.v1.extension_profiles import (
    CONTROL_PROFILE_ID,
    CONTROL_PROFILE_VERSION,
    validate_extension_profiles,
)
from geotask_core.v1.control_expressions import (
    CONTROL_EXPRESSION_LANGUAGE_ID,
    CONTROL_EXPRESSION_LANGUAGE_VERSION,
    ExpressionSyntaxError,
    ExpressionEvaluationError,
    parse_control_expression,
    evaluate_control_expression,
    referenced_identifiers,
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
    "CONTROL_PROFILE_ID",
    "CONTROL_PROFILE_VERSION",
    "validate_extension_profiles",
    "CONTROL_EXPRESSION_LANGUAGE_ID",
    "CONTROL_EXPRESSION_LANGUAGE_VERSION",
    "ExpressionSyntaxError",
    "ExpressionEvaluationError",
    "parse_control_expression",
    "evaluate_control_expression",
    "referenced_identifiers",
]
