"""GeoTask Core: Lightweight spatial task representation for LLMs.

STIR was the original prototype name. The project has been renamed to GeoTask.
Selected old function names, the ``stir`` CLI, and the ``stir:`` YAML key
remain deprecated aliases. The old ``stir_core`` Python package path is not
distributed; imports must use ``geotask_core``.

v1.0 modules are available under geotask_core.v1.*
"""

from geotask_core._version import __version__

from geotask_core.models import (
    PointObject, LineObject, RectObject, StirDocument,
)
from geotask_core.parser import (
    load_geotask, validate_geotask, load_stir, validate_stir,
)
from geotask_core.ops import distance_2d, line_intersects_rect
from geotask_core.runner import run_geotask, run_stir
from geotask_core.normalizer import normalize_model_output
from geotask_core.evaluator import evaluate_model_output
from geotask_core.verifier import verify_normalized_result
from geotask_core.result_schema import (
    STATUS_VERIFIED,
    STATUS_CONTRADICTED,
    STATUS_NEED_REVIEW,
    STATUS_EXTRACTED,
)

# v1.0 exports
from geotask_core.v1.enums import (
    ExecutionMode, VerificationMode, AssuranceLevel,
    ExecutionStatus, ClaimStatus, EncodingType,
    is_valid_geotask_id,
)
from geotask_core.v1.ir import CanonicalDocument, GeotaskMetadata
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.validator import validate_canonical
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.result import (
    GEOTASK_RESULT_SCHEMA_ID,
    GEOTASK_RESULT_SCHEMA_VERSION,
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
from geotask_core.v1.control_evaluation import (
    CONTROL_EVALUATION_SCHEMA_ID,
    CONTROL_EVALUATION_SCHEMA_VERSION,
    ControlContextError,
    ControlEvaluationFormatError,
    ControlContextEntry,
    ControlContext,
    ControlBlockEvaluation,
    ControlEvaluationResult,
    build_control_context,
    evaluate_control_profile,
    load_control_evaluation,
)
from geotask_core.v1.serialized_validation import (
    VersionedPayloadContract,
    VersionedPayloadValidationReport,
    invalid_versioned_payload_report,
    validate_versioned_payload,
    EXECUTION_RESULT_VALIDATION_CONTRACT,
    CONTROL_EVALUATION_VALIDATION_CONTRACT,
)

__all__ = [
    "__version__",
    "PointObject",
    "LineObject",
    "RectObject",
    "StirDocument",
    "load_geotask",
    "validate_geotask",
    "load_stir",
    "validate_stir",
    "distance_2d",
    "line_intersects_rect",
    "run_geotask",
    "run_stir",
    "normalize_model_output",
    "evaluate_model_output",
    "verify_normalized_result",
    "STATUS_VERIFIED",
    "STATUS_CONTRADICTED",
    "STATUS_NEED_REVIEW",
    "STATUS_EXTRACTED",
    # v1.0
    "ExecutionMode",
    "VerificationMode",
    "AssuranceLevel",
    "ExecutionStatus",
    "ClaimStatus",
    "EncodingType",
    "is_valid_geotask_id",
    "CanonicalDocument",
    "GeotaskMetadata",
    "canonicalize",
    "validate_canonical",
    "execute_canonical",
    "GEOTASK_RESULT_SCHEMA_ID",
    "GEOTASK_RESULT_SCHEMA_VERSION",
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
    "CONTROL_EVALUATION_SCHEMA_ID",
    "CONTROL_EVALUATION_SCHEMA_VERSION",
    "ControlContextError",
    "ControlEvaluationFormatError",
    "ControlContextEntry",
    "ControlContext",
    "ControlBlockEvaluation",
    "ControlEvaluationResult",
    "build_control_context",
    "evaluate_control_profile",
    "load_control_evaluation",
    "VersionedPayloadContract",
    "VersionedPayloadValidationReport",
    "invalid_versioned_payload_report",
    "validate_versioned_payload",
    "EXECUTION_RESULT_VALIDATION_CONTRACT",
    "CONTROL_EVALUATION_VALIDATION_CONTRACT",
]
