"""Core public-distribution ownership boundary tests."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".release" / "public-manifest.yaml"
BOUNDARY_DOC = ROOT / "docs" / "reference" / "core-distribution-boundary-v0.1.md"

CORE_GOVERNANCE_PATHS = {
    "docs/reference/cross-line-promotion-gate-v0.1.md",
    "docs/reference/lowa-gt-integration-contract-v0.1.md",
    "docs/reference/core-distribution-boundary-v0.1.md",
}

INTEGRATION_IMPLEMENTATION_PATHS = {
    "examples/integrations/lowa_gt_shadow/**",
    "tests/test_lowa_gt_shadow_fixture.py",
    "tests/test_lowa_gt_shadow_batch.py",
    "tests/test_lowa_gt_handoff_package.py",
    "tests/test_lowa_gt_human_baseline_compare.py",
    "docs/reference/lowa-gt-shadow-study-protocol-v0.1.md",
}

INTEGRATION_FORBIDDEN_PREFIXES = {
    "examples/integrations/",
    "tests/test_lowa_gt_shadow_fixture.py",
    "tests/test_lowa_gt_shadow_batch.py",
    "tests/test_lowa_gt_handoff_package.py",
    "tests/test_lowa_gt_human_baseline_compare.py",
    "docs/reference/lowa-gt-shadow-study-protocol-v0.1.md",
}


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def test_core_export_keeps_governance_and_reference_agent() -> None:
    manifest = _manifest()
    include = set(manifest["include"])
    required = set(manifest["required"])

    assert CORE_GOVERNANCE_PATHS <= include
    assert "examples/reference_agent/**" in include
    for path in (
        ".release/core-baseline-manifest.yaml",
        ".release/plan_core_baseline.py",
        ".release/verify_core_commit_scope.py",
        "tests/test_core_baseline_plan.py",
        "tests/test_core_distribution_boundary.py",
    ):
        assert path in include
        assert path in required


def test_core_export_does_not_include_integration_implementation() -> None:
    manifest = _manifest()
    include = set(manifest["include"])
    required = set(manifest["required"])

    assert INTEGRATION_IMPLEMENTATION_PATHS.isdisjoint(include)
    assert INTEGRATION_IMPLEMENTATION_PATHS.isdisjoint(required)


def test_core_export_explicitly_forbids_integration_implementation() -> None:
    manifest = _manifest()
    forbidden = set(manifest["forbidden_paths"])

    assert INTEGRATION_FORBIDDEN_PREFIXES <= forbidden


def test_distribution_boundary_document_is_explicit() -> None:
    text = BOUNDARY_DOC.read_text(encoding="utf-8")

    for fragment in (
        "same repository != same product line",
        "public-safe Integration code != Core release artifact",
        "Reference Agent = Core-owned generic teaching/reference implementation",
        "Lowa-GT shadow harness = Integration-owned industry validation implementation",
        "Integration validates; Core abstracts; Lowa owns business facts",
        "Cross-Line Promotion Gate",
    ):
        assert fragment in text
