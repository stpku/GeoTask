#!/usr/bin/env python3
"""Collect or merge machine-generated GeoTask Core RC evidence.

This tool never publishes, tags, pushes, or authorizes a release. It is deliberately
fail-closed: evidence can become ``passed`` only when it is generated from a clean
Git worktree whose source version already equals the requested target release.

Examples:
    python .release/collect_rc_evidence.py collect \
        --target-version 0.4.0 \
        --artifacts dist \
        --public-export /tmp/geotask-public-rc \
        --reference-python /tmp/geotask-rc-install/bin/python \
        --output rc-evidence-3.12.json

    python .release/collect_rc_evidence.py merge \
        rc-evidence-3.10.json rc-evidence-3.11.json \
        rc-evidence-3.12.json rc-evidence-3.13.json \
        --output rc-evidence.json

``--record-python-ci`` is intended for CI jobs. It requires ``CI=true`` and reruns
the repository test suite with the current interpreter before marking that exact
Python minor as passed. One job can therefore attest only to its own interpreter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Sequence


EXPECTED_PYTHON_MINORS = ("3.10", "3.11", "3.12", "3.13")
GENERATOR_ID = ".release/collect_rc_evidence.py"
SCHEMA_VERSION = "0.1"
DEFAULT_TARGET_VERSION = "0.4.0"

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    runner: Runner = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    return runner(
        list(command),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _source_version(root: Path) -> str:
    path = root / "src" / "geotask_core" / "_version.py"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(
        r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$',
        text,
        re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def _git_state(root: Path, *, runner: Runner = subprocess.run) -> tuple[str, bool, str]:
    head_result = _run(["git", "rev-parse", "HEAD"], cwd=root, runner=runner)
    status_result = _run(["git", "status", "--porcelain"], cwd=root, runner=runner)
    if head_result.returncode != 0 or status_result.returncode != 0:
        detail = (head_result.stderr + status_result.stderr).strip() or "git inspection failed"
        return "", False, detail
    head = head_result.stdout.strip()
    dirty = [line for line in status_result.stdout.splitlines() if line.strip()]
    return head, not dirty, f"head={head}; dirty_paths={len(dirty)}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_inventory(artifact_dir: Path | None) -> dict[str, Any]:
    if artifact_dir is None:
        return {"status": "pending", "files": {}}
    artifact_dir = artifact_dir.resolve()
    files = sorted(
        path for path in artifact_dir.iterdir() if path.is_file() and (path.suffix == ".whl" or path.name.endswith(".tar.gz"))
    ) if artifact_dir.is_dir() else []
    return {
        "status": "observed" if files else "pending",
        "files": {path.name: _sha256(path) for path in files},
    }


def _base_payload(target_version: str, commit: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATOR_ID,
        "evidence_kind": "collector_shard",
        "target_version": target_version,
        "commit": commit,
        "python_ci": {version: "pending" for version in EXPECTED_PYTHON_MINORS},
        "public_export": {"verification": "pending", "scan": "pending"},
        "reference_agent_replay": "pending",
    }


def collect_evidence(
    root: Path,
    *,
    target_version: str = DEFAULT_TARGET_VERSION,
    artifact_dir: Path | None = None,
    public_export_dir: Path | None = None,
    reference_python: Path | None = None,
    record_python_ci: bool = False,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    """Collect one fail-closed evidence shard from the current environment."""

    root = root.resolve()
    commit, clean, git_detail = _git_state(root, runner=runner)
    source_version = _source_version(root)
    release_candidate = bool(commit) and clean and source_version == target_version
    runtime_minor = f"{sys.version_info.major}.{sys.version_info.minor}"

    evidence = _base_payload(target_version, commit)
    local: dict[str, Any] = {
        "source_version": source_version,
        "worktree_clean": clean,
        "git_detail": git_detail,
        "runtime_python_minor": runtime_minor,
        "release_candidate_eligible": release_candidate,
        "artifacts": _artifact_inventory(artifact_dir),
        "checks": {},
    }

    if not release_candidate:
        reason = (
            "evidence remains pending until the worktree is clean and source version "
            f"equals target {target_version}"
        )
        local["checks"]["release_candidate"] = {"status": "pending", "detail": reason}
    else:
        local["checks"]["release_candidate"] = {
            "status": "passed",
            "detail": f"clean exact commit {commit}",
        }

    if artifact_dir is not None and release_candidate:
        preflight = _run(
            [
                sys.executable,
                str(root / ".release" / "verify_release_preflight.py"),
                "--expected-version",
                target_version,
                "--expected-tag",
                f"v{target_version}",
                "--artifacts",
                str(artifact_dir.resolve()),
                "--format",
                "json",
            ],
            cwd=root,
            runner=runner,
        )
        schema = _run(
            [
                sys.executable,
                str(root / ".release" / "verify_schema_distribution.py"),
                str(artifact_dir.resolve()),
                "--format",
                "json",
            ],
            cwd=root,
            runner=runner,
        )
        local["checks"]["artifact_preflight"] = {
            "status": "passed" if preflight.returncode == 0 else "failed",
            "detail": preflight.stderr.strip() or "release preflight completed",
        }
        local["checks"]["schema_distribution"] = {
            "status": "passed" if schema.returncode == 0 else "failed",
            "detail": schema.stderr.strip() or "schema distribution verification completed",
        }

    if public_export_dir is not None and release_candidate:
        export_result = _run(
            [
                sys.executable,
                str(root / ".release" / "export_public.py"),
                str(public_export_dir.resolve()),
                "--clean",
            ],
            cwd=root,
            runner=runner,
        )
        verify_result = _run(
            [
                sys.executable,
                str(root / ".release" / "verify_public_export.py"),
                str(public_export_dir.resolve()),
            ],
            cwd=root,
            runner=runner,
        ) if export_result.returncode == 0 else export_result
        scan_result = _run(
            [
                sys.executable,
                str(root / ".release" / "scan_public_export.py"),
                str(public_export_dir.resolve()),
            ],
            cwd=root,
            runner=runner,
        ) if export_result.returncode == 0 else export_result
        evidence["public_export"] = {
            "verification": "passed" if verify_result.returncode == 0 else "failed",
            "scan": "passed" if scan_result.returncode == 0 else "failed",
        }
        local["checks"]["public_export"] = {
            "status": "passed"
            if verify_result.returncode == 0 and scan_result.returncode == 0
            else "failed",
            "detail": (
                f"export_rc={export_result.returncode}; verify_rc={verify_result.returncode}; "
                f"scan_rc={scan_result.returncode}"
            ),
        }

    if reference_python is not None and release_candidate:
        replay = _run(
            [
                str(reference_python.resolve()),
                "-I",
                str(root / "examples" / "reference_agent" / "facility_assessment_update" / "replay.py"),
                "--scenario",
                "success",
                "--check-expected",
            ],
            cwd=root,
            runner=runner,
        )
        replay_ok = False
        fingerprint = ""
        if replay.returncode == 0:
            try:
                agent = json.loads(replay.stdout)["reference_agent"]
                assurance = agent["decision_assurance"]
                replay_ok = (
                    assurance.get("production_write_performed") is False
                    and assurance.get("production_report_refreshed") is False
                    and assurance.get("action_authorized") is False
                    and assurance.get("action_executed") is False
                )
                fingerprint = str(agent.get("replay_fingerprint") or "")
            except (json.JSONDecodeError, KeyError, TypeError):
                replay_ok = False
        evidence["reference_agent_replay"] = "passed" if replay_ok else "failed"
        local["checks"]["reference_agent_replay"] = {
            "status": "passed" if replay_ok else "failed",
            "detail": f"returncode={replay.returncode}; replay_fingerprint={fingerprint or '<missing>'}",
        }

    if record_python_ci:
        ci_flag = os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
        if runtime_minor not in EXPECTED_PYTHON_MINORS:
            local["checks"]["python_ci"] = {
                "status": "failed",
                "detail": f"unsupported runtime Python minor {runtime_minor}",
            }
        elif not release_candidate:
            local["checks"]["python_ci"] = {
                "status": "pending",
                "detail": "CI execution cannot attest a dirty/non-target release candidate",
            }
        elif not ci_flag:
            local["checks"]["python_ci"] = {
                "status": "pending",
                "detail": "CI environment marker is not true; local execution is not CI evidence",
            }
        else:
            test_result = _run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=root,
                runner=runner,
            )
            if test_result.returncode == 0:
                evidence["python_ci"][runtime_minor] = "passed"
                local["checks"]["python_ci"] = {
                    "status": "passed",
                    "detail": f"full pytest passed on Python {runtime_minor}",
                }
            else:
                evidence["python_ci"][runtime_minor] = "failed"
                local["checks"]["python_ci"] = {
                    "status": "failed",
                    "detail": f"pytest returncode={test_result.returncode}",
                }

    evidence["collector"] = local
    return {"rc_evidence": evidence}


def _load_generated(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))["rc_evidence"]
    if payload.get("generated_by") != GENERATOR_ID:
        raise ValueError(f"{path}: evidence was not generated by {GENERATOR_ID}")
    if payload.get("evidence_kind") not in {"collector_shard", "collector_merged"}:
        raise ValueError(f"{path}: unsupported evidence kind")
    return payload


def merge_evidence(paths: Sequence[Path]) -> dict[str, Any]:
    """Merge generated evidence shards bound to one exact target and commit."""

    if not paths:
        raise ValueError("at least one evidence shard is required")
    shards = [_load_generated(path) for path in paths]
    for shard in shards:
        failed_python = [
            version
            for version, status in shard.get("python_ci", {}).items()
            if status == "failed"
        ]
        public_export = shard.get("public_export", {})
        replay_failed = shard.get("reference_agent_replay") == "failed"
        collector_checks = shard.get("collector", {}).get("checks", {})
        failed_checks = [
            name
            for name, check in collector_checks.items()
            if isinstance(check, dict) and check.get("status") == "failed"
        ]
        if failed_python or "failed" in public_export.values() or replay_failed or failed_checks:
            raise ValueError(
                "cannot merge failed evidence shard: "
                f"python={failed_python}; public_export={public_export}; "
                f"reference_agent_failed={replay_failed}; collector_checks={failed_checks}"
            )

    target_versions = {str(shard.get("target_version") or "") for shard in shards}
    commits = {str(shard.get("commit") or "") for shard in shards}
    if len(target_versions) != 1 or "" in target_versions:
        raise ValueError(f"evidence target versions do not match: {sorted(target_versions)!r}")
    if len(commits) != 1 or "" in commits:
        raise ValueError(f"evidence commits do not match: {sorted(commits)!r}")

    target_version = next(iter(target_versions))
    commit = next(iter(commits))
    merged = _base_payload(target_version, commit)
    merged["evidence_kind"] = "collector_merged"

    for version in EXPECTED_PYTHON_MINORS:
        if any(shard.get("python_ci", {}).get(version) == "passed" for shard in shards):
            merged["python_ci"][version] = "passed"

    merged["public_export"] = {
        key: "passed"
        if any(shard.get("public_export", {}).get(key) == "passed" for shard in shards)
        else "pending"
        for key in ("verification", "scan")
    }
    merged["reference_agent_replay"] = (
        "passed" if any(shard.get("reference_agent_replay") == "passed" for shard in shards) else "pending"
    )

    artifact_sets = []
    for shard in shards:
        files = shard.get("collector", {}).get("artifacts", {}).get("files", {})
        if files:
            artifact_sets.append(files)
    if artifact_sets and any(files != artifact_sets[0] for files in artifact_sets[1:]):
        raise ValueError("artifact hashes differ across evidence shards")

    merged["collector"] = {
        "merged_shards": len(shards),
        "artifact_files": artifact_sets[0] if artifact_sets else {},
        "source_kinds": [str(shard.get("evidence_kind")) for shard in shards],
    }
    return {"rc_evidence": merged}


def _write_payload(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="collect one machine-generated evidence shard")
    collect.add_argument("--root", type=Path, default=Path.cwd())
    collect.add_argument("--target-version", default=DEFAULT_TARGET_VERSION)
    collect.add_argument("--artifacts", type=Path)
    collect.add_argument("--public-export", type=Path)
    collect.add_argument("--reference-python", type=Path)
    collect.add_argument("--record-python-ci", action="store_true")
    collect.add_argument("--output", type=Path)

    merge = subparsers.add_parser("merge", help="merge evidence shards for one exact RC commit")
    merge.add_argument("evidence", nargs="+", type=Path)
    merge.add_argument("--output", type=Path)

    args = parser.parse_args()
    try:
        if args.command == "collect":
            payload = collect_evidence(
                args.root,
                target_version=args.target_version,
                artifact_dir=args.artifacts,
                public_export_dir=args.public_export,
                reference_python=args.reference_python,
                record_python_ci=args.record_python_ci,
            )
        else:
            payload = merge_evidence(args.evidence)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)

    _write_payload(payload, args.output)


if __name__ == "__main__":
    main()
