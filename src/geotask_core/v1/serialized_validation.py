"""Shared validation contracts for versioned serialized GeoTask artifacts.

The framework centralizes strict loader invocation, schema metadata, summary
extraction, and machine-readable validation reports. Artifact-specific modules
remain responsible for validating their own payload semantics.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from geotask_core.v1.control_evaluation import (
    CONTROL_EVALUATION_SCHEMA_ID,
    CONTROL_EVALUATION_SCHEMA_VERSION,
    ControlEvaluationResult,
    load_control_evaluation,
)
from geotask_core.v1.result import (
    GEOTASK_RESULT_SCHEMA_ID,
    GEOTASK_RESULT_SCHEMA_VERSION,
    GeotaskResult,
)


T = TypeVar("T")


@dataclass(frozen=True)
class VersionedPayloadContract(Generic[T]):
    """Strict loader and report metadata for one serialized artifact type."""

    artifact_name: str
    report_key: str
    schema_id: str
    schema_version: str
    invalid_code: str
    count_field: str
    count_label: str
    loader: Callable[[Mapping[str, object]], T]
    task_id_getter: Callable[[T], str]
    count_getter: Callable[[T], int]


@dataclass(frozen=True)
class VersionedPayloadValidationReport:
    """Common validation result for a versioned serialized payload."""

    contract: VersionedPayloadContract[Any]
    file: str
    valid: bool
    task_id: str = ""
    item_count: int = 0
    diagnostics: tuple[dict[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "valid": self.valid,
            "schema_id": self.contract.schema_id,
            "schema_version": self.contract.schema_version,
            "file": self.file,
            "task_id": self.task_id,
            self.contract.count_field: self.item_count,
            "diagnostics": [dict(item) for item in self.diagnostics],
        }
        return {self.contract.report_key: body}


def invalid_versioned_payload_report(
    contract: VersionedPayloadContract[Any],
    *,
    file: str,
    message: str,
    path: str = "",
) -> VersionedPayloadValidationReport:
    """Build a stable invalid report for load or format failures."""

    return VersionedPayloadValidationReport(
        contract=contract,
        file=file,
        valid=False,
        diagnostics=(
            {
                "code": contract.invalid_code,
                "path": path,
                "message": message,
            },
        ),
    )


def validate_versioned_payload(
    payload: Mapping[str, object],
    contract: VersionedPayloadContract[T],
    *,
    file: str,
) -> tuple[VersionedPayloadValidationReport, T | None]:
    """Load one payload and return a common report plus the loaded artifact."""

    try:
        loaded = contract.loader(payload)
    except (TypeError, ValueError) as exc:
        return (
            invalid_versioned_payload_report(
                contract,
                file=file,
                message=str(exc),
            ),
            None,
        )

    count = contract.count_getter(loaded)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise TypeError("contract count_getter must return a non-negative integer")
    task_id = contract.task_id_getter(loaded)
    if not isinstance(task_id, str):
        raise TypeError("contract task_id_getter must return a string")

    return (
        VersionedPayloadValidationReport(
            contract=contract,
            file=file,
            valid=True,
            task_id=task_id,
            item_count=count,
        ),
        loaded,
    )


EXECUTION_RESULT_VALIDATION_CONTRACT = VersionedPayloadContract[GeotaskResult](
    artifact_name="Result",
    report_key="result_validation",
    schema_id=GEOTASK_RESULT_SCHEMA_ID,
    schema_version=GEOTASK_RESULT_SCHEMA_VERSION,
    invalid_code="invalid_geotask_result",
    count_field="check_count",
    count_label="Checks",
    loader=GeotaskResult.from_dict,
    task_id_getter=lambda result: result.task_id,
    count_getter=lambda result: len(result.checks),
)

CONTROL_EVALUATION_VALIDATION_CONTRACT = VersionedPayloadContract[
    ControlEvaluationResult
](
    artifact_name="Control evaluation",
    report_key="control_validation",
    schema_id=CONTROL_EVALUATION_SCHEMA_ID,
    schema_version=CONTROL_EVALUATION_SCHEMA_VERSION,
    invalid_code="invalid_control_evaluation",
    count_field="evaluation_count",
    count_label="Evaluations",
    loader=load_control_evaluation,
    task_id_getter=lambda result: result.task_id,
    count_getter=lambda result: len(result.evaluations),
)


__all__ = [
    "VersionedPayloadContract",
    "VersionedPayloadValidationReport",
    "invalid_versioned_payload_report",
    "validate_versioned_payload",
    "EXECUTION_RESULT_VALIDATION_CONTRACT",
    "CONTROL_EVALUATION_VALIDATION_CONTRACT",
]
