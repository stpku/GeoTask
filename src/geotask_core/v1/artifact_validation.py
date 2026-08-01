"""Unified validation for registered public GeoTask artifacts.

The API dispatches by stable Artifact ID, verifies the installed Schema Bundle,
and reuses each artifact's strict semantic validator. Validation is read-only and
never executes operators, control actions, or output releases.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from geotask_core.v1.agent_artifacts import (
    AgentArtifactFormatError,
    load_agent_evidence_recovery_report,
    load_agent_generation_preparation_report,
    load_agent_revision_retry_report,
    load_agent_revision_verification_report,
)
from geotask_core.v1.artifact_registry import (
    ARTIFACT_VALIDATION_SCHEMA_ID,
    ARTIFACT_VALIDATION_SCHEMA_VERSION,
    ArtifactDescriptor,
    get_artifact_descriptor,
)
from geotask_core.v1.core_benchmark_contract import CoreBenchmarkFormatError
from geotask_core.v1.core_benchmark_report import load_core_benchmark_report
from geotask_core.v1.observation import ObservationFormatError, load_observation
from geotask_core.v1.runtime_interface import (
    RuntimeInterfaceFormatError,
    load_runtime_descriptor,
    load_runtime_request,
    load_runtime_response,
)
from geotask_core.v1.schema_bundle import verify_schema_bundle
from geotask_core.v1.serialized_validation import (
    CONTROL_EVALUATION_VALIDATION_CONTRACT,
    EXECUTION_RESULT_VALIDATION_CONTRACT,
    VersionedPayloadContract,
    validate_versioned_payload,
)


ARTIFACT_VALIDATION_REPORT_VERSION = "1.0"


class ArtifactValidationFormatError(ValueError):
    """Raised when a serialized Artifact Validation Report is inconsistent."""


@dataclass(frozen=True)
class ArtifactValidationReport:
    """Common validation result for one registered public artifact."""

    descriptor: ArtifactDescriptor
    file: str
    valid: bool
    schema_verified: bool
    summary: Mapping[str, object]
    diagnostics: tuple[dict[str, object], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return the stable ``artifact_validation/1.0`` envelope."""

        return {
            "artifact_validation": {
                "report_version": ARTIFACT_VALIDATION_REPORT_VERSION,
                "valid": self.valid,
                "artifact_id": self.descriptor.artifact_id,
                "artifact_kind": self.descriptor.kind,
                "schema_id": self.descriptor.schema_id,
                "schema_version": self.descriptor.schema_version,
                "schema_verified": self.schema_verified,
                "file": self.file,
                "summary": dict(self.summary),
                "diagnostics": [dict(item) for item in self.diagnostics],
            }
        }


_REPORT_BODY_FIELDS = {
    "report_version",
    "valid",
    "artifact_id",
    "artifact_kind",
    "schema_id",
    "schema_version",
    "schema_verified",
    "file",
    "summary",
    "diagnostics",
}
_REPORT_DIAGNOSTIC_FIELDS = {
    "code",
    "path",
    "message",
    "severity",
    "suggested_fix",
}


def _require_report_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ArtifactValidationFormatError(f"{label} must be an object")
    return value


