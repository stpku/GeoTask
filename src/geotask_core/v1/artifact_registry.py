"""Public registry for versioned GeoTask machine-readable artifacts.

The registry is intentionally explicit rather than filesystem-discovered. Each
entry represents a stable public contract with a published JSON Schema,
specification, producer guidance, and validation command.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from geotask_core.v1.control_evaluation import (
    CONTROL_EVALUATION_SCHEMA_ID,
    CONTROL_EVALUATION_SCHEMA_VERSION,
)
from geotask_core.v1.result import (
    GEOTASK_RESULT_SCHEMA_ID,
    GEOTASK_RESULT_SCHEMA_VERSION,
)


ARTIFACT_REGISTRY_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-artifact-registry-v1.0.schema.json"
)
ARTIFACT_REGISTRY_VERSION = "1.0"
GEOTASK_DOCUMENT_SCHEMA_ID = (
    "https://github.com/stpku/GeoTask/schemas/geotask-v1.0.schema.json"
)
GEOTASK_DOCUMENT_SCHEMA_VERSION = "1.0"
ARTIFACT_VALIDATION_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-artifact-validation-v1.0.schema.json"
)
ARTIFACT_VALIDATION_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ArtifactDescriptor:
    """Metadata needed to discover and operate on one public artifact type."""

    artifact_id: str
    title: str
    kind: str
    schema_id: str
    schema_version: str
    schema_path: str
    specification_path: str
    wrapper_key: str | None
    generation_command: str | None
    generation_note: str
    validation_command: str
    description: str
    execution_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "title": self.title,
            "kind": self.kind,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "schema_path": self.schema_path,
            "specification_path": self.specification_path,
            "wrapper_key": self.wrapper_key,
            "generation_command": self.generation_command,
            "generation_note": self.generation_note,
            "validation_command": self.validation_command,
            "description": self.description,
            "execution_boundary": self.execution_boundary,
        }


_ARTIFACTS = (
    ArtifactDescriptor(
        artifact_id="geotask.document",
        title="GeoTask Document v1.0",
        kind="task_document",
        schema_id=GEOTASK_DOCUMENT_SCHEMA_ID,
        schema_version=GEOTASK_DOCUMENT_SCHEMA_VERSION,
        schema_path="schemas/geotask-v1.0.schema.json",
        specification_path="docs/spec/geotask-language-spec-v1.0.md",
        wrapper_key=None,
        generation_command=None,
        generation_note=(
            "Authored input. GeoTask Core does not synthesize task documents; "
            "public case starters may be created with tools/scaffold_case.py."
        ),
        validation_command=(
            "geotask artifact validate geotask.document <task.yaml>"
        ),
        description=(
            "Declarative spatial-task input consumed by GeoTask Core validation "
            "and deterministic execution."
        ),
        execution_boundary="Validation does not execute operators.",
    ),
    ArtifactDescriptor(
        artifact_id="geotask.execution-result",
        title="GeoTask Execution Result v1.0",
        kind="execution_result",
        schema_id=GEOTASK_RESULT_SCHEMA_ID,
        schema_version=GEOTASK_RESULT_SCHEMA_VERSION,
        schema_path="schemas/geotask-result-v1.0.schema.json",
        specification_path="docs/spec/geotask-result-v1.0.md",
        wrapper_key="geotask_result",
        generation_command=(
            "geotask run <task.yaml> --format v1-json "
            "--output <execution-result.json>"
        ),
        generation_note="Produced by deterministic GeoTask Core execution.",
        validation_command=(
            "geotask artifact validate geotask.execution-result "
            "<execution-result.json>"
        ),
        description=(
            "Canonical checks, outputs, summary, assurance, warnings, and errors "
            "returned by GeotaskResult.to_dict()."
        ),
        execution_boundary="Result validation does not rerun the task.",
    ),
    ArtifactDescriptor(
        artifact_id="geotask.control-evaluation",
        title="GeoTask Control Evaluation Result v1.0",
        kind="control_evaluation_result",
        schema_id=CONTROL_EVALUATION_SCHEMA_ID,
        schema_version=CONTROL_EVALUATION_SCHEMA_VERSION,
        schema_path="schemas/geotask-control-evaluation-v1.0.schema.json",
        specification_path="docs/spec/geotask-control-evaluation-v1.0.md",
        wrapper_key="control_evaluation",
        generation_command=(
            "geotask control evaluate <task.yaml> "
            "--result <execution-result.json> [--state <state.yaml>] "
            "--output <control-evaluation.json>"
        ),
        generation_note=(
            "Produced by read-only evaluation of geotask.control/1.0 conditions."
        ),
        validation_command=(
            "geotask artifact validate geotask.control-evaluation "
            "<control-evaluation.json>"
        ),
        description=(
            "Read-only control context, gate state, unknown identifiers, and "
            "blocked or eligible outputs."
        ),
        execution_boundary=(
            "Evaluation and validation never execute next_action or release outputs."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.artifact-validation-report",
        title="GeoTask Artifact Validation Report v1.0",
        kind="artifact_validation_report",
        schema_id=ARTIFACT_VALIDATION_SCHEMA_ID,
        schema_version=ARTIFACT_VALIDATION_SCHEMA_VERSION,
        schema_path="schemas/geotask-artifact-validation-v1.0.schema.json",
        specification_path="docs/spec/geotask-artifact-validation-v1.0.md",
        wrapper_key="artifact_validation",
        generation_command=(
            "geotask artifact validate <artifact-id> <file> --format json "
            "> <artifact-validation.json>"
        ),
        generation_note=(
            "Produced by read-only Registry-driven validation of a public artifact."
        ),
        validation_command=(
            "geotask artifact validate geotask.artifact-validation-report "
            "<artifact-validation.json>"
        ),
        description=(
            "Versioned validation outcome containing target Artifact identity, "
            "Schema integrity state, summary, and normalized diagnostics."
        ),
        execution_boundary=(
            "Validating a report does not repeat the original validation target, "
            "execute operators, or release outputs."
        ),
    ),
)

_ARTIFACT_BY_ID = {item.artifact_id: item for item in _ARTIFACTS}


def list_artifact_descriptors() -> tuple[ArtifactDescriptor, ...]:
    """Return the stable public artifact registry in display order."""

    return _ARTIFACTS


def get_artifact_descriptor(artifact_id: str) -> ArtifactDescriptor:
    """Return one registered artifact or raise KeyError for an unknown ID."""

    try:
        return _ARTIFACT_BY_ID[artifact_id]
    except KeyError as exc:
        raise KeyError(f"unknown GeoTask artifact: {artifact_id}") from exc


def artifact_registry_payload(artifact_id: str | None = None) -> dict[str, Any]:
    """Return the public registry payload, optionally filtered by artifact ID."""

    artifacts = (
        _ARTIFACTS
        if artifact_id is None
        else (get_artifact_descriptor(artifact_id),)
    )

    return {
        "artifact_registry": {
            "schema_id": ARTIFACT_REGISTRY_SCHEMA_ID,
            "registry_version": ARTIFACT_REGISTRY_VERSION,
            "artifact_count": len(artifacts),
            "artifacts": [item.to_dict() for item in artifacts],
        }
    }


__all__ = [
    "ARTIFACT_REGISTRY_SCHEMA_ID",
    "ARTIFACT_REGISTRY_VERSION",
    "GEOTASK_DOCUMENT_SCHEMA_ID",
    "GEOTASK_DOCUMENT_SCHEMA_VERSION",
    "ARTIFACT_VALIDATION_SCHEMA_ID",
    "ARTIFACT_VALIDATION_SCHEMA_VERSION",
    "ArtifactDescriptor",
    "list_artifact_descriptors",
    "get_artifact_descriptor",
    "artifact_registry_payload",
]
