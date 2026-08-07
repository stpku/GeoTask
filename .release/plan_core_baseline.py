#!/usr/bin/env python3
"""Classify the dirty GeoTask workspace into one exact Core baseline staging plan.

The planner is intentionally fail-closed. A dirty path is accepted into the Core
baseline only when it is listed in ``core-baseline-manifest.yaml``. Known
Integration/internal paths are excluded. Any remaining dirty path is ``unknown``
and makes the plan fail.

The tool is read-only with respect to Git. ``--write-pathspec`` writes a plain
newline-delimited file containing the exact Core paths that a later local
executor may pass to ``git add --pathspec-from-file=...``. It never stages,
commits, tags, pushes, publishes, or changes release identity.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


DEFAULT_MANIFEST = Path(".release/core-baseline-manifest.yaml")
GENERATOR_ID = ".release/plan_core_baseline.py"


def _run(command: list[str], *, root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _head_commit(root: Path) -> str:
    result = _run(["git", "rev-parse", "HEAD"], root=root)
    return result.stdout.strip() if result.returncode == 0 else ""


def _dirty_paths(root: Path) -> tuple[list[str], str]:
    commands = (
        ["git", "-c", "core.quotepath=false", "diff", "--name-only", "--relative"],
        ["git", "-c", "core.quotepath=false", "diff", "--cached", "--name-only", "--relative"],
        ["git", "-c", "core.quotepath=false", "ls-files", "--others", "--exclude-standard"],
    )
    paths: set[str] = set()
    for command in commands:
        result = _run(command, root=root)
        if result.returncode != 0:
            return [], result.stderr.strip() or f"failed: {' '.join(command)}"
        paths.update(line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip())
    return sorted(paths), ""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    payload = yaml.safe_load(raw)
    if not isinstance(payload, dict):
        raise ValueError("baseline manifest must be a YAML object")
    core_paths = payload.get("core_exact_paths")
    exclusions = payload.get("excluded_patterns")
    if not isinstance(core_paths, list) or not all(isinstance(item, str) and item for item in core_paths):
        raise ValueError("core_exact_paths must be a non-empty string list")
    if len(core_paths) != len(set(core_paths)):
        raise ValueError("core_exact_paths contains duplicates")
    if not isinstance(exclusions, dict):
        raise ValueError("excluded_patterns must be an object")
    for category, patterns in exclusions.items():
        if not isinstance(category, str) or not isinstance(patterns, list) or not all(
            isinstance(pattern, str) and pattern for pattern in patterns
        ):
            raise ValueError("each excluded_patterns category must contain string patterns")
    return payload, raw


def _classify(path: str, manifest: dict[str, Any]) -> tuple[str, str]:
    core_paths = set(manifest["core_exact_paths"])
    if path in core_paths:
        return "core", "core_exact_paths"
    for category, patterns in manifest["excluded_patterns"].items():
        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern):
                return "excluded", str(category)
    return "unknown", "no_manifest_rule"


def _core_entry(root: Path, path: str) -> dict[str, str]:
    absolute = root / path
    if absolute.is_file():
        return {"path": path, "worktree_sha256": _sha256_file(absolute)}
    if not absolute.exists():
        return {"path": path, "worktree_sha256": "<deleted>"}
    return {"path": path, "worktree_sha256": "<non-file>"}


def _plan_digest(
    *,
    head_commit: str,
    manifest_sha256: str,
    core_entries: list[dict[str, str]],
) -> str:
    canonical = json.dumps(
        {
            "head_commit": head_commit,
            "manifest_sha256": manifest_sha256,
            "core_paths": core_entries,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(canonical)


def build_plan(root: Path, manifest_path: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = manifest_path if manifest_path.is_absolute() else root / manifest_path
    manifest, manifest_raw = _load_manifest(manifest_path)
    dirty_paths, error = _dirty_paths(root)
    head = _head_commit(root)

    if error or not head:
        return {
            "core_baseline_plan": {
                "schema_version": "0.1",
                "generated_by": GENERATOR_ID,
                "state": "failed",
                "ready_to_stage": False,
                "error": error or "cannot resolve HEAD",
                "side_effects": {
                    "index_changed": False,
                    "commit_created": False,
                    "push_performed": False,
                    "release_identity_changed": False,
                },
            }
        }

    core_paths: list[str] = []
    excluded: list[dict[str, str]] = []
    unknown: list[str] = []
    for path in dirty_paths:
        classification, reason = _classify(path, manifest)
        if classification == "core":
            core_paths.append(path)
        elif classification == "excluded":
            excluded.append({"path": path, "category": reason})
        else:
            unknown.append(path)

    core_entries = [_core_entry(root, path) for path in core_paths]
    manifest_sha256 = _sha256_bytes(manifest_raw)
    state = "passed" if core_paths and not unknown else "pending" if not dirty_paths else "failed"
    return {
        "core_baseline_plan": {
            "schema_version": "0.1",
            "generated_by": GENERATOR_ID,
            "baseline_id": manifest.get("baseline_id"),
            "target_release": manifest.get("target_release"),
            "manifest": str(manifest_path.relative_to(root)),
            "manifest_sha256": manifest_sha256,
            "head_commit": head,
            "state": state,
            "ready_to_stage": state == "passed",
            "dirty_count": len(dirty_paths),
            "core_count": len(core_paths),
            "excluded_count": len(excluded),
            "unknown_count": len(unknown),
            "core_paths": core_entries,
            "excluded_paths": excluded,
            "unknown_paths": unknown,
            "plan_digest": _plan_digest(
                head_commit=head,
                manifest_sha256=manifest_sha256,
                core_entries=core_entries,
            ),
            "invariants": {
                "unknown_dirty_path_policy": manifest.get("unknown_dirty_path_policy", "fail"),
                "integration_validation_is_not_core_ownership": True,
                "pathspec_is_exact_current_dirty_core_set": True,
            },
            "side_effects": {
                "index_changed": False,
                "commit_created": False,
                "push_performed": False,
                "release_identity_changed": False,
            },
        }
    }


def _write_pathspec(report: dict[str, Any], output: Path) -> None:
    if report.get("state") != "passed":
        raise ValueError("refusing to write staging pathspec from a non-passing baseline plan")
    paths = [entry["path"] for entry in report.get("core_paths", [])]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(f"{path}\n" for path in paths), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path, help="write the full JSON plan to this path")
    parser.add_argument("--write-pathspec", type=Path, help="write exact Core staging paths after a passing classification")
    args = parser.parse_args()

    try:
        payload = build_plan(args.root, args.manifest)
        report = payload["core_baseline_plan"]
        if args.write_pathspec is not None:
            _write_pathspec(report, args.write_pathspec)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")

    if args.format == "json":
        sys.stdout.write(text)
    elif report["state"] == "passed":
        print(
            "[PASS] Core baseline classified: "
            f"core={report['core_count']} excluded={report['excluded_count']} unknown=0 "
            f"digest={report['plan_digest']}"
        )
    elif report["state"] == "pending":
        print("[PENDING] No dirty Core baseline paths found", file=sys.stderr)
    else:
        print(
            "[FAIL] Core baseline contains unclassified dirty paths: "
            + ", ".join(report.get("unknown_paths", [])),
            file=sys.stderr,
        )

    raise SystemExit(0 if report["state"] == "passed" else 2 if report["state"] == "pending" else 1)


if __name__ == "__main__":
    main()
