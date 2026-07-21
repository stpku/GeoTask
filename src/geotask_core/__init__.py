"""GeoTask Core: Lightweight spatial task representation for LLMs.

STIR was the original prototype name. The project has been renamed to GeoTask.
Old import paths (stir_core.*) are still supported as deprecated aliases.

v1.0 modules are available under geotask_core.v1.*
"""

__version__ = "0.2.0"

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
from geotask_core.v1.result import GeotaskResult

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
    "GeotaskResult",
]
