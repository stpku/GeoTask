"""v1.0 Result dataclasses and serialization helpers.

Defines the structured output types (CheckResult, ExecutionSummary,
ResultSummary, OverallResult, GeotaskResult) produced by the execution
engine, plus helper functions for formatting, timestamp generation,
and AssuranceLevel conversion.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from geotask_core.v1.enums import (
    AssuranceLevel,
    ClaimStatus,
    ExecutionMode,
    ExecutionStatus,
    ExecutorType,
)


GEOTASK_RESULT_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/geotask-result-v1.0.schema.json"
)
GEOTASK_RESULT_SCHEMA_VERSION = "1.0"

_EXECUTION_MODES = {item.value for item in ExecutionMode}
_EXECUTION_STATUSES = {item.value for item in ExecutionStatus}
_EXECUTOR_TYPES = {item.value for item in ExecutorType}
_CLAIM_STATUSES = {item.value for item in ClaimStatus}
_ASSURANCE_LEVELS = {item.name for item in AssuranceLevel}


# -- Result Dataclasses


class ResultFormatError(ValueError):
    """Raised when serialized GeoTask result data violates the v1 contract."""


def _require_mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ResultFormatError(f"{path} must be an object")
    return value


def _require_list(value: object, path: str) -> list:
    if not isinstance(value, list):
        raise ResultFormatError(f"{path} must be an array")
    return value


def _require_string(value: object, path: str) -> str:
    if not isinstance(value, str):
        raise ResultFormatError(f"{path} must be a string")
    return value


def _require_enum(value: object, path: str, allowed: set[str]) -> str:
    text = _require_string(value, path)
    if text not in allowed:
        raise ResultFormatError(
            f"{path} must be one of: {', '.join(sorted(allowed))}"
        )
    return text


def _require_bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise ResultFormatError(f"{path} must be a boolean")
    return value


def _require_int(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ResultFormatError(f"{path} must be an integer")
    return value


def _require_keys(
    value: Mapping[str, Any],
    *,
    path: str,
    required: set[str],
) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise ResultFormatError(
            f"{path} is missing required field(s): {', '.join(missing)}"
        )
    unknown = sorted(set(value) - required)
    if unknown:
        raise ResultFormatError(
            f"{path} contains unknown field(s): {', '.join(unknown)}"
        )


@dataclass
class CheckResult:
    """Result of dispatching a single assertion."""

    assertion_id: str
    operator: str
    object_refs: list
    executor: str  # "local", "model", "connector", "human"
    value: Any = None
    unit: str = ""
    status: str = ""  # ClaimStatus value
    assurance_level: str = ""  # AssuranceLevel name
    deterministic: bool = False
    evidence_refs: list = field(default_factory=list)
    error: dict | None = None  # structured error info if failed


@dataclass
class ExecutionSummary:
    """Metadata about the overall execution run."""

    mode: str = ""
    status: str = ""  # ExecutionStatus
    started_at: str = ""
    finished_at: str = ""


@dataclass
class ResultSummary:
    """Aggregate counts across all checks."""

    total_checks: int = 0
    verified: int = 0
    contradicted: int = 0
    need_review: int = 0
    invalid: int = 0


@dataclass
class OverallResult:
    """Synthesised overall verdict and confidence."""

    status: str = ""  # ClaimStatus
    assurance_level: str = ""  # AssuranceLevel name


@dataclass
class GeotaskResult:
    """Complete result of executing a CanonicalDocument.

    Legacy projections (measurements, conclusion, verified_by) are
    computed as ``@property`` from ``self.checks`` — they are NOT a
    second source of truth.
    """

    schema_version: str = "1.0"
    task_id: str = ""
    execution: ExecutionSummary = field(default_factory=ExecutionSummary)
    checks: list = field(default_factory=list)  # list[CheckResult]
    outputs: dict = field(default_factory=dict)
    summary: ResultSummary = field(default_factory=ResultSummary)
    overall: OverallResult = field(default_factory=OverallResult)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    # -- Legacy compatibility projections (computed, not stored)

    @property
    def measurements(self) -> list:
        """Legacy measurement list computed dynamically from checks."""
        result: list = []
        for check in self.checks:
            result.append(
                {
                    "name": check.assertion_id,
                    "value": check.value,
                    "unit": check.unit,
                    "object_refs": check.object_refs,
                    "verified_by": check.operator,
                    "status": check.status,
                }
            )
        return result

    @property
    def conclusion(self) -> dict:
        """Legacy conclusion dict computed dynamically from checks."""
        parts: list[str] = []
        for check in self.checks:
            unit_str = f" {check.unit}" if check.unit else ""
            val = check.value
            val_str = (
                str(val).lower()
                if isinstance(val, bool)
                else str(val)
                if val is not None
                else "N/A"
            )
            parts.append(f"{check.assertion_id}={val_str}{unit_str}")

        return {
            "summary": (
                "; ".join(parts) if parts else "no measurements computed"
            ),
            "external_data_used": False,
        }

    @property
    def verified_by(self) -> list:
        """Legacy verified_by list computed dynamically from checks."""
        return [
            {
                "operation": check.operator,
                "result": _format_value(check.value),
            }
            for check in self.checks
        ]

    # -- v1 Serialization

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GeotaskResult":
        """Deserialize the canonical v1 ``geotask_result`` JSON shape.

        The loader is intentionally strict: missing and unknown fields are
        rejected so CLI control evaluation cannot silently reinterpret a
        legacy or partially shaped result.
        """

        wrapper = _require_mapping(payload, "result")
        _require_keys(wrapper, path="result", required={"geotask_result"})
        data = _require_mapping(wrapper["geotask_result"], "geotask_result")
        _require_keys(
            data,
            path="geotask_result",
            required={
                "schema_version",
                "task_id",
                "execution",
                "checks",
                "outputs",
                "summary",
                "overall",
                "warnings",
                "errors",
            },
        )

        schema_version = _require_string(
            data["schema_version"], "geotask_result.schema_version"
        )
        if schema_version != "1.0":
            raise ResultFormatError(
                "geotask_result.schema_version must be '1.0'"
            )
        task_id = _require_string(data["task_id"], "geotask_result.task_id")
        if not task_id:
            raise ResultFormatError("geotask_result.task_id must not be empty")

        execution_data = _require_mapping(
            data["execution"], "geotask_result.execution"
        )
        _require_keys(
            execution_data,
            path="geotask_result.execution",
            required={"mode", "status", "started_at", "finished_at"},
        )
        execution = ExecutionSummary(
            mode=_require_enum(
                execution_data["mode"],
                "geotask_result.execution.mode",
                _EXECUTION_MODES,
            ),
            status=_require_enum(
                execution_data["status"],
                "geotask_result.execution.status",
                _EXECUTION_STATUSES,
            ),
            started_at=_require_string(
                execution_data["started_at"],
                "geotask_result.execution.started_at",
            ),
            finished_at=_require_string(
                execution_data["finished_at"],
                "geotask_result.execution.finished_at",
            ),
        )

        checks: list[CheckResult] = []
        for index, raw_check in enumerate(
            _require_list(data["checks"], "geotask_result.checks")
        ):
            path = f"geotask_result.checks[{index}]"
            check = _require_mapping(raw_check, path)
            _require_keys(
                check,
                path=path,
                required={
                    "assertion_id",
                    "operator",
                    "object_refs",
                    "executor",
                    "value",
                    "unit",
                    "status",
                    "assurance_level",
                    "deterministic",
                    "evidence_refs",
                    "error",
                },
            )
            object_refs = _require_list(check["object_refs"], f"{path}.object_refs")
            evidence_refs = _require_list(
                check["evidence_refs"], f"{path}.evidence_refs"
            )
            for ref_index, ref in enumerate(object_refs):
                _require_string(ref, f"{path}.object_refs[{ref_index}]")
            for ref_index, ref in enumerate(evidence_refs):
                _require_string(ref, f"{path}.evidence_refs[{ref_index}]")
            error = check["error"]
            if error is not None:
                error = dict(_require_mapping(error, f"{path}.error"))

            checks.append(
                CheckResult(
                    assertion_id=_require_string(
                        check["assertion_id"], f"{path}.assertion_id"
                    ),
                    operator=_require_string(check["operator"], f"{path}.operator"),
                    object_refs=list(object_refs),
                    executor=_require_enum(
                        check["executor"], f"{path}.executor", _EXECUTOR_TYPES
                    ),
                    value=check["value"],
                    unit=_require_string(check["unit"], f"{path}.unit"),
                    status=_require_enum(
                        check["status"], f"{path}.status", _CLAIM_STATUSES
                    ),
                    assurance_level=_require_enum(
                        check["assurance_level"],
                        f"{path}.assurance_level",
                        _ASSURANCE_LEVELS,
                    ),
                    deterministic=_require_bool(
                        check["deterministic"], f"{path}.deterministic"
                    ),
                    evidence_refs=list(evidence_refs),
                    error=error,
                )
            )

        outputs = dict(
            _require_mapping(data["outputs"], "geotask_result.outputs")
        )
        summary_data = _require_mapping(
            data["summary"], "geotask_result.summary"
        )
        _require_keys(
            summary_data,
            path="geotask_result.summary",
            required={
                "total_checks",
                "verified",
                "contradicted",
                "need_review",
                "invalid",
            },
        )
        summary = ResultSummary(
            total_checks=_require_int(
                summary_data["total_checks"],
                "geotask_result.summary.total_checks",
            ),
            verified=_require_int(
                summary_data["verified"], "geotask_result.summary.verified"
            ),
            contradicted=_require_int(
                summary_data["contradicted"],
                "geotask_result.summary.contradicted",
            ),
            need_review=_require_int(
                summary_data["need_review"],
                "geotask_result.summary.need_review",
            ),
            invalid=_require_int(
                summary_data["invalid"], "geotask_result.summary.invalid"
            ),
        )
        summary_counts = {
            "total_checks": summary.total_checks,
            "verified": summary.verified,
            "contradicted": summary.contradicted,
            "need_review": summary.need_review,
            "invalid": summary.invalid,
        }
        negative_counts = sorted(
            name for name, value in summary_counts.items() if value < 0
        )
        if negative_counts:
            raise ResultFormatError(
                "geotask_result.summary contains negative count(s): "
                + ", ".join(negative_counts)
            )
        if summary.total_checks != len(checks):
            raise ResultFormatError(
                "geotask_result.summary.total_checks must equal the number "
                f"of checks ({len(checks)})"
            )

        overall_data = _require_mapping(
            data["overall"], "geotask_result.overall"
        )
        _require_keys(
            overall_data,
            path="geotask_result.overall",
            required={"status", "assurance_level"},
        )
        overall = OverallResult(
            status=_require_enum(
                overall_data["status"],
                "geotask_result.overall.status",
                _CLAIM_STATUSES,
            ),
            assurance_level=_require_enum(
                overall_data["assurance_level"],
                "geotask_result.overall.assurance_level",
                _ASSURANCE_LEVELS,
            ),
        )

        warnings = _require_list(data["warnings"], "geotask_result.warnings")
        for index, warning in enumerate(warnings):
            _require_string(warning, f"geotask_result.warnings[{index}]")
        errors = _require_list(data["errors"], "geotask_result.errors")
        for index, error in enumerate(errors):
            _require_mapping(error, f"geotask_result.errors[{index}]")

        return cls(
            schema_version=schema_version,
            task_id=task_id,
            execution=execution,
            checks=checks,
            outputs=outputs,
            summary=summary,
            overall=overall,
            warnings=list(warnings),
            errors=[dict(error) for error in errors],
        )

    def to_dict(self) -> dict:
        """Serialize to v1.0 result dict format.

        AssuranceLevel enums are serialized as their lowercase ``.name``
        string, NEVER as integers.  Datetimes use RFC 3339 format.
        Legacy projections are NOT duplicated in the serialized output.
        """
        return {
            "geotask_result": {
                "schema_version": self.schema_version,
                "task_id": self.task_id,
                "execution": {
                    "mode": self.execution.mode,
                    "status": self.execution.status,
                    "started_at": self.execution.started_at,
                    "finished_at": self.execution.finished_at,
                },
                "checks": [
                    {
                        "assertion_id": c.assertion_id,
                        "operator": c.operator,
                        "object_refs": c.object_refs,
                        "executor": c.executor,
                        "value": c.value,
                        "unit": c.unit,
                        "status": c.status,
                        "assurance_level": _serialize_assurance(c.assurance_level),
                        "deterministic": c.deterministic,
                        "evidence_refs": c.evidence_refs,
                        "error": c.error,
                    }
                    for c in self.checks
                ],
                "outputs": dict(self.outputs),
                "summary": {
                    "total_checks": self.summary.total_checks,
                    "verified": self.summary.verified,
                    "contradicted": self.summary.contradicted,
                    "need_review": self.summary.need_review,
                    "invalid": self.summary.invalid,
                },
                "overall": {
                    "status": self.overall.status,
                    "assurance_level": _serialize_assurance(self.overall.assurance_level),
                },
                "warnings": list(self.warnings),
                "errors": list(self.errors),
            }
        }


# -- Serialization Helpers


def _serialize_assurance(level: str) -> str:
    """Serialize assurance level as lowercase ``.name`` string."""
    if not level:
        return AssuranceLevel.unverified.name
    # Already a lowercase name string — use as-is
    if isinstance(level, str) and not level.isdigit():
        return level
    # Defensive: if stored as integer string, convert
    try:
        return _assurance_level_by_int(int(level))
    except (ValueError, TypeError):
        return AssuranceLevel.unverified.name


# -- Utility Helpers


def _now_iso() -> str:
    """Return current UTC timestamp as ISO 8601 / RFC 3339 string."""
    return datetime.now(timezone.utc).isoformat()


def _format_value(value: Any) -> str:
    """Format a value for legacy ``verified_by`` projection."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


# -- Assurance Level Mapping Helpers

_ASSURANCE_NAME_TO_INT: dict[str, int] = {
    level.name: level.value for level in AssuranceLevel
}

_ASSURANCE_INT_TO_NAME: dict[int, str] = {
    level.value: level.name for level in AssuranceLevel
}


def _assurance_level_int(name: str) -> int:
    """Convert an AssuranceLevel name to its integer value."""
    return _ASSURANCE_NAME_TO_INT.get(name, 0)


def _assurance_level_by_int(value: int) -> str:
    """Convert an integer to an AssuranceLevel name string."""
    if value in _ASSURANCE_INT_TO_NAME:
        return _ASSURANCE_INT_TO_NAME[value]
    return AssuranceLevel.unverified.name
