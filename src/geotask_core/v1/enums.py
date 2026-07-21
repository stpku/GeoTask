"""v1.0 Enumeration types, error codes, status constants, and ID validation.

All v1.0 canonical concepts as clean Python 3.10+ enums with string values.
Imported by ir.py, validator.py, executor.py, and result_builder.py to avoid
magic-string dispersion across the codebase.
"""

from __future__ import annotations

import re
from enum import Enum, IntEnum


# ═══════════════════════════════════════════════════════════════════════════════
# -- Encoding Types
# ═══════════════════════════════════════════════════════════════════════════════

class EncodingType(str, Enum):
    """How a GeoTask document is serialised for transport / storage."""
    natural_language = "natural_language"
    geotask_yaml     = "geotask_yaml"
    geotask_json     = "geotask_json"
    compact_dsl      = "compact_dsl"

# Backward-compatible uppercase aliases (v0.1 Runtime contract)
EncodingType.NATURAL_LANGUAGE = EncodingType.natural_language
EncodingType.GEOTASK_YAML     = EncodingType.geotask_yaml
EncodingType.COMPACT_DSL      = EncodingType.compact_dsl


# ═══════════════════════════════════════════════════════════════════════════════
# -- Execution
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionMode(str, Enum):
    """Where a task or step is executed."""
    model_only    = "model_only"
    local_only    = "local_only"
    hybrid        = "hybrid"
    shadow_compare = "shadow_compare"


class ExecutionStatus(str, Enum):
    """Lifecycle of a single execution step."""
    pending   = "pending"
    running   = "running"
    completed = "completed"
    partial   = "partial"
    failed    = "failed"
    skipped   = "skipped"


class ExecutorType(str, Enum):
    """Who / what executes a step."""
    model     = "model"
    local     = "local"
    connector = "connector"
    human     = "human"
    runtime   = "runtime"


# ═══════════════════════════════════════════════════════════════════════════════
# -- Verification
# ═══════════════════════════════════════════════════════════════════════════════

class VerificationMode(str, Enum):
    """How a claim is verified."""
    none                  = "none"
    model_self_check      = "model_self_check"
    local_deterministic   = "local_deterministic"
    model_local_compare   = "model_local_compare"
    cross_model_compare   = "cross_model_compare"
    human_review          = "human_review"


class AssuranceLevel(IntEnum):
    """Ordered confidence that a computed result is correct (higher = stronger)."""
    unverified               = 0
    model_generated          = 1
    model_self_checked       = 2
    local_deterministic      = 3
    model_local_agreement    = 4
    independent_cross_verified = 5
    human_reviewed           = 6


# ═══════════════════════════════════════════════════════════════════════════════
# -- Claim / Proposition Status
# ═══════════════════════════════════════════════════════════════════════════════

class ClaimStatus(str, Enum):
    """States a claim (proposition) can be in during the pipeline."""
    proposed          = "proposed"
    computed          = "computed"
    verified          = "verified"
    contradicted      = "contradicted"
    need_review       = "need_review"
    need_data         = "need_data"
    invalid_input     = "invalid_input"
    invalid_operator  = "invalid_operator"
    invalid_reference = "invalid_reference"
    execution_error   = "execution_error"
    unverifiable      = "unverifiable"


# ═══════════════════════════════════════════════════════════════════════════════
# -- Error / Diagnostic Codes
# ═══════════════════════════════════════════════════════════════════════════════

# Document-level structural errors
MISSING_FIELD           = "missing_field"
UNKNOWN_FIELD           = "unknown_field"
INVALID_TYPE            = "invalid_type"
DUPLICATE_ID            = "duplicate_id"
DUPLICATE_KEY           = "duplicate_key"
UNKNOWN_OBJECT_TYPE     = "unknown_object_type"

# Geometry / spatial errors
INVALID_COORDINATES     = "invalid_coordinates"
INVALID_GEOMETRY        = "invalid_geometry"
INVALID_INTERVAL        = "invalid_interval"
INVALID_CRS             = "invalid_crs"
UNIT_MISMATCH           = "unit_mismatch"

# Operator / reference errors
INVALID_OPERATOR        = "invalid_operator"
INVALID_REFERENCE       = "invalid_reference"
ARITY_MISMATCH          = "arity_mismatch"
OBJECT_TYPE_MISMATCH    = "object_type_mismatch"

# Execution errors
UNSUPPORTED_EXECUTION_MODE = "unsupported_execution_mode"
EXECUTION_LIMIT_EXCEEDED   = "execution_limit_exceeded"
CYCLIC_DEPENDENCY          = "cyclic_dependency"
MISSING_DATA               = "missing_data"

# Claim / result errors
UNVERIFIABLE_CLAIM         = "unverifiable_claim"
EXECUTION_ERROR            = "execution_error"
OUTPUT_CONTRACT_VIOLATION  = "output_contract_violation"


class DiagnosticSeverity(str, Enum):
    """How severe a diagnostic / validation issue is."""
    error   = "error"
    warning = "warning"


# ═══════════════════════════════════════════════════════════════════════════════
# -- GeoTask Object Types
# ═══════════════════════════════════════════════════════════════════════════════

OBJECT_TYPE_POINT              = "point"
OBJECT_TYPE_POLYLINE           = "polyline"
OBJECT_TYPE_RECT               = "rect"
OBJECT_TYPE_TIME_INTERVAL      = "time_interval"
OBJECT_TYPE_ALTITUDE_INTERVAL  = "altitude_interval"
OBJECT_TYPE_FEATURE_COLLECTION = "feature_collection"

VALID_OBJECT_TYPES: set[str] = {
    OBJECT_TYPE_POINT,
    OBJECT_TYPE_POLYLINE,
    OBJECT_TYPE_RECT,
    OBJECT_TYPE_TIME_INTERVAL,
    OBJECT_TYPE_ALTITUDE_INTERVAL,
    OBJECT_TYPE_FEATURE_COLLECTION,
}

LEGACY_OBJECT_TYPE_MAP: dict[str, str] = {
    "line":      OBJECT_TYPE_POLYLINE,
    "time":      OBJECT_TYPE_TIME_INTERVAL,
    "altitude":  OBJECT_TYPE_ALTITUDE_INTERVAL,
}


# ═══════════════════════════════════════════════════════════════════════════════
# -- On-Error Policy
# ═══════════════════════════════════════════════════════════════════════════════

class OnErrorPolicy(str, Enum):
    """What the runtime should do when a step / task fails."""
    stop       = "stop"
    skip       = "skip"
    continue_  = "continue"    # 'continue' is a Python keyword
    need_review = "need_review"
    fallback   = "fallback"


# ═══════════════════════════════════════════════════════════════════════════════
# -- ID Validation
# ═══════════════════════════════════════════════════════════════════════════════

_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")


def is_valid_geotask_id(id_str: str) -> bool:
    """Return True if *id_str* is a valid v1.0 GeoTask identifier.

    Rules:
      - Starts with an ASCII letter (A-Z / a-z)
      - Remaining 0–127 characters are letters, digits, underscore, dot, or hyphen
      - Max total length: 128
    """
    return bool(_ID_PATTERN.match(id_str))
