"""Shared helpers and path setup for the v1 categorized test suite.

All helper functions are prefixed with ``_`` so pytest does not collect them.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

# ── Path setup ───────────────────────────────────────────────────────────────
# tests/v1/conftest.py → tests/v1/ → tests/ → project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_EXAMPLES_DIR = _PROJECT_ROOT / "examples"

sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "src"))


# ── Shared helpers ───────────────────────────────────────────────────────────

def _load_yaml(rel_path: str) -> dict:
    """Load a YAML file relative to the project root."""
    full = _PROJECT_ROOT / rel_path
    with open(full, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _find_diag(
    diagnostics: list[dict], *, code: str = "", path_contains: str = ""
) -> dict | None:
    """Find the first diagnostic matching *code* and/or *path_contains*."""
    for d in diagnostics:
        if code and d.get("code") != code:
            continue
        if path_contains and path_contains not in d.get("path", ""):
            continue
        return d
    return None


def _write_temp_yaml(content: str) -> str:
    """Write *content* to a temporary .yaml file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".yaml", prefix="geotask_test_")
    os.close(fd)
    Path(path).write_text(content, encoding="utf-8")
    return path


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run ``python -m geotask_core.cli`` with *args* and return the process."""
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
