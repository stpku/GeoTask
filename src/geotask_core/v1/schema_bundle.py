"""Offline access and integrity verification for GeoTask JSON Schemas."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from geotask_core.v1.artifact_registry import (
    AGENT_EVIDENCE_RECOVERY_SCHEMA_ID,
    AGENT_GENERATION_PREPARATION_SCHEMA_ID,
    AGENT_REVISION_RETRY_SCHEMA_ID,
    AGENT_REVISION_VERIFICATION_SCHEMA_ID,
    ARTIFACT_REGISTRY_SCHEMA_ID,
    ARTIFACT_VALIDATION_SCHEMA_ID,
    GEOTASK_DOCUMENT_SCHEMA_ID,
    OBSERVATION_SCHEMA_ID,
    WORLD_STATE_SCHEMA_ID,
    STATE_TRANSITION_SCHEMA_ID,
    VERIFICATION_SESSION_SCHEMA_ID,
    DISCREPANCY_REPORT_SCHEMA_ID,
    CORRECTION_REQUEST_SCHEMA_ID,
    IMPACT_GRAPH_SCHEMA_ID,
    INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID,
    WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID,
    RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID,
    OBSERVATION_MERGE_RESULT_SCHEMA_ID,
    TRAJECTORY_IDENTITY_ADJUDICATION_SCHEMA_ID,
    IDENTITY_MERGE_PROPOSAL_SCHEMA_ID,
    RUNTIME_DESCRIPTOR_SCHEMA_ID,
    RUNTIME_REQUEST_SCHEMA_ID,
    RUNTIME_RESPONSE_SCHEMA_ID,
    VERIFICATION_PROVIDER_DESCRIPTOR_SCHEMA_ID,
    VERIFICATION_REQUEST_SCHEMA_ID,
    VERIFICATION_RESPONSE_SCHEMA_ID,
    ASSURANCE_PROFILE_SCHEMA_ID,
    get_artifact_descriptor,
)
from geotask_core.v1.control_evaluation import CONTROL_EVALUATION_SCHEMA_ID
from geotask_core.v1.core_benchmark_contract import CORE_BENCHMARK_SCHEMA_ID
from geotask_core.v1.result import GEOTASK_RESULT_SCHEMA_ID


SCHEMA_BUNDLE_VERSION = "1.0"
SCHEMA_BUNDLE_MANIFEST_FILENAME = "schema-bundle-manifest-v1.0.json"
_SCHEMA_FILENAME_BY_ID = {
    ARTIFACT_REGISTRY_SCHEMA_ID: "geotask-artifact-registry-v1.0.schema.json",
    GEOTASK_DOCUMENT_SCHEMA_ID: "geotask-v1.0.schema.json",
    OBSERVATION_SCHEMA_ID: "geotask-observation-v0.1.schema.json",
    WORLD_STATE_SCHEMA_ID: "geotask-world-state-v0.1.schema.json",
    STATE_TRANSITION_SCHEMA_ID: "geotask-state-transition-v0.1.schema.json",
    VERIFICATION_SESSION_SCHEMA_ID: "geotask-verification-session-v0.1.schema.json",
    DISCREPANCY_REPORT_SCHEMA_ID: "geotask-discrepancy-report-v0.1.schema.json",
    CORRECTION_REQUEST_SCHEMA_ID: "geotask-correction-request-v0.1.schema.json",
    IMPACT_GRAPH_SCHEMA_ID: "geotask-impact-graph-v0.1.schema.json",
    INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID: (
        "geotask-incremental-reevaluation-result-v0.1.schema.json"
    ),
    WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID: (
        "geotask-world-state-materialization-result-v0.1.schema.json"
    ),
    RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID: (
        "geotask-recompute-derivation-result-v0.1.schema.json"
    ),
    OBSERVATION_MERGE_RESULT_SCHEMA_ID: (
        "geotask-observation-merge-result-v0.1.schema.json"
    ),
    TRAJECTORY_IDENTITY_ADJUDICATION_SCHEMA_ID: (
        "geotask-trajectory-identity-adjudication-v0.1.schema.json"
    ),
    IDENTITY_MERGE_PROPOSAL_SCHEMA_ID: (
        "geotask-identity-merge-proposal-v0.1.schema.json"
    ),
    GEOTASK_RESULT_SCHEMA_ID: "geotask-result-v1.0.schema.json",
    CONTROL_EVALUATION_SCHEMA_ID: "geotask-control-evaluation-v1.0.schema.json",
    AGENT_GENERATION_PREPARATION_SCHEMA_ID: (
        "geotask-agent-generation-preparation-v0.1.schema.json"
    ),
    AGENT_REVISION_VERIFICATION_SCHEMA_ID: (
        "geotask-agent-revision-verification-v0.1.schema.json"
    ),
    AGENT_REVISION_RETRY_SCHEMA_ID: "geotask-agent-revision-retry-v0.1.schema.json",
    AGENT_EVIDENCE_RECOVERY_SCHEMA_ID: "geotask-agent-integration-v0.1.schema.json",
    RUNTIME_DESCRIPTOR_SCHEMA_ID: "geotask-runtime-descriptor-v0.1.schema.json",
    RUNTIME_REQUEST_SCHEMA_ID: "geotask-runtime-request-v0.1.schema.json",
    RUNTIME_RESPONSE_SCHEMA_ID: "geotask-runtime-response-v0.1.schema.json",
    VERIFICATION_PROVIDER_DESCRIPTOR_SCHEMA_ID: (
        "geotask-verification-provider-descriptor-v0.1.schema.json"
    ),
    VERIFICATION_REQUEST_SCHEMA_ID: "geotask-verification-request-v0.1.schema.json",
    VERIFICATION_RESPONSE_SCHEMA_ID: "geotask-verification-response-v0.1.schema.json",
    ASSURANCE_PROFILE_SCHEMA_ID: "geotask-assurance-profile-v0.1.schema.json",
    CORE_BENCHMARK_SCHEMA_ID: "geotask-core-benchmark-v0.1.schema.json",
    ARTIFACT_VALIDATION_SCHEMA_ID: "geotask-artifact-validation-v1.0.schema.json",
}
BUNDLED_SCHEMA_IDS = tuple(_SCHEMA_FILENAME_BY_ID)


def _source_checkout_schema_root() -> Path | None:
    """Return the authoritative root Schema directory only in repo ``src`` layout."""

    module_path = Path(__file__).resolve()
    repository_root = module_path.parents[3]
    source_package = repository_root / "src" / "geotask_core"
    try:
        module_path.relative_to(source_package)
    except ValueError:
        return None
    schema_root = repository_root / "schemas"
    return schema_root if schema_root.is_dir() else None


def list_bundled_schema_ids() -> tuple[str, ...]:
    """Return published Schema IDs available without network access."""

    return BUNDLED_SCHEMA_IDS


def _schema_bytes(schema_id: str) -> bytes:
    try:
        filename = _SCHEMA_FILENAME_BY_ID[schema_id]
    except KeyError as exc:
        raise KeyError(f"unknown bundled GeoTask schema: {schema_id}") from exc

    resource = files("geotask_core.schemas").joinpath(filename)
    if resource.is_file():
        return resource.read_bytes()

    # Source checkouts intentionally keep one authoritative schema copy at the
    # repository root. Package builds mirror those files into geotask_core.schemas.
    # Never use this fallback from an installed package: a missing installed
    # resource must fail closed instead of silently rebuilding trust metadata.
    source_root = _source_checkout_schema_root()
    if source_root is not None:
        source_path = source_root / filename
        if source_path.is_file():
            return source_path.read_bytes()

    raise FileNotFoundError(
        f"bundled GeoTask schema is unavailable: {schema_id} ({filename})"
    )


def _computed_source_manifest() -> dict[str, Any]:
    entries: list[dict[str, object]] = []
    for schema_id, filename in _SCHEMA_FILENAME_BY_ID.items():
        raw = _schema_bytes(schema_id)
        entries.append(
            {
                "schema_id": schema_id,
                "filename": filename,
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return {
        "schema_bundle": {
            "bundle_version": SCHEMA_BUNDLE_VERSION,
            "schema_count": len(entries),
            "schemas": entries,
        }
    }


def _validate_manifest(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Schema Bundle Manifest must be an object")
    bundle = payload.get("schema_bundle")
    if not isinstance(bundle, dict):
        raise ValueError("Schema Bundle Manifest requires schema_bundle")
    if bundle.get("bundle_version") != SCHEMA_BUNDLE_VERSION:
        raise ValueError(
            "unsupported Schema Bundle Manifest version: "
            f"{bundle.get('bundle_version')!r}"
        )
    entries = bundle.get("schemas")
    if not isinstance(entries, list):
        raise ValueError("Schema Bundle Manifest schemas must be an array")
    if bundle.get("schema_count") != len(entries):
        raise ValueError("Schema Bundle Manifest schema_count mismatch")

    seen_ids: set[str] = set()
    normalized_entries: list[dict[str, object]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Schema Bundle Manifest entry {index} must be an object")
        schema_id = entry.get("schema_id")
        filename = entry.get("filename")
        size_bytes = entry.get("size_bytes")
        sha256 = entry.get("sha256")
        if (
            not isinstance(schema_id, str)
            or schema_id not in _SCHEMA_FILENAME_BY_ID
        ):
            raise ValueError(
                f"Schema Bundle Manifest contains unknown schema ID: {schema_id!r}"
            )
        if schema_id in seen_ids:
            raise ValueError(
                f"Schema Bundle Manifest contains duplicate schema ID: {schema_id}"
            )
        if filename != _SCHEMA_FILENAME_BY_ID[schema_id]:
            raise ValueError(
                f"Schema Bundle Manifest filename mismatch for {schema_id}"
            )
        if not isinstance(size_bytes, int) or size_bytes < 0:
            raise ValueError(
                f"Schema Bundle Manifest size_bytes is invalid for {schema_id}"
            )
        if (
            not isinstance(sha256, str)
            or len(sha256) != 64
            or any(char not in "0123456789abcdef" for char in sha256)
        ):
            raise ValueError(
                f"Schema Bundle Manifest sha256 is invalid for {schema_id}"
            )
        seen_ids.add(schema_id)
        normalized_entries.append(dict(entry))

    if seen_ids != set(BUNDLED_SCHEMA_IDS):
        missing = sorted(set(BUNDLED_SCHEMA_IDS) - seen_ids)
        raise ValueError(
            "Schema Bundle Manifest does not cover all public schemas: "
            + ", ".join(missing)
        )

    return {
        "schema_bundle": {
            "bundle_version": SCHEMA_BUNDLE_VERSION,
            "schema_count": len(normalized_entries),
            "schemas": normalized_entries,
        }
    }


def schema_bundle_manifest() -> dict[str, Any]:
    """Return the installed bundle manifest or a source-checkout equivalent."""

    resource = files("geotask_core.schemas").joinpath(
        SCHEMA_BUNDLE_MANIFEST_FILENAME
    )
    if resource.is_file():
        try:
            payload = json.loads(resource.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("invalid installed Schema Bundle Manifest JSON") from exc
        return _validate_manifest(payload)
    if _source_checkout_schema_root() is not None:
        return _validate_manifest(_computed_source_manifest())
    raise FileNotFoundError(
        "installed Schema Bundle Manifest is unavailable: "
        f"{SCHEMA_BUNDLE_MANIFEST_FILENAME}"
    )


def _manifest_entry(schema_id: str) -> dict[str, object]:
    manifest = schema_bundle_manifest()["schema_bundle"]
    entries = manifest["schemas"]
    for entry in entries:
        if entry["schema_id"] == schema_id:
            return dict(entry)
    raise ValueError(f"Schema Bundle Manifest is missing {schema_id}")


def _parse_and_verify_schema(schema_id: str, raw: bytes) -> dict[str, Any]:
    entry = _manifest_entry(schema_id)
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if entry["size_bytes"] != len(raw):
        raise ValueError(
            "bundled GeoTask schema size mismatch: "
            f"{schema_id} expected {entry['size_bytes']}, got {len(raw)}"
        )
    if entry["sha256"] != actual_sha256:
        raise ValueError(
            "bundled GeoTask schema digest mismatch: "
            f"{schema_id} expected {entry['sha256']}, got {actual_sha256}"
        )

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid bundled GeoTask schema JSON: {schema_id}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"bundled GeoTask schema must be an object: {schema_id}")
    if payload.get("$id") != schema_id:
        raise ValueError(
            "bundled GeoTask schema ID mismatch: "
            f"expected {schema_id}, got {payload.get('$id')!r}"
        )
    return payload


def load_bundled_schema(schema_id: str) -> dict[str, Any]:
    """Load and integrity-check one bundled JSON Schema by published ``$id``."""

    return _parse_and_verify_schema(schema_id, _schema_bytes(schema_id))


def load_artifact_schema(artifact_id: str) -> dict[str, Any]:
    """Load the integrity-checked JSON Schema for one registered artifact."""

    descriptor = get_artifact_descriptor(artifact_id)
    return load_bundled_schema(descriptor.schema_id)


def verify_schema_bundle(artifact_id: str | None = None) -> dict[str, Any]:
    """Verify all bundled schemas, or one schema selected by Artifact ID."""

    if artifact_id is None:
        schema_ids = BUNDLED_SCHEMA_IDS
    else:
        schema_ids = (get_artifact_descriptor(artifact_id).schema_id,)

    diagnostics: list[dict[str, str]] = []
    schema_reports: list[dict[str, object]] = []
    try:
        manifest = schema_bundle_manifest()["schema_bundle"]
        entries = {
            str(entry["schema_id"]): entry for entry in manifest["schemas"]
        }
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        diagnostics.append(
            {
                "code": "invalid_schema_bundle_manifest",
                "schema_id": "",
                "message": str(exc),
            }
        )
        entries = {}

    for schema_id in schema_ids:
        entry = entries.get(schema_id, {})
        item_diagnostics: list[dict[str, str]] = []
        report: dict[str, object] = {
            "schema_id": schema_id,
            "filename": _SCHEMA_FILENAME_BY_ID[schema_id],
            "expected_sha256": entry.get("sha256", ""),
            "actual_sha256": "",
            "size_bytes": 0,
            "valid": False,
            "diagnostics": item_diagnostics,
        }
        try:
            raw = _schema_bytes(schema_id)
            report["actual_sha256"] = hashlib.sha256(raw).hexdigest()
            report["size_bytes"] = len(raw)
            _parse_and_verify_schema(schema_id, raw)
            report["valid"] = True
        except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
            diagnostic = {
                "code": "invalid_bundled_schema",
                "schema_id": schema_id,
                "message": str(exc),
            }
            item_diagnostics.append(diagnostic)
            diagnostics.append(diagnostic)
        schema_reports.append(report)

    return {
        "schema_bundle_verification": {
            "valid": not diagnostics,
            "bundle_version": SCHEMA_BUNDLE_VERSION,
            "checked_count": len(schema_reports),
            "schemas": schema_reports,
            "diagnostics": diagnostics,
        }
    }


__all__ = [
    "SCHEMA_BUNDLE_VERSION",
    "SCHEMA_BUNDLE_MANIFEST_FILENAME",
    "BUNDLED_SCHEMA_IDS",
    "list_bundled_schema_ids",
    "schema_bundle_manifest",
    "load_bundled_schema",
    "load_artifact_schema",
    "verify_schema_bundle",
]
