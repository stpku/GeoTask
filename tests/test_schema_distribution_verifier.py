"""Release-gate tests for built Schema Bundle distributions."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / ".release" / "verify_schema_distribution.py"
SCHEMA_FILENAMES = (
    "geotask-agent-generation-preparation-v0.1.schema.json",
    "geotask-agent-integration-v0.1.schema.json",
    "geotask-agent-revision-retry-v0.1.schema.json",
    "geotask-agent-revision-verification-v0.1.schema.json",
    "geotask-artifact-registry-v1.0.schema.json",
    "geotask-artifact-validation-v1.0.schema.json",
    "geotask-control-evaluation-v1.0.schema.json",
    "geotask-result-v1.0.schema.json",
    "geotask-v1.0.schema.json",
)


def _load_verifier():
    spec = importlib.util.spec_from_file_location(
        "verify_schema_distribution", VERIFIER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _schema_sources() -> dict[str, bytes]:
    return {
        filename: (ROOT / "schemas" / filename).read_bytes()
        for filename in SCHEMA_FILENAMES
    }


def _bundle_manifest(schema_bytes: dict[str, bytes]) -> bytes:
    entries = []
    for filename in sorted(schema_bytes):
        raw = schema_bytes[filename]
        schema = json.loads(raw.decode("utf-8"))
        entries.append(
            {
                "schema_id": schema["$id"],
                "filename": filename,
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return (
        json.dumps(
            {
                "schema_bundle": {
                    "bundle_version": "1.0",
                    "schema_count": len(entries),
                    "schemas": entries,
                }
            },
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _write_tar_member(archive: tarfile.TarFile, name: str, raw: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(raw)
    archive.addfile(info, io.BytesIO(raw))


def _create_distribution(
    dist_dir: Path,
    *,
    tamper_wheel_schema: bool = False,
    omit_sdist_build_support: bool = False,
) -> None:
    dist_dir.mkdir(parents=True)
    source_schemas = _schema_sources()
    wheel_schemas = dict(source_schemas)
    manifest = _bundle_manifest(wheel_schemas)
    if tamper_wheel_schema:
        wheel_schemas["geotask-result-v1.0.schema.json"] += b"\n"

    wheel_path = dist_dir / "geotask_core-0.3.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, mode="w") as archive:
        archive.writestr(
            "geotask_core/schemas/schema-bundle-manifest-v1.0.json",
            manifest,
        )
        for filename, raw in wheel_schemas.items():
            archive.writestr(f"geotask_core/schemas/{filename}", raw)
        archive.writestr(
            "geotask_core-0.3.0.dist-info/entry_points.txt",
            "[console_scripts]\ngeotask = geotask_core.cli:main\n",
        )

    sdist_path = dist_dir / "geotask_core-0.3.0.tar.gz"
    prefix = "geotask_core-0.3.0"
    required_sources = {
        "MANIFEST.in": (ROOT / "MANIFEST.in").read_bytes(),
        "pyproject.toml": (ROOT / "pyproject.toml").read_bytes(),
        "src/geotask_build_support.py": (
            ROOT / "src" / "geotask_build_support.py"
        ).read_bytes(),
        "src/geotask_core/schemas/__init__.py": (
            ROOT / "src" / "geotask_core" / "schemas" / "__init__.py"
        ).read_bytes(),
        "src/geotask_core/v1/schema_bundle.py": (
            ROOT / "src" / "geotask_core" / "v1" / "schema_bundle.py"
        ).read_bytes(),
        "src/geotask_core/v1/artifact_validation.py": (
            ROOT / "src" / "geotask_core" / "v1" / "artifact_validation.py"
        ).read_bytes(),
    }
    if omit_sdist_build_support:
        required_sources.pop("src/geotask_build_support.py")

    with tarfile.open(sdist_path, mode="w:gz") as archive:
        for relative, raw in required_sources.items():
            _write_tar_member(archive, f"{prefix}/{relative}", raw)
        for filename, raw in source_schemas.items():
            _write_tar_member(archive, f"{prefix}/schemas/{filename}", raw)


def test_distribution_verifier_accepts_matching_wheel_and_sdist(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    _create_distribution(dist_dir)
    verifier = _load_verifier()

    report = verifier.verify_distribution(dist_dir)[
        "schema_distribution_verification"
    ]

    assert report["valid"] is True
    assert report["bundle_version"] == "1.0"
    assert report["schema_count"] == 9
    assert all(item["valid"] for item in report["schemas"])
    assert report["errors"] == []


def test_distribution_verifier_detects_tampered_wheel_schema(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    _create_distribution(dist_dir, tamper_wheel_schema=True)
    verifier = _load_verifier()

    report = verifier.verify_distribution(dist_dir)[
        "schema_distribution_verification"
    ]

    assert report["valid"] is False
    assert any("sha256 mismatch" in error for error in report["errors"])
    assert any(
        "sdist authoritative schema differs from wheel resource" in error
        for error in report["errors"]
    )


def test_distribution_verifier_requires_build_sources_in_sdist(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    _create_distribution(dist_dir, omit_sdist_build_support=True)
    verifier = _load_verifier()

    report = verifier.verify_distribution(dist_dir)[
        "schema_distribution_verification"
    ]

    assert report["valid"] is False
    assert any(
        "src/geotask_build_support.py" in error for error in report["errors"]
    )


def test_distribution_verifier_cli_emits_machine_readable_report(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    _create_distribution(dist_dir)

    result = subprocess.run(
        [
            sys.executable,
            str(VERIFIER_PATH),
            str(dist_dir),
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    report = json.loads(result.stdout)["schema_distribution_verification"]
    assert report["valid"] is True
    assert report["schema_count"] == 9


def test_ci_and_publish_workflows_enforce_distribution_gate() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    publish = (ROOT / ".github" / "workflows" / "publish-pypi.yml").read_text(
        encoding="utf-8"
    )

    for workflow in (ci, publish):
        assert "verify_schema_distribution.py" in workflow
        assert "schema verify --format json" in workflow
        assert "schema export geotask.execution-result --compact" in workflow
        assert (
            "inspect schemas geotask.execution-result --verify --format json"
            in workflow
        )
        for artifact_id in (
            "geotask.document",
            "geotask.execution-result",
            "geotask.control-evaluation",
            "geotask.agent-generation-preparation",
            "geotask.agent-revision-verification",
            "geotask.agent-revision-retry",
            "geotask.agent-evidence-recovery",
            "geotask.artifact-validation-report",
        ):
            assert f"artifact validate {artifact_id}" in workflow
        assert "artifact_validation" in workflow
        assert "checked_count\"] == 9" in workflow
        assert "checked_count\"] == 1" in workflow

    assert "pip wheel --no-deps --wheel-dir dist-from-sdist" in ci
    assert "verify_schema_distribution.py dist-from-sdist" in ci
    assert "pip install dist-from-sdist/*.whl" in ci
    assert "pip install dist/*.whl" in publish
