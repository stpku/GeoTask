#!/usr/bin/env python3
"""Generate and verify SHA-256 manifest for public export or Git tree.

Usage:
    # Filesystem export mode
    python .release/hash_public_export.py generate EXPORT_DIR [OUTPUT]
    python .release/hash_public_export.py verify EXPORT_DIR MANIFEST

    # Git tree mode (CI-safe, platform-independent)
    python .release/hash_public_export.py generate-git REPO_DIR OUTPUT [--ref HEAD]
    python .release/hash_public_export.py verify-git REPO_DIR MANIFEST [--ref HEAD]

Git tree mode reads committed blob bytes via `git show <ref>:<path>`.
This avoids platform-specific LF/CRLF working-tree differences — the
hash reflects the canonical committed content regardless of checkout EOL.

Does NOT access network. Excludes dist/, egg-info, pycache, .git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

EXCLUDE_DIRS = {".git", "dist", "build", ".egg-info", "__pycache__", ".pytest_cache"}


def _excluded(rel_path: str) -> bool:
    """Check if a relative path should be excluded from hash tracking."""
    return rel_path.endswith(".sha256.json") or rel_path.endswith("_report.txt")


def _excluded_dir(dirname: str) -> bool:
    """Return True if this directory should be excluded from walking."""
    return dirname in EXCLUDE_DIRS or dirname.endswith(".egg-info")


def _bypass_stdin(text: str) -> None:
    """Write text to stderr to avoid interfering with pipe-based authentication."""
    sys.stderr.write(text)
    sys.stderr.flush()


# -- Filesystem export mode

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
    """Verify all filesystem files match the manifest."""
    with open(manifest_path, encoding="utf-8") as fh:
        expected = json.load(fh)

    expected_map = {e["path"]: e for e in expected}
    errors = []

    seen = set()
    for e in expected:
        if e["path"] in seen:
            errors.append(f"Duplicate path in manifest: {e['path']}")
        seen.add(e["path"])

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
            errors.append(f"Size mismatch: {entry['path']} (expected {entry['size']}, got {actual_size})")

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


# -- Git tree mode (platform-independent)

def _git_files(repo_dir: Path, ref: str) -> list[str]:
    """Return sorted list of tracked file paths in the given ref."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", ref],
        capture_output=True, text=True, cwd=str(repo_dir),
    )
    if result.returncode != 0:
        raise RuntimeError(f"git ls-tree failed: {result.stderr.strip()}")
    paths = [p for p in result.stdout.split("\0") if p]
    return sorted(p for p in paths if not _excluded_dir_from_path(p) and not _excluded(p))


def _excluded_dir_from_path(rel: str) -> bool:
    """Check if any segment of the path is an excluded directory."""
    parts = rel.replace("\\", "/").split("/")
    return any(_excluded_dir(p) for p in parts)


def _git_blob_bytes(repo_dir: Path, ref: str, path: str) -> bytes:
    """Read blob bytes for a path at a given ref."""
    spec = f"{ref}:{path}"
    result = subprocess.run(
        ["git", "show", spec],
        capture_output=True, cwd=str(repo_dir),
    )
    if result.returncode != 0:
        raise RuntimeError(f"git show {spec} failed: {result.stderr.strip()}")
    return result.stdout


def generate_git_manifest(repo_dir: Path, output_path: Path, ref: str = "HEAD") -> dict:
    """Generate SHA-256 manifest from committed Git blob bytes."""
    if not (repo_dir / ".git").exists():
        raise RuntimeError(f"Not a Git repository: {repo_dir}")

    files = _git_files(repo_dir, ref)
    manifest: list[dict] = []

    for path in files:
        blob = _git_blob_bytes(repo_dir, ref, path)
        sha = hashlib.sha256(blob).hexdigest()
        size = len(blob)
        manifest.append({"path": path, "size": size, "sha256": sha})

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print(f"Generated {output_path} from git:{ref} ({len(manifest)} files)")
    return {"count": len(manifest), "path": str(output_path)}


def verify_git_manifest(repo_dir: Path, manifest_path: Path, ref: str = "HEAD") -> bool:
    """Verify committed Git blob bytes match the manifest."""
    if not (repo_dir / ".git").exists():
        print("ERROR: Not a Git repository")
        return False

    with open(manifest_path, encoding="utf-8") as fh:
        expected = json.load(fh)

    expected_map = {e["path"]: e for e in expected}
    actual_files = set(_git_files(repo_dir, ref))
    errors = []

    # Check for duplicate paths
    seen = set()
    for e in expected:
        if e["path"] in seen:
            errors.append(f"Duplicate path in manifest: {e['path']}")
        seen.add(e["path"])

    # Check each manifest entry against blob
    for entry in expected:
        if entry["path"] not in actual_files:
            errors.append(f"File not in git tree: {entry['path']}")
            continue
        blob = _git_blob_bytes(repo_dir, ref, entry["path"])
        actual_sha = hashlib.sha256(blob).hexdigest()
        if actual_sha != entry["sha256"]:
            errors.append(f"SHA-256 mismatch: {entry['path']}")
        actual_size = len(blob)
        if actual_size != entry["size"]:
            errors.append(f"Size mismatch: {entry['path']} (expected {entry['size']}, got {actual_size})")

    # Check for untracked (in git but not in manifest)
    for path in actual_files:
        if path not in expected_map:
            errors.append(f"Untracked in manifest: {path}")

    if errors:
        print(f"\nHASH VERIFY FAILED — {len(errors)} issue(s):\n")
        for err in errors:
            print(f"  [FAIL] {err}")
        return False

    print(f"\n[PASS] Git hash verify — {len(expected)} files match git:{ref} blobs.\n")
    return True


# -- Main

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate/verify SHA-256 manifest (filesystem or git-tree mode)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate from filesystem directory")
    gen.add_argument("export_dir", type=str)
    gen.add_argument("output", type=str, nargs="?", default="public-files.sha256.json")

    ver = sub.add_parser("verify", help="Verify against filesystem directory")
    ver.add_argument("export_dir", type=str)
    ver.add_argument("manifest", type=str, default="public-files.sha256.json")

    ggen = sub.add_parser("generate-git", help="Generate from committed Git blobs")
    ggen.add_argument("repo_dir", type=str)
    ggen.add_argument("output", type=str, nargs="?", default="public-files.sha256.json")
    ggen.add_argument("--ref", type=str, default="HEAD", help="Git ref (default: HEAD)")

    gver = sub.add_parser("verify-git", help="Verify against committed Git blobs")
    gver.add_argument("repo_dir", type=str)
    gver.add_argument("manifest", type=str, default="public-files.sha256.json")
    gver.add_argument("--ref", type=str, default="HEAD", help="Git ref (default: HEAD)")

    args = parser.parse_args()

    try:
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
        elif args.command == "generate-git":
            rd = Path(args.repo_dir).resolve()
            out = Path(args.output)
            if not out.is_absolute():
                out = Path.cwd() / out
            generate_git_manifest(rd, out, args.ref)
        elif args.command == "verify-git":
            rd = Path(args.repo_dir).resolve()
            mf = Path(args.manifest)
            if not mf.is_absolute():
                mf = Path.cwd() / mf
            ok = verify_git_manifest(rd, mf, args.ref)
            sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
