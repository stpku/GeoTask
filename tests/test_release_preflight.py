"""Release identity preflight regression tests."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_PATH = ROOT / ".release" / "verify_release_preflight.py"
VERSION = "0.2.0"


def _load_preflight():
    spec = importlib.util.spec_from_file_location(
        "verify_release_preflight", PREFLIGHT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_tar_member(archive: tarfile.TarFile, name: str, raw: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(raw)
    archive.addfile(info, io.BytesIO(raw))


def _create_artifacts(
    dist_dir: Path,
    *,
    wheel_metadata_version: str = VERSION,
    sdist_metadata_version: str = VERSION,
) -> None:
    dist_dir.mkdir(parents=True)
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: geotask-core\n"
        f"Version: {wheel_metadata_version}\n"
        "\n"
    ).encode("utf-8")
    wheel_path = dist_dir / f"geotask_core-{VERSION}-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, mode="w") as archive:
        archive.writestr(
            f"geotask_core-{VERSION}.dist-info/METADATA",
            metadata,
        )

    sdist_metadata = (
        "Metadata-Version: 2.4\n"
        "Name: geotask-core\n"
        f"Version: {sdist_metadata_version}\n"
        "\n"
    ).encode("utf-8")
    sdist_path = dist_dir / f"geotask_core-{VERSION}.tar.gz"
    with tarfile.open(sdist_path, mode="w:gz") as archive:
        _write_tar_member(
            archive,
            f"geotask_core-{VERSION}/PKG-INFO",
            sdist_metadata,
        )
        _write_tar_member(
            archive,
            f"geotask_core-{VERSION}/pyproject.toml",
            b"[build-system]\n",
        )


def test_release_preflight_accepts_current_source_contract() -> None:
    preflight = _load_preflight()

    report = preflight.verify_release_preflight(
        ROOT,
        expected_version=VERSION,
        expected_tag=f"v{VERSION}",
    )["release_preflight"]

    assert report["valid"] is True
    assert report["version"] == VERSION
    assert report["tag"] == f"v{VERSION}"
    assert report["release_date"] == "2026-07-30"
    assert report["release_notes"] == "docs/release_v0_2_0.md"
    assert report["artifacts_checked"] is False
    assert report["errors"] == []
    assert all(check["valid"] for check in report["checks"])


def test_release_preflight_accepts_matching_wheel_and_sdist(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    _create_artifacts(dist_dir)
    preflight = _load_preflight()

    report = preflight.verify_release_preflight(
        ROOT,
        expected_version=VERSION,
        artifact_dir=dist_dir,
    )["release_preflight"]

    assert report["valid"] is True
    assert report["artifacts_checked"] is True
    assert report["wheel"] == f"geotask_core-{VERSION}-py3-none-any.whl"
    assert report["sdist"] == f"geotask_core-{VERSION}.tar.gz"
    assert report["errors"] == []


def test_release_preflight_rejects_expected_version_mismatch() -> None:
    preflight = _load_preflight()

    report = preflight.verify_release_preflight(
        ROOT,
        expected_version="0.2.1",
    )["release_preflight"]

    assert report["valid"] is False
    assert any("expected release version" in error for error in report["errors"])


def test_release_preflight_rejects_wheel_metadata_version_drift(
    tmp_path: Path,
) -> None:
    dist_dir = tmp_path / "dist"
    _create_artifacts(dist_dir, wheel_metadata_version="9.9.9")
    preflight = _load_preflight()

    report = preflight.verify_release_preflight(
        ROOT,
        expected_version=VERSION,
        artifact_dir=dist_dir,
    )["release_preflight"]

    assert report["valid"] is False
    assert any(
        "wheel METADATA Version mismatch" in error for error in report["errors"]
    )


def test_release_preflight_cli_emits_machine_readable_failure() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(PREFLIGHT_PATH),
            "--root",
            str(ROOT),
            "--expected-version",
            "0.2.1",
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stderr == ""
    report = json.loads(result.stdout)["release_preflight"]
    assert report["valid"] is False
    assert report["version"] == VERSION
    assert report["expected_version"] == "0.2.1"
    assert any("expected release version" in error for error in report["errors"])
    assert "Traceback" not in result.stdout


def test_ci_and_publish_workflows_enforce_release_preflight() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    publish = (ROOT / ".github" / "workflows" / "publish-pypi.yml").read_text(
        encoding="utf-8"
    )

    assert "verify_release_preflight.py --artifacts dist --format json" in ci
    assert "inputs:" in publish
    assert "version:" in publish
    assert "required: true" in publish
    assert "verify_release_preflight.py" in publish
    assert '${{ github.ref_type }}' in publish
    assert '${{ github.ref_name }}' in publish
    assert '${{ github.event.repository.default_branch }}' in publish
    assert 'if [ "$DISPATCH_REF_TYPE" != "branch" ]' in publish
    assert 'if [ "$DISPATCH_REF_NAME" != "$DEFAULT_BRANCH" ]' in publish
    assert 'ref: v${{ inputs.version }}' in publish
    assert "fetch-depth: 0" in publish
    assert 'tag_commit="$(git rev-list -n 1 "$expected_tag")"' in publish
    assert 'if [ "$head_commit" != "$tag_commit" ]' in publish
    assert '--expected-version "$EXPECTED_VERSION"' in publish
    assert '--expected-tag "v$EXPECTED_VERSION"' in publish
    assert "--artifacts dist" in publish


def test_publish_workflow_package_version_step_executes(tmp_path: Path) -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "publish-pypi.yml").read_text(
            encoding="utf-8"
        )
    )
    step = next(
        item
        for item in workflow["jobs"]["build"]["steps"]
        if item.get("id") == "package-version"
    )
    output_path = tmp_path / "github-output.txt"
    environment = os.environ.copy()
    environment["GITHUB_OUTPUT"] = output_path.as_posix()

    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.read_text(encoding="utf-8") == f"version={VERSION}\n"
