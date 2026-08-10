"""Setuptools build hooks for GeoTask package data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from shutil import copy2

from setuptools.command.build_py import build_py as _build_py


SCHEMA_BUNDLE_VERSION = "1.0"
SCHEMA_BUNDLE_MANIFEST_FILENAME = "schema-bundle-manifest-v1.0.json"
REFERENCE_AGENT_BUNDLE_VERSION = "0.1"
REFERENCE_AGENT_BUNDLE_MANIFEST_FILENAME = "bundle-manifest-v0.1.json"
REFERENCE_AGENT_SOURCE = Path("examples/reference_agent/facility_assessment_update")
REFERENCE_AGENT_ALLOWED_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".json"}


def _copy_reference_agent_bundle(project_root: Path, build_lib: Path) -> None:
    source_dir = project_root / REFERENCE_AGENT_SOURCE
    if not source_dir.is_dir():
        raise RuntimeError(
            "GeoTask build requires the public Reference Agent activation source bundle"
        )

    target_dir = build_lib / "geotask_core" / "reference_agent_demo"
    target_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []
    for source in sorted(source_dir.rglob("*")):
        if not source.is_file():
            continue
        if "__pycache__" in source.parts or source.suffix == ".pyc":
            continue
        if source.suffix.lower() not in REFERENCE_AGENT_ALLOWED_SUFFIXES:
            continue
        relative = source.relative_to(source_dir)
        raw = source.read_bytes()
        destination = target_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(source, destination)
        entries.append(
            {
                "path": relative.as_posix(),
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )

    if not entries:
        raise RuntimeError("GeoTask build found an empty Reference Agent activation bundle")
    canonical = json.dumps(
        entries,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    manifest = {
        "reference_agent_bundle": {
            "bundle_version": REFERENCE_AGENT_BUNDLE_VERSION,
            "file_count": len(entries),
            "files": entries,
            "content_sha256": hashlib.sha256(canonical).hexdigest(),
        }
    }
    (target_dir / REFERENCE_AGENT_BUNDLE_MANIFEST_FILENAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class BuildPy(_build_py):
    """Copy public JSON Schemas and the verified Reference Agent activation bundle."""

    def run(self) -> None:
        super().run()
        project_root = Path(__file__).resolve().parents[1]
        source_dir = project_root / "schemas"
        build_lib = Path(self.build_lib)
        target_dir = build_lib / "geotask_core" / "schemas"
        target_dir.mkdir(parents=True, exist_ok=True)

        schema_files = sorted(source_dir.glob("*.schema.json"))
        if not schema_files:
            raise RuntimeError("GeoTask build requires public JSON Schema files")

        entries: list[dict[str, object]] = []
        for source in schema_files:
            raw = source.read_bytes()
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    f"GeoTask build found invalid JSON Schema: {source.name}"
                ) from exc
            schema_id = payload.get("$id") if isinstance(payload, dict) else None
            if not isinstance(schema_id, str) or not schema_id:
                raise RuntimeError(
                    f"GeoTask build requires a non-empty $id in {source.name}"
                )

            copy2(source, target_dir / source.name)
            entries.append(
                {
                    "schema_id": schema_id,
                    "filename": source.name,
                    "size_bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )

        manifest = {
            "schema_bundle": {
                "bundle_version": SCHEMA_BUNDLE_VERSION,
                "schema_count": len(entries),
                "schemas": entries,
            }
        }
        manifest_path = target_dir / SCHEMA_BUNDLE_MANIFEST_FILENAME
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        _copy_reference_agent_bundle(project_root, build_lib)
