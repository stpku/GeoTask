"""Public conformance and performance benchmark for production GeoTask Core.

The benchmark uses fixed fictional in-memory cases and production Core APIs only.
It does not call a model, access a network, fetch external evidence, or use a
benchmark-local verifier. Performance values are local regression observations,
not cross-hardware claims.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import statistics
import time
from collections.abc import Mapping
from datetime import datetime, timezone

from geotask_core._version import __version__
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.core_benchmark_cases import (
    CORE_BENCHMARK_CASES,
    CORE_BENCHMARK_OPERATOR_COVERAGE,
)
from geotask_core.v1.core_benchmark_contract import (
    CORE_BENCHMARK_ID,
    CORE_BENCHMARK_REPORT_VERSION,
    CORE_BENCHMARK_SCHEMA_ID,
    CORE_BENCHMARK_SCHEMA_VERSION,
    CORE_BENCHMARK_STAGE_NAMES,
    CORE_BENCHMARK_VERSION,
    CoreBenchmarkFormatError,
    DEFAULT_BENCHMARK_ITERATIONS,
    DEFAULT_BENCHMARK_WARMUP_ITERATIONS,
    DEFAULT_MAX_PIPELINE_P95_MS,
)
from geotask_core.v1.core_benchmark_report import load_core_benchmark_report
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.result import GeotaskResult
from geotask_core.v1.validator import validate_canonical


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _semantic_sha256(payload: Mapping[str, object]) -> str:
    copied = json.loads(_stable_json(payload))
    body = copied["geotask_result"]
    body["execution"]["started_at"] = ""
    body["execution"]["finished_at"] = ""
    return hashlib.sha256(_stable_json(copied).encode("utf-8")).hexdigest()


def _error_diagnostics(diagnostics: list[dict]) -> list[dict[str, str]]:
    return [
        {
            "code": str(item.get("code", "benchmark_validation_error")),
            "message": str(item.get("message", "validation failed")),
        }
        for item in diagnostics
        if item.get("severity", "error") == "error"
    ]


def _actual_evidence_refs(result: GeotaskResult) -> dict[str, list[str]]:
    return {
        check.assertion_id: list(check.evidence_refs)
        for check in result.checks
        if check.evidence_refs
    }


def _run_conformance_case(case: Mapping[str, object]) -> dict[str, object]:
    diagnostics: list[dict[str, str]] = []
    semantic_sha256 = ""
    deterministic_replay = False
    result_roundtrip = False
    expected_outputs_match = False
    evidence_refs_match = False
    overall_status = "unverifiable"
    assertion_count = 0
    operators: list[str] = []

    try:
        first_doc = canonicalize(json.loads(str(case["payload_json"])))
        validation = validate_canonical(first_doc)
        diagnostics.extend(_error_diagnostics(validation))
        if diagnostics:
            raise CoreBenchmarkFormatError("case validation failed")

        first_result = execute_canonical(first_doc)
        first_serialized = first_result.to_dict()
        semantic_sha256 = _semantic_sha256(first_serialized)
        result_roundtrip = (
            GeotaskResult.from_dict(first_serialized).to_dict() == first_serialized
        )
        expected_outputs_match = first_result.outputs == dict(case["expected_outputs"])
        evidence_refs_match = _actual_evidence_refs(first_result) == dict(
            case["expected_evidence_refs"]
        )
        overall_status = first_result.overall.status
        assertion_count = len(first_result.checks)
        operators = [check.operator for check in first_result.checks]

        second_result = execute_canonical(
            canonicalize(json.loads(str(case["payload_json"])))
        )
        deterministic_replay = (
            semantic_sha256 == _semantic_sha256(second_result.to_dict())
        )
    except Exception as exc:
        if not diagnostics:
            diagnostics.append(
                {
                    "code": "benchmark_case_error",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )

    valid = all(
        (
            not diagnostics,
            deterministic_replay,
            result_roundtrip,
            expected_outputs_match,
            evidence_refs_match,
            overall_status == "verified",
            operators == list(case["operators"]),
        )
    )
    return {
        "case_id": str(case["case_id"]),
        "valid": valid,
        "assertion_count": assertion_count,
        "operators": operators,
        "semantic_sha256": semantic_sha256,
        "deterministic_replay": deterministic_replay,
        "result_roundtrip": result_roundtrip,
        "expected_outputs_match": expected_outputs_match,
        "evidence_refs_match": evidence_refs_match,
        "overall_status": overall_status,
        "diagnostics": diagnostics,
    }


def _percentile_nearest_rank(samples: list[float], percentile: float) -> float:
    ordered = sorted(samples)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _metric(samples: list[float]) -> dict[str, object]:
    if not samples:
        raise ValueError("performance samples must not be empty")
    return {
        "sample_count": len(samples),
        "min_ms": round(min(samples), 6),
        "median_ms": round(statistics.median(samples), 6),
        "p95_ms": round(_percentile_nearest_rank(samples, 0.95), 6),
        "max_ms": round(max(samples), 6),
    }


def _run_pipeline_sample(payload_json: str) -> dict[str, float]:
    pipeline_started = time.perf_counter_ns()

    started = time.perf_counter_ns()
    payload = json.loads(payload_json)
    decode_ms = (time.perf_counter_ns() - started) / 1_000_000

    started = time.perf_counter_ns()
    document = canonicalize(payload)
    canonicalize_ms = (time.perf_counter_ns() - started) / 1_000_000

    started = time.perf_counter_ns()
    diagnostics = validate_canonical(document)
    validate_ms = (time.perf_counter_ns() - started) / 1_000_000
    errors = [item for item in diagnostics if item.get("severity", "error") == "error"]
    if errors:
        raise CoreBenchmarkFormatError(
            f"benchmark case produced {len(errors)} validation error(s)"
        )

    started = time.perf_counter_ns()
    result = execute_canonical(document)
    execute_ms = (time.perf_counter_ns() - started) / 1_000_000
    if result.overall.status != "verified":
        raise CoreBenchmarkFormatError(
            f"benchmark case did not verify: {result.overall.status}"
        )

    started = time.perf_counter_ns()
    result.to_dict()
    serialize_ms = (time.perf_counter_ns() - started) / 1_000_000

    return {
        "decode": decode_ms,
        "canonicalize": canonicalize_ms,
        "validate": validate_ms,
        "execute": execute_ms,
        "serialize": serialize_ms,
        "pipeline": (time.perf_counter_ns() - pipeline_started) / 1_000_000,
    }


def _validate_configuration(
    iterations: int,
    warmup_iterations: int,
    max_pipeline_p95_ms: float,
    enforce_performance: bool,
) -> None:
    if isinstance(iterations, bool) or not isinstance(iterations, int):
        raise TypeError("iterations must be an integer")
    if not 1 <= iterations <= 10_000:
        raise ValueError("iterations must be between 1 and 10000")
    if isinstance(warmup_iterations, bool) or not isinstance(warmup_iterations, int):
        raise TypeError("warmup_iterations must be an integer")
    if not 0 <= warmup_iterations <= 1_000:
        raise ValueError("warmup_iterations must be between 0 and 1000")
    if isinstance(max_pipeline_p95_ms, bool) or not isinstance(
        max_pipeline_p95_ms, (int, float)
    ):
        raise TypeError("max_pipeline_p95_ms must be a number")
    if not math.isfinite(float(max_pipeline_p95_ms)) or max_pipeline_p95_ms <= 0:
        raise ValueError("max_pipeline_p95_ms must be a finite positive number")
    if not isinstance(enforce_performance, bool):
        raise TypeError("enforce_performance must be a boolean")


def run_core_benchmark(
    *,
    iterations: int = DEFAULT_BENCHMARK_ITERATIONS,
    warmup_iterations: int = DEFAULT_BENCHMARK_WARMUP_ITERATIONS,
    max_pipeline_p95_ms: float = DEFAULT_MAX_PIPELINE_P95_MS,
    enforce_performance: bool = False,
) -> dict[str, object]:
    """Run the public production-Core conformance and performance benchmark."""
    _validate_configuration(
        iterations,
        warmup_iterations,
        max_pipeline_p95_ms,
        enforce_performance,
    )

    conformance_cases = [_run_conformance_case(case) for case in CORE_BENCHMARK_CASES]
    passed = sum(1 for case in conformance_cases if case["valid"])
    conformance_valid = passed == len(conformance_cases)

    for _ in range(warmup_iterations):
        for case in CORE_BENCHMARK_CASES:
            _run_pipeline_sample(str(case["payload_json"]))

    stage_samples: dict[str, list[float]] = {
        stage: [] for stage in CORE_BENCHMARK_STAGE_NAMES
    }
    case_samples: dict[str, list[float]] = {
        str(case["case_id"]): [] for case in CORE_BENCHMARK_CASES
    }
    for _ in range(iterations):
        for case in CORE_BENCHMARK_CASES:
            timings = _run_pipeline_sample(str(case["payload_json"]))
            for stage in CORE_BENCHMARK_STAGE_NAMES:
                stage_samples[stage].append(timings[stage])
            case_samples[str(case["case_id"])].append(timings["pipeline"])

    stage_metrics = [
        {"stage": stage, **_metric(stage_samples[stage])}
        for stage in CORE_BENCHMARK_STAGE_NAMES
    ]
    case_metrics = [
        {"case_id": case_id, **_metric(samples)}
        for case_id, samples in case_samples.items()
    ]
    pipeline_metric = next(
        metric for metric in stage_metrics if metric["stage"] == "pipeline"
    )
    total_pipeline_ms = sum(stage_samples["pipeline"])
    throughput = (
        len(stage_samples["pipeline"]) * 1000.0 / total_pipeline_ms
        if total_pipeline_ms > 0
        else 0.0
    )
    guardrail_passed = float(pipeline_metric["p95_ms"]) <= float(
        max_pipeline_p95_ms
    )
    overall_valid = conformance_valid and (
        guardrail_passed if enforce_performance else True
    )

    report: dict[str, object] = {
        "core_benchmark": {
            "report_version": CORE_BENCHMARK_REPORT_VERSION,
            "schema_id": CORE_BENCHMARK_SCHEMA_ID,
            "schema_version": CORE_BENCHMARK_SCHEMA_VERSION,
            "benchmark_id": CORE_BENCHMARK_ID,
            "benchmark_version": CORE_BENCHMARK_VERSION,
            "generated_at": _utc_now(),
            "environment": {
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "platform_system": platform.system() or "unknown",
                "platform_machine": platform.machine() or "unknown",
                "geotask_core_version": __version__,
            },
            "configuration": {
                "iterations": iterations,
                "warmup_iterations": warmup_iterations,
                "max_pipeline_p95_ms": float(max_pipeline_p95_ms),
                "performance_enforced": enforce_performance,
            },
            "conformance": {
                "valid": conformance_valid,
                "case_count": len(conformance_cases),
                "passed": passed,
                "failed": len(conformance_cases) - passed,
                "operator_coverage": list(CORE_BENCHMARK_OPERATOR_COVERAGE),
                "cases": conformance_cases,
            },
            "performance": {
                "valid": guardrail_passed,
                "sample_count": len(stage_samples["pipeline"]),
                "throughput_cases_per_second": round(throughput, 3),
                "stage_metrics": stage_metrics,
                "case_metrics": case_metrics,
                "guardrail": {
                    "metric": "pipeline_p95_ms",
                    "threshold_ms": float(max_pipeline_p95_ms),
                    "observed_ms": float(pipeline_metric["p95_ms"]),
                    "enforced": enforce_performance,
                    "passed": guardrail_passed,
                },
            },
            "overall": {
                "valid": overall_valid,
                "state": "passed" if overall_valid else "failed",
                "conformance_passed": conformance_valid,
                "performance_guardrail_passed": guardrail_passed,
            },
            "boundaries": {
                "production_core_only": True,
                "benchmark_local_verifier_used": False,
                "network_used": False,
                "model_called": False,
                "external_data_used": False,
                "cross_hardware_comparison_supported": False,
            },
        }
    }
    load_core_benchmark_report(report)
    return report


__all__ = [
    "CORE_BENCHMARK_ID",
    "CORE_BENCHMARK_REPORT_VERSION",
    "CORE_BENCHMARK_SCHEMA_ID",
    "CORE_BENCHMARK_SCHEMA_VERSION",
    "CORE_BENCHMARK_VERSION",
    "CoreBenchmarkFormatError",
    "DEFAULT_BENCHMARK_ITERATIONS",
    "DEFAULT_BENCHMARK_WARMUP_ITERATIONS",
    "DEFAULT_MAX_PIPELINE_P95_MS",
    "load_core_benchmark_report",
    "run_core_benchmark",
]
