"""Offline self-diagnostic for an installed GeoTask Core developer environment.

The doctor command aggregates existing public Core health signals. It does not add
an Artifact, Schema, Operator, GT capability, external evidence source, model call,
or production action. All checks are local, read-only apart from an explicitly
requested CLI output file, and fail closed when a required component is unhealthy.
"""

from __future__ import annotations

import json
import platform
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TextIO

from geotask_core._version import __version__
from geotask_core.capability_registry import (
    CAPABILITY_REGISTRY_VERSION,
    capability_registry_payload,
)
from geotask_core.operator_registry import (
    REQUIRED_OPERATOR_METADATA_FIELDS,
    list_operator_metadata,
)
from geotask_core.reference_agent_activation import (
    ReferenceAgentActivationError,
    locate_reference_agent_bundle,
    replay_materialized_reference_agent,
    verify_reference_agent_bundle,
)
from geotask_core.v1.artifact_registry import artifact_registry_payload
from geotask_core.v1.core_benchmark import run_core_benchmark
from geotask_core.v1.schema_bundle import BUNDLED_SCHEMA_IDS, verify_schema_bundle
from geotask_core.verification_quality_benchmark import (
    run_verification_quality_benchmark,
)

DOCTOR_SCHEMA_VERSION = "0.1"
REQUIRES_PYTHON = ">=3.10"
CI_TESTED_PYTHON_VERSIONS = ("3.10", "3.11", "3.12", "3.13")


class DoctorError(ValueError):
    """Raised when doctor CLI arguments or output handling are invalid."""


def _failure(check_id: str, exc: BaseException) -> dict[str, Any]:
    return {
        "id": check_id,
        "state": "failed",
        "valid": False,
        "summary": str(exc) or exc.__class__.__name__,
        "diagnostics": [
            {
                "code": "doctor_check_failed",
                "message": str(exc) or exc.__class__.__name__,
                "exception_type": exc.__class__.__name__,
            }
        ],
    }


