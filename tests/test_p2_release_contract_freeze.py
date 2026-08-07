"""P2 machine-readable public naming freeze for the 0.4.0 release scope."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from geotask_core.operator_registry import operator_names
from geotask_core.v1.artifact_registry import list_artifact_descriptors
from geotask_core.v1.schema_bundle import list_bundled_schema_ids


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "docs" / "reference" / "p2-release-contract-freeze-v0.4.json"
DOC = ROOT / "docs" / "reference" / "p2-release-contract-freeze-v0.4.md"
PYPROJECT = ROOT / "pyproject.toml"


def _snapshot() -> dict:
    return json.loads(FREEZE.read_text(encoding="utf-8"))["release_contract_freeze"]


def test_release_scope_freeze_matches_live_operator_artifact_and_schema_registries() -> None:
    snapshot = _snapshot()
    assert snapshot["operator_ids"] == operator_names()
    assert snapshot["artifact_ids"] == [
        descriptor.artifact_id for descriptor in list_artifact_descriptors()
    ]
    assert snapshot["schema_count"] == len(list_bundled_schema_ids()) == 33
    assert snapshot["registry_version"] == "1.0"


def test_release_scope_freeze_matches_current_cli_help() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", "--help"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    commands_line = next(
        line for line in completed.stdout.splitlines() if line.startswith("Commands: ")
    )
    actual = [item.strip() for item in commands_line.removeprefix("Commands: ").split(",")]
    assert actual == _snapshot()["top_level_cli_commands"]


def test_release_scope_freeze_matches_package_and_python_support_metadata() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    package = _snapshot()["package"]
    assert f'name = "{package["pypi_name"]}"' in text
    assert 'requires-python = ">=3.10"' in text
    for version in package["supported_python_minors"]:
        assert f'"Programming Language :: Python :: {version}"' in text
    assert 'geotask = "geotask_core.cli:main"' in text
    assert 'stir = "geotask_core.cli:main"' in text


def test_release_scope_freeze_does_not_claim_040_is_released() -> None:
    snapshot = _snapshot()
    assert snapshot["target_release"] == "0.4.0"
    assert snapshot["status"] == "release_scope_frozen_not_released"
    assert snapshot["boundaries"]["this_file_announces_release"] is False
    text = DOC.read_text(encoding="utf-8")
    assert "0.4.0 is not released" in text
    assert "testable release gate" in text
