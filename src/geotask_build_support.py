"""Setuptools build hooks for GeoTask package data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from shutil import copy2

from setuptools.command.build_py import build_py as _build_py


SCHEMA_BUNDLE_VERSION = "1.0"
SCHEMA_BUNDLE_MANIFEST_FILENAME = "schema-bundle-manifest-v1.0.json"


class BuildPy(_build_py):
    """Copy public JSON Schemas and generate their installed bundle manifest."""

    def run(self) -> None:
        super().run()
        project_root = Path(__file__).resolve().parents[1]
        source_dir = project_root / "schemas"
        target_dir = Path(self.build_lib) / "geotask_core" / "schemas"
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