def _run_check(
    check_id: str,
    callback: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    try:
        result = callback()
    except Exception as exc:  # noqa: BLE001 - fail closed and report each check
        return _failure(check_id, exc)

    valid = result.get("valid")
    if not isinstance(valid, bool):
        return _failure(
            check_id,
            DoctorError(f"{check_id} did not return a boolean valid field"),
        )
    state = result.get("state")
    if state is None:
        state = "passed" if valid else "failed"
    if state not in {"passed", "warning", "failed"}:
        return _failure(
            check_id,
            DoctorError(f"{check_id} returned unsupported state {state!r}"),
        )
    if not valid and state != "failed":
        state = "failed"
    return {**result, "id": check_id, "state": state}


def _check_package() -> dict[str, Any]:
    version = str(__version__).strip()
    valid = bool(version)
    return {
        "valid": valid,
        "summary": f"geotask-core {version}" if valid else "package version is unavailable",
        "version": version,
    }


def _check_python_support() -> dict[str, Any]:
    major_minor = (sys.version_info.major, sys.version_info.minor)
    version_key = f"{major_minor[0]}.{major_minor[1]}"
    meets_requires_python = major_minor >= (3, 10)
    ci_tested = version_key in CI_TESTED_PYTHON_VERSIONS
    state = "passed" if meets_requires_python and ci_tested else "warning"
    if not meets_requires_python:
        state = "failed"
    return {
        "valid": meets_requires_python,
        "state": state,
        "summary": (
            f"Python {platform.python_version()} is in the Core CI matrix"
            if meets_requires_python and ci_tested
            else (
                f"Python {platform.python_version()} satisfies {REQUIRES_PYTHON} "
                "but is outside the current Core CI matrix"
                if meets_requires_python
                else f"Python {platform.python_version()} does not satisfy {REQUIRES_PYTHON}"
            )
        ),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "requires_python": REQUIRES_PYTHON,
        "ci_tested_versions": list(CI_TESTED_PYTHON_VERSIONS),
        "ci_tested": ci_tested,
    }


def _check_schema_bundle() -> dict[str, Any]:
    report = verify_schema_bundle()["schema_bundle_verification"]
    checked_count = report.get("checked_count")
    valid = bool(report.get("valid")) and checked_count == len(BUNDLED_SCHEMA_IDS)
    diagnostics = report.get("diagnostics")
    return {
        "valid": valid,
        "summary": (
            f"verified {checked_count} bundled schemas"
            if valid
            else "Schema Bundle verification failed"
        ),
        "checked_count": checked_count,
        "expected_count": len(BUNDLED_SCHEMA_IDS),
        "bundle_version": report.get("bundle_version"),
        "diagnostics": diagnostics if isinstance(diagnostics, list) else [],
    }


def _check_artifact_registry() -> dict[str, Any]:
    body = artifact_registry_payload()["artifact_registry"]
    artifacts = body.get("artifacts")
    if not isinstance(artifacts, list):
        raise DoctorError("Artifact Registry artifacts must be an array")
    artifact_ids = [
        item.get("artifact_id")
        for item in artifacts
        if isinstance(item, Mapping)
    ]
    declared_count = body.get("artifact_count")
    valid = (
        bool(artifacts)
        and len(artifact_ids) == len(artifacts)
        and declared_count == len(artifacts)
        and len(set(artifact_ids)) == len(artifact_ids)
        and all(isinstance(item, str) and item for item in artifact_ids)
    )
    return {
        "valid": valid,
        "summary": (
            f"discovered {len(artifact_ids)} registered public artifacts"
            if valid
            else "Artifact Registry discovery is inconsistent"
        ),
        "registry_version": body.get("registry_version"),
        "artifact_count": len(artifact_ids),
    }


def _check_operator_registry() -> dict[str, Any]:
    operators = list_operator_metadata()
    names = [item.get("name") for item in operators]
    missing_fields = {
        str(item.get("name", f"operator-{index}")): sorted(
            REQUIRED_OPERATOR_METADATA_FIELDS - set(item)
        )
        for index, item in enumerate(operators)
        if REQUIRED_OPERATOR_METADATA_FIELDS - set(item)
    }
    nondeterministic = [
        str(item.get("name"))
        for item in operators
        if item.get("deterministic") is not True
    ]
    valid = (
        bool(operators)
        and len(set(names)) == len(names)
        and not missing_fields
        and not nondeterministic
        and all(isinstance(name, str) and name for name in names)
    )
    return {
        "valid": valid,
        "summary": (
            f"discovered {len(operators)} deterministic Core operators"
            if valid
            else "Operator Registry discovery is inconsistent"
        ),
        "operator_count": len(operators),
        "missing_metadata_fields": missing_fields,
        "nondeterministic_operators": nondeterministic,
    }


def _check_capability_registry() -> dict[str, Any]:
    body = capability_registry_payload()["capability_registry"]
    capabilities = body.get("capabilities")
    boundaries = body.get("boundaries")
    if not isinstance(capabilities, list) or not isinstance(boundaries, Mapping):
        raise DoctorError("Capability Registry returned an invalid report shape")
    capability_ids = {
        item.get("id")
        for item in capabilities
        if isinstance(item, Mapping)
    }
    required = {
        "geotask.operator-registry",
        "geotask.artifact-registry",
        "geotask.schema-bundle",
        "geotask.runtime-interface",
        "geotask.verification-provider-interface",
        "geotask.reference-agent",
        "geotask.core-benchmark",
        "geotask.verification-quality-benchmark",
        "geotask.self-diagnostic",
    }
    valid = all(
        (
            body.get("registry_version") == CAPABILITY_REGISTRY_VERSION,
            body.get("scope") == "installed_public_core",
            body.get("capability_count") == len(capabilities),
            required.issubset(capability_ids),
            boundaries.get("registered_artifact") is False,
            boundaries.get("new_schema_introduced") is False,
            boundaries.get("new_operator_introduced") is False,
            boundaries.get("external_plugins_discovered") is False,
            boundaries.get("runtime_instances_discovered") is False,
            boundaries.get("provider_instances_discovered") is False,
            boundaries.get("network_used") is False,
            boundaries.get("real_world_validation_claimed") is False,
            boundaries.get("authorization_granted") is False,
            boundaries.get("action_executed") is False,
        )
    )
    return {
        "valid": valid,
        "summary": (
            f"discovered {len(capabilities)} installed public Core capability surfaces"
            if valid
            else "Capability Registry discovery is inconsistent"
        ),
        "registry_version": body.get("registry_version"),
        "capability_count": len(capabilities),
    }


def _check_reference_agent_bundle() -> dict[str, Any]:
    bundle = locate_reference_agent_bundle()
    manifest = verify_reference_agent_bundle(bundle)["reference_agent_bundle"]
    content_sha256 = manifest.get("content_sha256")
    file_count = manifest.get("file_count")
    valid = (
        isinstance(file_count, int)
        and file_count > 0
        and isinstance(content_sha256, str)
        and len(content_sha256) == 64
    )
    return {
        "valid": valid,
        "summary": (
            f"verified Reference Agent bundle ({file_count} files)"
            if valid
            else "Reference Agent bundle manifest is invalid"
        ),
        "bundle_version": manifest.get("bundle_version"),
        "file_count": file_count,
        "content_sha256": content_sha256,
    }


def _check_reference_agent_replay() -> dict[str, Any]:
    bundle = locate_reference_agent_bundle()
    result = replay_materialized_reference_agent(bundle, scenario="success")
    body = result.get("reference_agent")
    if not isinstance(body, Mapping):
        raise ReferenceAgentActivationError("Reference Agent replay requires reference_agent")
    verification = body.get("verification")
    decision = body.get("decision_assurance")
    if not isinstance(verification, Mapping) or not isinstance(decision, Mapping):
        raise ReferenceAgentActivationError(
            "Reference Agent replay is missing verification or decision_assurance"
        )
    valid = all(
        (
            verification.get("state") == "satisfied",
            decision.get("report_update_eligible") is True,
            decision.get("production_write_performed") is False,
            decision.get("production_report_refreshed") is False,
            decision.get("action_authorized") is False,
            decision.get("action_executed") is False,
        )
    )
    return {
        "valid": valid,
        "summary": (
            "deterministic Reference Agent success replay passed"
            if valid
            else "Reference Agent success replay violated its expected boundary"
        ),
        "scenario": "success",
        "verification_state": verification.get("state"),
        "report_update_eligible": decision.get("report_update_eligible"),
        "production_write_performed": decision.get("production_write_performed"),
        "action_authorized": decision.get("action_authorized"),
        "action_executed": decision.get("action_executed"),
    }


def _check_core_benchmark() -> dict[str, Any]:
    report = run_core_benchmark(
        iterations=1,
        warmup_iterations=0,
        enforce_performance=False,
    )["core_benchmark"]
    overall = report.get("overall")
    conformance = report.get("conformance")
    boundaries = report.get("boundaries")
    if not all(isinstance(item, Mapping) for item in (overall, conformance, boundaries)):
        raise DoctorError("Core benchmark returned an invalid report shape")
    valid = all(
        (
            overall.get("valid") is True,
            conformance.get("valid") is True,
            boundaries.get("network_used") is False,
            boundaries.get("model_called") is False,
            boundaries.get("external_data_used") is False,
        )
    )
    return {
        "valid": valid,
        "summary": (
            f"Core conformance passed {conformance.get('passed')}/{conformance.get('case_count')} cases"
            if valid
            else "Core conformance benchmark failed"
        ),
        "benchmark_version": report.get("benchmark_version"),
        "case_count": conformance.get("case_count"),
        "passed": conformance.get("passed"),
        "performance_enforced": False,
    }


def _check_quality_benchmark() -> dict[str, Any]:
    report = run_verification_quality_benchmark()["verification_quality_benchmark"]
    boundaries = report.get("boundaries")
    if not isinstance(boundaries, Mapping):
        raise DoctorError("Verification Quality Benchmark returned invalid boundaries")
    valid = all(
        (
            report.get("valid") is True,
            boundaries.get("fictional_data_only") is True,
            boundaries.get("network_used") is False,
            boundaries.get("model_called") is False,
            boundaries.get("production_system_accessed") is False,
            boundaries.get("production_write_performed") is False,
            boundaries.get("cross_domain_generalization_claimed") is False,
        )
    )
    return {
        "valid": valid,
        "summary": (
            "Verification Quality Benchmark fixed suite passed"
            if valid
            else "Verification Quality Benchmark fixed suite failed"
        ),
        "benchmark_version": report.get("benchmark_version"),
        "metric_scope": boundaries.get("metric_scope"),
    }


def run_doctor() -> dict[str, Any]:
    """Run all local self-diagnostic checks and return a machine-readable payload."""

    checks = [
        _run_check("package", _check_package),
        _run_check("python_support", _check_python_support),
        _run_check("schema_bundle", _check_schema_bundle),
        _run_check("artifact_registry", _check_artifact_registry),
        _run_check("operator_registry", _check_operator_registry),
        _run_check("capability_registry", _check_capability_registry),
        _run_check("reference_agent_bundle", _check_reference_agent_bundle),
        _run_check("reference_agent_replay", _check_reference_agent_replay),
        _run_check("core_benchmark", _check_core_benchmark),
        _run_check("quality_benchmark", _check_quality_benchmark),
    ]
    failed = sum(1 for check in checks if check["valid"] is not True)
    warnings = sum(1 for check in checks if check["state"] == "warning")
    passed = len(checks) - failed - warnings
    valid = failed == 0
    return {
        "geotask_core_doctor": {
            "schema_version": DOCTOR_SCHEMA_VERSION,
            "state": "passed" if valid else "failed",
            "valid": valid,
            "geotask_core_version": __version__,
            "summary": {
                "check_count": len(checks),
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
            },
            "checks": checks,
            "boundaries": {
                "registered_artifact": False,
                "new_schema_introduced": False,
                "new_operator_introduced": False,
                "network_used": False,
                "model_called": False,
                "external_truth_fetched": False,
                "production_system_accessed": False,
                "production_write_performed": False,
                "action_authorized": False,
                "action_executed": False,
                "core_benchmark_performance_enforced": False,
                "quality_benchmark_suite": "fixed",
            },
        }
    }


def render_doctor_text(report: Mapping[str, Any]) -> str:
    body = report.get("geotask_core_doctor")
    if not isinstance(body, Mapping):
        raise DoctorError("doctor report requires geotask_core_doctor")
    summary = body.get("summary")
    checks = body.get("checks")
    if not isinstance(summary, Mapping) or not isinstance(checks, list):
        raise DoctorError("doctor report is missing summary or checks")

    lines = [
        f"GeoTask Core Doctor v{body.get('schema_version')}",
        f"state: {body.get('state')}",
        f"geotask-core: {body.get('geotask_core_version')}",
        (
            "checks: "
            f"{summary.get('passed')} passed, "
            f"{summary.get('warnings')} warnings, "
            f"{summary.get('failed')} failed"
        ),
        "",
    ]
    for check in checks:
        if not isinstance(check, Mapping):
            continue
        state = str(check.get("state", "failed"))
        label = {"passed": "PASS", "warning": "WARN", "failed": "FAIL"}.get(
            state,
            "FAIL",
        )
        lines.append(f"[{label}] {check.get('id')}: {check.get('summary')}")
    lines.extend(
        [
            "",
            "boundary: offline/read-only; no model, network, production access, authorization, or action execution",
            "note: doctor output is a diagnostic payload, not a registered GeoTask Artifact",
        ]
    )
    return "\n".join(lines) + "\n"


def print_doctor_usage(stream: TextIO | None = None) -> None:
    output = stream or sys.stdout
    print(
        "Usage: geotask inspect health [--format text|json] [--output <file>|-] [--compact]",
        file=output,
    )
    print(
        "Runs offline read-only package, registry, bundle, replay, and benchmark health checks.",
        file=output,
    )


def _parse_args(args: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {
        "help": False,
        "format": "text",
        "output_path": None,
        "compact": False,
    }
    seen: set[str] = set()
    index = 0
    while index < len(args):
        argument = args[index]
        if argument in {"--help", "-h"}:
            parsed["help"] = True
            index += 1
            continue
        if argument == "--compact":
            if argument in seen:
                raise DoctorError("--compact may be provided only once")
            seen.add(argument)
            parsed["compact"] = True
            index += 1
            continue
        if argument in {"--format", "--output"}:
            if argument in seen:
                raise DoctorError(f"{argument} may be provided only once")
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                raise DoctorError(f"{argument} requires a value")
            seen.add(argument)
            if argument == "--format":
                parsed["format"] = args[index + 1]
            else:
                parsed["output_path"] = args[index + 1]
            index += 2
            continue
        raise DoctorError(f"unknown doctor option: {argument}")

    output_format = str(parsed["format"])
    if output_format not in {"text", "json"}:
        raise DoctorError(
            f"unsupported doctor format: {output_format}. Supported formats: text, json"
        )
    if parsed["compact"] and output_format != "json":
        raise DoctorError("--compact is supported only with --format json")
    return parsed


def _render_report(
    report: dict[str, Any],
    *,
    output_format: str,
    compact: bool,
) -> str:
    if output_format == "text":
        return render_doctor_text(report)
    if compact:
        return json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    return json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


def _write_report(rendered: str, output_path: object, stdout: TextIO) -> None:
    if output_path is None or output_path == "-":
        stdout.write(rendered)
        return
    target = Path(str(output_path)).resolve()
    if target.exists() and not target.is_file():
        raise DoctorError("--output must identify a file")
    try:
        target.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        raise DoctorError(f"cannot write doctor output {str(output_path)!r}: {exc}") from exc


def run_doctor_command(
    args: list[str],
    *,
    stdout: TextIO | None = None,
) -> tuple[dict[str, Any] | None, int]:
    """Run the doctor CLI command and return ``(report, exit_code)``."""

    output = stdout or sys.stdout
    parsed = _parse_args(args)
    if parsed["help"]:
        print_doctor_usage(output)
        return None, 0

    report = run_doctor()
    rendered = _render_report(
        report,
        output_format=str(parsed["format"]),
        compact=bool(parsed["compact"]),
    )
    _write_report(rendered, parsed["output_path"], output)
    valid = bool(report["geotask_core_doctor"]["valid"])
    return report, 0 if valid else 2


__all__ = [
    "CI_TESTED_PYTHON_VERSIONS",
    "DOCTOR_SCHEMA_VERSION",
    "REQUIRES_PYTHON",
    "DoctorError",
    "print_doctor_usage",
    "render_doctor_text",
    "run_doctor",
    "run_doctor_command",
]
