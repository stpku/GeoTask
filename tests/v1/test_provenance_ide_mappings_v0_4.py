"""v0.4 provenance, evidence propagation, audit, and IDE Schema mappings."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "core" / "v1_provenance_evidence_audit.yaml"


def _payload() -> dict:
    from geotask_core.parser import load_geotask

    return load_geotask(EXAMPLE)


def _diagnostics(payload: dict) -> list[dict]:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    return validate_canonical(canonicalize(payload))


def test_public_provenance_example_validates_and_propagates_evidence() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical
    from geotask_core.v1.validator import validate_canonical

    canonical = canonicalize(_payload())
    assert canonical.provenance is not None
    assert validate_canonical(canonical) == []

    result = execute_canonical(canonical)
    assert result.execution.status == "completed"
    assert result.outputs == {"survey_distance": 5.0}
    assert result.checks[0].evidence_refs == ["survey_dataset"]
    assert result.checks[0].assurance_level == "local_deterministic"
    assert result.overall.status == "verified"


def test_provenance_round_trip_is_stable() -> None:
    from geotask_core.v1.canonicalizer import canonicalize, document_to_dict

    first = canonicalize(_payload())
    restored = document_to_dict(first)
    second = canonicalize(restored)

    assert restored["provenance"]["audit"]["audit_ref"] == (
        "audit:fictional:provenance-evidence-audit-v1"
    )
    assert second.provenance == first.provenance


def test_documents_without_provenance_remain_backward_compatible() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical
    from geotask_core.v1.validator import validate_canonical

    payload = _payload()
    payload.pop("provenance")
    canonical = canonicalize(payload)
    assert canonical.provenance is None
    assert validate_canonical(canonical) == []
    result = execute_canonical(canonical)
    assert result.checks[0].evidence_refs == []


def test_unknown_source_and_assertion_references_fail_closed() -> None:
    payload = _payload()
    payload["provenance"]["evidence_bindings"][0] = {
        "assertion_id": "missing_assertion",
        "source_refs": ["missing_source"],
    }
    diagnostics = _diagnostics(payload)

    assert any(
        item["code"] == "invalid_reference"
        and item["path"].endswith("assertion_id")
        for item in diagnostics
    )
    assert any(
        item["code"] == "invalid_reference"
        and item["path"].endswith("source_refs[0]")
        for item in diagnostics
    )


def test_duplicate_source_and_binding_fail_closed() -> None:
    payload = _payload()
    duplicate = copy.deepcopy(payload["provenance"]["sources"][0])
    payload["provenance"]["sources"].append(duplicate)
    payload["provenance"]["evidence_bindings"].append(
        copy.deepcopy(payload["provenance"]["evidence_bindings"][0])
    )
    diagnostics = _diagnostics(payload)

    assert any(
        item["code"] == "duplicate_id"
        and item["path"].startswith("provenance.sources")
        for item in diagnostics
    )
    assert any(
        item["code"] == "duplicate_id"
        and item["path"].startswith("provenance.evidence_bindings")
        for item in diagnostics
    )


def test_bad_hash_timestamp_and_unknown_field_fail_closed() -> None:
    payload = _payload()
    source = payload["provenance"]["sources"][0]
    source["sha256"] = "ABC"
    source["verified_at"] = "2026-07-31T08:10:00"
    source["confidence"] = 1.0
    diagnostics = _diagnostics(payload)

    assert any(item["path"].endswith("sha256") for item in diagnostics)
    assert any(item["path"].endswith("verified_at") for item in diagnostics)
    assert any(
        item["code"] == "unknown_field"
        and item["path"].endswith("confidence")
        for item in diagnostics
    )


def test_source_and_audit_time_order_fail_closed() -> None:
    payload = _payload()
    source = payload["provenance"]["sources"][0]
    source["retrieved_at"] = "2026-07-31T08:20:00+00:00"
    source["verified_at"] = "2026-07-31T08:10:00+00:00"
    payload["provenance"]["audit"]["generated_at"] = "2026-07-31T08:09:00+00:00"
    diagnostics = _diagnostics(payload)

    assert any(
        item["code"] == "invalid_interval"
        and item["path"].endswith("verified_at")
        for item in diagnostics
    )
    assert any(
        item["code"] == "invalid_interval"
        and item["path"] == "provenance.audit.generated_at"
        for item in diagnostics
    )


def test_audit_requires_valid_identity_time_and_sources() -> None:
    payload = _payload()
    audit = payload["provenance"]["audit"]
    audit["generated_by"] = ""
    audit["generated_at"] = "not-a-time"
    audit["source_refs"] = ["missing_source"]
    diagnostics = _diagnostics(payload)

    assert any(item["path"].endswith("generated_by") for item in diagnostics)
    assert any(item["path"].endswith("generated_at") for item in diagnostics)
    assert any(
        item["code"] == "invalid_reference"
        and item["path"] == "provenance.audit.source_refs[0]"
        for item in diagnostics
    )


def test_invalid_provenance_blocks_execution() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    payload = _payload()
    payload["provenance"]["evidence_bindings"][0]["source_refs"] = ["missing_source"]
    result = execute_canonical(canonicalize(payload))
    assert result.execution.status == "failed"
    assert result.overall.status == "unverifiable"
    assert any(error["code"] == "invalid_reference" for error in result.errors)


def test_cli_run_emits_bound_evidence_refs() -> None:
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "geotask_core.cli",
            "run",
            str(EXAMPLE),
            "--format",
            "v1-json",
            "--compact",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)["geotask_result"]
    assert payload["checks"][0]["evidence_refs"] == ["survey_dataset"]
    assert payload["overall"]["status"] == "verified"


def test_json_schema_covers_provenance_contract() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "geotask-v1.0.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    assert list(validator.iter_errors(_payload())) == []

    invalid = _payload()
    invalid["provenance"]["sources"][0]["sha256"] = "not-a-hash"
    assert list(validator.iter_errors(invalid))


def test_artifact_registry_exposes_portable_ide_file_patterns() -> None:
    from geotask_core.v1.artifact_registry import artifact_registry_payload

    payload = artifact_registry_payload()
    artifacts = payload["artifact_registry"]["artifacts"]
    assert artifacts
    assert all("ide_file_patterns" in item for item in artifacts)

    document = next(item for item in artifacts if item["artifact_id"] == "geotask.document")
    assert "*.geotask.yaml" in document["ide_file_patterns"]
    assert "examples/core/**/*.yaml" in document["ide_file_patterns"]

    execution_result = next(
        item for item in artifacts if item["artifact_id"] == "geotask.execution-result"
    )
    assert "*.geotask-result.json" in execution_result["ide_file_patterns"]


def test_artifact_registry_schema_accepts_ide_mappings() -> None:
    from geotask_core.v1.artifact_registry import artifact_registry_payload

    schema = json.loads(
        (ROOT / "schemas" / "geotask-artifact-registry-v1.0.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(artifact_registry_payload())) == []


def test_cli_inspect_schemas_emits_ide_patterns() -> None:
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "geotask_core.cli",
            "inspect",
            "schemas",
            "geotask.document",
            "--format",
            "json",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    document = payload["artifact_registry"]["artifacts"][0]
    assert document["artifact_id"] == "geotask.document"
    assert "*.geotask.yaml" in document["ide_file_patterns"]
