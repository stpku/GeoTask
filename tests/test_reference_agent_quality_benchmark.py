"""Product Track verification-quality benchmark tests for Reference Agent v0.1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "reference_agent" / "facility_assessment_update" / "quality_benchmark.py"
DOC = ROOT / "docs" / "reference" / "verification-quality-benchmark-v0.1.md"
EXPECTED_METRICS = {
    "error_detection_rate_pct": 100.0,
    "missed_error_rate_pct": 0.0,
    "false_blocking_rate_pct": 0.0,
    "correction_success_rate_pct": 100.0,
    "impact_scope_precision_pct": 100.0,
    "impact_scope_recall_pct": 100.0,
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
