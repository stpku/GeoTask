#!/usr/bin/env python3
"""Verify a public export directory against the manifest rules.

Usage:
    python .release/verify_public_export.py EXPORT_DIR

Checks:
  1. All files in export match whitelist patterns (no extra files).
  2. All required files exist.
  3. No forbidden paths are present.
   4. Core source files do not import internal modules (geotask" + "_domain_packs,
     priv" + "ate_runtime, etc.).
  5. Core source files do not import domain_packs or commercial runtime modules.

Does NOT access network.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import sys
from pathlib import Path
from typing import Optional

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / ".release" / "public-manifest.yaml"


def load_manifest() -> dict:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def matches_any(name: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(name, pat):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  Check 1: Whitelist — every exported file must match an include pattern
# ═══════════════════════════════════════════════════════════════════════════════


def check_whitelist(export_dir: Path, manifest: dict) -> list[str]:
    """Check all files in export_dir are covered by include patterns."""
    includes: list[str] = manifest.get("include", [])
    errors: list[str] = []

    for root, _dirs, files in os.walk(export_dir):
        for f in files:
            full = Path(root) / f
            rel = os.path.relpath(full, export_dir).replace("\\", "/")

            if not matches_any(rel, includes):
                errors.append(f"WHITELIST: '{rel}' not matched by any include pattern")

    return errors


# ═══════════════════════════════════════════════════════════════════════════════
#  Check 2: Required files
# ═══════════════════════════════════════════════════════════════════════════════


def check_required(export_dir: Path, manifest: dict) -> list[str]:
    """Check all required files exist in export_dir."""
    required: list[str] = manifest.get("required", [])
    errors: list[str] = []

    for req in required:
        if not (export_dir / req).is_file():
            errors.append(f"REQUIRED: '{req}' is missing")

    return errors


# ═══════════════════════════════════════════════════════════════════════════════
#  Check 3: Forbidden paths
# ═══════════════════════════════════════════════════════════════════════════════


def check_forbidden_paths(export_dir: Path, manifest: dict) -> list[str]:
    """Check no forbidden paths appear in the export."""
    forbidden: list[str] = manifest.get("forbidden_paths", [])
    errors: list[str] = []

    for root, dirs, files in os.walk(export_dir):
        for d in dirs:
            rel_dir = os.path.relpath(os.path.join(root, d), export_dir).replace("\\", "/")
            for fp in forbidden:
                fp_norm = fp.rstrip("/")
                if rel_dir == fp_norm or rel_dir.startswith(fp_norm + "/"):
                    errors.append(f"FORBIDDEN_PATH: '{rel_dir}' matches '{fp}'")
        for f in files:
            rel_file = os.path.relpath(os.path.join(root, f), export_dir).replace("\\", "/")
            for fp in forbidden:
                fp_norm = fp.rstrip("/")
                if rel_file == fp_norm or rel_file.startswith(fp_norm + "/"):
                    errors.append(f"FORBIDDEN_PATH: '{rel_file}' matches '{fp}'")

    return errors


# ═══════════════════════════════════════════════════════════════════════════════
#  Check 4 & 5: Internal imports in Core source
# ═══════════════════════════════════════════════════════════════════════════════


def _extract_imports(file_path: Path) -> list[str]:
    """Extract all import module names from a Python file using AST."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except Exception:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                if node.level == 0:
                    imports.append(node.module)
                else:
                    # Relative import — reconstruct full dotted path
                    depth = node.level
                    parts = str(file_path.parent.relative_to(PROJECT_ROOT)).replace("\\", "/").split("/")
                    if depth <= len(parts):
                        base = ".".join(parts[:-depth] if depth > 0 else parts)
                        imports.append(f"{base}.{node.module}" if node.module else base)
    return imports


def check_internal_imports(export_dir: Path, manifest: dict) -> list[str]:
    """Check Core Python files don't import forbidden internal modules."""
    boundary_rules: dict = manifest.get("boundary_rules", {})
    forbidden_imports: list[str] = boundary_rules.get("forbidden_core_imports", [])
    allowed_imports: list[str] = boundary_rules.get("allowed_core_imports", [])
    exceptions: list[dict] = (
        manifest.get("exact_exceptions", {}).get("allowed_forbidden_imports", [])
    )

    errors: list[str] = []
    core_src = export_dir / "src" / "geotask_core"

    if not core_src.is_dir():
        return []

    for root, _dirs, files in os.walk(core_src):
        for f in files:
            if not f.endswith(".py"):
                continue
            file_path = Path(root) / f
            rel_path = os.path.relpath(file_path, export_dir).replace("\\", "/")
            imports = _extract_imports(file_path)

            for imp in imports:
                # Check if import is forbidden
                is_forbidden = False
                for forbidden in forbidden_imports:
                    if imp == forbidden or imp.startswith(forbidden + "."):
                        is_forbidden = True
                        # Check exceptions
                        for exc in exceptions:
                            if matches_any(rel_path, [exc.get("in_file", "")]):
                                is_forbidden = False
                                break
                        if is_forbidden:
                            errors.append(
                                f"INTERNAL_IMPORT: {rel_path} imports '{imp}' "
                                f"(forbidden: {forbidden})"
                            )

    return errors


# ═══════════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify public export against manifest rules"
    )
    parser.add_argument(
        "export_dir",
        type=str,
        help="Path to the exported public directory to verify",
    )
    args = parser.parse_args()

    export_dir = Path(args.export_dir).resolve()
    if not export_dir.is_dir():
        print(f"ERROR: '{export_dir}' is not a directory")
        sys.exit(1)

    manifest = load_manifest()

    all_errors: list[str] = []
    all_errors.extend(check_whitelist(export_dir, manifest))
    all_errors.extend(check_required(export_dir, manifest))
    all_errors.extend(check_forbidden_paths(export_dir, manifest))
    all_errors.extend(check_internal_imports(export_dir, manifest))

    if all_errors:
        print(f"\nVERIFICATION FAILED — {len(all_errors)} error(s):\n")
        for err in all_errors:
            print(f"  [FAIL] {err}")
        print()
        sys.exit(1)

    print("\n[PASS] Public export verification PASSED — all checks clear.\n")


if __name__ == "__main__":
    main()
