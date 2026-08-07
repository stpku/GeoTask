"""Core pre-RC baseline closed-set staging-plan tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / ".release" / "plan_core_baseline.py"
MANIFEST = ROOT / ".release" / "core-baseline-manifest.yaml"


def _load_planner():
    spec = importlib.util.spec_from_file_location("plan_core_baseline", PLANNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_is_closed_set_and_self_describing() -> None:
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    core_paths = payload["core_exact_paths"]

    assert payload["baseline_id"] == "core-pre-rc-2026-08-07"
    assert payload["target_release"] == "0.4.0"
    assert payload["status"] == "pre_rc_not_released"
    assert payload["unknown_dirty_path_policy"] == "fail"
    assert len(core_paths) == len(set(core_paths))
    for required in (
        ".release/core-baseline-manifest.yaml",
        ".release/plan_core_baseline.py",
        ".release/verify_core_commit_scope.py",
        "tests/test_core_baseline_plan.py",
        "docs/reference/lowa-gt-integration-contract-v0.1.md",
        "docs/reference/cross-line-promotion-gate-v0.1.md",
    ):
        assert required in core_paths

    integration_patterns = payload["excluded_patterns"]["integration_owned"]
    assert "examples/integrations/**" in integration_patterns
    assert "tests/test_lowa_gt_*.py" in integration_patterns
    assert "docs/internal/lowa-gt-*" in integration_patterns
    assert "docs/reports/lowa_gt_*" in integration_patterns


def test_plan_accepts_declared_core_and_excludes_integration(monkeypatch) -> None:
    planner = _load_planner()
    dirty = [
        "README.md",
        "docs/reference/lowa-gt-integration-contract-v0.1.md",
        "examples/integrations/lowa_gt_shadow/shadow_verify.py",
        "docs/reports/lowa_gt_shadow_revalidation_v2_20260807.md",
        "docs/internal/GeoTask_长期战略_计划与落地须知_v1.0.md",
    ]
    monkeypatch.setattr(planner, "_dirty_paths", lambda root: (dirty, ""))
    monkeypatch.setattr(planner, "_head_commit", lambda root: "1" * 40)

    report = planner.build_plan(ROOT, Path(".release/core-baseline-manifest.yaml"))["core_baseline_plan"]

    assert report["state"] == "passed"
    assert report["ready_to_stage"] is True
    assert report["core_count"] == 2
    assert report["excluded_count"] == 3
    assert report["unknown_count"] == 0
    assert [entry["path"] for entry in report["core_paths"]] == [
        "README.md",
        "docs/reference/lowa-gt-integration-contract-v0.1.md",
    ]
    categories = {entry["path"]: entry["category"] for entry in report["excluded_paths"]}
    assert categories["examples/integrations/lowa_gt_shadow/shadow_verify.py"] == "integration_owned"
    assert categories["docs/reports/lowa_gt_shadow_revalidation_v2_20260807.md"] == "integration_owned"
    assert categories["docs/internal/GeoTask_长期战略_计划与落地须知_v1.0.md"] == "internal_or_noncore"


def test_unknown_dirty_path_is_hard_failure(monkeypatch) -> None:
    planner = _load_planner()
    monkeypatch.setattr(
        planner,
        "_dirty_paths",
        lambda root: (["README.md", "unexpected/new_core_claim.py"], ""),
    )
    monkeypatch.setattr(planner, "_head_commit", lambda root: "2" * 40)

    report = planner.build_plan(ROOT, Path(".release/core-baseline-manifest.yaml"))["core_baseline_plan"]

    assert report["state"] == "failed"
    assert report["ready_to_stage"] is False
    assert report["unknown_paths"] == ["unexpected/new_core_claim.py"]
    assert report["unknown_count"] == 1


def test_pathspec_contains_only_exact_core_paths(monkeypatch, tmp_path: Path) -> None:
    planner = _load_planner()
    monkeypatch.setattr(
        planner,
        "_dirty_paths",
        lambda root: (
            [
                "README.md",
                "docs/reference/cross-line-promotion-gate-v0.1.md",
                "tests/test_lowa_gt_shadow_batch.py",
            ],
            "",
        ),
    )
    monkeypatch.setattr(planner, "_head_commit", lambda root: "3" * 40)
    report = planner.build_plan(ROOT, Path(".release/core-baseline-manifest.yaml"))["core_baseline_plan"]
    output = tmp_path / "core.pathspec"

    planner._write_pathspec(report, output)

    assert output.read_text(encoding="utf-8").splitlines() == [
        "README.md",
        "docs/reference/cross-line-promotion-gate-v0.1.md",
    ]


def test_pathspec_refuses_non_passing_plan(tmp_path: Path) -> None:
    planner = _load_planner()

    with pytest.raises(ValueError, match="non-passing baseline plan"):
        planner._write_pathspec(
            {"state": "failed", "core_paths": [{"path": "README.md"}]},
            tmp_path / "bad.pathspec",
        )
