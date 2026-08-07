"""P2 installation/migration matrix conformance tests."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "reference" / "install-migration-matrix-v0.4.md"
MIGRATION = ROOT / "MIGRATION.md"
CI = ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = ROOT / "pyproject.toml"


def test_install_matrix_separates_declared_ci_and_local_evidence() -> None:
    text = MATRIX.read_text(encoding="utf-8")
    assert "declared support" in text
    assert "CI-configured verification" in text
    assert "local clean-room evidence" in text
    assert "not locally executed in this session" in text
    assert "3.12 | yes | yes | **passed**" in text


def test_install_matrix_matches_python_support_and_ci_matrix() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    ci = CI.read_text(encoding="utf-8")
    matrix = MATRIX.read_text(encoding="utf-8")
    assert 'requires-python = ">=3.10"' in pyproject
    assert 'python-version: ["3.10", "3.11", "3.12", "3.13"]' in ci
    for version in ("3.10", "3.11", "3.12", "3.13"):
        assert f"| {version} | yes | yes |" in matrix


def test_install_matrix_records_real_p2_artifact_and_reference_agent_gates() -> None:
    text = MATRIX.read_text(encoding="utf-8")
    for fragment in (
        "656 files",
        "geotask_core-0.3.0-py3-none-any.whl: built",
        "geotask_core-0.3.0.tar.gz: built",
        "Schema Bundle distribution: 33 schemas, PASS",
        "32 registered Artifacts / 33 Schemas, PASS",
        "Reference Agent success replay: PASS",
        "Verification Quality Benchmark v0.1: PASS",
        "example is intentionally not bundled inside `geotask-core` wheel",
    ):
        assert fragment in text


def test_install_matrix_does_not_claim_040_is_available() -> None:
    text = MATRIX.read_text(encoding="utf-8")
    assert "0.4.0 is not released" in text
    assert "Do not run a pinned `geotask-core==0.4.0` installation command until the release exists" in text
    assert "not evidence that 0.4.0 is currently available" in text
    assert "full CI evidence on Python 3.10, 3.11, 3.12 and 3.13" in text


def test_top_level_migration_document_links_the_p2_matrix() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "docs/reference/install-migration-matrix-v0.4.md" in text
    assert "0.4.0 has not been released" in text
