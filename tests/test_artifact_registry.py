"""Public artifact registry and `inspect schemas` CLI tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from geotask_core.v1.artifact_registry import (
    ARTIFACT_REGISTRY_SCHEMA_ID,
    ARTIFACT_REGISTRY_VERSION,
    GEOTASK_DOCUMENT_SCHEMA_ID,
    GEOTASK_DOCUMENT_SCHEMA_VERSION,
    ArtifactDescriptor,
    artifact_registry_payload,
    get_artifact_descriptor,
    list_artifact_descriptors,
)
from geotask_core.v1.control_evaluation import CONTROL_EVALUATION_SCHEMA_ID
from geotask_core.v1.result import GEOTASK_RESULT_SCHEMA_ID


REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "geotask_core.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_registry_contains_exactly_three_stable_public_artifacts() -> None:
    artifacts = list_artifact_descriptors()
    payload = artifact_registry_payload()["artifact_registry"]

    assert ARTIFACT_REGISTRY_SCHEMA_ID.endswith(
        "geotask-artifact-registry-v1.0.schema.json"
    )
    assert payload["schema_id"] == ARTIFACT_REGISTRY_SCHEMA_ID
    assert ARTIFACT_REGISTRY_VERSION == "1.0"
    assert isinstance(artifacts, tuple)
    assert all(isinstance(item, ArtifactDescriptor) for item in artifacts)
    assert [item.artifact_id for item in artifacts] == [
        "geotask.document",
        "geotask.execution-result",
        "geotask.control-evaluation",
    ]
    assert len({item.artifact_id for item in artifacts}) == len(artifacts)
    assert artifact_registry_payload()["artifact_registry"]["artifact_count"] == 3


def test_registry_payload_matches_its_public_json_schema() -> None:
    schema_path = (
        REPO_ROOT / "schemas" / "geotask-artifact-registry-v1.0.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == ARTIFACT_REGISTRY_SCHEMA_ID
    assert list(
        Draft202012Validator(schema).iter_errors(artifact_registry_payload())
    ) == []


def test_registry_schema_metadata_matches_published_json_schemas() -> None:
    expected = {
        "geotask.document": GEOTASK_DOCUMENT_SCHEMA_ID,
        "geotask.execution-result": GEOTASK_RESULT_SCHEMA_ID,
        "geotask.control-evaluation": CONTROL_EVALUATION_SCHEMA_ID,
    }

    assert GEOTASK_DOCUMENT_SCHEMA_VERSION == "1.0"
    for artifact in list_artifact_descriptors():
        schema_path = REPO_ROOT / artifact.schema_path
        specification_path = REPO_ROOT / artifact.specification_path
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        assert schema["$id"] == expected[artifact.artifact_id]
        assert artifact.schema_id == schema["$id"]
        assert artifact.schema_version == "1.0"
        assert specification_path.is_file()
        assert specification_path.stat().st_size > 500


def test_registry_generation_and_validation_guidance_is_explicit() -> None:
    document = get_artifact_descriptor("geotask.document")
    execution = get_artifact_descriptor("geotask.execution-result")
    control = get_artifact_descriptor("geotask.control-evaluation")

    assert document.generation_command is None
    assert "does not synthesize" in document.generation_note
    assert document.validation_command == "geotask validate <task.yaml>"

    assert "--format v1-json" in str(execution.generation_command)
    assert execution.validation_command.startswith("geotask result validate")
    assert execution.wrapper_key == "geotask_result"

    assert "geotask control evaluate" in str(control.generation_command)
    assert control.validation_command.startswith("geotask control validate")
    assert control.wrapper_key == "control_evaluation"
    assert "never execute next_action" in control.execution_boundary


def test_registry_is_public_core_only_and_lookup_is_strict() -> None:
    rendered = json.dumps(artifact_registry_payload(), ensure_ascii=False)

    for forbidden in (
        "geotask_runtime",
        "geotask_domain_packs",
        "patent_evidence",
        "internal",
    ):
        assert forbidden not in rendered

    with pytest.raises(KeyError, match="unknown GeoTask artifact"):
        get_artifact_descriptor("geotask.unknown")


def test_public_manifest_requires_artifact_registry_assets() -> None:
    manifest = yaml.safe_load(
        (REPO_ROOT / ".release" / "public-manifest.yaml").read_text(
            encoding="utf-8"
        )
    )
    included = set(manifest["include"])
    required = set(manifest["required"])

    assert "tests/test_artifact_registry.py" in included
    for path in (
        "src/geotask_core/v1/artifact_registry.py",
        "docs/spec/geotask-artifact-registry-v1.0.md",
        "schemas/geotask-artifact-registry-v1.0.schema.json",
        "tests/test_artifact_registry.py",
    ):
        assert path in required


def test_public_namespaces_export_artifact_registry() -> None:
    import geotask_core
    import geotask_core.v1 as v1

    for namespace in (geotask_core, v1):
        assert namespace.ARTIFACT_REGISTRY_SCHEMA_ID == ARTIFACT_REGISTRY_SCHEMA_ID
        assert namespace.ARTIFACT_REGISTRY_VERSION == "1.0"
        assert namespace.GEOTASK_DOCUMENT_SCHEMA_ID == GEOTASK_DOCUMENT_SCHEMA_ID
        assert namespace.GEOTASK_DOCUMENT_SCHEMA_VERSION == "1.0"
        assert namespace.ArtifactDescriptor is ArtifactDescriptor
        assert namespace.list_artifact_descriptors is list_artifact_descriptors
        assert namespace.get_artifact_descriptor is get_artifact_descriptor
        assert namespace.artifact_registry_payload is artifact_registry_payload


def test_inspect_schemas_default_yaml_is_parseable() -> None:
    result = _run_cli("inspect", "schemas")

    assert result.returncode == 0
    assert result.stderr == ""
    payload = yaml.safe_load(result.stdout)
    registry = payload["artifact_registry"]
    assert registry["registry_version"] == "1.0"
    assert registry["artifact_count"] == 3
    assert registry["artifacts"][0]["artifact_id"] == "geotask.document"
    assert registry["artifacts"][0]["generation_command"] is None


def test_inspect_schemas_json_is_stable_machine_readable_output() -> None:
    result = _run_cli("inspect", "schemas", "--format", "json")

    assert result.returncode == 0
    assert result.stderr == ""
    assert not result.stdout.startswith("[inspect]")
    payload = json.loads(result.stdout)
    assert payload == artifact_registry_payload()
    for artifact in payload["artifact_registry"]["artifacts"]:
        assert artifact["schema_id"].startswith("https://")
        assert artifact["schema_version"] == "1.0"
        assert artifact["validation_command"].startswith("geotask ")
        assert "execution_boundary" in artifact


def test_inspect_help_lists_singular_and_plural_schema_targets() -> None:
    top = _run_cli("inspect", "--help")
    schemas = _run_cli("inspect", "schemas", "--help")

    assert top.returncode == 0
    assert "schema|schemas" in top.stdout
    assert schemas.returncode == 0
    assert "inspect schemas" in schemas.stdout
    assert "--format yaml|json" in schemas.stdout
    assert "generation guidance" in schemas.stdout


def test_inspect_schemas_rejects_invalid_options_without_traceback() -> None:
    cases = (
        ("inspect", "schemas", "--format", "xml"),
        ("inspect", "schemas", "--format"),
        (
            "inspect",
            "schemas",
            "--format",
            "json",
            "--format",
            "yaml",
        ),
        ("inspect", "schemas", "--unknown"),
        ("inspect", "schemas", "unexpected"),
    )

    for args in cases:
        result = _run_cli(*args)
        assert result.returncode != 0
        assert "inspect_schemas_failed" in result.stderr
        assert "Traceback" not in result.stderr


def test_legacy_inspect_schema_remains_compatible() -> None:
    result = _run_cli("inspect", "schema")

    assert result.returncode == 0
    payload = yaml.safe_load(result.stdout)
    assert "schema" in payload
    assert "required_top_level_keys" in payload["schema"]
    assert "artifact_registry" not in payload
