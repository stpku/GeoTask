"""Product Track verification-quality benchmark tests for Reference Agent v0.1/v0.2."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "reference_agent" / "facility_assessment_update" / "quality_benchmark.py"
SCRIPT_V02 = ROOT / "examples" / "reference_agent" / "facility_assessment_update" / "quality_benchmark_v0_2.py"
DOC = ROOT / "docs" / "reference" / "verification-quality-benchmark-v0.1.md"
DOC_V02 = ROOT / "docs" / "reference" / "verification-quality-benchmark-v0.2.md"
EXPECTED_METRICS = {
    "error_detection_rate_pct": 100.0,
    "missed_error_rate_pct": 0.0,
    "false_blocking_rate_pct": 0.0,
    "correction_success_rate_pct": 100.0,
    "impact_scope_precision_pct": 100.0,
    "impact_scope_recall_pct": 100.0,
    "side_effect_boundary_pass_rate_pct": 100.0,
}
EXPECTED_METRICS_V02 = {
    "outcome_match_rate_pct": 100.0,
    "error_detection_rate_pct": 100.0,
    "missed_error_rate_pct": 0.0,
    "false_blocking_rate_pct": 0.0,
    "control_gate_block_rate_pct": 100.0,
    "threshold_boundary_accuracy_pct": 100.0,
    "correction_success_rate_pct": 100.0,
    "impact_scope_precision_pct": 100.0,
    "impact_scope_recall_pct": 100.0,
    "deterministic_replay_pass_rate_pct": 100.0,
    "side_effect_boundary_pass_rate_pct": 100.0,
}


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_v02(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_V02), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_quality_benchmark_json_metrics_and_boundaries() -> None:
    completed = _run("--format", "json")
    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)["verification_quality_benchmark"]

    assert report["state"] == "passed"
    assert report["valid"] is True
    assert report["metrics"] == EXPECTED_METRICS
    assert report["counts"] == {
        "known_error_cases": 4,
        "clean_cases": 1,
        "correction_cases": 2,
        "safety_boundary_cases": 5,
    }
    assert report["boundaries"] == {
        "fictional_data_only": True,
        "network_used": False,
        "model_called": False,
        "production_system_accessed": False,
        "production_write_performed": False,
        "automatic_dependency_discovery": False,
        "automatic_global_recompute": False,
        "metric_scope": "reference_agent_v0.1_fixed_scenarios",
        "cross_domain_generalization_claimed": False,
    }

    error_rows = report["cases"]["error_detection"]
    assert [row["scenario"] for row in error_rows] == [
        "missing_evidence",
        "conflicting_evidence",
        "stale_evidence",
        "contradicted",
    ]
    assert all(row["error_detected"] is True for row in error_rows)
    assert all(row["report_update_eligible"] is False for row in error_rows)

    correction_rows = report["cases"]["correction_and_scope"]
    assert [row["scenario"] for row in correction_rows] == ["success", "contradicted"]
    assert all(row["correction_success"] is True for row in correction_rows)
    assert all(row["scope_exact_match"] is True for row in correction_rows)
    assert all(row["reused_scope_exact_match"] is True for row in correction_rows)


def test_quality_benchmark_is_deterministic() -> None:
    first = _run("--format", "json")
    second = _run("--format", "json")
    assert first.returncode == second.returncode == 0
    assert json.loads(first.stdout) == json.loads(second.stdout)


def test_quality_benchmark_output_file_and_text_summary(tmp_path: Path) -> None:
    output = tmp_path / "quality.json"
    completed = _run("--format", "json", "--output", str(output))
    assert completed.returncode == 0
    assert completed.stdout == ""
    assert json.loads(output.read_text(encoding="utf-8"))[
        "verification_quality_benchmark"
    ]["metrics"] == EXPECTED_METRICS

    text = _run("--format", "text")
    assert text.returncode == 0
    for fragment in (
        "state: passed",
        "error detection rate: 100.00%",
        "missed error rate: 0.00%",
        "false blocking rate: 0.00%",
        "correction success rate: 100.00%",
        "impact scope precision: 100.00%",
        "impact scope recall: 100.00%",
        "no automatic dependency discovery claim",
    ):
        assert fragment in text.stdout


def test_quality_benchmark_documentation_preserves_interpretation_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    for fragment in (
        "Product Track quality gate",
        "fixed fictional Reference Agent v0.1 scenarios only",
        "100% error detection on real low-altitude data",
        "automatic_dependency_discovery = false",
        "cross_domain_generalization_claimed = false",
        "must not silently replace this deterministic fixture",
    ):
        assert fragment in text


def test_quality_benchmark_v02_perturbation_matrix_metrics_and_boundaries() -> None:
    completed = _run_v02("--format", "json")
    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)["verification_quality_benchmark"]

    assert report["benchmark_version"] == "0.2"
    assert report["state"] == "passed"
    assert report["valid"] is True
    assert report["metrics"] == EXPECTED_METRICS_V02
    assert report["counts"] == {
        "total_cases": 34,
        "known_error_cases": 12,
        "clean_cases": 14,
        "control_gate_cases": 8,
        "threshold_boundary_cases": 16,
        "correction_cases": 28,
        "deterministic_replay_cases": 34,
        "side_effect_boundary_cases": 34,
    }
    assert report["boundaries"] == {
        "fictional_data_only": True,
        "generated_synthetic_perturbations": True,
        "network_used": False,
        "model_called": False,
        "production_system_accessed": False,
        "production_write_performed": False,
        "automatic_dependency_discovery": False,
        "automatic_global_recompute": False,
        "metric_scope": "reference_agent_v0.1_deterministic_synthetic_perturbation_matrix",
        "real_world_accuracy_claimed": False,
        "cross_domain_generalization_claimed": False,
    }

    rows = report["cases"]
    assert len(rows) == 34
    assert all(row["outcome_match"] is True for row in rows)
    assert all(row["deterministic_replay"] is True for row in rows)
    assert all(row["side_effect_boundary_pass"] is True for row in rows)
    assert all(
        row["correction_success"] is True
        for row in rows
        if row["correction_success"] is not None
    )
    control_rows = [row for row in rows if row["kind"] == "control_gate"]
    assert len(control_rows) == 8
    assert all(row["actual_verification_state"] == "satisfied" for row in control_rows)
    assert all(row["actual_report_update_eligible"] is False for row in control_rows)


def test_quality_benchmark_v02_is_deterministic_and_installed_cli_equivalent() -> None:
    first = _run_v02("--format", "json")
    second = _run_v02("--format", "json")
    assert first.returncode == second.returncode == 0
    assert json.loads(first.stdout) == json.loads(second.stdout)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "geotask_core.cli",
            "benchmark",
            "quality",
            "--suite",
            "perturbation",
            "--compact",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert cli.returncode == 0, cli.stderr or cli.stdout
    assert json.loads(cli.stdout) == json.loads(first.stdout)


def test_quality_benchmark_v02_documentation_preserves_interpretation_boundary() -> None:
    text = DOC_V02.read_text(encoding="utf-8")
    for fragment in (
        "34",
        "deterministic synthetic perturbation",
        "real-world accuracy",
        "cross-domain generalization",
        "not Core Promotion evidence",
        "automatic_dependency_discovery = false",
        "eligible != authorized != executed",
    ):
        assert fragment in text


def test_installed_cli_surface_runs_same_quality_gate() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "geotask_core.cli",
            "benchmark",
            "quality",
            "--compact",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)["verification_quality_benchmark"]
    assert report["state"] == "passed"
    assert report["metrics"] == EXPECTED_METRICS
    assert report["boundaries"]["fictional_data_only"] is True
    assert report["boundaries"]["network_used"] is False
    assert report["boundaries"]["cross_domain_generalization_claimed"] is False


def test_benchmark_help_discovers_quality_without_hiding_core() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", "benchmark", "--help"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "Usage: geotask benchmark core" in completed.stdout
    assert "Usage: geotask benchmark quality" in completed.stdout
    assert "--suite fixed|perturbation" in completed.stdout
