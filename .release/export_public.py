#!/usr/bin/env python3
"""Export public GeoTask Core files according to public-manifest.yaml.

Usage:
    python .release/export_public.py [--dry-run] [--clean] OUTPUT_DIR

Reads ``.release/public-manifest.yaml``, copies include-matched files to
OUTPUT_DIR, respects exclude patterns, and checks forbidden paths.

Does NOT access network, commit, or push.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

import yaml


# ── Globals ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / ".release" / "public-manifest.yaml"


def load_manifest() -> dict:
    """Load and return the public release manifest."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def matches_any(name: str, patterns: list[str]) -> bool:
    """Return True after normalizing Windows and POSIX path separators."""
    normalized_name = name.replace("\\", "/")
    for pattern in patterns:
        normalized_pattern = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized_name, normalized_pattern):
            return True
    return False


def collect_files(manifest: dict) -> list[Path]:
    """Walk the project and collect files matching include/exclude rules."""
    includes: list[str] = manifest.get("include", [])
    excludes: list[str] = manifest.get("exclude", [])
    forbidden: list[str] = manifest.get("forbidden_paths", [])

    collected: dict[str, Path] = {}  # relative_path → absolute Path

    # Walk entire project
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Skip excluded directories in-place
        dirs_to_remove = []
        for d in dirs:
            rel_dir = os.path.relpath(os.path.join(root, d), PROJECT_ROOT).replace("\\", "/")
            if matches_any(rel_dir + "/", excludes) or matches_any(rel_dir, excludes):
                dirs_to_remove.append(d)
                continue
            # Also skip forbidden directories during traversal
            for fp in forbidden:
                fp_norm = fp.rstrip("/")
                if rel_dir == fp_norm or rel_dir.startswith(fp_norm + "/"):
                    dirs_to_remove.append(d)
                    break
        for d in dirs_to_remove:
            dirs.remove(d)

        for f in files:
            abs_path = Path(root) / f
            rel_path = os.path.relpath(abs_path, PROJECT_ROOT).replace("\\", "/")

            # Explicit exclude check
            if matches_any(rel_path, excludes):
                continue

            # Skip forbidden paths silently (they are excluded from export)
            is_forbidden = False
            for fp in forbidden:
                fp_norm = fp.rstrip("/")
                if rel_path == fp_norm or rel_path.startswith(fp_norm + "/"):
                    is_forbidden = True
                    break
            if is_forbidden:
                continue

            # Include check
            if matches_any(rel_path, includes) or matches_any(rel_path + "/", includes):
                collected[rel_path] = abs_path

    return list(collected.values())


def export_files(
    files: list[Path],
    output_dir: Path,
    *,
    dry_run: bool = False,
    clean: bool = False,
) -> tuple[int, int]:
    """Copy collected files to output_dir. Returns (file_count, total_bytes)."""
    if clean and output_dir.exists():
        if dry_run:
            print(f"[DRY-RUN] Would clean: {output_dir}")
        else:
            shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    file_count = 0

    for abs_path in sorted(files):
        rel_path = os.path.relpath(abs_path, PROJECT_ROOT).replace("\\", "/")
        dest = output_dir / rel_path
        file_size = abs_path.stat().st_size
        total_bytes += file_size
        file_count += 1

        if dry_run:
            print(f"[DRY-RUN] {rel_path}  ({_format_size(file_size)})")
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(abs_path, dest)

    return file_count, total_bytes


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    n: float = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export public GeoTask Core files per public-manifest.yaml"
    )
    parser.add_argument(
        "output_dir",
        type=str,
        help="Destination directory for the public export",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which files would be copied without actually copying",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove output directory before exporting",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()

    # Safety: refuse to export into the project tree
    try:
        output_dir.relative_to(PROJECT_ROOT)
        print("ERROR: Output directory must be outside the project tree.")
        sys.exit(1)
    except ValueError:
        pass  # OK — output_dir is outside project root

    manifest = load_manifest()
    files = collect_files(manifest)

    if not files:
        print("WARNING: No files matched the include patterns.")
        sys.exit(1)

    count, total_bytes = export_files(
        files, output_dir, dry_run=args.dry_run, clean=args.clean
    )

    if args.dry_run:
        print(f"\n[DRY-RUN] Would export {count} files, {_format_size(total_bytes)}")
    else:
        print(f"Exported {count} files ({_format_size(total_bytes)}) to {output_dir}")


if __name__ == "__main__":
    main()
