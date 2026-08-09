from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCANNER_PATH = ROOT / ".release" / "scan_public_identity.py"
PRIVATE_DENYLIST = ROOT / ".release" / "private-public-identity-denylist.txt"
MANIFEST = ROOT / ".release" / "public-manifest.yaml"

_spec = importlib.util.spec_from_file_location("scan_public_identity", SCANNER_PATH)
assert _spec and _spec.loader
scanner = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = scanner
_spec.loader.exec_module(scanner)


def test_public_identity_scanner_allows_safe_export(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(scanner, "_PROTECTED_HASHES", set())
    monkeypatch.setattr(scanner, "PRIVATE_DENYLIST", tmp_path / "missing-private-denylist.txt")
    (tmp_path / "README.md").write_text("GeoTask Core public-safe content\n", encoding="utf-8")

    assert scanner.scan(tmp_path) == []


def test_public_identity_scanner_blocks_hashed_identifier_without_echoing_it(
    tmp_path: Path, monkeypatch
) -> None:
    protected = "internal-demo-marker"
    monkeypatch.setattr(scanner, "_PROTECTED_HASHES", {scanner._fingerprint(protected)})
    monkeypatch.setattr(scanner, "PRIVATE_DENYLIST", tmp_path / "missing-private-denylist.txt")
    (tmp_path / "example.md").write_text(f"candidate {protected} must not ship\n", encoding="utf-8")

    findings = scanner.scan(tmp_path)

    assert len(findings) == 1
    assert findings[0].startswith("PRIVATE_IDENTITY: example.md:1")
    assert protected not in findings[0]


def test_source_private_denylist_is_enforced_but_not_publicly_exported(
    tmp_path: Path, monkeypatch
) -> None:
    protected = "source-private-demo-marker"
    private_file = tmp_path / "private-denylist.txt"
    private_file.write_text(protected + "\n", encoding="utf-8")
    monkeypatch.setattr(scanner, "_PROTECTED_HASHES", set())
    monkeypatch.setattr(scanner, "PRIVATE_DENYLIST", private_file)
    (tmp_path / "example.md").write_text(protected + "\n", encoding="utf-8")

    assert scanner.scan(tmp_path)

    manifest_text = MANIFEST.read_text(encoding="utf-8")
    assert '.release/scan_public_identity.py' in manifest_text
    assert '.release/private-public-identity-denylist.txt' not in manifest_text
    assert 'docs/architecture_decisions/**' not in manifest_text
