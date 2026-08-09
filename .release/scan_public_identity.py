#!/usr/bin/env python3
"""Fail-closed scan for protected employer/internal identity markers in public export.

The public scanner intentionally stores only SHA-256 fingerprints for protected
identifiers. Plaintext protected names may be maintained in the source-private
`.release/private-public-identity-denylist.txt`, which is not part of public export.

The scanner never prints the matched identifier; findings contain only path/line.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIVATE_DENYLIST = PROJECT_ROOT / ".release" / "private-public-identity-denylist.txt"

# Public-safe fingerprints. Do not replace these with plaintext labels.
_PROTECTED_HASHES: set[str] = {
    "05d96884de1836c28a74dcc59736931200c2d8606c5ba705de19dc916222212c",
    "16258ae25d62dee040529b88236ff1d408e310681c03d7bd24969af609549426",
    "18bf91d23949790a9872371d01d575cecfabe40a2041290a1768e775208f3619",
    "234b5b671f805415ff7f3d26e37f78d1e40ea60fdfa5f61dce7624662afa7307",
    "35f34c8626e6b38aa4e3197cb905c6246a8a58be059447c0cbe608016a9bd7c0",
    "45728ac5dd6a6ee9a2b0b59f545f7504a11ffa7837f9e34dd9f9740d03b76ef9",
    "65f388f09efac33d0d229dea70f12d356f8d2762739032ba4e0d53b55d6ae776",
    "82eaaba81d9dcc54deabafe357f46f8668bd9bf13a30f319fb0a6d7874592295",
    "91a6cb49fd37ab64702d935e87569c5fd0e7373ede0219005f6da445b8e5f758",
    "9cb5925c14a5f303ec7f32b9bf52234d84dbcc62c4456b1e588340c6b2919d7f",
    "b81c8201acfc7639be3bd3d7f875ba5ca76e422fa2163cec9dace50662b637a7",
    "ba24fbb6a1213fa2938a93ca888f9a46fcc961030ebad3c5e7c2918bebc8420d",
}

_BINARY_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".zip", ".tar", ".gz", ".7z", ".png", ".jpg", ".jpeg", ".gif",
    ".ico", ".pdf", ".docx", ".xlsx", ".pptx",
}


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.casefold().encode("utf-8")).hexdigest()


def _load_hashes() -> set[str]:
    hashes = set(_PROTECTED_HASHES)
    if not PRIVATE_DENYLIST.is_file():
        return hashes
    for raw in PRIVATE_DENYLIST.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if value and not value.startswith("#"):
            hashes.add(_fingerprint(value))
    return hashes


def _candidates(line: str) -> set[str]:
    candidates = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,63}", line))
    for run in re.findall(r"[\u3400-\u9fff]+", line):
        upper = min(len(run), 16)
        for width in range(2, upper + 1):
            for start in range(len(run) - width + 1):
                candidates.add(run[start : start + width])
    return candidates


def scan(export_dir: Path) -> list[str]:
    protected = _load_hashes()
    findings: list[str] = []
    for root, dirs, files in os.walk(export_dir):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".pytest_cache"}]
        for filename in files:
            if Path(filename).suffix.lower() in _BINARY_EXTENSIONS:
                continue
            path = Path(root) / filename
            rel = path.relative_to(export_dir).as_posix()
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for line_no, line in enumerate(content.splitlines(), start=1):
                if any(_fingerprint(candidate) in protected for candidate in _candidates(line)):
                    findings.append(
                        f"PRIVATE_IDENTITY: {rel}:{line_no}  protected employer/internal identifier"
                    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_dir", type=Path)
    args = parser.parse_args()
    export_dir = args.export_dir.resolve()
    if not export_dir.is_dir():
        print(f"ERROR: '{export_dir}' is not a directory")
        return 1

    findings = scan(export_dir)
    if findings:
        print(f"SCAN FOUND {len(findings)} protected identity finding(s):")
        for finding in findings:
            print(f"  [BLOCK] {finding}")
        return 1

    print("[PASS] Public identity scan passed — no protected employer/internal identifiers detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
