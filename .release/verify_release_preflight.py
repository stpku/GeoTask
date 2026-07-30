#!/usr/bin/env python3
"""Verify GeoTask release identity before publishing.

The preflight is local-only and uses the Python standard library. It checks that
package version, release date, Git tag text, changelog, citation metadata,
release notes, Quickstarts, README navigation, and optional wheel/sdist metadata
all describe the same release.

Examples:
    python .release/verify_release_preflight.py --expected-version 0.2.0
    python .release/verify_release_preflight.py \
        --expected-version 0.2.0 --artifacts dist --format json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tarfile
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any


_VERSION_PATTERN = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$', re.MULTILINE)
_STABLE_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def _read_text(path: Path, label: str, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read {label} at {path}: {exc}")
        return ""


def _record_check(
    checks: list[dict[str, object]],
    errors: list[str],
    *,
    name: str,
    valid: bool,
    detail: str,
    error: str,
) -> None:
    checks.append({"name": name, "valid": valid, "detail": detail})
    if not valid:
        errors.append(error)


def _citation_field(text: str, field: str) -> str:
    match = re.search(rf"^{re.escape(field)}:\s*[\"']?([^\n\"']+)[\"']?\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _metadata_version(raw: bytes, label: str, errors: list[str]) -> str:
    try:
        message = BytesParser(policy=policy.default).parsebytes(raw)
    except Exception as exc:  # email parser failures are implementation-specific
        errors.append(f"cannot parse {label}: {exc}")
        return ""
    value = message.get("Version")
    return str(value).strip() if value is not None else ""


def _select_one(
    directory: Path,
    pattern: str,
    label: str,
    errors: list[str],
) -> Path | None:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        errors.append(
            f"expected exactly one {label} matching {pattern!r}, found {len(matches)}"
        )
        return None
    return matches[0]


def _verify_wheel(
    wheel_path: Path,
    version: str,
    checks: list[dict[str, object]],
    errors: list[str],
) -> None:
    expected_prefix = f"geotask_core-{version}-"
    _record_check(
        checks,
        errors,
        name="wheel_filename",
        valid=wheel_path.name.startswith(expected_prefix) and wheel_path.suffix == ".whl",
        detail=wheel_path.name,
        error=(
            f"wheel filename must start with {expected_prefix!r}: {wheel_path.name}"
        ),
    )

    metadata_version = ""
    metadata_path = ""
    try:
        with zipfile.ZipFile(wheel_path) as archive:
            metadata_paths = sorted(
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            )
            if len(metadata_paths) != 1:
                errors.append(
                    "wheel must contain exactly one .dist-info/METADATA file"
                )
            else:
                metadata_path = metadata_paths[0]
                metadata_version = _metadata_version(
                    archive.read(metadata_path), "wheel METADATA", errors
                )
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"cannot read wheel {wheel_path.name}: {exc}")

    expected_metadata_path = f"geotask_core-{version}.dist-info/METADATA"
    _record_check(
        checks,
        errors,
        name="wheel_metadata_path",
        valid=metadata_path == expected_metadata_path,
        detail=metadata_path,
        error=(
            "wheel METADATA path mismatch: "
            f"expected {expected_metadata_path!r}, got {metadata_path!r}"
        ),
    )
    _record_check(
        checks,
        errors,
        name="wheel_metadata_version",
        valid=metadata_version == version,
        detail=metadata_version,
        error=(
            f"wheel METADATA Version mismatch: expected {version!r}, "
            f"got {metadata_version!r}"
        ),
    )


def _verify_sdist(
    sdist_path: Path,
    version: str,
    checks: list[dict[str, object]],
    errors: list[str],
) -> None:
    expected_name = f"geotask_core-{version}.tar.gz"
    _record_check(
        checks,
        errors,
        name="sdist_filename",
        valid=sdist_path.name == expected_name,
        detail=sdist_path.name,
        error=f"sdist filename mismatch: expected {expected_name!r}, got {sdist_path.name!r}",
    )

    expected_root = f"geotask_core-{version}"
    roots: set[str] = set()
    metadata_version = ""
    try:
        with tarfile.open(sdist_path, mode="r:gz") as archive:
            regular = [member for member in archive.getmembers() if member.isfile()]
            roots = {
                Path(member.name).parts[0]
                for member in regular
                if Path(member.name).parts
            }
            metadata_member = archive.getmember(f"{expected_root}/PKG-INFO")
            extracted = archive.extractfile(metadata_member)
            if extracted is not None:
                metadata_version = _metadata_version(
                    extracted.read(), "sdist PKG-INFO", errors
                )
    except (KeyError, OSError, tarfile.TarError) as exc:
        errors.append(f"cannot read sdist {sdist_path.name}: {exc}")

    _record_check(
        checks,
        errors,
        name="sdist_root",
        valid=roots == {expected_root},
        detail=", ".join(sorted(roots)),
        error=(
            f"sdist top-level directory mismatch: expected {expected_root!r}, "
            f"got {sorted(roots)!r}"
        ),
    )
    _record_check(
        checks,
        errors,
        name="sdist_metadata_version",
        valid=metadata_version == version,
        detail=metadata_version,
        error=(
            f"sdist PKG-INFO Version mismatch: expected {version!r}, "
            f"got {metadata_version!r}"
        ),
    )


def verify_release_preflight(
    root: Path,
    *,
    expected_version: str | None = None,
    expected_tag: str | None = None,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    """Verify release identity across source metadata and optional distributions."""

    root = root.resolve()
    checks: list[dict[str, object]] = []
    errors: list[str] = []

    version_source = _read_text(
        root / "src" / "geotask_core" / "_version.py",
        "version source",
        errors,
    )
    match = _VERSION_PATTERN.search(version_source)
    version = match.group(1).strip() if match else ""
    _record_check(
        checks,
        errors,
        name="source_version",
        valid=bool(version) and bool(_STABLE_VERSION_PATTERN.fullmatch(version)),
        detail=version,
        error=(
            "src/geotask_core/_version.py must define one stable X.Y.Z release version"
        ),
    )

    if expected_version is not None:
        _record_check(
            checks,
            errors,
            name="expected_version",
            valid=version == expected_version,
            detail=expected_version,
            error=(
                f"expected release version {expected_version!r}, source declares {version!r}"
            ),
        )

    tag = expected_tag or (f"v{version}" if version else "")
    if expected_tag is not None:
        _record_check(
            checks,
            errors,
            name="expected_tag",
            valid=expected_tag == f"v{version}",
            detail=expected_tag,
            error=(
                f"expected tag must equal 'v' plus package version: {expected_tag!r}"
            ),
        )

    citation = _read_text(root / "CITATION.cff", "CITATION.cff", errors)
    citation_version = _citation_field(citation, "version")
    release_date = _citation_field(citation, "date-released")
    _record_check(
        checks,
        errors,
        name="citation_version",
        valid=citation_version == version,
        detail=citation_version,
        error=(
            f"CITATION.cff version mismatch: expected {version!r}, got {citation_version!r}"
        ),
    )
    _record_check(
        checks,
        errors,
        name="citation_release_date",
        valid=bool(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", release_date)),
        detail=release_date,
        error="CITATION.cff date-released must use YYYY-MM-DD",
    )

    changelog = _read_text(root / "CHANGELOG.md", "CHANGELOG.md", errors)
    changelog_header = f"## [{version}] - {release_date}"
    changelog_link = f"[{version}]: https://github.com/stpku/GeoTask/releases/tag/{tag}"
    _record_check(
        checks,
        errors,
        name="changelog_release",
        valid=changelog_header in changelog and changelog_link in changelog,
        detail=changelog_header,
        error=(
            "CHANGELOG.md must contain the exact release heading and GitHub tag link: "
            f"{changelog_header!r}, {changelog_link!r}"
        ),
    )

    release_slug = version.replace(".", "_").replace("-", "_")
    release_notes_rel = f"docs/release_v{release_slug}.md"
    release_notes = _read_text(
        root / release_notes_rel, release_notes_rel, errors
    )
    release_note_markers = (
        f"# GeoTask Core v{version}",
        f"- **Release date:** {release_date}",
        f"- **Git tag:** `{tag}`",
        f"- **Package version:** `{version}`",
        f"geotask-core=={version}",
    )
    missing_markers = [marker for marker in release_note_markers if marker not in release_notes]
    _record_check(
        checks,
        errors,
        name="release_notes",
        valid=not missing_markers,
        detail=release_notes_rel,
        error=(
            f"{release_notes_rel} is missing release identity markers: "
            + ", ".join(repr(marker) for marker in missing_markers)
        ),
    )

    quickstart_paths = (
        "docs/tutorials/quickstart.md",
        "docs/tutorials/quickstart.zh-CN.md",
    )
    pin = f"python -m pip install --no-cache-dir geotask-core=={version}"
    quickstart_missing: list[str] = []
    for relative in quickstart_paths:
        text = _read_text(root / relative, relative, errors)
        if pin not in text:
            quickstart_missing.append(relative)
    _record_check(
        checks,
        errors,
        name="quickstart_version_pins",
        valid=not quickstart_missing,
        detail=pin,
        error=(
            "Quickstart files must pin the release version; missing in: "
            + ", ".join(quickstart_missing)
        ),
    )

    readme_requirements = {
        "README.md": (f"| GeoTask Core包 | `{version}` |", release_notes_rel),
        "README.en.md": (f"| GeoTask Core package | `{version}` |", release_notes_rel),
        "docs/README.md": (Path(release_notes_rel).name,),
        "docs/README.en.md": (Path(release_notes_rel).name,),
    }
    readme_missing: list[str] = []
    for relative, markers in readme_requirements.items():
        text = _read_text(root / relative, relative, errors)
        if any(marker not in text for marker in markers):
            readme_missing.append(relative)
    _record_check(
        checks,
        errors,
        name="readme_release_navigation",
        valid=not readme_missing,
        detail=release_notes_rel,
        error=(
            "README release version/link mismatch in: " + ", ".join(readme_missing)
        ),
    )

    manifest = _read_text(
        root / ".release" / "public-manifest.yaml",
        "public release manifest",
        errors,
    )
    manifest_entry = f'- "{release_notes_rel}"'
    _record_check(
        checks,
        errors,
        name="public_manifest_release_notes",
        valid=manifest.count(manifest_entry) >= 2,
        detail=release_notes_rel,
        error=(
            f"public-manifest.yaml must include and require {release_notes_rel!r}"
        ),
    )

    pyproject = _read_text(root / "pyproject.toml", "pyproject.toml", errors)
    _record_check(
        checks,
        errors,
        name="dynamic_version_source",
        valid=(
            'dynamic = ["version"]' in pyproject
            and 'version = {attr = "geotask_core._version.__version__"}' in pyproject
        ),
        detail="geotask_core._version.__version__",
        error="pyproject.toml must use geotask_core._version.__version__ as dynamic version",
    )

    wheel_name = ""
    sdist_name = ""
    artifacts_checked = artifact_dir is not None
    if artifact_dir is not None:
        artifact_dir = artifact_dir.resolve()
        wheel_path = _select_one(artifact_dir, "*.whl", "wheel", errors)
        sdist_path = _select_one(artifact_dir, "*.tar.gz", "sdist", errors)
        if wheel_path is not None:
            wheel_name = wheel_path.name
            _verify_wheel(wheel_path, version, checks, errors)
        if sdist_path is not None:
            sdist_name = sdist_path.name
            _verify_sdist(sdist_path, version, checks, errors)

    return {
        "release_preflight": {
            "valid": not errors,
            "version": version,
            "expected_version": expected_version or "",
            "tag": tag,
            "release_date": release_date,
            "release_notes": release_notes_rel,
            "artifacts_checked": artifacts_checked,
            "wheel": wheel_name,
            "sdist": sdist_name,
            "checks": checks,
            "errors": errors,
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repository root (default: current directory)",
    )
    parser.add_argument(
        "--expected-version",
        help="fail unless the repository declares this exact version",
    )
    parser.add_argument(
        "--expected-tag",
        help="expected Git tag text in release metadata (default: v<version>)",
    )
    parser.add_argument(
        "--artifacts",
        type=Path,
        help="directory containing exactly one wheel and one sdist",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="report format (default: text)",
    )
    args = parser.parse_args()

    payload = verify_release_preflight(
        args.root,
        expected_version=args.expected_version,
        expected_tag=args.expected_tag,
        artifact_dir=args.artifacts,
    )
    report = payload["release_preflight"]

    if args.format == "json":
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    elif report["valid"]:
        artifact_text = (
            f", wheel={report['wheel']}, sdist={report['sdist']}"
            if report["artifacts_checked"]
            else ""
        )
        print(
            "[PASS] Release preflight verified: "
            f"version={report['version']}, tag={report['tag']}, "
            f"date={report['release_date']}{artifact_text}"
        )
    else:
        for error in report["errors"]:
            print(f"[FAIL] {error}", file=sys.stderr)

    raise SystemExit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
