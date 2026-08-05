"""Public Core conformance and local performance benchmark tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

from geotask_core.v1.artifact_registry import get_artifact_descriptor
from geotask_core.v1.artifact_validation import validate_artifact_payload
from geotask_core.v1.core_benchmark import (
    CORE_BENCHMARK_SCHEMA_ID,
    CoreBenchmarkFormatError,
    load_core_benchmark_report,
    run_core_benchmark,
)
from geotask_core.v1.core_benchmark_cases import CORE_BENCHMARK_OPERATOR_COVERAGE
from geotask_core.v1.schema_bundle import load_artifact_schema


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "geotask-core-benchmark-v0.1.schema.json"
EXPECTED_OPERATORS = (
    "altitude_overlap",
    "distance_2d",
    "line_intersects_rect",
    "multi_polyline_intersects_rect",
    "point_in_polygon",
    "point_to_line_distance_2d",
    "polygon_contains_point",
    "rect_contains_point",
    "time_overlap",
    "trajectory_duration_seconds",
    "trajectory_segment_acceleration_estimates",
    "trajectory_segment_classifications",
    "trajectory_segment_metrics",
)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _report(*, enforce: bool = True, threshold: float = 100.0) -> dict:
    return run_core_benchmark(
        iterations=2,
        warmup_iterations=1,
        max_pipeline_p95_ms=threshold,
        enforce_performance=enforce,
    )


def test_benchmark_covers_all_public_operators_and_contracts() -> None:
    body = _report()["core_benchmark"]

    assert CORE_BENCHMARK_OPERATOR_COVERAGE == EXPECTED_OPERATORS
    assert tuple(body["conformance"]["operator_coverage"]) == EXPECTED_OPERATORS
    assert body["conformance"]["case_count"] == 9
    assert body["conformance"]["passed"] == 9
    assert body["conformance"]["failed"] == 0
    assert body["conformance"]["valid"] is True
    assert body["overall"] == {
        "valid": True,
        "state": "passed",
        "conformance_passed": True,
        "performance_guardrail_passed": True,
    }
    assert all(case["deterministic_replay"] for case in body["conformance"]["cases"])
    assert all(case["result_roundtrip"] for case in body["conformance"]["cases"])
    assert all(case["expected_outputs_match"] for case in body["conformance"]["cases"])
    assert all(case["evidence_refs_match"] for case in body["conformance"]["cases"])
    assert all(len(case["semantic_sha256"]) == 64 for case in body["conformance"]["cases"])


def test_benchmark_report_matches_json_schema_and_strict_loader() -> None:
    report = _report()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    assert list(validator.iter_errors(report)) == []
    assert load_core_benchmark_report(report) == json.loads(
        json.dumps(report, sort_keys=True, separators=(",", ":"))
    )


def test_benchmark_boundaries_are_explicit_and_fail_closed() -> None:
    boundaries = _report()["core_benchmark"]["boundaries"]
    assert boundaries == {
        "production_core_only": True,
        "benchmark_local_verifier_used": False,
        "network_used": False,
        "model_called": False,
        "external_data_used": False,
        "cross_hardware_comparison_supported": False,
    }

    tampered = _report()
    tampered["core_benchmark"]["boundaries"]["network_used"] = True
    with pytest.raises(CoreBenchmarkFormatError, match="network_used"):
        load_core_benchmark_report(tampered)


def test_benchmark_report_tampering_is_rejected() -> None:
    cases = [
        ("counts", lambda report: report["core_benchmark"]["conformance"].update(passed=4)),
        (
            "digest",
            lambda report: report["core_benchmark"]["conformance"]["cases"][0].update(
                semantic_sha256="0" * 63
            ),
        ),
        (
            "guardrail",
            lambda report: report["core_benchmark"]["performance"]["guardrail"].update(
                observed_ms=999.0
            ),
        ),
        (
            "stage order",
            lambda report: report["core_benchmark"]["performance"]["stage_metrics"].reverse(),
        ),
    ]
    for _, mutate in cases:
        report = _report()
        mutate(report)
        with pytest.raises(CoreBenchmarkFormatError):
            load_core_benchmark_report(report)


def test_performance_guardrail_is_observational_unless_enforced() -> None:
    observational = _report(enforce=False, threshold=0.000001)["core_benchmark"]
    assert observational["performance"]["guardrail"]["passed"] is False
    assert observational["performance"]["valid"] is False
    assert observational["overall"]["valid"] is True
    assert observational["overall"]["state"] == "passed"

    enforced = _report(enforce=True, threshold=0.000001)["core_benchmark"]
    assert enforced["performance"]["guardrail"]["passed"] is False
    assert enforced["overall"]["valid"] is False
    assert enforced["overall"]["state"] == "failed"


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"iterations": 0}, ValueError),
        ({"iterations": True}, TypeError),
        ({"warmup_iterations": -1}, ValueError),
        ({"max_pipeline_p95_ms": 0}, ValueError),
        ({"max_pipeline_p95_ms": float("nan")}, ValueError),
        ({"enforce_performance": 1}, TypeError),
    ],
)
def test_benchmark_configuration_rejects_invalid_values(
    kwargs: dict, error: type[Exception]
) -> None:
    with pytest.raises(error):
        run_core_benchmark(**kwargs)


def test_artifact_registry_and_bundle_expose_benchmark_report() -> None:
    descriptor = get_artifact_descriptor("geotask.core-benchmark-report")
    schema = load_artifact_schema(descriptor.artifact_id)

    assert descriptor.kind == "core_benchmark_report"
    assert descriptor.schema_id == CORE_BENCHMARK_SCHEMA_ID
    assert descriptor.schema_version == "0.1"
    assert descriptor.wrapper_key == "core_benchmark"
    assert "benchmark core" in str(descriptor.generation_command)
    assert "cross" in descriptor.execution_boundary.lower()
    assert schema["$id"] == CORE_BENCHMARK_SCHEMA_ID


def test_unified_artifact_validation_summarizes_benchmark() -> None:
    report = validate_artifact_payload(
        "geotask.core-benchmark-report",
        _report(),
        file="core-benchmark.json",
    )
    payload = report.to_dict()["artifact_validation"]

    assert payload["valid"] is True
    assert payload["schema_verified"] is True
    assert payload["summary"]["benchmark_state"] == "passed"
    assert payload["summary"]["case_count"] == 9
    assert payload["summary"]["operator_count"] == 13
    assert payload["diagnostics"] == []

    tampered = _report()
    tampered["core_benchmark"]["overall"]["valid"] = False
    invalid = validate_artifact_payload(
        "geotask.core-benchmark-report",
        tampered,
    ).to_dict()["artifact_validation"]
    assert invalid["valid"] is False
    assert invalid["diagnostics"][0]["code"] == "invalid_core_benchmark_report"


def test_cli_benchmark_json_yaml_and_output_file(tmp_path: Path) -> None:
    compact = _run_cli(
        "benchmark",
        "core",
        "--iterations",
        "2",
        "--warmup",
        "1",
        "--compact",
    )
    assert compact.returncode == 0
    assert compact.stderr == ""
    assert compact.stdout.count("\n") == 1
    assert json.loads(compact.stdout)["core_benchmark"]["overall"]["valid"] is True

    yaml_result = _run_cli(
        "benchmark",
        "core",
        "--iterations",
        "1",
        "--warmup",
        "0",
        "--format",
        "yaml",
    )
    assert yaml_result.returncode == 0
    assert yaml.safe_load(yaml_result.stdout)["core_benchmark"]["conformance"]["passed"] == 9

    output = tmp_path / "core-benchmark.json"
    file_result = _run_cli(
        "benchmark",
        "core",
        "--iterations",
        "1",
        "--warmup",
        "0",
        "--output",
        str(output),
    )
    assert file_result.returncode == 0
    assert file_result.stdout == ""
    assert json.loads(output.read_text(encoding="utf-8"))["core_benchmark"]["overall"]["valid"] is True


def test_cli_benchmark_exit_codes_and_help() -> None:
    help_result = _run_cli("benchmark", "--help")
    assert help_result.returncode == 0
    assert "Usage: geotask benchmark core" in help_result.stdout

    failed_guardrail = _run_cli(
        "benchmark",
        "core",
        "--iterations",
        "1",
        "--warmup",
        "0",
        "--max-p95-ms",
        "0.000001",
        "--enforce-performance",
        "--compact",
    )
    assert failed_guardrail.returncode == 2
    assert json.loads(failed_guardrail.stdout)["core_benchmark"]["overall"]["state"] == "failed"

    invalid = _run_cli("benchmark", "core", "--iterations", "0")
    assert invalid.returncode == 1
    assert "benchmark_failed" in invalid.stderr


def test_cli_generated_report_can_be_validated_as_artifact(tmp_path: Path) -> None:
    output = tmp_path / "core-benchmark.json"
    generated = _run_cli(
        "benchmark",
        "core",
        "--iterations",
        "1",
        "--warmup",
        "0",
        "--output",
        str(output),
    )
    validated = _run_cli(
        "artifact",
        "validate",
        "geotask.core-benchmark-report",
        str(output),
        "--format",
        "json",
    )

    assert generated.returncode == 0
    assert validated.returncode == 0
    body = json.loads(validated.stdout)["artifact_validation"]
    assert body["valid"] is True
    assert body["summary"]["operator_count"] == 13


def test_public_namespaces_export_benchmark_contract() -> None:
    import geotask_core
    import geotask_core.v1 as v1

    for namespace in (geotask_core, v1):
        assert namespace.CORE_BENCHMARK_SCHEMA_ID == CORE_BENCHMARK_SCHEMA_ID
        assert namespace.CORE_BENCHMARK_SCHEMA_VERSION == "0.1"
        assert namespace.run_core_benchmark is run_core_benchmark
        assert namespace.load_core_benchmark_report is load_core_benchmark_report
        assert namespace.CoreBenchmarkFormatError is CoreBenchmarkFormatError


def test_benchmark_modules_remain_bounded_and_public_safe() -> None:
    paths = {
        "core_benchmark_contract.py": 100,
        "core_benchmark_cases.py": 750,
        "core_benchmark.py": 400,
        "core_benchmark_report.py": 550,
        "core_benchmark_cli.py": 250,
    }
    for filename, limit in paths.items():
        path = ROOT / "src" / "geotask_core" / "v1" / filename
        text = path.read_text(encoding="utf-8")
        assert len(text.splitlines()) <= limit
        assert "requests" not in text
        assert "openai" not in text.casefold()

    combined = "\n".join(
        (ROOT / "src" / "geotask_core" / "v1" / filename).read_text(encoding="utf-8")
        for filename in paths
    )
    assert "geotask_runtime" not in combined
    assert "benchmarks." not in combined
