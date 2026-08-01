"""Public artifact registry and `inspect schemas` CLI tests."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

import geotask_core.cli as cli_module
from geotask_core.v1.agent_artifacts import (
    AGENT_EVIDENCE_RECOVERY_SCHEMA_ID,
    AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION,
    AGENT_GENERATION_PREPARATION_SCHEMA_ID,
    AGENT_GENERATION_PREPARATION_SCHEMA_VERSION,
    AGENT_REVISION_RETRY_SCHEMA_ID,
    AGENT_REVISION_RETRY_SCHEMA_VERSION,
    AGENT_REVISION_VERIFICATION_SCHEMA_ID,
    AGENT_REVISION_VERIFICATION_SCHEMA_VERSION,
)
from geotask_core.v1.artifact_registry import (
    ARTIFACT_REGISTRY_SCHEMA_ID,
    ARTIFACT_REGISTRY_VERSION,
    GEOTASK_DOCUMENT_SCHEMA_ID,
    GEOTASK_DOCUMENT_SCHEMA_VERSION,
    ARTIFACT_VALIDATION_SCHEMA_ID,
    ARTIFACT_VALIDATION_SCHEMA_VERSION,
    ArtifactDescriptor,
    artifact_registry_payload,
    get_artifact_descriptor,
    list_artifact_descriptors,
)
from geotask_core.v1.control_evaluation import CONTROL_EVALUATION_SCHEMA_ID
from geotask_core.v1.core_benchmark_contract import (
    CORE_BENCHMARK_SCHEMA_ID,
    CORE_BENCHMARK_SCHEMA_VERSION,
)
from geotask_core.v1.observation import (
    OBSERVATION_SCHEMA_ID,
    OBSERVATION_SCHEMA_VERSION,
)
from geotask_core.v1.world_state import (
    WORLD_STATE_SCHEMA_ID,
    WORLD_STATE_SCHEMA_VERSION,
)
from geotask_core.v1.result import GEOTASK_RESULT_SCHEMA_ID
from geotask_core.v1.runtime_interface import (
    RUNTIME_DESCRIPTOR_SCHEMA_ID,
    RUNTIME_DESCRIPTOR_SCHEMA_VERSION,
    RUNTIME_REQUEST_SCHEMA_ID,
    RUNTIME_REQUEST_SCHEMA_VERSION,
    RUNTIME_RESPONSE_SCHEMA_ID,
    RUNTIME_RESPONSE_SCHEMA_VERSION,
)
import geotask_core.v1.schema_bundle as schema_bundle_module
from geotask_core.v1.schema_bundle import (
    SCHEMA_BUNDLE_VERSION,
    SCHEMA_BUNDLE_MANIFEST_FILENAME,
    BUNDLED_SCHEMA_IDS,
    list_bundled_schema_ids,
    schema_bundle_manifest,
    load_artifact_schema,
    load_bundled_schema,
    verify_schema_bundle,
)
from geotask_core.v1.artifact_validation import (
    ARTIFACT_VALIDATION_REPORT_VERSION,
    ArtifactValidationFormatError,
    ArtifactValidationReport,
    load_artifact_validation_report,
    validate_artifact_payload,
    validate_artifact_file,
)


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


def test_registry_contains_exactly_fourteen_stable_public_artifacts() -> None:
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
        "geotask.observation",
        "geotask.world-state",
        "geotask.execution-result",
        "geotask.control-evaluation",
        "geotask.agent-generation-preparation",
        "geotask.agent-revision-verification",
        "geotask.agent-revision-retry",
        "geotask.agent-evidence-recovery",
        "geotask.runtime-descriptor",
        "geotask.runtime-request",
        "geotask.runtime-response",
        "geotask.core-benchmark-report",
        "geotask.artifact-validation-report",
    ]
    assert len({item.artifact_id for item in artifacts}) == len(artifacts)
    assert artifact_registry_payload()["artifact_registry"]["artifact_count"] == 14


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
        "geotask.document": (GEOTASK_DOCUMENT_SCHEMA_ID, "1.0"),
        "geotask.observation": (OBSERVATION_SCHEMA_ID, OBSERVATION_SCHEMA_VERSION),
        "geotask.world-state": (WORLD_STATE_SCHEMA_ID, WORLD_STATE_SCHEMA_VERSION),
        "geotask.execution-result": (GEOTASK_RESULT_SCHEMA_ID, "1.0"),
        "geotask.control-evaluation": (CONTROL_EVALUATION_SCHEMA_ID, "1.0"),
        "geotask.agent-generation-preparation": (
            AGENT_GENERATION_PREPARATION_SCHEMA_ID,
            AGENT_GENERATION_PREPARATION_SCHEMA_VERSION,
        ),
        "geotask.agent-revision-verification": (
            AGENT_REVISION_VERIFICATION_SCHEMA_ID,
            AGENT_REVISION_VERIFICATION_SCHEMA_VERSION,
        ),
        "geotask.agent-revision-retry": (
            AGENT_REVISION_RETRY_SCHEMA_ID,
            AGENT_REVISION_RETRY_SCHEMA_VERSION,
        ),
        "geotask.agent-evidence-recovery": (
            AGENT_EVIDENCE_RECOVERY_SCHEMA_ID,
            AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION,
        ),
        "geotask.runtime-descriptor": (
            RUNTIME_DESCRIPTOR_SCHEMA_ID,
            RUNTIME_DESCRIPTOR_SCHEMA_VERSION,
        ),
        "geotask.runtime-request": (
            RUNTIME_REQUEST_SCHEMA_ID,
            RUNTIME_REQUEST_SCHEMA_VERSION,
        ),
        "geotask.runtime-response": (
            RUNTIME_RESPONSE_SCHEMA_ID,
            RUNTIME_RESPONSE_SCHEMA_VERSION,
        ),
        "geotask.core-benchmark-report": (
            CORE_BENCHMARK_SCHEMA_ID,
            CORE_BENCHMARK_SCHEMA_VERSION,
        ),
        "geotask.artifact-validation-report": (
            ARTIFACT_VALIDATION_SCHEMA_ID,
            "1.0",
        ),
    }

    assert GEOTASK_DOCUMENT_SCHEMA_VERSION == "1.0"
    for artifact in list_artifact_descriptors():
        schema_path = REPO_ROOT / artifact.schema_path
        specification_path = REPO_ROOT / artifact.specification_path
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        expected_id, expected_version = expected[artifact.artifact_id]

        assert schema["$id"] == expected_id
        assert artifact.schema_id == schema["$id"]
        assert artifact.schema_version == expected_version
        assert specification_path.is_file()
        assert specification_path.stat().st_size > 500


def test_schema_bundle_exposes_all_public_schema_ids_offline() -> None:
    expected_ids = (
        ARTIFACT_REGISTRY_SCHEMA_ID,
        GEOTASK_DOCUMENT_SCHEMA_ID,
        OBSERVATION_SCHEMA_ID,
        WORLD_STATE_SCHEMA_ID,
        GEOTASK_RESULT_SCHEMA_ID,
        CONTROL_EVALUATION_SCHEMA_ID,
        AGENT_GENERATION_PREPARATION_SCHEMA_ID,
        AGENT_REVISION_VERIFICATION_SCHEMA_ID,
        AGENT_REVISION_RETRY_SCHEMA_ID,
        AGENT_EVIDENCE_RECOVERY_SCHEMA_ID,
        RUNTIME_DESCRIPTOR_SCHEMA_ID,
        RUNTIME_REQUEST_SCHEMA_ID,
        RUNTIME_RESPONSE_SCHEMA_ID,
        CORE_BENCHMARK_SCHEMA_ID,
        ARTIFACT_VALIDATION_SCHEMA_ID,
    )

    assert BUNDLED_SCHEMA_IDS == expected_ids
    assert list_bundled_schema_ids() == expected_ids
    for schema_id in expected_ids:
        schema = load_bundled_schema(schema_id)
        assert schema["$id"] == schema_id
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_artifact_schema_loader_uses_registry_schema_ids() -> None:
    for descriptor in list_artifact_descriptors():
        first = load_artifact_schema(descriptor.artifact_id)
        second = load_artifact_schema(descriptor.artifact_id)

        assert first["$id"] == descriptor.schema_id
        assert first == second
        assert first is not second

    with pytest.raises(KeyError, match="unknown bundled GeoTask schema"):
        load_bundled_schema("https://example.invalid/unknown.schema.json")
    with pytest.raises(KeyError, match="unknown GeoTask artifact"):
        load_artifact_schema("geotask.unknown")


def test_schema_bundle_manifest_matches_authoritative_schema_bytes() -> None:
    manifest = schema_bundle_manifest()["schema_bundle"]

    assert SCHEMA_BUNDLE_VERSION == "1.0"
    assert SCHEMA_BUNDLE_MANIFEST_FILENAME == "schema-bundle-manifest-v1.0.json"
    assert manifest["bundle_version"] == SCHEMA_BUNDLE_VERSION
    assert manifest["schema_count"] == 15
    assert len(manifest["schemas"]) == 15

    for entry in manifest["schemas"]:
        raw = (REPO_ROOT / "schemas" / entry["filename"]).read_bytes()
        assert entry["schema_id"] in BUNDLED_SCHEMA_IDS
        assert entry["size_bytes"] == len(raw)
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()


def test_schema_bundle_verification_supports_all_and_one_artifact() -> None:
    all_report = verify_schema_bundle()["schema_bundle_verification"]
    one_report = verify_schema_bundle(
        "geotask.execution-result"
    )["schema_bundle_verification"]

    assert all_report["valid"] is True
    assert all_report["bundle_version"] == SCHEMA_BUNDLE_VERSION
    assert all_report["checked_count"] == 15
    assert all(item["valid"] for item in all_report["schemas"])
    assert all_report["diagnostics"] == []

    assert one_report["valid"] is True
    assert one_report["checked_count"] == 1
    assert one_report["schemas"][0]["schema_id"] == GEOTASK_RESULT_SCHEMA_ID
    assert one_report["schemas"][0]["expected_sha256"] == (
        one_report["schemas"][0]["actual_sha256"]
    )

    with pytest.raises(KeyError, match="unknown GeoTask artifact"):
        verify_schema_bundle("geotask.unknown")


def test_schema_bundle_verification_detects_tampered_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_manifest = schema_bundle_manifest()
    original_reader = schema_bundle_module._schema_bytes

    def tampered_reader(schema_id: str) -> bytes:
        raw = original_reader(schema_id)
        if schema_id == GEOTASK_RESULT_SCHEMA_ID:
            return raw + b"\n"
        return raw

    monkeypatch.setattr(
        schema_bundle_module,
        "schema_bundle_manifest",
        lambda: original_manifest,
    )
    monkeypatch.setattr(schema_bundle_module, "_schema_bytes", tampered_reader)

    report = verify_schema_bundle(
        "geotask.execution-result"
    )["schema_bundle_verification"]

    assert report["valid"] is False
    assert report["checked_count"] == 1
    assert report["schemas"][0]["valid"] is False
    assert report["schemas"][0]["expected_sha256"] != (
        report["schemas"][0]["actual_sha256"]
    )
    assert report["diagnostics"][0]["code"] == "invalid_bundled_schema"
    assert "mismatch" in report["diagnostics"][0]["message"]


def test_installed_bundle_missing_manifest_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        schema_bundle_module,
        "_source_checkout_schema_root",
        lambda: None,
    )

    with pytest.raises(
        FileNotFoundError,
        match="installed Schema Bundle Manifest is unavailable",
    ):
        schema_bundle_manifest()

    report = verify_schema_bundle(
        "geotask.execution-result"
    )["schema_bundle_verification"]

    assert report["valid"] is False
    assert report["checked_count"] == 1
    assert report["diagnostics"][0]["code"] == "invalid_schema_bundle_manifest"
    assert "Manifest is unavailable" in report["diagnostics"][0]["message"]


def test_schema_bundle_build_configuration_is_public_and_complete() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    expected_files = {
        "geotask-agent-generation-preparation-v0.1.schema.json",
        "geotask-agent-integration-v0.1.schema.json",
        "geotask-agent-revision-retry-v0.1.schema.json",
        "geotask-agent-revision-verification-v0.1.schema.json",
        "geotask-artifact-registry-v1.0.schema.json",
        "geotask-artifact-validation-v1.0.schema.json",
        "geotask-v1.0.schema.json",
        "geotask-result-v1.0.schema.json",
        "geotask-control-evaluation-v1.0.schema.json",
        "geotask-core-benchmark-v0.1.schema.json",
        "geotask-observation-v0.1.schema.json",
        "geotask-world-state-v0.1.schema.json",
        "geotask-runtime-descriptor-v0.1.schema.json",
        "geotask-runtime-request-v0.1.schema.json",
        "geotask-runtime-response-v0.1.schema.json",
    }

    assert 'build_py = "geotask_build_support.BuildPy"' in pyproject
    assert "include src/geotask_build_support.py" in manifest
    assert "recursive-include schemas *.schema.json" in manifest
    assert (REPO_ROOT / "src" / "geotask_build_support.py").is_file()
    assert {path.name for path in (REPO_ROOT / "schemas").glob("*.schema.json")} == expected_files


def test_registry_generation_and_validation_guidance_is_explicit() -> None:
    document = get_artifact_descriptor("geotask.document")
    observation = get_artifact_descriptor("geotask.observation")
    world_state = get_artifact_descriptor("geotask.world-state")
    execution = get_artifact_descriptor("geotask.execution-result")
    control = get_artifact_descriptor("geotask.control-evaluation")
    preparation = get_artifact_descriptor("geotask.agent-generation-preparation")
    verification = get_artifact_descriptor("geotask.agent-revision-verification")
    retry = get_artifact_descriptor("geotask.agent-revision-retry")
    recovery = get_artifact_descriptor("geotask.agent-evidence-recovery")
    runtime_descriptor = get_artifact_descriptor("geotask.runtime-descriptor")
    runtime_request = get_artifact_descriptor("geotask.runtime-request")
    runtime_response = get_artifact_descriptor("geotask.runtime-response")
    benchmark_report = get_artifact_descriptor("geotask.core-benchmark-report")
    validation_report = get_artifact_descriptor(
        "geotask.artifact-validation-report"
    )

    assert document.generation_command is None
    assert "does not synthesize" in document.generation_note
    assert document.validation_command == (
        "geotask artifact validate geotask.document <task.yaml>"
    )

    assert observation.generation_command is None
    assert observation.wrapper_key == "observation"
    assert observation.schema_id == OBSERVATION_SCHEMA_ID
    assert observation.schema_version == "0.1"
    assert "does not verify claim truth" in observation.execution_boundary

    assert world_state.generation_command is None
    assert world_state.wrapper_key == "world_state"
    assert world_state.schema_id == WORLD_STATE_SCHEMA_ID
    assert world_state.schema_version == "0.1"
    assert "does not fetch evidence" in world_state.execution_boundary
    assert "compute a State Transition" in world_state.execution_boundary

    assert "--format v1-json" in str(execution.generation_command)
    assert execution.validation_command.startswith(
        "geotask artifact validate geotask.execution-result"
    )
    assert execution.wrapper_key == "geotask_result"

    assert "geotask control evaluate" in str(control.generation_command)
    assert control.validation_command.startswith(
        "geotask artifact validate geotask.control-evaluation"
    )
    assert control.wrapper_key == "control_evaluation"
    assert "never execute next_action" in control.execution_boundary

    assert "geotask agent prepare" in str(preparation.generation_command)
    assert preparation.wrapper_key == "agent_generation_preparation"
    assert preparation.schema_version == "0.1"
    assert "does not prepare or execute" in preparation.execution_boundary

    assert "geotask agent retry" in str(verification.generation_command)
    assert "--verification-output" in str(verification.generation_command)
    assert verification.wrapper_key == "agent_revision_verification"
    assert verification.schema_version == "0.1"
    assert "does not rerun diff verification" in verification.execution_boundary

    assert "geotask agent retry" in str(retry.generation_command)
    assert retry.wrapper_key == "agent_revision_retry"
    assert retry.schema_version == "0.1"
    assert "does not repeat the retry" in retry.execution_boundary

    assert "geotask agent recover" in str(recovery.generation_command)
    assert recovery.wrapper_key == "agent_integration"
    assert recovery.schema_version == "0.1"
    assert recovery.schema_id == AGENT_EVIDENCE_RECOVERY_SCHEMA_ID
    assert "does not reacquire evidence" in recovery.execution_boundary

    assert runtime_descriptor.generation_command == (
        "geotask runtime inspect --format json"
    )
    assert runtime_descriptor.wrapper_key == "runtime_descriptor"
    assert runtime_descriptor.schema_id == RUNTIME_DESCRIPTOR_SCHEMA_ID
    assert "does not connect to or invoke" in runtime_descriptor.execution_boundary

    assert runtime_request.generation_command is None
    assert runtime_request.wrapper_key == "runtime_request"
    assert runtime_request.schema_id == RUNTIME_REQUEST_SCHEMA_ID
    assert "never submits it" in runtime_request.execution_boundary

    assert "geotask runtime mock" in str(runtime_response.generation_command)
    assert runtime_response.wrapper_key == "runtime_response"
    assert runtime_response.schema_id == RUNTIME_RESPONSE_SCHEMA_ID
    assert "does not repeat" in runtime_response.execution_boundary

    assert "geotask benchmark core" in str(benchmark_report.generation_command)
    assert benchmark_report.wrapper_key == "core_benchmark"
    assert benchmark_report.schema_id == CORE_BENCHMARK_SCHEMA_ID
    assert benchmark_report.schema_version == "0.1"
    assert "not comparable across" in benchmark_report.execution_boundary

    assert "artifact validate <artifact-id>" in str(
        validation_report.generation_command
    )
    assert validation_report.validation_command.startswith(
        "geotask artifact validate geotask.artifact-validation-report"
    )
    assert validation_report.wrapper_key == "artifact_validation"
    assert validation_report.schema_id == ARTIFACT_VALIDATION_SCHEMA_ID


def test_registry_payload_can_filter_by_stable_artifact_id() -> None:
    payload = artifact_registry_payload("geotask.execution-result")
    registry = payload["artifact_registry"]

    assert registry["artifact_count"] == 1
    assert [item["artifact_id"] for item in registry["artifacts"]] == [
        "geotask.execution-result"
    ]

    with pytest.raises(KeyError, match="unknown GeoTask artifact"):
        artifact_registry_payload("geotask.unknown")


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
    assert "tests/test_artifact_validation.py" in included
    assert "tests/test_release_preflight.py" in included
    for path in (
        "src/geotask_build_support.py",
        "src/geotask_core/schemas/__init__.py",
        "src/geotask_core/v1/artifact_registry.py",
        "src/geotask_core/v1/schema_bundle.py",
        "src/geotask_core/v1/artifact_validation.py",
        "src/geotask_core/v1/observation.py",
        "src/geotask_core/v1/world_state.py",
        "src/geotask_core/v1/core_benchmark_contract.py",
        "src/geotask_core/v1/core_benchmark_cases.py",
        "src/geotask_core/v1/core_benchmark_report.py",
        "src/geotask_core/v1/core_benchmark.py",
        "src/geotask_core/v1/core_benchmark_cli.py",
        "src/geotask_core/v1/agent_artifacts.py",
        "src/geotask_core/v1/runtime_interface.py",
        ".release/verify_release_preflight.py",
        ".release/verify_schema_distribution.py",
        "docs/spec/geotask-artifact-registry-v1.0.md",
        "docs/spec/geotask-artifact-validation-v1.0.md",
        "docs/spec/geotask-runtime-interface-profile-v0.1.md",
        "docs/spec/geotask-core-benchmark-v0.1.md",
        "docs/spec/geotask-observation-v0.1.md",
        "docs/spec/geotask-world-state-v0.1.md",
        "examples/core/runtime_validate_artifact_request.json",
        "examples/core/observation_uav_delay.json",
        "examples/core/world_state_uav_separation.json",
        "schemas/geotask-agent-generation-preparation-v0.1.schema.json",
        "schemas/geotask-agent-revision-verification-v0.1.schema.json",
        "schemas/geotask-agent-revision-retry-v0.1.schema.json",
        "schemas/geotask-runtime-descriptor-v0.1.schema.json",
        "schemas/geotask-runtime-request-v0.1.schema.json",
        "schemas/geotask-runtime-response-v0.1.schema.json",
        "schemas/geotask-core-benchmark-v0.1.schema.json",
        "schemas/geotask-observation-v0.1.schema.json",
        "schemas/geotask-world-state-v0.1.schema.json",
        "schemas/geotask-artifact-registry-v1.0.schema.json",
        "schemas/geotask-artifact-validation-v1.0.schema.json",
        "tests/test_artifact_registry.py",
        "tests/test_artifact_validation.py",
        "tests/test_agent_artifacts.py",
        "tests/test_runtime_interface.py",
        "tests/test_release_preflight.py",
        "tests/v1/test_core_benchmark_v0_4.py",
        "tests/v1/test_observation_v0_5.py",
        "tests/v1/test_world_state_v0_5.py",
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
        assert namespace.ARTIFACT_VALIDATION_SCHEMA_ID == (
            ARTIFACT_VALIDATION_SCHEMA_ID
        )
        assert namespace.ARTIFACT_VALIDATION_SCHEMA_VERSION == (
            ARTIFACT_VALIDATION_SCHEMA_VERSION
        )
        assert namespace.AGENT_GENERATION_PREPARATION_SCHEMA_ID == (
            AGENT_GENERATION_PREPARATION_SCHEMA_ID
        )
        assert namespace.AGENT_GENERATION_PREPARATION_SCHEMA_VERSION == "0.1"
        assert namespace.AGENT_REVISION_VERIFICATION_SCHEMA_ID == (
            AGENT_REVISION_VERIFICATION_SCHEMA_ID
        )
        assert namespace.AGENT_REVISION_VERIFICATION_SCHEMA_VERSION == "0.1"
        assert namespace.AGENT_REVISION_RETRY_SCHEMA_ID == AGENT_REVISION_RETRY_SCHEMA_ID
        assert namespace.AGENT_REVISION_RETRY_SCHEMA_VERSION == "0.1"
        assert namespace.AGENT_EVIDENCE_RECOVERY_SCHEMA_ID == (
            AGENT_EVIDENCE_RECOVERY_SCHEMA_ID
        )
        assert namespace.AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION == "0.1"
        assert namespace.RUNTIME_DESCRIPTOR_SCHEMA_ID == RUNTIME_DESCRIPTOR_SCHEMA_ID
        assert namespace.RUNTIME_DESCRIPTOR_SCHEMA_VERSION == "0.1"
        assert namespace.RUNTIME_REQUEST_SCHEMA_ID == RUNTIME_REQUEST_SCHEMA_ID
        assert namespace.RUNTIME_REQUEST_SCHEMA_VERSION == "0.1"
        assert namespace.RUNTIME_RESPONSE_SCHEMA_ID == RUNTIME_RESPONSE_SCHEMA_ID
        assert namespace.RUNTIME_RESPONSE_SCHEMA_VERSION == "0.1"
        assert namespace.ArtifactDescriptor is ArtifactDescriptor
        assert namespace.list_artifact_descriptors is list_artifact_descriptors
        assert namespace.get_artifact_descriptor is get_artifact_descriptor
        assert namespace.artifact_registry_payload is artifact_registry_payload
        assert namespace.SCHEMA_BUNDLE_VERSION == SCHEMA_BUNDLE_VERSION
        assert namespace.SCHEMA_BUNDLE_MANIFEST_FILENAME == (
            SCHEMA_BUNDLE_MANIFEST_FILENAME
        )
        assert namespace.BUNDLED_SCHEMA_IDS == BUNDLED_SCHEMA_IDS
        assert namespace.list_bundled_schema_ids is list_bundled_schema_ids
        assert namespace.schema_bundle_manifest is schema_bundle_manifest
        assert namespace.load_bundled_schema is load_bundled_schema
        assert namespace.load_artifact_schema is load_artifact_schema
        assert namespace.verify_schema_bundle is verify_schema_bundle
        assert namespace.ARTIFACT_VALIDATION_REPORT_VERSION == (
            ARTIFACT_VALIDATION_REPORT_VERSION
        )
        assert namespace.ArtifactValidationFormatError is (
            ArtifactValidationFormatError
        )
        assert namespace.ArtifactValidationReport is ArtifactValidationReport
        assert namespace.load_artifact_validation_report is (
            load_artifact_validation_report
        )
        assert namespace.validate_artifact_payload is validate_artifact_payload
        assert namespace.validate_artifact_file is validate_artifact_file


def test_schema_export_writes_clean_formatted_json_to_stdout() -> None:
    result = _run_cli("schema", "export", "geotask.document")

    assert result.returncode == 0
    assert result.stderr == ""
    schema = json.loads(result.stdout)
    assert schema["$id"] == GEOTASK_DOCUMENT_SCHEMA_ID
    assert result.stdout.startswith("{\n  ")


def test_schema_export_supports_compact_stdout() -> None:
    result = _run_cli(
        "schema",
        "export",
        "geotask.execution-result",
        "--compact",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    assert json.loads(result.stdout)["$id"] == GEOTASK_RESULT_SCHEMA_ID


def test_schema_export_writes_file_without_stdout(tmp_path: Path) -> None:
    output_path = tmp_path / "control-evaluation.schema.json"
    result = _run_cli(
        "schema",
        "export",
        "geotask.control-evaluation",
        "--output",
        str(output_path),
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert json.loads(output_path.read_text(encoding="utf-8"))["$id"] == (
        CONTROL_EVALUATION_SCHEMA_ID
    )


def test_schema_verify_supports_text_json_and_exact_artifact() -> None:
    text_result = _run_cli("schema", "verify")
    json_result = _run_cli("schema", "verify", "--format", "json")
    exact_result = _run_cli(
        "schema",
        "verify",
        "geotask.control-evaluation",
        "--format",
        "json",
    )

    assert text_result.returncode == 0
    assert text_result.stderr == ""
    assert "Schema Bundle valid: 15 schema(s), version 1.0" in text_result.stdout
    assert text_result.stdout.count("sha256=") == 15

    assert json_result.returncode == 0
    assert json_result.stderr == ""
    all_report = json.loads(json_result.stdout)["schema_bundle_verification"]
    assert all_report["valid"] is True
    assert all_report["checked_count"] == 15
    assert all_report["diagnostics"] == []

    assert exact_result.returncode == 0
    assert exact_result.stderr == ""
    one_report = json.loads(exact_result.stdout)["schema_bundle_verification"]
    assert one_report["valid"] is True
    assert one_report["checked_count"] == 1
    assert one_report["schemas"][0]["schema_id"] == CONTROL_EVALUATION_SCHEMA_ID


def test_schema_help_and_invalid_arguments_are_stable() -> None:
    top_help = _run_cli("--help")
    help_result = _run_cli("schema", "--help")

    assert top_help.returncode == 0
    assert "schema" in top_help.stdout
    assert help_result.returncode == 0
    assert help_result.stderr == ""
    assert "schema export <artifact-id>" in help_result.stdout
    assert "schema verify [artifact-id]" in help_result.stdout
    assert "--output <file>|-" in help_result.stdout
    assert "--compact" in help_result.stdout
    assert "--format text|json" in help_result.stdout

    export_cases = (
        ("schema", "export"),
        ("schema", "export", "geotask.unknown"),
        ("schema", "export", "geotask.document", "extra"),
        ("schema", "export", "geotask.document", "--output"),
        (
            "schema",
            "export",
            "geotask.document",
            "--output",
            "one.json",
            "--output",
            "two.json",
        ),
        ("schema", "export", "geotask.document", "--compact", "--compact"),
        ("schema", "export", "geotask.document", "--unknown"),
    )
    verify_cases = (
        ("schema", "verify", "geotask.unknown"),
        ("schema", "verify", "geotask.document", "extra"),
        ("schema", "verify", "--format"),
        ("schema", "verify", "--format", "yaml"),
        (
            "schema",
            "verify",
            "--format",
            "json",
            "--format",
            "text",
        ),
        ("schema", "verify", "--unknown"),
    )

    for args in export_cases:
        result = _run_cli(*args)
        assert result.returncode != 0
        assert "schema_export_failed" in result.stderr
        assert "Traceback" not in result.stderr

    for args in verify_cases:
        result = _run_cli(*args)
        assert result.returncode != 0
        assert "schema_verify_failed" in result.stderr
        assert "Traceback" not in result.stderr

    unknown = _run_cli("schema", "unknown", "geotask.document")
    assert unknown.returncode != 0
    assert "schema_failed" in unknown.stderr
    assert "Traceback" not in unknown.stderr


def test_inspect_schemas_default_yaml_is_parseable() -> None:
    result = _run_cli("inspect", "schemas")

    assert result.returncode == 0
    assert result.stderr == ""
    payload = yaml.safe_load(result.stdout)
    registry = payload["artifact_registry"]
    assert registry["registry_version"] == "1.0"
    assert registry["artifact_count"] == 14
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
        expected_version = (
            "0.1"
            if artifact["artifact_id"].startswith(
                (
                    "geotask.agent-",
                    "geotask.runtime-",
                    "geotask.core-benchmark",
                    "geotask.observation",
                    "geotask.world-state",
                )
            )
            else "1.0"
        )
        assert artifact["schema_version"] == expected_version
        assert artifact["validation_command"].startswith(
            "geotask artifact validate "
        )
        assert "execution_boundary" in artifact


def test_inspect_schemas_can_query_one_artifact_by_stable_id() -> None:
    result = _run_cli(
        "inspect",
        "schemas",
        "geotask.control-evaluation",
        "--format",
        "json",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    registry = json.loads(result.stdout)["artifact_registry"]
    assert registry["artifact_count"] == 1
    assert registry["artifacts"][0]["artifact_id"] == "geotask.control-evaluation"
    assert registry["artifacts"][0]["wrapper_key"] == "control_evaluation"


def test_inspect_schemas_can_include_bundle_integrity_results() -> None:
    all_result = _run_cli(
        "inspect",
        "schemas",
        "--verify",
        "--format",
        "json",
    )
    exact_result = _run_cli(
        "inspect",
        "schemas",
        "geotask.execution-result",
        "--verify",
    )

    assert all_result.returncode == 0
    assert all_result.stderr == ""
    all_payload = json.loads(all_result.stdout)
    assert all_payload["artifact_registry"]["artifact_count"] == 14
    all_verification = all_payload["schema_bundle_verification"]
    assert all_verification["valid"] is True
    assert all_verification["checked_count"] == 15
    assert all_verification["diagnostics"] == []

    assert exact_result.returncode == 0
    assert exact_result.stderr == ""
    exact_payload = yaml.safe_load(exact_result.stdout)
    assert exact_payload["artifact_registry"]["artifact_count"] == 1
    assert exact_payload["artifact_registry"]["artifacts"][0]["artifact_id"] == (
        "geotask.execution-result"
    )
    exact_verification = exact_payload["schema_bundle_verification"]
    assert exact_verification["valid"] is True
    assert exact_verification["checked_count"] == 1
    assert exact_verification["schemas"][0]["schema_id"] == GEOTASK_RESULT_SCHEMA_ID


def test_inspect_schemas_verify_emits_json_before_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    invalid_report = {
        "schema_bundle_verification": {
            "valid": False,
            "bundle_version": "1.0",
            "checked_count": 15,
            "schemas": [],
            "diagnostics": [
                {
                    "code": "invalid_bundled_schema",
                    "schema_id": GEOTASK_RESULT_SCHEMA_ID,
                    "message": "digest mismatch",
                }
            ],
        }
    }
    monkeypatch.setattr(
        cli_module,
        "verify_schema_bundle",
        lambda artifact_id=None: invalid_report,
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_module.cmd_inspect(["schemas", "--verify", "--format", "json"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["artifact_registry"]["artifact_count"] == 14
    assert payload["schema_bundle_verification"]["valid"] is False
    assert payload["schema_bundle_verification"]["diagnostics"][0]["code"] == (
        "invalid_bundled_schema"
    )


def test_inspect_help_lists_singular_and_plural_schema_targets() -> None:
    top = _run_cli("inspect", "--help")
    schemas = _run_cli("inspect", "schemas", "--help")

    assert top.returncode == 0
    assert "schema|schemas" in top.stdout
    assert schemas.returncode == 0
    assert "inspect schemas" in schemas.stdout
    assert "[artifact-id]" in schemas.stdout
    assert "--format yaml|json" in schemas.stdout
    assert "--verify" in schemas.stdout
    assert "integrity results" in schemas.stdout
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
        ("inspect", "schemas", "--verify", "--verify"),
        ("inspect", "schemas", "geotask.unknown"),
        ("inspect", "schemas", "geotask.document", "extra"),
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
