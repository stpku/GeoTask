import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_SCRIPT = ROOT / ".release" / "release_public.py"
HASH_SCRIPT = ROOT / ".release" / "hash_public_export.py"


def _load_hash_module():
    spec = importlib.util.spec_from_file_location("hash_public_export", HASH_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_boundary_summary_is_not_nested_in_tree_walk() -> None:
    """The release pre-check should report its summary once, not once per file."""
    source = RELEASE_SCRIPT.read_text(encoding="utf-8")
    summary = "Boundary check complete — forbidden paths handled by export exclude"

    assert "os.walk(PROJECT_ROOT)" not in source
    assert source.count(summary) == 1


def test_hash_manifest_normalizes_utf8_line_endings(tmp_path: Path) -> None:
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    sample = export_dir / "sample.md"
    sample.write_bytes(b"alpha\r\nbeta\r\n")
    manifest_path = export_dir / "public-files.sha256.json"
    hash_module = _load_hash_module()

    hash_module.generate_manifest(export_dir, manifest_path)
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    canonical = b"alpha\nbeta\n"

    assert entries == [
        {
            "path": "sample.md",
            "size": len(canonical),
            "sha256": hashlib.sha256(canonical).hexdigest(),
        }
    ]

    sample.write_bytes(canonical)
    assert hash_module.verify_manifest(export_dir, manifest_path) is True
