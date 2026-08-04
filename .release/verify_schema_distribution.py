#!/usr/bin/env python3
"""Verify GeoTask wheel and sdist Schema Bundle integrity.

Usage:
    python .release/verify_schema_distribution.py dist
    python .release/verify_schema_distribution.py dist --format json

The verifier uses only the Python standard library. It does not import the built
package and does not access the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any


BUNDLE_VERSION = "1.0"
BUNDLE_MANIFEST_PATH = (
    "geotask_core/schemas/schema-bundle-manifest-v1.0.json"
)
EXPECTED_SCHEMA_FILENAMES = {
    "geotask-agent-generation-preparation-v0.1.schema.json",
    "geotask-agent-integration-v0.1.schema.json",
    "geotask-agent-revision-retry-v0.1.schema.json",
    "geotask-agent-revision-verification-v0.1.schema.json",
    "geotask-artifact-registry-v1.0.schema.json",
    "geotask-artifact-validation-v1.0.schema.json",
    "geotask-control-evaluation-v1.0.schema.json",
    "geotask-core-benchmark-v0.1.schema.json",
    "geotask-observation-v0.1.schema.json",
    "geotask-world-state-v0.1.schema.json",
    "geotask-state-transition-v0.1.schema.json",
    "geotask-verification-session-v0.1.schema.json",
    "geotask-discrepancy-report-v0.1.schema.json",
    "geotask-correction-request-v0.1.schema.json",
    "geotask-impact-graph-v0.1.schema.json",
    "geotask-incremental-reevaluation-result-v0.1.schema.json",
    "geotask-world-state-materialization-result-v0.1.schema.json",
    "geotask-recompute-derivation-result-v0.1.schema.json",
    "geotask-observation-merge-result-v0.1.schema.json",
    "geotask-result-v1.0.schema.json",
    "geotask-runtime-descriptor-v0.1.schema.json",
    "geotask-runtime-request-v0.1.schema.json",
    "geotask-runtime-response-v0.1.schema.json",
    "geotask-verification-provider-descriptor-v0.1.schema.json",
    "geotask-verification-request-v0.1.schema.json",
    "geotask-verification-response-v0.1.schema.json",
    "geotask-assurance-profile-v0.1.schema.json",
    "geotask-v1.0.schema.json",
}
REQUIRED_SDIST_PATHS = {
    "MANIFEST.in",
    "pyproject.toml",
    "src/geotask_build_support.py",
    "src/geotask_core/schemas/__init__.py",
    "src/geotask_core/v1/schema_bundle.py",
    "src/geotask_core/v1/artifact_validation.py",
    "src/geotask_core/v1/impact_graph.py",
    "src/geotask_core/v1/incremental_reevaluation_result.py",
    "src/geotask_core/v1/world_state_materialization.py",
    "src/geotask_core/v1/recompute_derivation.py",
    "src/geotask_core/v1/observation_merge.py",
    "src/geotask_core/v1/runtime_interface.py",
    "src/geotask_core/v1/verification_provider.py",
    *(f"schemas/{name}" for name in EXPECTED_SCHEMA_FILENAMES),
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _select_artifact(
    artifact_dir: Path,
    pattern: str,
    label: str,
    errors: list[str],
) -> Path | None:
    matches = sorted(artifact_dir.glob(pattern))
    if len(matches) != 1:
        errors.append(
            f"expected exactly one {label} matching {pattern!r}, found {len(matches)}"
        )
        return None
    return matches[0]


def _parse_json_object(raw: bytes, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label} is not valid UTF-8 JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label} must contain a JSON object")
        return None
    return payload


def _read_wheel(
    wheel_path: Path,
    errors: list[str],
) -> tuple[dict[str, Any] | None, dict[str, bytes]]:
    schema_bytes: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(wheel_path) as archive:
            names = set(archive.namelist())
            if BUNDLE_MANIFEST_PATH not in names:
                errors.append(f"wheel is missing {BUNDLE_MANIFEST_PATH}")
                return None, schema_bytes

            entry_point_files = sorted(
                name for name in names if name.endswith(".dist-info/entry_points.txt")
            )
            if len(entry_point_files) != 1:
                errors.append(
                    "wheel must contain exactly one .dist-info/entry_points.txt"
                )
            else:
                entry_points = archive.read(entry_point_files[0]).decode(
                    "utf-8", errors="replace"
                )
                if "geotask = geotask_core.cli:main" not in entry_points:
                    errors.append("wheel entry points do not expose geotask_core.cli:main")

            manifest = _parse_json_object(
                archive.read(BUNDLE_MANIFEST_PATH),
                "wheel Schema Bundle Manifest",
                errors,
            )
            if manifest is None:
                return None, schema_bytes

            for filename in EXPECTED_SCHEMA_FILENAMES:
                path = f"geotask_core/schemas/{filename}"
                if path not in names:
                    errors.append(f"wheel is missing {path}")
                    continue
                schema_bytes[filename] = archive.read(path)
            return manifest, schema_bytes
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"cannot read wheel {wheel_path.name}: {exc}")
        return None, schema_bytes


def _validate_bundle_manifest(
    manifest: dict[str, Any] | None,
    wheel_schema_bytes: dict[str, bytes],
    errors: list[str],
) -> tuple[list[dict[str, object]], dict[str, str]]:
    reports: list[dict[str, object]] = []
    schema_ids_by_filename: dict[str, str] = {}
    if manifest is None:
        return reports, schema_ids_by_filename

    bundle = manifest.get("schema_bundle")
    if not isinstance(bundle, dict):
        errors.append("wheel Manifest requires schema_bundle object")
        return reports, schema_ids_by_filename
    if bundle.get("bundle_version") != BUNDLE_VERSION:
        errors.append(
            "wheel Manifest bundle_version mismatch: "
            f"expected {BUNDLE_VERSION!r}, got {bundle.get('bundle_version')!r}"
        )

    entries = bundle.get("schemas")
    if not isinstance(entries, list):
        errors.append("wheel Manifest schemas must be an array")
        return reports, schema_ids_by_filename
    if bundle.get("schema_count") != len(entries):
        errors.append("wheel Manifest schema_count does not match schemas length")
    if len(entries) != len(EXPECTED_SCHEMA_FILENAMES):
        errors.append(
            "wheel Manifest must describe exactly "
            f"{len(EXPECTED_SCHEMA_FILENAMES)} schemas"
        )

    seen_filenames: set[str] = set()
    seen_schema_ids: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"wheel Manifest schema entry {index} must be an object")
            continue
        filename = entry.get("filename")
        schema_id = entry.get("schema_id")
        expected_size = entry.get("size_bytes")
        expected_digest = entry.get("sha256")
        if not isinstance(filename, str) or filename not in EXPECTED_SCHEMA_FILENAMES:
            errors.append(f"wheel Manifest contains unexpected filename: {filename!r}")
            continue
        if filename in seen_filenames:
            errors.append(f"wheel Manifest contains duplicate filename: {filename}")
            continue
        seen_filenames.add(filename)
        if not isinstance(schema_id, str) or not schema_id:
            errors.append(f"wheel Manifest schema_id is invalid for {filename}")
            continue
        if schema_id in seen_schema_ids:
            errors.append(f"wheel Manifest contains duplicate schema_id: {schema_id}")
        seen_schema_ids.add(schema_id)
        schema_ids_by_filename[filename] = schema_id

        raw = wheel_schema_bytes.get(filename)
        actual_size = len(raw) if raw is not None else 0
        actual_digest = _sha256(raw) if raw is not None else ""
        valid = True
        item_errors: list[str] = []
        if raw is None:
            item_errors.append("schema file is missing from wheel")
            valid = False
        if expected_size != actual_size:
            item_errors.append(
                f"size mismatch: expected {expected_size!r}, got {actual_size}"
            )
            valid = False
        if expected_digest != actual_digest:
            item_errors.append(
                f"sha256 mismatch: expected {expected_digest!r}, got {actual_digest}"
            )
            valid = False

        if raw is not None:
            schema = _parse_json_object(raw, f"wheel schema {filename}", item_errors)
            if schema is None or schema.get("$id") != schema_id:
                actual_id = schema.get("$id") if schema is not None else None
                item_errors.append(
                    f"$id mismatch: expected {schema_id!r}, got {actual_id!r}"
                )
                valid = False

        if item_errors:
            errors.extend(f"{filename}: {message}" for message in item_errors)
        reports.append(
            {
                "filename": filename,
                "schema_id": schema_id,
                "size_bytes": actual_size,
                "sha256": actual_digest,
                "valid": valid,
            }
        )

    missing = EXPECTED_SCHEMA_FILENAMES - seen_filenames
    if missing:
        errors.append("wheel Manifest is missing schemas: " + ", ".join(sorted(missing)))
    return reports, schema_ids_by_filename


def _read_sdist_members(
    sdist_path: Path,
    errors: list[str],
) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    try:
        with tarfile.open(sdist_path, mode="r:gz") as archive:
            regular = [member for member in archive.getmembers() if member.isfile()]
            roots = {Path(member.name).parts[0] for member in regular if Path(member.name).parts}
            if len(roots) != 1:
                errors.append("sdist must contain exactly one top-level directory")
                return members
            root = next(iter(roots))
            prefix = root + "/"
            for member in regular:
                if not member.name.startswith(prefix):
                    continue
                relative = member.name[len(prefix) :]
                extracted = archive.extractfile(member)
                if extracted is not None:
                    members[relative] = extracted.read()
    except (OSError, tarfile.TarError) as exc:
        errors.append(f"cannot read sdist {sdist_path.name}: {exc}")
    return members


def _validate_sdist(
    members: dict[str, bytes],
    wheel_schema_bytes: dict[str, bytes],
    schema_ids_by_filename: dict[str, str],
    errors: list[str],
) -> None:
    missing = REQUIRED_SDIST_PATHS - set(members)
    if missing:
        errors.append("sdist is missing required paths: " + ", ".join(sorted(missing)))

    for filename in EXPECTED_SCHEMA_FILENAMES:
        source_path = f"schemas/{filename}"
        source_raw = members.get(source_path)
        wheel_raw = wheel_schema_bytes.get(filename)
        if source_raw is None or wheel_raw is None:
            continue
        if source_raw != wheel_raw:
            errors.append(
                f"sdist authoritative schema differs from wheel resource: {filename}"
            )
        schema = _parse_json_object(source_raw, f"sdist schema {filename}", errors)
        expected_id = schema_ids_by_filename.get(filename)
        if schema is not None and expected_id and schema.get("$id") != expected_id:
            errors.append(
                f"sdist schema $id differs from wheel Manifest for {filename}"
            )


def verify_distribution(artifact_dir: Path) -> dict[str, Any]:
    """Verify one wheel and one sdist in ``artifact_dir``."""

    artifact_dir = artifact_dir.resolve()
    errors: list[str] = []
    wheel_path = _select_artifact(artifact_dir, "*.whl", "wheel", errors)
    sdist_path = _select_artifact(artifact_dir, "*.tar.gz", "sdist", errors)

    manifest: dict[str, Any] | None = None
    wheel_schema_bytes: dict[str, bytes] = {}
    schema_reports: list[dict[str, object]] = []
    schema_ids_by_filename: dict[str, str] = {}
    if wheel_path is not None:
        manifest, wheel_schema_bytes = _read_wheel(wheel_path, errors)
        schema_reports, schema_ids_by_filename = _validate_bundle_manifest(
            manifest, wheel_schema_bytes, errors
        )
    if sdist_path is not None:
        members = _read_sdist_members(sdist_path, errors)
        _validate_sdist(
            members,
            wheel_schema_bytes,
            schema_ids_by_filename,
            errors,
        )

    return {
        "schema_distribution_verification": {
            "valid": not errors,
            "bundle_version": BUNDLE_VERSION,
            "wheel": wheel_path.name if wheel_path is not None else "",
            "sdist": sdist_path.name if sdist_path is not None else "",
            "schema_count": len(schema_reports),
            "schemas": schema_reports,
            "errors": errors,
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify GeoTask wheel and sdist Schema Bundle integrity"
    )
    parser.add_argument("artifact_dir", help="Directory containing one wheel and one sdist")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Report format (default: text)",
    )
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    if not artifact_dir.is_dir():
        print(f"ERROR: artifact directory does not exist: {artifact_dir}", file=sys.stderr)
        sys.exit(1)

    report = verify_distribution(artifact_dir)
    verification = report["schema_distribution_verification"]
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif verification["valid"]:
        print(
            "[PASS] Schema distribution verified: "
            f"{verification['schema_count']} schemas, "
            f"wheel={verification['wheel']}, sdist={verification['sdist']}"
        )
    else:
        print("[FAIL] Schema distribution verification failed:", file=sys.stderr)
        for error in verification["errors"]:
            print(f"  - {error}", file=sys.stderr)

    if not verification["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
