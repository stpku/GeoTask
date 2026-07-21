"""Architecture boundary tests — prevent cross-layer imports.

Each test scans the AST of a source file (or directory) and asserts that
forbidden import patterns are absent.
"""

import ast
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
CORE = SRC / "geotask_core"
V1 = CORE / "v1"


def _get_import_strings(filepath: Path) -> set[str]:
    """Return all fully-qualified module names imported by *filepath*."""
    tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])  # top-level module
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def _get_full_import_strings(filepath: Path) -> set[str]:
    """Return all fully-qualified ``from X import Y`` module strings."""
    tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _python_files(root: Path) -> list[Path]:
    """Return all ``.py`` files under *root* (non-recursive for single files)."""
    if root.is_file():
        return [root]
    return sorted(root.rglob("*.py"))


# ── Core vs Domain Packs ───────────────────────────────────────────────────


def test_core_does_not_import_domain_packs():
    """geotask_core must not import from geotask" + "_domain_packs."""
    for py in _python_files(CORE):
        imports = _get_import_strings(py)
        # Check both top-level module and subpackage
        assert (
            "geotask_domain_packs" not in imports
        ), f"{py.relative_to(SRC)} imports geotask_domain_packs"


def test_core_does_not_import_runtime_impl():
    """geotask_core must not import geotask_runtime mocks."""
    for py in _python_files(CORE):
        imports = _get_full_import_strings(py)
        # Allow geotask_runtime if it's only a stdlib-like name,
        # but block any actual import from geotask_runtime
        for imp in imports:
            assert not imp.startswith("geotask_runtime"), (
                f"{py.relative_to(SRC)} imports from geotask_runtime: {imp}"
            )


# ── v1 modules vs compat ──────────────────────────────────────────────────


def test_v1_does_not_import_legacy_compat():
    """v1 modules must not import from geotask_core.compat."""
    for py in _python_files(V1):
        imports = _get_full_import_strings(py)
        for imp in imports:
            assert not imp.startswith("geotask_core.compat"), (
                f"{py.relative_to(SRC)} imports from compat: {imp}"
            )


# ── ir.py vs executor.py ──────────────────────────────────────────────────


def test_ir_does_not_import_executor():
    """ir.py must not import from executor.py."""
    ir_path = V1 / "ir.py"
    imports = _get_full_import_strings(ir_path)
    for imp in imports:
        assert "executor" not in imp.lower(), (
            f"ir.py imports from executor: {imp}"
        )


# ── validator.py vs runner.py ────────────────────────────────────────────


def test_validator_does_not_import_runner():
    """validator.py must not import from runner.py."""
    val_path = V1 / "validator.py"
    imports = _get_full_import_strings(val_path)
    for imp in imports:
        assert "runner" not in imp.lower(), (
            f"validator.py imports from runner: {imp}"
        )


# ── Operator modules vs cli.py ────────────────────────────────────────────


def test_operators_do_not_import_cli():
    """Operator modules must not import from cli.py."""
    operator_modules = [
        V1 / "operator_contracts.py",
        CORE / "ops.py",
        CORE / "operator_registry.py",
    ]
    for mod in operator_modules:
        if not mod.exists():
            continue
        imports = _get_full_import_strings(mod)
        for imp in imports:
            assert "cli" not in imp.lower(), (
                f"{mod.relative_to(SRC)} imports from cli: {imp}"
            )


# ── Core vs patent_evidence ────────────────────────────────────────────────


def test_public_modules_do_not_import_patent_evidence():
    """src/geotask_core must not import patent_evidence."""
    for py in _python_files(CORE):
        imports = _get_full_import_strings(py)
        for imp in imports:
            assert not imp.startswith("patent_evidence"), (
                f"{py.relative_to(SRC)} imports patent_evidence: {imp}"
            )
