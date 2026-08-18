from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_tc1_benchmark_module_runs_from_repository_root():
    completed = subprocess.run(
        [sys.executable, "-m", "benchmarks.run_task_context_v0_1"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "GeoTask TC1 Task Context Proof Benchmark" in completed.stdout
    assert "synthetic_fixture=true" in completed.stdout
    assert "task_outcome_regret=not_available" in completed.stdout
    assert "low-altitude-mission | B0/full_context" in completed.stdout
    assert "low-altitude-mission | B1/manual_template" in completed.stdout
    assert "low-altitude-mission | G0/declared_min_cost_v0" in completed.stdout
    assert "spatial-planning | B0/full_context" in completed.stdout
    assert "spatial-planning | B1/manual_template" in completed.stdout
    assert "spatial-planning | G0/declared_min_cost_v0" in completed.stdout
