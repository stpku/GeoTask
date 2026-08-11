"""Packaged activation support for the GeoTask Reference Agent.

This module does not add a new Core contract. It exposes the existing public
Reference Agent teaching example as an install-time developer activation asset:
verify the bundled text snapshot, materialize it into a new user directory, and
optionally replay one of the fixed deterministic scenarios.

The activation path is offline and fail-closed. It never fetches external data,
never overwrites an existing target directory, never authorizes an action, and
never performs a production write or real-world action.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

from geotask_core._version import __version__


REFERENCE_AGENT_BUNDLE_VERSION = "0.1"
REFERENCE_AGENT_BUNDLE_MANIFEST = "bundle-manifest-v0.1.json"
REFERENCE_AGENT_DEFAULT_OUTPUT = "geotask-reference-agent"
REFERENCE_AGENT_SCENARIOS = (
    "success",
    "missing_evidence",
    "conflicting_evidence",
    "stale_evidence",
    "contradicted",
)

_PACKAGE_BUNDLE = Path(__file__).resolve().parent / "reference_agent_demo"
_SOURCE_BUNDLE = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "reference_agent"
    / "facility_assessment_update"
)
_ALLOWED_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".json"}


class ReferenceAgentActivationError(ValueError):
    """Raised when Reference Agent activation cannot proceed safely."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _bundle_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == REFERENCE_AGENT_BUNDLE_MANIFEST:
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.suffix.lower() not in _ALLOWED_SUFFIXES:
            continue
        files.append(path)
    return files


def compute_reference_agent_bundle_manifest(root: Path) -> dict[str, Any]:
    """Compute the deterministic manifest for a Reference Agent bundle directory."""
    resolved = root.resolve()
    if not resolved.is_dir():
        raise ReferenceAgentActivationError(f"Reference Agent bundle not found: {root}")

    entries: list[dict[str, Any]] = []
    for path in _bundle_files(resolved):
        raw = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(resolved).as_posix(),
                "size_bytes": len(raw),
                "sha256": _sha256_bytes(raw),
            }
        )
    if not entries:
        raise ReferenceAgentActivationError("Reference Agent bundle contains no activation files")

    canonical = json.dumps(
        entries,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "reference_agent_bundle": {
            "bundle_version": REFERENCE_AGENT_BUNDLE_VERSION,
            "file_count": len(entries),
            "files": entries,
            "content_sha256": _sha256_bytes(canonical),
        }
    }


def _load_installed_manifest(root: Path) -> Mapping[str, Any] | None:
    path = root / REFERENCE_AGENT_BUNDLE_MANIFEST
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReferenceAgentActivationError(
            f"invalid installed Reference Agent bundle manifest: {exc}"
        ) from exc
    if not isinstance(value, Mapping):
        raise ReferenceAgentActivationError("installed Reference Agent bundle manifest must be an object")
    return value


def locate_reference_agent_bundle() -> Path:
    """Locate the installed bundle, or the canonical source example in a checkout."""
    if _PACKAGE_BUNDLE.is_dir():
        return _PACKAGE_BUNDLE
    if _SOURCE_BUNDLE.is_dir():
        return _SOURCE_BUNDLE
    raise ReferenceAgentActivationError(
        "Reference Agent activation bundle is unavailable in this installation"
    )


def verify_reference_agent_bundle(root: Path | None = None) -> dict[str, Any]:
    """Verify the installed bundle manifest when present and return computed metadata."""
    bundle_root = (root or locate_reference_agent_bundle()).resolve()
    computed = compute_reference_agent_bundle_manifest(bundle_root)
    installed = _load_installed_manifest(bundle_root)
    if installed is not None and dict(installed) != computed:
        raise ReferenceAgentActivationError(
            "installed Reference Agent activation bundle failed SHA-256 manifest verification"
        )
    return computed


