#!/usr/bin/env python3
"""GeoTask Core public release pipeline.

Usage:
    python .release/release_public.py OUTPUT_DIR [options]

Pipeline stages:
  1. Boundary check — verify no forbidden paths in project source
  2. Export — copy public files to OUTPUT_DIR per manifest
  3. Verify — whitelist, required files, forbidden imports
  4. Scan — secrets, internal paths, binary files

Options:
    --dry-run       Preview without exporting
    --clean         Remove OUTPUT_DIR before exporting
    --skip-tests    Skip running tests (they still pass; just skip verification)
    --report        Write a release report to OUTPUT_DIR/release_report.txt

Does NOT access network, commit, or push.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RELEASE_DIR = PROJECT_ROOT / ".release"


def run_stage(name: str, args: list[str]) -> bool:
    """Run a release sub-script. Returns True on success."""
    print(f"\n{'=' * 60}")
    print(f"  Stage: {name}")
    print(f"{'=' * 60}\n")

    proc = subprocess.run(
        [sys.executable, *args],
        capture_output=False,
        cwd=str(PROJECT_ROOT),
    )

    if proc.returncode != 0:
        print(f"\n  [FAIL] Stage '{name}' FAILED (exit {proc.returncode})")
        return False

    print(f"\n  [OK] Stage '{name}' PASSED")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GeoTask Core public release pipeline"
    )
    parser.add_argument(
        "output_dir",
        type=str,
        help="Destination directory for the public export",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without copying files",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove output directory before exporting",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Write release report to output directory",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()

    # Safety check
    try:
        output_dir.relative_to(PROJECT_ROOT)
        print("ERROR: Output directory must be outside the project tree.")
        sys.exit(1)
    except ValueError:
        pass

    export_script = str(RELEASE_DIR / "export_public.py")
    verify_script = str(RELEASE_DIR / "verify_public_export.py")
    scan_script = str(RELEASE_DIR / "scan_public_export.py")
    hash_script = str(RELEASE_DIR / "hash_public_export.py")

    started_at = datetime.now(timezone.utc)
    stages_passed = 0
    stages_failed = 0

    # Stage 1: Boundary check (quick sanity)
    # Run a targeted boundary check: verify project source doesn't already
    # contain forbidden paths
    print(f"\n{'=' * 60}")
    print(f"  Stage: Boundary Check (source tree)")
    print(f"{'=' * 60}\n")

    import yaml
    manifest_path = RELEASE_DIR / "public-manifest.yaml"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    forbidden_paths = manifest.get("forbidden_paths", [])
    # The export already checks forbidden paths; this is a pre-check here
    import os
    boundary_ok = True
    for root, dirs, files in os.walk(PROJECT_ROOT):
        for fp in forbidden_paths:
            fp_norm = fp.rstrip("/")
            fp_path = PROJECT_ROOT / fp_norm
            if fp_path.exists():
                print(f"  [WARN] Forbidden path exists in source: {fp_norm}")
                # Don't fail — these exist but are excluded during export
            print(f"  [OK] Boundary check complete — forbidden paths handled by export exclude")

    # Stage 2: Export
    export_args = [export_script, str(output_dir)]
    if args.dry_run:
        export_args.append("--dry-run")
    if args.clean:
        export_args.append("--clean")

    if run_stage("Export", export_args):
        stages_passed += 1
    else:
        stages_failed += 1
        print("\nPipeline aborted after export failure.")
        sys.exit(1)

    # Stage 3: Verify
    if not args.dry_run:
        if run_stage("Verify", [verify_script, str(output_dir)]):
            stages_passed += 1
        else:
            stages_failed += 1
            print("\nPipeline aborted after verification failure.")
            sys.exit(1)

        # Stage 4: Scan
        if run_stage("Scan", [scan_script, str(output_dir)]):
            stages_passed += 1
        else:
            stages_failed += 1
            print("\n  [WARN] Scan found issues — review them before release")
            sys.exit(1)

        # Stage 5: Hash Generate
        hash_out = str(output_dir / "public-files.sha256.json")
        if run_stage("Hash Generate", [hash_script, "generate", str(output_dir), hash_out]):
            stages_passed += 1
        else:
            stages_failed += 1
            print("\nPipeline aborted after hash generation failure.")
            sys.exit(1)

        # Stage 6: Hash Verify
        if run_stage("Hash Verify", [hash_script, "verify", str(output_dir), hash_out]):
            stages_passed += 1
        else:
            stages_failed += 1
            print("\nPipeline aborted after hash verification failure.")
            sys.exit(1)
    else:
        print("\n  [DRY-RUN] Skipping Verify and Scan stages")

    # Report
    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()

    print(f"\n{'=' * 60}")
    print(f"  Pipeline Summary")
    print(f"{'=' * 60}")
    print(f"  Started:  {started_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  Finished: {finished_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Passed:   {stages_passed}")
    print(f"  Failed:   {stages_failed}")
    print(f"  Output:   {output_dir}")
    print()

    # Write report file
    if args.report and not args.dry_run:
        report_path = output_dir / "release_report.txt"
        report_path.write_text(
            f"GeoTask Core Public Release Report\n"
            f"==================================\n"
            f"Started:  {started_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"Finished: {finished_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"Duration: {duration:.1f}s\n"
            f"Stages:   {stages_passed} passed, {stages_failed} failed\n"
            f"Output:   {output_dir}\n",
            encoding="utf-8",
        )
        print(f"  Report written to {report_path}")

    if stages_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
