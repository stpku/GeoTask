"""Foundation CLI tests for explain, inspect, and report commands."""

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_EXAMPLE = "examples/geotask_core_lite.yaml"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_help_lists_foundation_commands():
    """Top-level help advertises foundation commands."""
    result = _run_cli("--help")

    assert result.returncode == 0
    for command in ["validate", "run", "explain", "inspect", "report"]:
        assert command in result.stdout


def test_cli_inspect_schema_outputs_minimal_structure():
    """`inspect schema` describes the public-safe YAML structure."""
    result = _run_cli("inspect", "schema")

    assert result.returncode == 0
    assert "geotask" in result.stdout
    assert "objects" in result.stdout
    assert "ops" in result.stdout
    assert "task" in result.stdout
    assert "assertions" in result.stdout
    assert "expected_results" in result.stdout
    assert "object_refs" in result.stdout
    assert "entry_required_fields" in result.stdout


def test_cli_inspect_examples_lists_public_safe_examples():
    """`inspect examples` lists runnable public-safe examples."""
    result = _run_cli("inspect", "examples")

    assert result.returncode == 0
    assert CORE_EXAMPLE in result.stdout
    assert "public_safe" in result.stdout


def test_cli_explain_outputs_operator_resolution():
    """`explain` shows how document ops resolve to registry metadata."""
    result = _run_cli("explain", CORE_EXAMPLE)

    assert result.returncode == 0
    assert "distance_2d" in result.stdout
    assert "line_intersects_rect" in result.stdout
    assert "deterministic" in result.stdout
    assert "Traceback" not in result.stderr


def test_cli_report_json_outputs_parseable_result():
    """`report --format json` emits clean parseable JSON."""
    result = _run_cli("report", CORE_EXAMPLE, "--format", "json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["total_checks"] == 2
    assert payload["result"]["conclusion"]["external_data_used"] is False
    assert "takeoff_to_school_distance" in result.stdout


def test_cli_report_markdown_outputs_report():
    """`report --format markdown` emits a compact Markdown report."""
    result = _run_cli("report", CORE_EXAMPLE, "--format", "markdown")

    assert result.returncode == 0
    assert "# GeoTask Report" in result.stdout
    assert "| Measurement | Value | Unit | Operator |" in result.stdout
    assert "takeoff_to_school_distance" in result.stdout


def test_cli_report_unknown_format_has_nonzero_clear_error():
    """Unknown report formats fail without a traceback."""
    result = _run_cli("report", CORE_EXAMPLE, "--format", "xml")
    combined = result.stdout + result.stderr

    assert result.returncode != 0
    assert "unsupported_report_format" in combined
    assert "Traceback" not in combined


def test_cli_usage_doc_covers_foundation_commands():
    """Public CLI docs cover the foundation command surface."""
    docs_path = REPO_ROOT / "docs" / "cli_usage.md"
    text = docs_path.read_text(encoding="utf-8")

    for command in [
        "validate",
        "run",
        "explain",
        "inspect operators",
        "inspect schema",
        "inspect examples",
        "report",
    ]:
        assert command in text
