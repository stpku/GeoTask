"""P2 Core 0.4.0 release-candidate readiness gate tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / ".release" / "verify_rc_readiness.py"
DOC = ROOT / "docs" / "reference" / "core-0.4-rc-readiness-v0.1.md"
TEMPLATE = ROOT / "docs" / "reference" / "core-0.4-rc-evidence-template.json"


def _load_auditor():
    spec = importlib.util.spec_from_file_location("verify_rc_readiness", AUDITOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _head_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_current_repository_is_pending_not_failed_for_0_4_rc() -> None:
    auditor = _load_auditor()

    report = auditor.verify_rc_readiness(ROOT)["rc_readiness"]
    checks = {item["name"]: item for item in report["checks"]}

    assert report["target_version"] == "0.4.0"
    assert report["source_version"] == "0.4.0"
    assert report["state"] == "pending"
    assert report["ready"] is False
    assert report["failed_count"] == 0
    assert report["pending_count"] >= 5

    for name in (
        "release_scope_freeze",
        "cross_line_promotion_gate",
        "core_distribution_boundary",
        "python_support_declaration",
        "ci_python_matrix_configuration",
    ):
        assert checks[name]["status"] == "passed"

    assert checks["release_candidate_worktree"]["status"] == "pending"
    assert report["worktree_clean"] is False
    assert report["head_commit"] == _head_commit()
    assert checks["target_version_metadata"]["status"] == "passed"
    assert checks["release_identity_preflight"]["status"] == "passed"
    assert checks["final_wheel_sdist"]["status"] == "pending"
    assert checks["schema_bundle_distribution"]["status"] == "pending"
    assert checks["python_ci_execution_evidence"]["status"] == "pending"
    assert checks["public_export_and_reference_agent_evidence"]["status"] == "pending"
    assert all(value is False for value in report["side_effects"].values())


def test_rc_readiness_cli_uses_pending_exit_code_without_traceback() -> None:
    result = subprocess.run(
        [sys.executable, str(AUDITOR), "--root", str(ROOT), "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stderr == ""
    payload = json.loads(result.stdout)["rc_readiness"]
    assert payload["state"] == "pending"
    assert payload["failed_count"] == 0
    assert "Traceback" not in result.stdout


def test_rc_evidence_template_cannot_claim_execution_by_default() -> None:
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))["rc_evidence"]

    assert payload["target_version"] == "0.4.0"
    assert payload["generated_by"].startswith("<run .release/collect_rc_evidence.py")
    assert payload["evidence_kind"].startswith("<collector_shard")
    assert payload["commit"].startswith("<")
    assert payload["python_ci"] == {
        "3.10": "pending",
        "3.11": "pending",
        "3.12": "pending",
        "3.13": "pending",
    }
    assert payload["public_export"] == {
        "verification": "pending",
        "scan": "pending",
    }
    assert payload["reference_agent_replay"] == "pending"


def test_executed_evidence_is_separate_from_configured_ci(tmp_path: Path) -> None:
    head_commit = _head_commit()
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "rc_evidence": {
                    "schema_version": "0.1",
                    "generated_by": ".release/collect_rc_evidence.py",
                    "evidence_kind": "collector_merged",
                    "target_version": "0.4.0",
                    "commit": head_commit,
                    "python_ci": {version: "passed" for version in ("3.10", "3.11", "3.12", "3.13")},
                    "public_export": {"verification": "passed", "scan": "passed"},
                    "reference_agent_replay": "passed",
                }
            }
        ),
        encoding="utf-8",
    )
    auditor = _load_auditor()

    report = auditor.verify_rc_readiness(ROOT, evidence_path=evidence)["rc_readiness"]
    checks = {item["name"]: item for item in report["checks"]}

    assert checks["python_ci_execution_evidence"]["status"] == "passed"
    assert checks["public_export_and_reference_agent_evidence"]["status"] == "passed"
    assert checks["rc_evidence_commit_binding"]["status"] == "passed"
    assert report["evidence_commit"] == head_commit
    assert report["state"] == "pending"
    assert report["ready"] is False
    assert checks["target_version_metadata"]["status"] == "passed"


def test_mismatched_evidence_commit_is_hard_failure(tmp_path: Path) -> None:
    evidence = tmp_path / "wrong-commit-evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "rc_evidence": {
                    "schema_version": "0.1",
                    "target_version": "0.4.0",
                    "commit": "0123456789abcdef",
                    "python_ci": {version: "passed" for version in ("3.10", "3.11", "3.12", "3.13")},
                    "public_export": {"verification": "passed", "scan": "passed"},
                    "reference_agent_replay": "passed",
                }
            }
        ),
        encoding="utf-8",
    )
    auditor = _load_auditor()

    report = auditor.verify_rc_readiness(ROOT, evidence_path=evidence)["rc_readiness"]
    checks = {item["name"]: item for item in report["checks"]}

    assert report["state"] == "failed"
    assert checks["rc_evidence_commit_binding"]["status"] == "failed"
    assert _head_commit() in checks["rc_evidence_commit_binding"]["detail"]


def test_mismatched_evidence_target_is_hard_failure(tmp_path: Path) -> None:
    evidence = tmp_path / "bad-evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "rc_evidence": {
                    "target_version": "9.9.9",
                    "python_ci": {},
                    "public_export": {},
                    "reference_agent_replay": "pending",
                }
            }
        ),
        encoding="utf-8",
    )
    auditor = _load_auditor()

    report = auditor.verify_rc_readiness(ROOT, evidence_path=evidence)["rc_readiness"]

    assert report["state"] == "failed"
    assert report["failed_count"] >= 1
    assert any(
        item["name"] == "rc_evidence_target_version" and item["status"] == "failed"
        for item in report["checks"]
    )


def test_rc_gate_document_preserves_core_only_and_promotion_boundaries() -> None:
    text = DOC.read_text(encoding="utf-8")

    for fragment in (
        "0.4.0 is not released",
        "configured CI matrix is never treated as proof",
        "Integration validation != Core promotion",
        "Core release readiness != Lowa production readiness",
        "Lowa production acceptance != Core abstraction approval",
        "eligible is not executed",
        "verify_rc_readiness.py",
        "collect_rc_evidence.py",
        "core-0.4-rc-evidence-template.json",
    ):
        assert fragment in text