def materialize_reference_agent(
    output_dir: str | Path = REFERENCE_AGENT_DEFAULT_OUTPUT,
) -> tuple[Path, dict[str, Any]]:
    """Copy the verified activation bundle into a new developer-owned directory."""
    source = locate_reference_agent_bundle().resolve()
    manifest = verify_reference_agent_bundle(source)
    target = Path(output_dir).expanduser().resolve()
    if target.exists():
        raise ReferenceAgentActivationError(
            f"activation target already exists; refusing to overwrite: {target}"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir()
    try:
        for source_path in _bundle_files(source):
            relative = source_path.relative_to(source)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)
        (target / REFERENCE_AGENT_BUNDLE_MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise

    return target, manifest


def _load_materialized_replay_module(target: Path) -> ModuleType:
    replay_path = target / "replay.py"
    if not replay_path.is_file():
        raise ReferenceAgentActivationError("materialized Reference Agent is missing replay.py")
    spec = importlib.util.spec_from_file_location(
        "geotask_reference_agent_materialized_replay",
        replay_path,
    )
    if spec is None or spec.loader is None:
        raise ReferenceAgentActivationError("cannot load materialized Reference Agent replay.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replay_materialized_reference_agent(
    target: str | Path,
    *,
    scenario: str = "success",
    scenario_path: str | Path | None = None,
) -> dict[str, Any]:
    """Replay a fixed or developer-supplied scenario from a verified activation bundle.

    Fixed named scenarios retain their shipped ``expected`` assertions. A custom
    ``scenario_path`` is intentionally replayed without inventing an expected result;
    callers may evaluate the returned deterministic state against their own declared
    oracle or acceptance criteria.
    """
    if scenario_path is None and scenario not in REFERENCE_AGENT_SCENARIOS:
        raise ReferenceAgentActivationError(
            f"unsupported Reference Agent scenario {scenario!r}; "
            f"supported: {', '.join(REFERENCE_AGENT_SCENARIOS)}"
        )
    target_path = Path(target).expanduser().resolve()
    if not target_path.is_dir():
        raise ReferenceAgentActivationError(f"materialized Reference Agent not found: {target_path}")

    verify_reference_agent_bundle(target_path)
    module = _load_materialized_replay_module(target_path)
    if scenario_path is None:
        result = module.replay_scenario(scenario)
        module._assert_expected(scenario, result)
    else:
        custom_path = Path(scenario_path).expanduser().resolve()
        if not custom_path.is_file():
            raise ReferenceAgentActivationError(
                f"Reference Agent scenario file not found: {custom_path}"
            )
        result = module.replay_scenario(scenario_path=custom_path)
    if not isinstance(result, dict):
        raise ReferenceAgentActivationError("Reference Agent replay did not return an object")
    return result


def activation_report(
    target: Path,
    manifest: Mapping[str, Any],
    *,
    scenario: str | None,
    replay_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build the user-facing activation report without expanding authority claims."""
    bundle = manifest["reference_agent_bundle"]
    report: dict[str, Any] = {
        "reference_agent_activation": {
            "schema_version": "0.1",
            "geotask_core_version": __version__,
            "output_dir": str(target),
            "bundle_version": bundle["bundle_version"],
            "bundle_file_count": bundle["file_count"],
            "bundle_content_sha256": bundle["content_sha256"],
            "scenario": scenario,
            "replayed": replay_result is not None,
            "external_truth_fetched": False,
            "production_write_performed": False,
            "action_authorized": False,
            "action_executed": False,
        }
    }
    if replay_result is not None:
        body = replay_result["reference_agent"]
        decision = body["decision_assurance"]
        report["reference_agent_activation"]["replay"] = {
            "verification_state": body["verification"]["state"],
            "control_state": body["control_evaluation"]["state"],
            "report_update_eligible": decision["report_update_eligible"],
            "production_write_performed": decision["production_write_performed"],
            "production_report_refreshed": decision["production_report_refreshed"],
            "action_authorized": decision["action_authorized"],
            "action_executed": decision["action_executed"],
            "replay_fingerprint": body["replay_fingerprint"],
        }
    return report
