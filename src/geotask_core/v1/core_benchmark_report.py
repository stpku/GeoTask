"""Strict semantic loader for public GeoTask Core benchmark reports."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from datetime import datetime

from geotask_core.v1.core_benchmark_contract import (
    CORE_BENCHMARK_ID,
    CORE_BENCHMARK_REPORT_VERSION,
    CORE_BENCHMARK_SCHEMA_ID,
    CORE_BENCHMARK_SCHEMA_VERSION,
    CORE_BENCHMARK_STAGE_NAMES,
    CORE_BENCHMARK_VERSION,
    CoreBenchmarkFormatError,
)


def _fail(message: str) -> None:
    raise CoreBenchmarkFormatError(message)


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail(f"{path} must be an object")
    return value


def _exact_keys(value: Mapping[str, object], path: str, required: set[str]) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required)
    if missing:
        _fail(f"{path} is missing field(s): {', '.join(missing)}")
    if unknown:
        _fail(f"{path} contains unknown field(s): {', '.join(unknown)}")


def _string(value: object, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        label = "string" if allow_empty else "non-empty string"
        _fail(f"{path} must be a {label}")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{path} must be a boolean")
    return value


def _integer(value: object, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail(f"{path} must be an integer >= {minimum}")
    return value


def _number(value: object, path: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{path} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        _fail(f"{path} must be finite and >= {minimum}")
    return result


def _array(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        _fail(f"{path} must be an array")
    return value


def _timestamp(value: object, path: str) -> str:
    text = _string(value, path)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        _fail(f"{path} must be an ISO 8601 timestamp")
    if parsed.tzinfo is None:
        _fail(f"{path} must include a timezone")
    return text


def _validate_metric(value: object, path: str) -> dict[str, float | int]:
    metric = _mapping(value, path)
    _exact_keys(
        metric,
        path,
        {"sample_count", "min_ms", "median_ms", "p95_ms", "max_ms"},
    )
    result: dict[str, float | int] = {
        "sample_count": _integer(
            metric["sample_count"], f"{path}.sample_count", minimum=1
        ),
        "min_ms": _number(metric["min_ms"], f"{path}.min_ms"),
        "median_ms": _number(metric["median_ms"], f"{path}.median_ms"),
        "p95_ms": _number(metric["p95_ms"], f"{path}.p95_ms"),
        "max_ms": _number(metric["max_ms"], f"{path}.max_ms"),
    }
    if not (
        float(result["min_ms"])
        <= float(result["median_ms"])
        <= float(result["p95_ms"])
        <= float(result["max_ms"])
    ):
        _fail(f"{path} latency ordering must satisfy min <= median <= p95 <= max")
    return result


def _validate_header(body: Mapping[str, object]) -> None:
    expected = {
        "report_version": CORE_BENCHMARK_REPORT_VERSION,
        "schema_id": CORE_BENCHMARK_SCHEMA_ID,
        "schema_version": CORE_BENCHMARK_SCHEMA_VERSION,
        "benchmark_id": CORE_BENCHMARK_ID,
        "benchmark_version": CORE_BENCHMARK_VERSION,
    }
    for field, expected_value in expected.items():
        actual = _string(body[field], f"core_benchmark.{field}")
        if actual != expected_value:
            _fail(f"core_benchmark.{field} is unsupported")
    _timestamp(body["generated_at"], "core_benchmark.generated_at")


def _validate_environment(value: object) -> None:
    path = "core_benchmark.environment"
    environment = _mapping(value, path)
    keys = {
        "python_version",
        "python_implementation",
        "platform_system",
        "platform_machine",
        "geotask_core_version",
    }
    _exact_keys(environment, path, keys)
    for key in keys:
        _string(environment[key], f"{path}.{key}")


def _validate_configuration(value: object) -> tuple[int, float, bool]:
    path = "core_benchmark.configuration"
    configuration = _mapping(value, path)
    _exact_keys(
        configuration,
        path,
        {
            "iterations",
            "warmup_iterations",
            "max_pipeline_p95_ms",
            "performance_enforced",
        },
    )
    iterations = _integer(configuration["iterations"], f"{path}.iterations", minimum=1)
    _integer(configuration["warmup_iterations"], f"{path}.warmup_iterations")
    threshold = _number(
        configuration["max_pipeline_p95_ms"],
        f"{path}.max_pipeline_p95_ms",
        minimum=0.000001,
    )
    enforced = _boolean(
        configuration["performance_enforced"], f"{path}.performance_enforced"
    )
    return iterations, threshold, enforced


def _validate_diagnostics(value: object, path: str) -> list[object]:
    diagnostics = _array(value, path)
    for index, raw_diagnostic in enumerate(diagnostics):
        diagnostic_path = f"{path}[{index}]"
        diagnostic = _mapping(raw_diagnostic, diagnostic_path)
        _exact_keys(diagnostic, diagnostic_path, {"code", "message"})
        _string(diagnostic["code"], f"{diagnostic_path}.code")
        _string(diagnostic["message"], f"{diagnostic_path}.message")
    return diagnostics


def _validate_conformance(value: object) -> tuple[bool, int, list[str]]:
    path = "core_benchmark.conformance"
    conformance = _mapping(value, path)
    _exact_keys(
        conformance,
        path,
        {"valid", "case_count", "passed", "failed", "operator_coverage", "cases"},
    )
    valid = _boolean(conformance["valid"], f"{path}.valid")
    case_count = _integer(conformance["case_count"], f"{path}.case_count", minimum=1)
    passed = _integer(conformance["passed"], f"{path}.passed")
    failed = _integer(conformance["failed"], f"{path}.failed")
    if passed + failed != case_count:
        _fail(f"{path} counts are inconsistent")
    if valid != (passed == case_count and failed == 0):
        _fail(f"{path}.valid is inconsistent with counts")

    coverage = [
        _string(item, f"{path}.operator_coverage[{index}]")
        for index, item in enumerate(_array(conformance["operator_coverage"], f"{path}.operator_coverage"))
    ]
    if coverage != sorted(set(coverage)):
        _fail(f"{path}.operator_coverage must be sorted and unique")

    cases = _array(conformance["cases"], f"{path}.cases")
    if len(cases) != case_count:
        _fail(f"{path}.cases length does not match case_count")
    case_ids: list[str] = []
    valid_count = 0
    for index, raw_case in enumerate(cases):
        case_path = f"{path}.cases[{index}]"
        case = _mapping(raw_case, case_path)
        _exact_keys(
            case,
            case_path,
            {
                "case_id",
                "valid",
                "assertion_count",
                "operators",
                "semantic_sha256",
                "deterministic_replay",
                "result_roundtrip",
                "expected_outputs_match",
                "evidence_refs_match",
                "overall_status",
                "diagnostics",
            },
        )
        case_id = _string(case["case_id"], f"{case_path}.case_id")
        if case_id in case_ids:
            _fail(f"{case_path}.case_id is duplicated")
        case_ids.append(case_id)
        case_valid = _boolean(case["valid"], f"{case_path}.valid")
        valid_count += int(case_valid)
        assertion_count = _integer(
            case["assertion_count"], f"{case_path}.assertion_count"
        )
        operators = _array(case["operators"], f"{case_path}.operators")
        if len(operators) != assertion_count:
            _fail(f"{case_path}.operators length must match assertion_count")
        for operator_index, operator in enumerate(operators):
            _string(operator, f"{case_path}.operators[{operator_index}]")
        digest = _string(
            case["semantic_sha256"],
            f"{case_path}.semantic_sha256",
            allow_empty=True,
        )
        if digest and (
            len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            _fail(f"{case_path}.semantic_sha256 must be a lowercase SHA-256 digest")
        flags = [
            _boolean(case[field], f"{case_path}.{field}")
            for field in (
                "deterministic_replay",
                "result_roundtrip",
                "expected_outputs_match",
                "evidence_refs_match",
            )
        ]
        overall_status = _string(
            case["overall_status"], f"{case_path}.overall_status"
        )
        diagnostics = _validate_diagnostics(
            case["diagnostics"], f"{case_path}.diagnostics"
        )
        expected_valid = (
            all(flags)
            and overall_status == "verified"
            and not diagnostics
            and bool(digest)
            and assertion_count > 0
        )
        if case_valid != expected_valid:
            _fail(f"{case_path}.valid is inconsistent with case evidence")
    if valid_count != passed:
        _fail(f"{path}.passed does not match valid cases")
    return valid, case_count, case_ids


def _validate_performance(
    value: object,
    *,
    iterations: int,
    case_count: int,
    case_ids: list[str],
    threshold: float,
    performance_enforced: bool,
) -> tuple[bool, bool]:
    path = "core_benchmark.performance"
    performance = _mapping(value, path)
    _exact_keys(
        performance,
        path,
        {
            "valid",
            "sample_count",
            "throughput_cases_per_second",
            "stage_metrics",
            "case_metrics",
            "guardrail",
        },
    )
    performance_valid = _boolean(performance["valid"], f"{path}.valid")
    sample_count = _integer(
        performance["sample_count"], f"{path}.sample_count", minimum=1
    )
    if sample_count != iterations * case_count:
        _fail(f"{path}.sample_count is inconsistent")
    _number(
        performance["throughput_cases_per_second"],
        f"{path}.throughput_cases_per_second",
    )

    stage_metrics = _array(performance["stage_metrics"], f"{path}.stage_metrics")
    if len(stage_metrics) != len(CORE_BENCHMARK_STAGE_NAMES):
        _fail(f"{path}.stage_metrics has unexpected length")
    stage_names: list[str] = []
    pipeline_p95: float | None = None
    for index, raw_metric in enumerate(stage_metrics):
        metric_path = f"{path}.stage_metrics[{index}]"
        metric = _mapping(raw_metric, metric_path)
        _exact_keys(
            metric,
            metric_path,
            {"stage", "sample_count", "min_ms", "median_ms", "p95_ms", "max_ms"},
        )
        stage = _string(metric["stage"], f"{metric_path}.stage")
        stage_names.append(stage)
        values = _validate_metric(
            {key: item for key, item in metric.items() if key != "stage"},
            metric_path,
        )
        if values["sample_count"] != sample_count:
            _fail(f"{metric_path}.sample_count is inconsistent")
        if stage == "pipeline":
            pipeline_p95 = float(values["p95_ms"])
    if stage_names != list(CORE_BENCHMARK_STAGE_NAMES):
        _fail(f"{path}.stage_metrics must use stable stage order")

    case_metrics = _array(performance["case_metrics"], f"{path}.case_metrics")
    if len(case_metrics) != case_count:
        _fail(f"{path}.case_metrics length is inconsistent")
    metric_case_ids: list[str] = []
    for index, raw_metric in enumerate(case_metrics):
        metric_path = f"{path}.case_metrics[{index}]"
        metric = _mapping(raw_metric, metric_path)
        _exact_keys(
            metric,
            metric_path,
            {"case_id", "sample_count", "min_ms", "median_ms", "p95_ms", "max_ms"},
        )
        metric_case_ids.append(_string(metric["case_id"], f"{metric_path}.case_id"))
        values = _validate_metric(
            {key: item for key, item in metric.items() if key != "case_id"},
            metric_path,
        )
        if values["sample_count"] != iterations:
            _fail(f"{metric_path}.sample_count must equal configured iterations")
    if metric_case_ids != case_ids:
        _fail(f"{path}.case_metrics must match conformance case order")

    guardrail_path = f"{path}.guardrail"
    guardrail = _mapping(performance["guardrail"], guardrail_path)
    _exact_keys(
        guardrail,
        guardrail_path,
        {"metric", "threshold_ms", "observed_ms", "enforced", "passed"},
    )
    if _string(guardrail["metric"], f"{guardrail_path}.metric") != "pipeline_p95_ms":
        _fail(f"{guardrail_path}.metric is unsupported")
    guardrail_threshold = _number(
        guardrail["threshold_ms"], f"{guardrail_path}.threshold_ms", minimum=0.000001
    )
    observed = _number(guardrail["observed_ms"], f"{guardrail_path}.observed_ms")
    enforced = _boolean(guardrail["enforced"], f"{guardrail_path}.enforced")
    passed = _boolean(guardrail["passed"], f"{guardrail_path}.passed")
    if guardrail_threshold != threshold or enforced != performance_enforced:
        _fail(f"{guardrail_path} configuration is inconsistent")
    if pipeline_p95 is None or observed != pipeline_p95:
        _fail(f"{guardrail_path}.observed_ms is inconsistent")
    if passed != (observed <= threshold):
        _fail(f"{guardrail_path}.passed is inconsistent")
    if performance_valid != passed:
        _fail(f"{path}.valid is inconsistent")
    return performance_valid, passed


def _validate_overall(
    value: object,
    *,
    conformance_valid: bool,
    guardrail_passed: bool,
    performance_enforced: bool,
) -> None:
    path = "core_benchmark.overall"
    overall = _mapping(value, path)
    _exact_keys(
        overall,
        path,
        {"valid", "state", "conformance_passed", "performance_guardrail_passed"},
    )
    valid = _boolean(overall["valid"], f"{path}.valid")
    state = _string(overall["state"], f"{path}.state")
    if state not in {"passed", "failed"}:
        _fail(f"{path}.state is unsupported")
    if _boolean(overall["conformance_passed"], f"{path}.conformance_passed") != conformance_valid:
        _fail(f"{path}.conformance_passed is inconsistent")
    if _boolean(
        overall["performance_guardrail_passed"],
        f"{path}.performance_guardrail_passed",
    ) != guardrail_passed:
        _fail(f"{path}.performance_guardrail_passed is inconsistent")
    expected_valid = conformance_valid and (
        guardrail_passed if performance_enforced else True
    )
    if valid != expected_valid or state != ("passed" if expected_valid else "failed"):
        _fail(f"{path} is inconsistent")


def _validate_boundaries(value: object) -> None:
    path = "core_benchmark.boundaries"
    boundaries = _mapping(value, path)
    expected = {
        "production_core_only": True,
        "benchmark_local_verifier_used": False,
        "network_used": False,
        "model_called": False,
        "external_data_used": False,
        "cross_hardware_comparison_supported": False,
    }
    _exact_keys(boundaries, path, set(expected))
    for field, expected_value in expected.items():
        if _boolean(boundaries[field], f"{path}.{field}") != expected_value:
            _fail(f"{path}.{field} violates the public benchmark boundary")


def load_core_benchmark_report(payload: object) -> dict[str, object]:
    """Strictly validate and return one serialized Core benchmark report."""
    root = _mapping(payload, "report")
    _exact_keys(root, "report", {"core_benchmark"})
    body = _mapping(root["core_benchmark"], "core_benchmark")
    _exact_keys(
        body,
        "core_benchmark",
        {
            "report_version",
            "schema_id",
            "schema_version",
            "benchmark_id",
            "benchmark_version",
            "generated_at",
            "environment",
            "configuration",
            "conformance",
            "performance",
            "overall",
            "boundaries",
        },
    )
    _validate_header(body)
    _validate_environment(body["environment"])
    iterations, threshold, enforced = _validate_configuration(body["configuration"])
    conformance_valid, case_count, case_ids = _validate_conformance(body["conformance"])
    _, guardrail_passed = _validate_performance(
        body["performance"],
        iterations=iterations,
        case_count=case_count,
        case_ids=case_ids,
        threshold=threshold,
        performance_enforced=enforced,
    )
    _validate_overall(
        body["overall"],
        conformance_valid=conformance_valid,
        guardrail_passed=guardrail_passed,
        performance_enforced=enforced,
    )
    _validate_boundaries(body["boundaries"])
    return json.loads(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    )


__all__ = ["load_core_benchmark_report"]
