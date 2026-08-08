"""P2 Core 0.4 RC machine-generated evidence collector tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / ".release" / "collect_rc_evidence.py"
AUDITOR = ROOT / ".release" / "verify_rc_readiness.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
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


def _generated_shard(commit: str, *, python_minor: str | None = None) -> dict:
    payload = {
        "schema_version": "0.1",
        "generated_by": ".release/collect_rc_evidence.py",
        "evidence_kind": "collector_shard",
        "target_version": "0.4.0",
        "commit": commit,
        "python_ci": {minor: "pending" for minor in ("3.10", "3.11", "3.12", "3.13")},
        "public_export": {"verification": "pending", "scan": "pending"},
        "reference_agent_replay": "pending",
        "collector": {
            "artifacts": {
                "files": {
                    "geotask_core-0.4.0-py3-none-any.whl": "a" * 64,
                    "geotask_core-0.4.0.tar.gz": "b" * 64,
                }
            }
        },
    }
    if python_minor is not None:
        payload["python_ci"][python_minor] = "passed"
    return {"rc_evidence": payload}


def test_dirty_target_repository_collects_pending_only(monkeypatch) -> None:
    collector = _load(COLLECTOR, "collect_rc_evidence")
    head_commit = _head_commit()
    monkeypatch.setattr(
        collector,
        "_git_state",
        lambda _root, **_kwargs: (head_commit, False, f"head={head_commit}; dirty_paths=1"),
    )

    payload = collector.collect_evidence(ROOT, target_version="0.4.0")["rc_evidence"]

    assert payload["generated_by"] == ".release/collect_rc_evidence.py"
    assert payload["evidence_kind"] == "collector_shard"
    assert payload["target_version"] == "0.4.0"
    assert payload["commit"] == _head_commit()
    assert set(payload["python_ci"].values()) == {"pending"}
    assert payload["public_export"] == {"verification": "pending", "scan": "pending"}
    assert payload["reference_agent_replay"] == "pending"
    assert payload["collector"]["source_version"] == "0.4.0"
    assert payload["collector"]["worktree_clean"] is False
    assert payload["collector"]["release_candidate_eligible"] is False


def test_merge_combines_only_exact_commit_python_shards(tmp_path: Path) -> None:
    collector = _load(COLLECTOR, "collect_rc_evidence_merge")
    commit = "1" * 40
    paths: list[Path] = []
    for minor in ("3.10", "3.11", "3.12", "3.13"):
        shard = _generated_shard(commit, python_minor=minor)
        if minor == "3.13":
            shard["rc_evidence"]["public_export"] = {"verification": "passed", "scan": "passed"}
            shard["rc_evidence"]["reference_agent_replay"] = "passed"
        path = tmp_path / f"evidence-{minor}.json"
        path.write_text(json.dumps(shard), encoding="utf-8")
        paths.append(path)

    merged = collector.merge_evidence(paths)["rc_evidence"]

    assert merged["evidence_kind"] == "collector_merged"
    assert merged["commit"] == commit
    assert merged["python_ci"] == {minor: "passed" for minor in ("3.10", "3.11", "3.12", "3.13")}
    assert merged["public_export"] == {"verification": "passed", "scan": "passed"}
    assert merged["reference_agent_replay"] == "passed"
    assert merged["collector"]["merged_shards"] == 4


def test_merge_rejects_cross_commit_evidence(tmp_path: Path) -> None:
    collector = _load(COLLECTOR, "collect_rc_evidence_cross_commit")
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps(_generated_shard("1" * 40, python_minor="3.10")), encoding="utf-8")
    second.write_text(json.dumps(_generated_shard("2" * 40, python_minor="3.11")), encoding="utf-8")

    with pytest.raises(ValueError, match="commits do not match"):
        collector.merge_evidence([first, second])


def test_merge_rejects_artifact_hash_mismatch(tmp_path: Path) -> None:
    collector = _load(COLLECTOR, "collect_rc_evidence_artifact_mismatch")
    commit = "3" * 40
    first_payload = _generated_shard(commit, python_minor="3.10")
    second_payload = _generated_shard(commit, python_minor="3.11")
    second_payload["rc_evidence"]["collector"]["artifacts"]["files"][
        "geotask_core-0.4.0-py3-none-any.whl"
    ] = "c" * 64
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps(first_payload), encoding="utf-8")
    second.write_text(json.dumps(second_payload), encoding="utf-8")

    with pytest.raises(ValueError, match="artifact hashes differ"):
        collector.merge_evidence([first, second])


def test_auditor_rejects_hand_authored_passed_evidence(tmp_path: Path) -> None:
    auditor = _load(AUDITOR, "verify_rc_readiness_manual_evidence")
    evidence = tmp_path / "manual.json"
    evidence.write_text(
        json.dumps(
            {
                "rc_evidence": {
                    "schema_version": "0.1",
                    "target_version": "0.4.0",
                    "commit": _head_commit(),
                    "python_ci": {minor: "passed" for minor in ("3.10", "3.11", "3.12", "3.13")},
                    "public_export": {"verification": "passed", "scan": "passed"},
                    "reference_agent_replay": "passed",
                }
            }
        ),
        encoding="utf-8",
    )

    report = auditor.verify_rc_readiness(ROOT, evidence_path=evidence)["rc_readiness"]
    checks = {check["name"]: check for check in report["checks"]}

    assert report["state"] == "failed"
    assert checks["rc_evidence_generation"]["status"] == "failed"


def test_auditor_accepts_generated_evidence_shape_even_while_other_gates_pending(tmp_path: Path) -> None:
    auditor = _load(AUDITOR, "verify_rc_readiness_generated_evidence")
    evidence = tmp_path / "generated.json"
    payload = _generated_shard(_head_commit())
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    report = auditor.verify_rc_readiness(ROOT, evidence_path=evidence)["rc_readiness"]
    checks = {check["name"]: check for check in report["checks"]}

    assert checks["rc_evidence_generation"]["status"] == "passed"
    assert checks["rc_evidence_commit_binding"]["status"] == "passed"
    assert report["state"] == "pending"
    assert report["failed_count"] == 0


def test_merge_rejects_failed_execution_shard(tmp_path: Path) -> None:
    collector = _load(COLLECTOR, "collect_rc_evidence_failed_shard")
    payload = _generated_shard("4" * 40)
    payload["rc_evidence"]["python_ci"]["3.12"] = "failed"
    path = tmp_path / "failed.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="cannot merge failed evidence shard"):
        collector.merge_evidence([path])


def test_auditor_treats_explicit_execution_failure_as_hard_failure(tmp_path: Path) -> None:
    auditor = _load(AUDITOR, "verify_rc_readiness_failed_execution")
    payload = _generated_shard(_head_commit())
    payload["rc_evidence"]["public_export"] = {"verification": "failed", "scan": "pending"}
    evidence = tmp_path / "failed-generated.json"
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    report = auditor.verify_rc_readiness(ROOT, evidence_path=evidence)["rc_readiness"]
    checks = {check["name"]: check for check in report["checks"]}

    assert report["state"] == "failed"
    assert checks["public_export_and_reference_agent_evidence"]["status"] == "failed"


def test_public_ci_wires_exact_commit_evidence_shards_and_merge() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    for fragment in (
        "python-version: [\"3.10\", \"3.11\", \"3.12\", \"3.13\"]",
        "collect_rc_evidence.py collect --target-version 0.4.0 --record-python-ci",
        "geotask-rc-evidence-${{ matrix.python-version }}",
        "name: geotask-core-rc-dist",
        "rc-build-evidence:",
        "--reference-python /tmp/geotask-rc-install/bin/python",
        "rc-evidence-merge:",
        "needs: [test, rc-build-evidence]",
        "collect_rc_evidence.py merge /tmp/geotask-rc-evidence/rc-evidence-3.10.json",
        "verify_rc_readiness.py",
        "result.returncode not in (0, 2)",
        "name: geotask-rc-evidence-merged",
    ):
        assert fragment in workflow
