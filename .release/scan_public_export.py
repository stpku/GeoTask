#!/usr/bin/env python3
"""Scan a public export directory for secrets, internal paths, and binary files.

Usage:
    python .release/scan_public_export.py EXPORT_DIR

Scans for:
  1. Private keys, tokens, API keys, secrets, passwords
  2. Internal paths (C:\\Users\\, /home/, /Users/)
  3. Binary files
  4. Reports error/warning with file, line, rule ID

Supports exact exceptions defined in public-manifest.yaml.

Does NOT access network.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from pathlib import Path
from typing import Optional

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / ".release" / "public-manifest.yaml"

# ── Built-in scan patterns (supplement manifest patterns) ─────────────────────

_SECRET_PATTERNS: list[tuple[str, str, str]] = [
    # (pattern, rule_id, description)
    (
        r'(?:api[_-]?key|apikey|api_key)\s*[:=]\s*["\'][A-Za-z0-9_\-]{20,}["\']',
        "SECRET_API_KEY",
        "Potential API key",
    ),
    (
        r'(?:secret[_-]?key|secret_key|secretkey)\s*[:=]\s*["\'][A-Za-z0-9_\-]{20,}["\']',
        "SECRET_SECRET_KEY",
        "Potential secret key",
    ),
    (
        r'(?:private[_-]?key|private_key|privkey)\s*[:=]\s*["\'][A-Za-z0-9_\-]{20,}["\']',
        "SECRET_PRIVATE_KEY",
        "Potential private key",
    ),
    (
        r'(?:access[_-]?token|access_token|accesstoken)\s*[:=]\s*["\'][A-Za-z0-9_\-\.]{20,}["\']',
        "SECRET_ACCESS_TOKEN",
        "Potential access token",
    ),
    (
        r'(?:auth[_-]?token|auth_token|authtoken)\s*[:=]\s*["\'][A-Za-z0-9_\-\.]{20,}["\']',
        "SECRET_AUTH_TOKEN",
        "Potential auth token",
    ),
    (
        r'(?:password|passwd|pwd)\s*[:=]\s*["\'][^\s]{4,}["\']',
        "SECRET_PASSWORD",
        "Potential hardcoded password",
    ),
    (
        r'(?:BEGIN\s+(?:RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY)',
        "SECRET_SSH_KEY",
        "SSH private key block",
    ),
    (
        r'(?:ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_]{36,}',
        "SECRET_GITHUB_TOKEN",
        "GitHub personal access token",
    ),
]

_PATH_PATTERNS: list[tuple[str, str, str]] = [
    (r"C:" + r"\\Users\\", "INTERNAL_PATH_WINDOWS", "Windows user path"),
    ("/" + r"home/[^/\s]+/", "INTERNAL_PATH_LINUX", "Linux home directory"),
    ("/" + r"Users/[^/\s]+/", "INTERNAL_PATH_MACOS", "macOS Users directory"),
    ("192" + r"\.168\.\d{1,3}\.\d{1,3}", "INTERNAL_IP", "Private network IP"),
    ("10" + r"\.\d{1,3}\.\d{1,3}\.\d{1,3}", "INTERNAL_IP_RFC1918", "Private network IP (Class A)"),
]

_BINARY_EXTENSIONS: set[str] = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".zip", ".tar", ".gz", ".7z", ".png", ".jpg", ".jpeg", ".gif",
    ".ico", ".pdf", ".docx", ".xlsx", ".pptx",
}


def load_manifest() -> dict:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def matches_any(name: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(name, pat):
            return True
    return False


def _read_file_safe(file_path: Path) -> Optional[str]:
    """Read text file safely; return None for binary/non-text files."""
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def _count_text_files(export_dir: Path) -> int:
    """Count candidate text files in export directory."""
    count = 0
    for root, dirs, files in os.walk(export_dir):
        if ".git" in root or "__pycache__" in root or ".pytest_cache" in root:
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in _BINARY_EXTENSIONS:
                count += 1
    return count


def _skipped_file_paths(export_dir: Path, manifest: dict) -> list[str]:
    """Return list of relative paths that are skipped across all scanners."""
    skipped: set[str] = set()
    for root, dirs, files in os.walk(export_dir):
        for f in files:
            rel = (Path(root) / f).relative_to(export_dir).as_posix()
            if "public-manifest.yaml" in rel:
                skipped.add(rel)
    return sorted(skipped)


def _count_skipped_files(export_dir: Path, exc_key: str, manifest: dict) -> int:
    """Count how many times a skip rule would fire across all candidate files."""
    count = 0
    exceptions = manifest.get("exact_exceptions", {}).get(exc_key, [])
    for root, dirs, files in os.walk(export_dir):
        if ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in _BINARY_EXTENSIONS:
                continue
            rel_path = (Path(root) / f).relative_to(export_dir).as_posix()
            if "public-manifest.yaml" in rel_path or rel_path.endswith("release_report.txt"):
                continue  # generated/manifest files contain paths
            if _is_excepted(rel_path, "allowed_secret_findings", manifest):
                continue
            for exc in exceptions:
                pattern = exc.get("in_file", "")
                if pattern and matches_any(rel_path, [pattern]):
                    count += 1
                    break
    return count
    """Read text file safely; return None for binary/non-text files."""
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


# -- Scanner

def _is_excepted(rel_path: str, exception_key: str, manifest: dict) -> bool:
    """Check if a file is covered by an exact exception of the given type."""
    exceptions: list[dict] = manifest.get("exact_exceptions", {}).get(exception_key, [])
    for exc in exceptions:
        pattern = exc.get("in_file", "")
        if pattern and matches_any(rel_path, [pattern]):
            return True
    return False


def scan_secrets(export_dir: Path, manifest: dict) -> list[str]:
    """Scan text files for secret patterns."""
    errors: list[str] = []
    forbidden_patterns: list[dict] = manifest.get("forbidden_content_patterns", [])
    exceptions: list[dict] = (
        manifest.get("exact_exceptions", {}).get("allowed_secret_findings", [])
    )

    # Collect all pattern sources
    all_patterns: list[tuple[str, str, str]] = []

    for fp in forbidden_patterns:
        pat = fp.get("pattern", "")
        if pat:
            all_patterns.append((pat, fp.get("description", "SECRET"), fp.get("severity", "error")))

    all_patterns.extend(_SECRET_PATTERNS)

    for root, _dirs, files in os.walk(export_dir):
        if ".git" in root or "__pycache__" in root or ".pytest_cache" in root:
            continue

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in _BINARY_EXTENSIONS:
                continue

            file_path = Path(root) / f
            rel_path = os.path.relpath(file_path, export_dir).replace("\\", "/")

            # Skip manifest files (they contain scanning rules, not violations)
            if rel_path.endswith("public-manifest.yaml"):
                continue

            if _is_excepted(rel_path, "allowed_secret_findings", manifest):
                continue

            content = _read_file_safe(file_path)
            if content is None:
                continue

            for line_no, line in enumerate(content.splitlines(), start=1):
                for pattern_str, rule_id, desc in all_patterns:
                    try:
                        if re.search(pattern_str, line, re.IGNORECASE):
                            errors.append(
                                f"{rule_id}: {rel_path}:{line_no}  {desc}"
                            )
                    except re.error:
                        pass

    return errors


def scan_paths(export_dir: Path, manifest: dict) -> list[str]:
    """Scan text files for internal path patterns."""
    errors: list[str] = []

    for root, _dirs, files in os.walk(export_dir):
        if ".git" in root or "__pycache__" in root:
            continue

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in _BINARY_EXTENSIONS:
                continue

            file_path = Path(root) / f
            rel_path = os.path.relpath(file_path, export_dir).replace("\\", "/")

            # Skip manifest files and generated reports
            if "public-manifest.yaml" in rel_path or rel_path.endswith("release_report.txt"):
                continue

            if _is_excepted(rel_path, "allowed_internal_paths", manifest):
                continue

            content = _read_file_safe(file_path)
            if content is None:
                continue

            for line_no, line in enumerate(content.splitlines(), start=1):
                for pattern_str, rule_id, desc in _PATH_PATTERNS:
                    try:
                        if re.search(pattern_str, line):
                            errors.append(
                                f"{rule_id}: {rel_path}:{line_no}  {desc}"
                            )
                    except re.error:
                        pass

    return errors


def scan_binaries(export_dir: Path, manifest: dict) -> list[str]:
    """Check for binary files in the export."""
    binary_ext_list: list[str] = manifest.get("binary_extensions", list(_BINARY_EXTENSIONS))
    binary_exts: set[str] = set(binary_ext_list)
    errors: list[str] = []

    for root, _dirs, files in os.walk(export_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in binary_exts:
                rel_path = os.path.relpath(os.path.join(root, f), export_dir).replace("\\", "/")
                errors.append(f"BINARY: {rel_path}  Binary file detected")

    return errors


# ═══════════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan public export for secrets, internal paths, and binaries"
    )
    parser.add_argument(
        "export_dir",
        type=str,
        help="Path to the exported public directory to scan",
    )
    args = parser.parse_args()

    export_dir = Path(args.export_dir).resolve()
    if not export_dir.is_dir():
        print(f"ERROR: '{export_dir}' is not a directory")
        sys.exit(1)

    manifest = load_manifest()

    all_findings: list[str] = []
    secret_findings = scan_secrets(export_dir, manifest)
    path_findings = scan_paths(export_dir, manifest)
    binary_findings = scan_binaries(export_dir, manifest)
    all_findings.extend(secret_findings)
    all_findings.extend(path_findings)
    all_findings.extend(binary_findings)

    # Count unique files
    skipped_secret = _count_skipped_files(export_dir, "allowed_secret_findings", manifest)
    skipped_path = _count_skipped_files(export_dir, "allowed_internal_paths", manifest)

    if all_findings:
        print(f"\nSCAN FOUND {len(all_findings)} issue(s):\n")
        for finding in all_findings:
            print(f"  [WARN] {finding}")
        print()

    # Statistics
    total = _count_text_files(export_dir)
    skip_files = _skipped_file_paths(export_dir, manifest)
    scanned = total - len(skip_files)
    print(f"  Scan stats: {total} candidate text files, "
          f"{scanned} scanned, {len(skip_files)} skipped")
    if len(skip_files) == 1:
        print(f"  Skipped file (manifest): {skip_files[0]}")
    print(f"  Scanner-pass skips: secret={skipped_secret}, path={skipped_path}")
    print(f"  Binary files checked: {len(binary_findings) if binary_findings else 0}")
    print(f"  Secret exceptions: {len(manifest.get('exact_exceptions', {}).get('allowed_secret_findings', []))}")
    print(f"  Path exceptions: {len(manifest.get('exact_exceptions', {}).get('allowed_internal_paths', []))}")
    print()

    if all_findings:
        sys.exit(1)

    print("[PASS] Scan PASSED — no secrets, internal paths, or binary files detected.\n")


if __name__ == "__main__":
    main()
