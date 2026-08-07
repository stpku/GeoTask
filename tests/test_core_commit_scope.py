"""Core-only staged commit ownership gate tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / ".release" / "verify_core_commit_scope.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("verify_core_commit_scope", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_unstaged_repository_reports_pending_without_side_effects() -> None:
    result = subprocess.run(
        [sys.executable, str(GATE), "--root", str(ROOT), "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert '"state": "pending"' in result.stdout
    assert '"staged_count": 0' in result.stdout
    assert '"index_changed": false' in result.stdout
    assert '"commit_created": false' in result.stdout
    assert '"push_performed": false' in result.stdout


def test_core_governance_paths_can_be_staged(monkeypatch) -> None:
    gate = _load_gate()
    monkeypatch.setattr(
        gate,
        "_staged_paths",
        lambda root: (
            [
                ".release/verify_rc_readiness.py",
                "docs/reference/lowa-gt-integration-contract-v0.1.md",
                "docs/reference/cross-line-promotion-gate-v0.1.md",
                "examples/reference_agent/facility_assessment_update/replay.py",
            ],
            "",
        ),
    )

    report = gate.verify_core_commit_scope(ROOT)["core_commit_scope"]

    assert report["state"] == "passed"
    assert report["valid"] is True
    assert report["forbidden_paths"] == []


def test_integration_paths_block_core_commit(monkeypatch) -> None:
    gate = _load_gate()
    monkeypatch.setattr(
        gate,
        "_staged_paths",
        lambda root: (
            [
                "examples/integrations/lowa_gt_shadow/shadow_verify.py",
                "tests/test_lowa_gt_shadow_batch.py",
                "docs/internal/lowa-gt-promotion-gate-v0.1.md",
                "docs/reports/lowa_gt_shadow_revalidation_v2_20260807.md",
            ],
            "",
        ),
    )

    report = gate.verify_core_commit_scope(ROOT)["core_commit_scope"]

    assert report["state"] == "failed"
    assert report["valid"] is False
    assert {item["path"] for item in report["forbidden_paths"]} == {
        "examples/integrations/lowa_gt_shadow/shadow_verify.py",
        "tests/test_lowa_gt_shadow_batch.py",
        "docs/internal/lowa-gt-promotion-gate-v0.1.md",
        "docs/reports/lowa_gt_shadow_revalidation_v2_20260807.md",
    }


def test_boundary_contract_is_allowed_but_shadow_protocol_is_not(monkeypatch) -> None:
    gate = _load_gate()
    monkeypatch.setattr(
        gate,
        "_staged_paths",
        lambda root: (
            [
                "docs/reference/lowa-gt-integration-contract-v0.1.md",
                "docs/reference/lowa-gt-shadow-study-protocol-v0.1.md",
            ],
            "",
        ),
    )

    report = gate.verify_core_commit_scope(ROOT)["core_commit_scope"]

    assert report["state"] == "failed"
    assert report["forbidden_paths"] == [
        {
            "path": "docs/reference/lowa-gt-shadow-study-protocol-v0.1.md",
            "pattern": "docs/reference/lowa-gt-shadow-study-protocol-v0.1.md",
        }
    ]


def _write_plan(tmp_path: Path, *, head: str, entries: list[dict[str, str]]) -> Path:
    path = tmp_path / "core-baseline-plan.json"
    path.write_text(
        json.dumps(
            {
                "core_baseline_plan": {
                    "schema_version": "0.1",
                    "generated_by": ".release/plan_core_baseline.py",
                    "state": "passed",
                    "ready_to_stage": True,
                    "head_commit": head,
                    "plan_digest": "plan-digest",
                    "core_paths": entries,
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def test_baseline_plan_requires_exact_staged_paths_head_and_blob_hashes(monkeypatch, tmp_path: Path) -> None:
    gate = _load_gate()
    head = "4" * 40
    entries = [
        {"path": "README.md", "worktree_sha256": "a" * 64},
        {"path": ".release/verify_core_commit_scope.py", "worktree_sha256": "b" * 64},
    ]
    plan = _write_plan(tmp_path, head=head, entries=entries)
    monkeypatch.setattr(
        gate,
        "_staged_paths",
        lambda root: ([".release/verify_core_commit_scope.py", "README.md"], ""),
    )
    monkeypatch.setattr(gate, "_head_commit", lambda root: head)
    monkeypatch.setattr(
        gate,
        "_staged_sha256",
        lambda root, path: {"README.md": "a" * 64, ".release/verify_core_commit_scope.py": "b" * 64}[path],
    )

    report = gate.verify_core_commit_scope(ROOT, baseline_plan=plan)["core_commit_scope"]

    assert report["state"] == "passed"
    assert report["valid"] is True
    assert report["baseline_plan"]["exact_staged_plan_match"] is True
    assert report["baseline_plan"]["missing_paths"] == []
    assert report["baseline_plan"]["unexpected_paths"] == []
    assert report["baseline_plan"]["content_mismatches"] == []


def test_baseline_plan_rejects_missing_extra_or_changed_staged_content(monkeypatch, tmp_path: Path) -> None:
    gate = _load_gate()
    head = "5" * 40
    plan = _write_plan(
        tmp_path,
        head=head,
        entries=[
            {"path": "README.md", "worktree_sha256": "a" * 64},
            {"path": "CHANGELOG.md", "worktree_sha256": "b" * 64},
        ],
    )
    monkeypatch.setattr(gate, "_staged_paths", lambda root: (["README.md", "ROADMAP.md"], ""))
    monkeypatch.setattr(gate, "_head_commit", lambda root: head)
    monkeypatch.setattr(gate, "_staged_sha256", lambda root, path: "c" * 64)

    report = gate.verify_core_commit_scope(ROOT, baseline_plan=plan)["core_commit_scope"]

    assert report["state"] == "failed"
    assert report["valid"] is False
    assert report["baseline_plan"]["missing_paths"] == ["CHANGELOG.md"]
    assert report["baseline_plan"]["unexpected_paths"] == ["ROADMAP.md"]
    assert report["baseline_plan"]["content_mismatches"] == [
        {
            "path": "README.md",
            "expected_sha256": "a" * 64,
            "staged_sha256": "c" * 64,
        }
    ]


def test_baseline_plan_rejects_head_change_after_planning(monkeypatch, tmp_path: Path) -> None:
    gate = _load_gate()
    plan = _write_plan(
        tmp_path,
        head="6" * 40,
        entries=[{"path": "README.md", "worktree_sha256": "a" * 64}],
    )
    monkeypatch.setattr(gate, "_staged_paths", lambda root: (["README.md"], ""))
    monkeypatch.setattr(gate, "_head_commit", lambda root: "7" * 40)
    monkeypatch.setattr(gate, "_staged_sha256", lambda root, path: "a" * 64)

    report = gate.verify_core_commit_scope(ROOT, baseline_plan=plan)["core_commit_scope"]

    assert report["state"] == "failed"
    assert report["baseline_plan"]["head_matches"] is False
    assert report["baseline_plan"]["exact_staged_plan_match"] is False
