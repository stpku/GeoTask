#!/usr/bin/env python3
"""Audit GeoTask Core release-candidate readiness without publishing anything.

The auditor deliberately separates repository/static checks, final release identity,
built distributions, executed multi-Python CI evidence, and clean public replay
evidence. A configured CI matrix is not treated as executed CI evidence.

Exit codes:
    0: ready
    1: failed (a hard contract mismatch exists)
    2: pending (no hard mismatch, but required release evidence is incomplete)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

EXPECTED_PYTHON_MINORS = ("3.10", "3.11", "3.12", "3.13")
DEFAULT_TARGET_VERSION = "0.4.0"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check(name: str, status: str, detail: str) -> dict[str, str]:
    if status not in {"passed", "pending", "failed"}:
        raise ValueError(f"invalid check status: {status}")
    return {"name": name, "status": status, "detail": detail}


def _source_version(root: Path) -> str:
    text = (root / "src" / "geotask_core" / "_version.py").read_text(encoding="utf-8")
    match = re.search(
        r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$',
        text,
        re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def _git_state(root: Path) -> tuple[str, bool, str]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        return "", False, f"cannot inspect git state: {exc}"
    dirty_count = len([line for line in status.splitlines() if line.strip()])
    return head, dirty_count == 0, f"head={head}; dirty_paths={dirty_count}"


def _python_declared(root: Path) -> tuple[bool, str]:
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    requires_ok = 'requires-python = ">=3.10"' in text
    missing = [
        version
        for version in EXPECTED_PYTHON_MINORS
        if f'"Programming Language :: Python :: {version}"' not in text
    ]
    valid = requires_ok and not missing
    detail = "requires-python >=3.10; classifiers=" + ",".join(EXPECTED_PYTHON_MINORS)
    if missing:
        detail += f"; missing={','.join(missing)}"
    return valid, detail


def _ci_matrix(root: Path) -> tuple[bool, str]:
    text = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    match = re.search(r"python-version:\s*\[([^\]]+)\]", text)
    if not match:
        return False, "python-version matrix not found"
    versions = tuple(re.findall(r'["\'](3\.\d+)["\']', match.group(1)))
    return versions == EXPECTED_PYTHON_MINORS, "configured=" + ",".join(versions)


def _promotion_gate(root: Path) -> tuple[bool, str]:
    path = root / "docs" / "reference" / "cross-line-promotion-gate-v0.1.md"
    if not path.is_file():
        return False, "cross-line Promotion Gate document missing"
    text = path.read_text(encoding="utf-8")
    required = (
        "GeoTask Core, Lowa Product, and Lowa-GT Integration",
        "validation != promotion",
        "consumption != ownership transfer",
        "PROMOTE",
        "KEEP_LOCAL",
        "DEFER",
        "REJECT",
    )
    missing = [item for item in required if item not in text]
    if missing:
        return False, f"missing={missing!r}"
    return True, "all required three-line invariants present"


def _distribution_boundary(root: Path) -> tuple[bool, str]:
    manifest_path = root / ".release" / "public-manifest.yaml"
    boundary_path = root / "docs" / "reference" / "core-distribution-boundary-v0.1.md"
    if not boundary_path.is_file():
        return False, "Core Distribution Boundary document missing"
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return False, f"cannot read public manifest: {exc}"

    include = set(manifest.get("include", ()))
    required = set(manifest.get("required", ()))
    forbidden = set(manifest.get("forbidden_paths", ()))
    core_required = {
        "docs/reference/cross-line-promotion-gate-v0.1.md",
        "docs/reference/lowa-gt-integration-contract-v0.1.md",
        "docs/reference/core-distribution-boundary-v0.1.md",
        "examples/reference_agent/**",
        "tests/test_core_distribution_boundary.py",
    }
    integration_paths = {
        "examples/integrations/lowa_gt_shadow/**",
        "tests/test_lowa_gt_shadow_fixture.py",
        "tests/test_lowa_gt_shadow_batch.py",
        "tests/test_lowa_gt_handoff_package.py",
        "tests/test_lowa_gt_human_baseline_compare.py",
        "docs/reference/lowa-gt-shadow-study-protocol-v0.1.md",
    }
    forbidden_required = {
        "examples/integrations/",
        "tests/test_lowa_gt_shadow_fixture.py",
        "tests/test_lowa_gt_shadow_batch.py",
        "tests/test_lowa_gt_handoff_package.py",
        "tests/test_lowa_gt_human_baseline_compare.py",
        "docs/reference/lowa-gt-shadow-study-protocol-v0.1.md",
    }

    missing_core = sorted(core_required - include)
    leaked = sorted((include | required) & integration_paths)
    missing_forbidden = sorted(forbidden_required - forbidden)
    if missing_core or leaked or missing_forbidden:
        return False, (
            f"missing_core={missing_core}; leaked_integration={leaked}; "
            f"missing_forbidden={missing_forbidden}"
        )
    return True, "Core export excludes Integration implementation and retains governance contracts"


def _freeze(root: Path, target_version: str) -> tuple[bool, str]:
    path = root / "docs" / "reference" / "p2-release-contract-freeze-v0.4.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))["release_contract_freeze"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        return False, f"cannot read release freeze: {exc}"
    valid = (
        payload.get("target_release") == target_version
        and payload.get("status") == "release_scope_frozen_not_released"
        and tuple(payload.get("package", {}).get("supported_python_minors", ()))
        == EXPECTED_PYTHON_MINORS
    )
    return valid, f"target={payload.get('target_release')}; status={payload.get('status')}"


def _external_evidence(
    evidence_path: Path | None,
    target_version: str,
    head_commit: str,
) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    if evidence_path is None:
        return [
            _check("python_ci_execution_evidence", "pending", "no RC evidence file supplied"),
            _check(
                "public_export_and_reference_agent_evidence",
                "pending",
                "no RC evidence file supplied",
            ),
        ], None

    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))["rc_evidence"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        return [_check("rc_evidence_file", "failed", f"cannot read RC evidence: {exc}")], None

    checks: list[dict[str, str]] = []
    generated_by = payload.get("generated_by")
    evidence_kind = payload.get("evidence_kind")
    if generated_by != ".release/collect_rc_evidence.py" or evidence_kind not in {
        "collector_shard",
        "collector_merged",
    }:
        checks.append(
            _check(
                "rc_evidence_generation",
                "failed",
                "RC evidence must be machine-generated by .release/collect_rc_evidence.py",
            )
        )
    else:
        checks.append(
            _check(
                "rc_evidence_generation",
                "passed",
                f"generated_by={generated_by}; kind={evidence_kind}",
            )
        )

    if payload.get("target_version") != target_version:
        checks.append(
            _check(
                "rc_evidence_target_version",
                "failed",
                f"expected {target_version}, got {payload.get('target_version')}",
            )
        )
    else:
        checks.append(_check("rc_evidence_target_version", "passed", target_version))

    evidence_commit = str(payload.get("commit") or "")
    if not head_commit:
        checks.append(
            _check(
                "rc_evidence_commit_binding",
                "failed",
                "current git HEAD could not be determined",
            )
        )
    elif evidence_commit != head_commit:
        checks.append(
            _check(
                "rc_evidence_commit_binding",
                "failed",
                f"evidence={evidence_commit or '<missing>'}; head={head_commit}",
            )
        )
    else:
        checks.append(_check("rc_evidence_commit_binding", "passed", head_commit))

    python_ci = payload.get("python_ci")
    if not isinstance(python_ci, dict):
        checks.append(
            _check("python_ci_execution_evidence", "failed", "python_ci must be an object")
        )
    else:
        failed_python = [
            version
            for version in EXPECTED_PYTHON_MINORS
            if python_ci.get(version) == "failed"
        ]
        not_passed = [
            version
            for version in EXPECTED_PYTHON_MINORS
            if python_ci.get(version) != "passed"
        ]
        if failed_python:
            checks.append(
                _check(
                    "python_ci_execution_evidence",
                    "failed",
                    "failed=" + ",".join(failed_python),
                )
            )
        else:
            checks.append(
                _check(
                    "python_ci_execution_evidence",
                    "passed" if not not_passed else "pending",
                    "all 3.10-3.13 passed"
                    if not not_passed
                    else "not passed=" + ",".join(not_passed),
                )
            )

    public_export = payload.get("public_export")
    replay = payload.get("reference_agent_replay")
    export_ok = (
        isinstance(public_export, dict)
        and public_export.get("verification") == "passed"
        and public_export.get("scan") == "passed"
    )
    replay_ok = replay == "passed"
    explicit_failure = (
        isinstance(public_export, dict)
        and "failed" in {public_export.get("verification"), public_export.get("scan")}
    ) or replay == "failed"
    checks.append(
        _check(
            "public_export_and_reference_agent_evidence",
            "failed" if explicit_failure else ("passed" if export_ok and replay_ok else "pending"),
            f"public_export={public_export!r}; reference_agent_replay={replay!r}",
        )
    )
    return checks, payload


def verify_rc_readiness(
    root: Path,
    *,
    target_version: str = DEFAULT_TARGET_VERSION,
    artifact_dir: Path | None = None,
    evidence_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    checks: list[dict[str, str]] = []

    freeze_ok, freeze_detail = _freeze(root, target_version)
    checks.append(
        _check(
            "release_scope_freeze",
            "passed" if freeze_ok else "failed",
            freeze_detail,
        )
    )

    gate_ok, gate_detail = _promotion_gate(root)
    checks.append(
        _check(
            "cross_line_promotion_gate",
            "passed" if gate_ok else "failed",
            gate_detail,
        )
    )

    distribution_ok, distribution_detail = _distribution_boundary(root)
    checks.append(
        _check(
            "core_distribution_boundary",
            "passed" if distribution_ok else "failed",
            distribution_detail,
        )
    )

    python_ok, python_detail = _python_declared(root)
    checks.append(
        _check(
            "python_support_declaration",
            "passed" if python_ok else "failed",
            python_detail,
        )
    )

    ci_ok, ci_detail = _ci_matrix(root)
    checks.append(
        _check(
            "ci_python_matrix_configuration",
            "passed" if ci_ok else "failed",
            ci_detail,
        )
    )

    head_commit, clean_worktree, git_detail = _git_state(root)
    checks.append(
        _check(
            "release_candidate_worktree",
            "passed" if clean_worktree else "pending",
            git_detail,
        )
    )

    source_version = _source_version(root)
    checks.append(
        _check(
            "target_version_metadata",
            "passed" if source_version == target_version else "pending",
            f"source={source_version or '<missing>'}; target={target_version}",
        )
    )

    preflight_valid = False
    if source_version != target_version:
        checks.append(
            _check(
                "release_identity_preflight",
                "pending",
                "source version has not been advanced to the target release",
            )
        )
    else:
        try:
            preflight = _load_module(
                root / ".release" / "verify_release_preflight.py",
                "geotask_release_preflight",
            )
            preflight_report = preflight.verify_release_preflight(
                root,
                expected_version=target_version,
                expected_tag=f"v{target_version}",
                artifact_dir=artifact_dir.resolve() if artifact_dir is not None else None,
            )["release_preflight"]
            preflight_valid = bool(preflight_report["valid"])
            checks.append(
                _check(
                    "release_identity_preflight",
                    "passed" if preflight_valid else "failed",
                    "valid"
                    if preflight_valid
                    else "; ".join(preflight_report.get("errors", ())),
                )
            )
        except Exception as exc:  # audit must fail closed without a traceback
            checks.append(
                _check(
                    "release_identity_preflight",
                    "failed",
                    f"preflight error: {exc}",
                )
            )

    if artifact_dir is None:
        checks.append(
            _check(
                "final_wheel_sdist",
                "pending",
                "final 0.4.0 artifact directory not supplied",
            )
        )
        checks.append(
            _check(
                "schema_bundle_distribution",
                "pending",
                "final 0.4.0 artifacts not supplied",
            )
        )
    elif source_version != target_version:
        checks.append(
            _check(
                "final_wheel_sdist",
                "pending",
                "artifacts cannot satisfy final target while source version is not target",
            )
        )
        checks.append(
            _check(
                "schema_bundle_distribution",
                "pending",
                "schema verification deferred until target-version artifacts exist",
            )
        )
    else:
        checks.append(
            _check(
                "final_wheel_sdist",
                "passed" if preflight_valid else "failed",
                str(artifact_dir.resolve()),
            )
        )
        try:
            schema_verifier = _load_module(
                root / ".release" / "verify_schema_distribution.py",
                "geotask_schema_distribution_verifier",
            )
            schema_report = schema_verifier.verify_distribution(artifact_dir)[
                "schema_distribution_verification"
            ]
            schema_ok = (
                bool(schema_report["valid"])
                and schema_report.get("schema_count") == 33
            )
            checks.append(
                _check(
                    "schema_bundle_distribution",
                    "passed" if schema_ok else "failed",
                    f"schema_count={schema_report.get('schema_count')}; errors={schema_report.get('errors')}",
                )
            )
        except Exception as exc:
            checks.append(
                _check(
                    "schema_bundle_distribution",
                    "failed",
                    f"schema verification error: {exc}",
                )
            )

    evidence_checks, evidence = _external_evidence(
        evidence_path,
        target_version,
        head_commit,
    )
    checks.extend(evidence_checks)

    failed = [item for item in checks if item["status"] == "failed"]
    pending = [item for item in checks if item["status"] == "pending"]
    state = "failed" if failed else ("pending" if pending else "ready")

    return {
        "rc_readiness": {
            "schema_version": "0.1",
            "target_version": target_version,
            "source_version": source_version,
            "head_commit": head_commit,
            "worktree_clean": clean_worktree,
            "state": state,
            "ready": state == "ready",
            "failed_count": len(failed),
            "pending_count": len(pending),
            "checks": checks,
            "evidence_file": str(evidence_path) if evidence_path is not None else None,
            "evidence_commit": evidence.get("commit") if isinstance(evidence, dict) else None,
            "side_effects": {
                "version_changed": False,
                "tag_created": False,
                "artifact_published": False,
                "remote_push_performed": False,
            },
        }
    }


def _render_text(report: dict[str, Any]) -> str:
    data = report["rc_readiness"]
    lines = [
        f"GeoTask Core RC readiness: {data['state'].upper()}",
        f"target={data['target_version']} source={data['source_version']} head={data['head_commit']}",
    ]
    for item in data["checks"]:
        lines.append(
            f"[{item['status'].upper()}] {item['name']}: {item['detail']}"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit GeoTask Core release-candidate readiness"
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: current directory)",
    )
    parser.add_argument("--target-version", default=DEFAULT_TARGET_VERSION)
    parser.add_argument(
        "--artifacts",
        help="Directory containing the final wheel and sdist",
    )
    parser.add_argument(
        "--evidence",
        help="JSON file containing executed CI/public replay evidence",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    args = parser.parse_args()

    report = verify_rc_readiness(
        Path(args.root),
        target_version=args.target_version,
        artifact_dir=Path(args.artifacts) if args.artifacts else None,
        evidence_path=Path(args.evidence) if args.evidence else None,
    )
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        sys.stdout.write(_render_text(report))

    state = report["rc_readiness"]["state"]
    sys.exit(0 if state == "ready" else (1 if state == "failed" else 2))


if __name__ == "__main__":
    main()
