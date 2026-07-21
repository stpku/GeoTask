"""v1.0 Result dataclasses and serialization helpers.

Defines the structured output types (CheckResult, ExecutionSummary,
ResultSummary, OverallResult, GeotaskResult) produced by the execution
engine, plus helper functions for formatting, timestamp generation,
and AssuranceLevel conversion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from geotask_core.v1.enums import AssuranceLevel


# -- Result Dataclasses


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
