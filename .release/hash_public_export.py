#!/usr/bin/env python3
"""Generate and verify SHA-256 manifest for a public export directory.

Usage:
    python .release/hash_public_export.py generate EXPORT_DIR [OUTPUT]
    python .release/hash_public_export.py verify EXPORT_DIR MANIFEST

Does NOT access network. Excludes dist/, egg-info, pycache, pytest_cache.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

EXCLUDE_DIRS = {".git", "dist", "build", ".egg-info", "__pycache__", ".pytest_cache"}


def _excluded(rel_path: str) -> bool:
    """Check if a relative path should be excluded from hash tracking."""
    return rel_path.endswith(".sha256.json") or rel_path.endswith("_report.txt")


def _excluded_dir(dirname: str) -> bool:
    """Return True if this directory should be excluded from walking."""
    return dirname in EXCLUDE_DIRS or dirname.endswith(".egg-info")


def generate_manifest(export_dir: Path, output_path: Path) -> dict:
    """Generate SHA-256 manifest for all files in export_dir."""
    manifest: list[dict] = []
    for root, dirs, files in os.walk(export_dir):
        dirs[:] = [d for d in dirs if not _excluded_dir(d)]
        for f in sorted(files):
            fp = Path(root) / f
            rel = fp.relative_to(export_dir).as_posix()
            if _excluded(rel):
                continue
            sha = hashlib.sha256(fp.read_bytes()).hexdigest()
            size = fp.stat().st_size
            manifest.append({"path": rel, "size": size, "sha256": sha})

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print(f"Generated {output_path} ({len(manifest)} files)")
    return {"count": len(manifest), "path": str(output_path)}


def verify_manifest(export_dir: Path, manifest_path: Path) -> bool:
    """Verify all files match the manifest. Returns True if valid."""
    with open(manifest_path, encoding="utf-8") as fh:
        expected = json.load(fh)

    expected_map = {e["path"]: e for e in expected}
    errors = []

    # Check for duplicate paths
    seen = set()
    for e in expected:
        if e["path"] in seen:
            errors.append(f"Duplicate path in manifest: {e['path']}")
        seen.add(e["path"])

    # Check each manifest entry
    for entry in expected:
        fp = export_dir / entry["path"]
        if not fp.exists():
            errors.append(f"Missing file: {entry['path']}")
            continue
        actual_sha = hashlib.sha256(fp.read_bytes()).hexdigest()
        if actual_sha != entry["sha256"]:
            errors.append(f"SHA-256 mismatch: {entry['path']}")
        actual_size = fp.stat().st_size
        if actual_size != entry["size"]:
            errors.append(
                f"Size mismatch: {entry['path']} "
                f"(expected {entry['size']}, got {actual_size})"
            )

    # Check for untracked files
    for root, dirs, files in os.walk(export_dir):
        dirs[:] = [d for d in dirs if not _excluded_dir(d)]
        for f in files:
            rel = (Path(root) / f).relative_to(export_dir).as_posix()
            if _excluded(rel):
                continue
            if rel not in expected_map:
                errors.append(f"Untracked file: {rel}")

    if errors:
        print(f"\nHASH VERIFY FAILED — {len(errors)} issue(s):\n")
        for err in errors:
            print(f"  [FAIL] {err}")
        return False

    print(f"\n[PASS] Hash verify — {len(expected)} files match manifest.\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate/verify SHA-256 manifest for public export"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="Generate manifest")
    gen.add_argument("export_dir", type=str)
    gen.add_argument("output", type=str, nargs="?", default="public-files.sha256.json")
    ver = sub.add_parser("verify", help="Verify manifest")
    ver.add_argument("export_dir", type=str)
    ver.add_argument("manifest", type=str, default="public-files.sha256.json")

    args = parser.parse_args()

    if args.command == "generate":
        ed = Path(args.export_dir).resolve()
        out = Path(args.output)
        if not out.is_absolute():
            out = Path.cwd() / out
        generate_manifest(ed, out)
    elif args.command == "verify":
        ed = Path(args.export_dir).resolve()
        mf = Path(args.manifest)
        if not mf.is_absolute():
            mf = Path.cwd() / mf
        ok = verify_manifest(ed, mf)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
