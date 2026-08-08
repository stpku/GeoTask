"""CLI tests for public-safe inspection commands."""

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


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


def test_cli_inspect_operators_lists_registry():
    """`inspect operators` lists registry metadata without requiring a file."""
    result = _run_cli("inspect", "operators")

    assert result.returncode == 0
    assert "distance_2d" in result.stdout
    assert "line_intersects_rect" in result.stdout
    assert "multi_polyline_intersects_rect" in result.stdout
    assert "point_in_polygon" in result.stdout
    assert "input_shape" in result.stdout
    assert "Traceback" not in result.stderr


def test_cli_inspect_single_operator_outputs_examples():
    """`inspect operators <name>` prints metadata for one operator."""
    result = _run_cli("inspect", "operators", "distance_2d")

    assert result.returncode == 0
    assert "distance_2d" in result.stdout
    assert "examples" in result.stdout
    assert "float" in result.stdout


def test_cli_inspect_unknown_operator_has_nonzero_clear_error():
    """Unknown operator inspection returns a clean non-zero CLI error."""
    result = _run_cli("inspect", "operators", "bogus_operator")

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "unsupported_operator" in combined
    assert "bogus_operator" in combined
    assert "Traceback" not in combined


def test_cli_inspect_operators_collection_supports_json_registry_output():
    result = _run_cli("inspect", "operators", "--format", "json")

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    operators = payload["operators"]
    assert len(operators) == 14
    assert [item["name"] for item in operators][:3] == [
        "distance_2d",
        "line_intersects_rect",
        "multi_polyline_intersects_rect",
    ]
    assert all(item["deterministic"] is True for item in operators)


def test_cli_inspect_single_operator_supports_json_after_or_before_id():
    after = _run_cli("inspect", "operators", "distance_2d", "--format", "json")
    before = _run_cli("inspect", "operators", "--format", "json", "distance_2d")

    assert after.returncode == before.returncode == 0
    assert json.loads(after.stdout) == json.loads(before.stdout)
    assert json.loads(after.stdout)["operator"]["name"] == "distance_2d"


def test_cli_inspect_operators_rejects_bad_format_without_traceback():
    result = _run_cli("inspect", "operators", "--format", "xml")

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "unsupported_inspect_operators_format" in combined
    assert "Traceback" not in combined