def _require_exact_report_fields(
    value: Mapping[str, object],
    expected: set[str],
    label: str,
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise ArtifactValidationFormatError(
            f"{label} is missing required field(s): {', '.join(missing)}"
        )
    if unknown:
        raise ArtifactValidationFormatError(
            f"{label} contains unknown field(s): {', '.join(unknown)}"
        )


def load_artifact_validation_report(
    payload: Mapping[str, object],
) -> ArtifactValidationReport:
    """Strictly load and cross-check an ``artifact_validation/1.0`` report."""

    root = _require_report_mapping(payload, "Artifact Validation Report")
    _require_exact_report_fields(root, {"artifact_validation"}, "report root")
    body = _require_report_mapping(
        root["artifact_validation"],
        "artifact_validation",
    )
    _require_exact_report_fields(
        body,
        _REPORT_BODY_FIELDS,
        "artifact_validation",
    )

    if body["report_version"] != ARTIFACT_VALIDATION_REPORT_VERSION:
        raise ArtifactValidationFormatError(
            "artifact_validation.report_version must be "
            f"{ARTIFACT_VALIDATION_REPORT_VERSION!r}"
        )
    valid = body["valid"]
    schema_verified = body["schema_verified"]
    if not isinstance(valid, bool):
        raise ArtifactValidationFormatError("artifact_validation.valid must be boolean")
    if not isinstance(schema_verified, bool):
        raise ArtifactValidationFormatError(
            "artifact_validation.schema_verified must be boolean"
        )

    artifact_id = body["artifact_id"]
    if not isinstance(artifact_id, str) or not artifact_id:
        raise ArtifactValidationFormatError(
            "artifact_validation.artifact_id must be a non-empty string"
        )
    try:
        descriptor = get_artifact_descriptor(artifact_id)
    except KeyError as exc:
        raise ArtifactValidationFormatError(str(exc)) from None

    identity_fields = {
        "artifact_kind": descriptor.kind,
        "schema_id": descriptor.schema_id,
        "schema_version": descriptor.schema_version,
    }
    for field, expected in identity_fields.items():
        if body[field] != expected:
            raise ArtifactValidationFormatError(
                f"artifact_validation.{field} must match Registry value "
                f"{expected!r} for {artifact_id}"
            )

    file = body["file"]
    if not isinstance(file, str):
        raise ArtifactValidationFormatError("artifact_validation.file must be a string")

    summary_value = _require_report_mapping(
        body["summary"],
        "artifact_validation.summary",
    )
    summary: dict[str, object] = {}
    for key, value in summary_value.items():
        if not isinstance(key, str):
            raise ArtifactValidationFormatError(
                "artifact_validation.summary keys must be strings"
            )
        if not isinstance(value, (str, int, float, bool)) and value is not None:
            raise ArtifactValidationFormatError(
                f"artifact_validation.summary.{key} must be a JSON scalar"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise ArtifactValidationFormatError(
                f"artifact_validation.summary.{key} must be finite"
            )
        summary[key] = value

    diagnostics_value = body["diagnostics"]
    if not isinstance(diagnostics_value, list):
        raise ArtifactValidationFormatError(
            "artifact_validation.diagnostics must be an array"
        )
    diagnostics: list[dict[str, object]] = []
    error_count = 0
    for index, item in enumerate(diagnostics_value):
        diagnostic = _require_report_mapping(
            item,
            f"artifact_validation.diagnostics[{index}]",
        )
        _require_exact_report_fields(
            diagnostic,
            _REPORT_DIAGNOSTIC_FIELDS,
            f"artifact_validation.diagnostics[{index}]",
        )
        code = diagnostic["code"]
        path = diagnostic["path"]
        message = diagnostic["message"]
        severity = diagnostic["severity"]
        suggested_fix = diagnostic["suggested_fix"]
        if not isinstance(code, str) or not code:
            raise ArtifactValidationFormatError(
                f"artifact_validation.diagnostics[{index}].code must be non-empty"
            )
        if not isinstance(path, str):
            raise ArtifactValidationFormatError(
                f"artifact_validation.diagnostics[{index}].path must be a string"
            )
        if not isinstance(message, str) or not message:
            raise ArtifactValidationFormatError(
                f"artifact_validation.diagnostics[{index}].message must be non-empty"
            )
        if severity not in {"error", "warning"}:
            raise ArtifactValidationFormatError(
                f"artifact_validation.diagnostics[{index}].severity must be "
                "'error' or 'warning'"
            )
        if not isinstance(suggested_fix, str):
            raise ArtifactValidationFormatError(
                f"artifact_validation.diagnostics[{index}].suggested_fix must be "
                "a string"
            )
        if severity == "error":
            error_count += 1
        diagnostics.append(dict(diagnostic))

    if valid and not schema_verified:
        raise ArtifactValidationFormatError(
            "artifact_validation.valid cannot be true when schema_verified is false"
        )
    if valid and error_count:
        raise ArtifactValidationFormatError(
            "artifact_validation.valid cannot be true with error diagnostics"
        )
    if not valid and error_count == 0:
        raise ArtifactValidationFormatError(
            "artifact_validation.valid false requires at least one error diagnostic"
        )

    return ArtifactValidationReport(
        descriptor=descriptor,
        file=file,
        valid=valid,
        schema_verified=schema_verified,
        summary=summary,
        diagnostics=tuple(diagnostics),
    )


def _diagnostic(
    *,
    code: str,
    message: str,
    path: str = "",
    severity: str = "error",
    suggested_fix: str = "",
) -> dict[str, object]:
    return {
        "code": code,
        "path": path,
        "message": message,
        "severity": severity,
        "suggested_fix": suggested_fix,
    }


def _normalize_diagnostics(
    diagnostics: list[dict] | tuple[dict[str, str], ...],
) -> tuple[dict[str, object], ...]:
    normalized: list[dict[str, object]] = []
    for item in diagnostics:
        normalized.append(
            _diagnostic(
                code=str(item.get("code", "invalid_artifact")),
                path=str(item.get("path", "")),
                message=str(item.get("message", "artifact validation failed")),
                severity=str(item.get("severity", "error")),
                suggested_fix=str(item.get("suggested_fix", "")),
            )
        )
    return tuple(normalized)


def _schema_integrity(
    descriptor: ArtifactDescriptor,
) -> tuple[bool, tuple[dict[str, object], ...]]:
    report = verify_schema_bundle(descriptor.artifact_id)[
        "schema_bundle_verification"
    ]
    if report["valid"]:
        return True, ()
    diagnostics = tuple(
        _diagnostic(
            code=str(item.get("code", "invalid_schema_bundle")),
            path="",
            message=str(item.get("message", "Schema Bundle integrity failed")),
            suggested_fix=(
                "Reinstall geotask-core from a verified distribution and rerun "
                "`geotask schema verify`."
            ),
        )
        for item in report["diagnostics"]
    )
    return False, diagnostics


def _invalid_file_report(
    descriptor: ArtifactDescriptor,
    *,
    file: str,
    message: str,
    schema_verified: bool,
) -> ArtifactValidationReport:
    return ArtifactValidationReport(
        descriptor=descriptor,
        file=file,
        valid=False,
        schema_verified=schema_verified,
        summary={},
        diagnostics=(
            _diagnostic(
                code="invalid_artifact_file",
                message=message,
                suggested_fix=(
                    "Provide a readable artifact file in the format registered for "
                    f"{descriptor.artifact_id}."
                ),
            ),
        ),
    )


def _validate_document_payload(
    descriptor: ArtifactDescriptor,
    payload: Mapping[str, object],
    *,
    file: str,
) -> ArtifactValidationReport:
    from geotask_core.parser import validate_document

    data = dict(payload)
    diagnostics = _normalize_diagnostics(validate_document(data))
    errors = [item for item in diagnostics if item["severity"] != "warning"]
    warnings = [item for item in diagnostics if item["severity"] == "warning"]
    metadata = data.get("geotask")
    if not isinstance(metadata, Mapping):
        metadata = data.get("stir") if isinstance(data.get("stir"), Mapping) else {}
    operators = data.get("operator_set", data.get("ops", {}))
    assertions = data.get("assertions", [])
    tasks = data.get("tasks", data.get("task", {}))
    summary = {
        "document_name": str(metadata.get("name", "")),
        "object_count": len(data.get("objects", {}))
        if isinstance(data.get("objects"), Mapping)
        else 0,
        "operator_count": len(operators) if isinstance(operators, Mapping) else 0,
        "assertion_count": len(assertions) if isinstance(assertions, list) else 0,
        "task_count": len(tasks) if isinstance(tasks, list) else (1 if tasks else 0),
        "warning_count": len(warnings),
        "error_count": len(errors),
    }
    return ArtifactValidationReport(
        descriptor=descriptor,
        file=file,
        valid=not errors,
        schema_verified=True,
        summary=summary,
        diagnostics=diagnostics,
    )


def _validate_serialized_payload(
    descriptor: ArtifactDescriptor,
    payload: Mapping[str, object],
    *,
    file: str,
    contract: VersionedPayloadContract,
) -> ArtifactValidationReport:
    report, loaded = validate_versioned_payload(payload, contract, file=file)
    summary: dict[str, object] = {
        "task_id": report.task_id,
        contract.count_field: report.item_count,
    }
    if loaded is None:
        summary = {
            "task_id": "",
            contract.count_field: 0,
        }
    return ArtifactValidationReport(
        descriptor=descriptor,
        file=file,
        valid=report.valid,
        schema_verified=True,
        summary=summary,
        diagnostics=_normalize_diagnostics(report.diagnostics),
    )


def _validate_artifact_validation_report_payload(
    descriptor: ArtifactDescriptor,
    payload: Mapping[str, object],
    *,
    file: str,
) -> ArtifactValidationReport:
    try:
        loaded = load_artifact_validation_report(payload)
    except ArtifactValidationFormatError as exc:
        return ArtifactValidationReport(
            descriptor=descriptor,
            file=file,
            valid=False,
            schema_verified=True,
            summary={
                "validated_artifact_id": "",
                "validated_artifact_valid": False,
                "diagnostic_count": 0,
            },
            diagnostics=(
                _diagnostic(
                    code="invalid_artifact_validation_report",
                    message=str(exc),
                    suggested_fix=(
                        "Regenerate the report with `geotask artifact validate "
                        "<artifact-id> <file> --format json`."
                    ),
                ),
            ),
        )

    return ArtifactValidationReport(
        descriptor=descriptor,
        file=file,
        valid=True,
        schema_verified=True,
        summary={
            "validated_artifact_id": loaded.descriptor.artifact_id,
            "validated_artifact_valid": loaded.valid,
            "diagnostic_count": len(loaded.diagnostics),
        },
    )


def _validate_agent_report_payload(
    descriptor: ArtifactDescriptor,
    payload: Mapping[str, object],
    *,
    file: str,
) -> ArtifactValidationReport:
    loaders = {
        "geotask.agent-generation-preparation": (
            load_agent_generation_preparation_report,
            "agent_generation_preparation",
        ),
        "geotask.agent-revision-verification": (
            load_agent_revision_verification_report,
            "agent_revision_verification",
        ),
        "geotask.agent-revision-retry": (
            load_agent_revision_retry_report,
            "agent_revision_retry",
        ),
        "geotask.agent-evidence-recovery": (
            load_agent_evidence_recovery_report,
            "agent_integration",
        ),
    }
    loader, wrapper = loaders[descriptor.artifact_id]
    try:
        loaded = loader(payload)
    except AgentArtifactFormatError as exc:
        return ArtifactValidationReport(
            descriptor=descriptor,
            file=file,
            valid=False,
            schema_verified=True,
            summary={},
            diagnostics=(
                _diagnostic(
                    code="invalid_agent_report",
                    message=str(exc),
                    suggested_fix=(
                        "Regenerate the report with its declared GeoTask Agent command."
                    ),
                ),
            ),
        )

    body = loaded[wrapper]
    if descriptor.artifact_id == "geotask.agent-generation-preparation":
        summary = {
            "report_state": body["state"],
            "final_valid": body["final_validation"]["valid"],
            "repair_count": body["summary"]["repair_count"],
            "task_executed": body["summary"]["task_executed"],
        }
    elif descriptor.artifact_id == "geotask.agent-revision-verification":
        summary = {
            "report_state": body["state"],
            "accepted": body["summary"]["accepted"],
            "changed_path_count": body["summary"]["changed_path_count"],
            "violation_count": body["summary"]["violation_count"],
        }
    elif descriptor.artifact_id == "geotask.agent-revision-retry":
        summary = {
            "report_state": body["state"],
            "revision_accepted": body["summary"]["revision_accepted"],
            "task_executed": body["summary"]["task_executed"],
            "preparation_state": body["summary"]["preparation_state"],
        }
    else:
        summary = {
            "report_state": body["state"],
            "evidence_complete": body["request"]["evidence_complete"],
            "task_reexecuted": body["materialization"]["task_reexecuted"],
            "decision_value": body["summary"]["decision_value"],
            "blocked_output_count": len(body["summary"]["blocked_outputs"]),
            "eligible_output_count": len(body["summary"]["eligible_outputs"]),
            "diagnostic_count": len(body["diagnostics"]),
        }
    return ArtifactValidationReport(
        descriptor=descriptor,
        file=file,
        valid=True,
        schema_verified=True,
        summary=summary,
    )


def _validate_runtime_artifact_payload(
    descriptor: ArtifactDescriptor,
    payload: Mapping[str, object],
    *,
    file: str,
) -> ArtifactValidationReport:
    loaders = {
        "geotask.runtime-descriptor": load_runtime_descriptor,
        "geotask.runtime-request": load_runtime_request,
        "geotask.runtime-response": load_runtime_response,
    }
    loader = loaders[descriptor.artifact_id]
    try:
        loaded = loader(payload)
    except RuntimeInterfaceFormatError as exc:
        return ArtifactValidationReport(
            descriptor=descriptor,
            file=file,
            valid=False,
            schema_verified=True,
            summary={},
            diagnostics=(
                _diagnostic(
                    code="invalid_runtime_artifact",
                    message=str(exc),
                    suggested_fix=(
                        "Regenerate or revise the Runtime artifact according to the "
                        "GeoTask Runtime Interface Profile v0.1."
                    ),
                ),
            ),
        )

    if descriptor.artifact_id == "geotask.runtime-descriptor":
        summary = {
            "runtime_id": loaded.runtime_id,
            "runtime_version": loaded.runtime_version,
            "operation_count": len(loaded.operations),
            "production_ready": loaded.production_ready,
            "external_side_effects_allowed": loaded.external_side_effects_allowed,
        }
    elif descriptor.artifact_id == "geotask.runtime-request":
        summary = {
            "request_id": loaded.request_id,
            "runtime_id": loaded.runtime_id,
            "operation_id": loaded.operation_id,
            "input_artifact_count": len(loaded.input_artifacts),
            "expected_output_count": len(loaded.expected_output_artifact_ids),
            "authorization_present": loaded.authorization_ref is not None,
        }
    else:
        summary = {
            "request_id": loaded.request_id,
            "runtime_id": loaded.runtime_id,
            "operation_id": loaded.operation_id,
            "response_state": loaded.state,
            "output_artifact_count": len(loaded.output_artifacts),
            "diagnostic_count": len(loaded.diagnostics),
            "side_effects_executed": loaded.side_effects_executed,
            "retryable": loaded.retryable,
        }
    return ArtifactValidationReport(
        descriptor=descriptor,
        file=file,
        valid=True,
        schema_verified=True,
        summary=summary,
    )


def _validate_core_benchmark_payload(
    descriptor: ArtifactDescriptor,
    payload: Mapping[str, object],
    *,
    file: str,
) -> ArtifactValidationReport:
    try:
        loaded = load_core_benchmark_report(payload)
    except CoreBenchmarkFormatError as exc:
        return ArtifactValidationReport(
            descriptor=descriptor,
            file=file,
            valid=False,
            schema_verified=True,
            summary={},
            diagnostics=(
                _diagnostic(
                    code="invalid_core_benchmark_report",
                    message=str(exc),
                    suggested_fix=(
                        "Regenerate the report with `geotask benchmark core --format json`."
                    ),
                ),
            ),
        )

    body = loaded["core_benchmark"]
    conformance = body["conformance"]
    guardrail = body["performance"]["guardrail"]
    return ArtifactValidationReport(
        descriptor=descriptor,
        file=file,
        valid=True,
        schema_verified=True,
        summary={
            "benchmark_state": body["overall"]["state"],
            "benchmark_valid": body["overall"]["valid"],
            "conformance_passed": conformance["valid"],
            "case_count": conformance["case_count"],
            "operator_count": len(conformance["operator_coverage"]),
            "pipeline_p95_ms": guardrail["observed_ms"],
            "performance_guardrail_passed": guardrail["passed"],
            "performance_enforced": guardrail["enforced"],
        },
    )


def _validate_observation_payload(
    descriptor: ArtifactDescriptor,
    payload: Mapping[str, object],
    *,
    file: str,
) -> ArtifactValidationReport:
    try:
        observation = load_observation(payload)
    except ObservationFormatError as exc:
        return ArtifactValidationReport(
            descriptor=descriptor,
            file=file,
            valid=False,
            schema_verified=True,
            summary={},
            diagnostics=(
                _diagnostic(
                    code="invalid_observation",
                    message=str(exc),
                    suggested_fix=(
                        "Revise the payload according to GeoTask Observation v0.1. "
                        "Structural validity does not prove that a claim is true."
                    ),
                ),
            ),
        )

    uncertain_claim_count = sum(
        1 for claim in observation.claims if claim.uncertainty is not None
    )
    return ArtifactValidationReport(
        descriptor=descriptor,
        file=file,
        valid=True,
        schema_verified=True,
        summary={
            "observation_id": observation.observation_id,
            "source_kind": observation.source.kind,
            "producer_kind": observation.producer.kind,
            "claim_count": len(observation.claims),
            "uncertain_claim_count": uncertain_claim_count,
            "supersedes_count": len(observation.supersedes),
            "truth_verified": False,
            "world_state_updated": False,
        },
    )


def _validate_verified_payload(
    descriptor: ArtifactDescriptor,
    payload: Mapping[str, object],
    *,
    file: str,
) -> ArtifactValidationReport:
    if descriptor.artifact_id == "geotask.document":
        return _validate_document_payload(descriptor, payload, file=file)
    if descriptor.artifact_id == "geotask.observation":
        return _validate_observation_payload(descriptor, payload, file=file)
    if descriptor.artifact_id == "geotask.execution-result":
        return _validate_serialized_payload(
            descriptor,
            payload,
            file=file,
            contract=EXECUTION_RESULT_VALIDATION_CONTRACT,
        )
    if descriptor.artifact_id == "geotask.control-evaluation":
        return _validate_serialized_payload(
            descriptor,
            payload,
            file=file,
            contract=CONTROL_EVALUATION_VALIDATION_CONTRACT,
        )
    if descriptor.artifact_id in {
        "geotask.agent-generation-preparation",
        "geotask.agent-revision-verification",
        "geotask.agent-revision-retry",
        "geotask.agent-evidence-recovery",
    }:
        return _validate_agent_report_payload(descriptor, payload, file=file)
    if descriptor.artifact_id in {
        "geotask.runtime-descriptor",
        "geotask.runtime-request",
        "geotask.runtime-response",
    }:
        return _validate_runtime_artifact_payload(descriptor, payload, file=file)
    if descriptor.artifact_id == "geotask.core-benchmark-report":
        return _validate_core_benchmark_payload(descriptor, payload, file=file)
    if descriptor.artifact_id == "geotask.artifact-validation-report":
        return _validate_artifact_validation_report_payload(
            descriptor,
            payload,
            file=file,
        )
    raise KeyError(f"no validator registered for GeoTask artifact: {descriptor.artifact_id}")


def validate_artifact_payload(
    artifact_id: str,
    payload: Mapping[str, object],
    *,
    file: str = "<memory>",
) -> ArtifactValidationReport:
    """Validate an in-memory payload selected by stable Artifact ID."""

    descriptor = get_artifact_descriptor(artifact_id)
    schema_verified, schema_diagnostics = _schema_integrity(descriptor)
    if not schema_verified:
        return ArtifactValidationReport(
            descriptor=descriptor,
            file=file,
            valid=False,
            schema_verified=False,
            summary={},
            diagnostics=schema_diagnostics,
        )
    if not isinstance(payload, Mapping):
        return _invalid_file_report(
            descriptor,
            file=file,
            message="artifact payload must be an object or mapping",
            schema_verified=True,
        )
    return _validate_verified_payload(descriptor, payload, file=file)


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is not allowed")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_json_mapping(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_nonfinite_json,
            object_pairs_hook=_unique_json_object,
        )
    except OSError as exc:
        raise ValueError(f"cannot read artifact file {str(path)!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON in artifact file {str(path)!r} at "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except ValueError as exc:
        raise ValueError(f"invalid JSON in artifact file {str(path)!r}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError(f"artifact file {str(path)!r} must contain a JSON object")
    return dict(payload)


def validate_artifact_file(
    artifact_id: str,
    path: str | Path,
) -> ArtifactValidationReport:
    """Validate one artifact file without executing its task or control actions."""

    descriptor = get_artifact_descriptor(artifact_id)
    file = str(path)
    schema_verified, schema_diagnostics = _schema_integrity(descriptor)
    if not schema_verified:
        return ArtifactValidationReport(
            descriptor=descriptor,
            file=file,
            valid=False,
            schema_verified=False,
            summary={},
            diagnostics=schema_diagnostics,
        )

    try:
        if descriptor.artifact_id == "geotask.document":
            from geotask_core.parser import load_geotask

            payload = load_geotask(path)
            if not isinstance(payload, Mapping):
                raise ValueError(f"GeoTask file {file!r} must contain a mapping")
            mapping = dict(payload)
        else:
            mapping = _load_json_mapping(Path(path))
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        return _invalid_file_report(
            descriptor,
            file=file,
            message=str(exc),
            schema_verified=True,
        )

    return _validate_verified_payload(descriptor, mapping, file=file)


__all__ = [
    "ARTIFACT_VALIDATION_SCHEMA_ID",
    "ARTIFACT_VALIDATION_SCHEMA_VERSION",
    "ARTIFACT_VALIDATION_REPORT_VERSION",
    "ArtifactValidationFormatError",
    "ArtifactValidationReport",
    "load_artifact_validation_report",
    "validate_artifact_payload",
    "validate_artifact_file",
]
