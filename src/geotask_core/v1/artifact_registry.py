"""Public registry for versioned GeoTask machine-readable artifacts.

The registry is intentionally explicit rather than filesystem-discovered. Each
entry represents a stable public contract with a published JSON Schema,
specification, producer guidance, and validation command.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
from geotask_core.v1.control_evaluation import (
    CONTROL_EVALUATION_SCHEMA_ID,
    CONTROL_EVALUATION_SCHEMA_VERSION,
)
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
from geotask_core.v1.state_transition import (
    STATE_TRANSITION_SCHEMA_ID,
    STATE_TRANSITION_SCHEMA_VERSION,
)
from geotask_core.v1.verification_session import (
    VERIFICATION_SESSION_SCHEMA_ID,
    VERIFICATION_SESSION_SCHEMA_VERSION,
)
from geotask_core.v1.discrepancy_report import (
    DISCREPANCY_REPORT_SCHEMA_ID,
    DISCREPANCY_REPORT_SCHEMA_VERSION,
)
from geotask_core.v1.correction_request import (
    CORRECTION_REQUEST_SCHEMA_ID,
    CORRECTION_REQUEST_SCHEMA_VERSION,
)
from geotask_core.v1.impact_graph import (
    IMPACT_GRAPH_SCHEMA_ID,
    IMPACT_GRAPH_SCHEMA_VERSION,
)
from geotask_core.v1.incremental_reevaluation_result import (
    INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID,
    INCREMENTAL_REEVALUATION_RESULT_SCHEMA_VERSION,
)
from geotask_core.v1.world_state_materialization import (
    WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID,
    WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_VERSION,
)
from geotask_core.v1.recompute_derivation import (
    RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID,
    RECOMPUTE_DERIVATION_RESULT_SCHEMA_VERSION,
)
from geotask_core.v1.observation_merge import (
    OBSERVATION_MERGE_RESULT_SCHEMA_ID,
    OBSERVATION_MERGE_RESULT_SCHEMA_VERSION,
)
from geotask_core.v1.trajectory_identity_adjudication import (
    TRAJECTORY_IDENTITY_ADJUDICATION_SCHEMA_ID,
    TRAJECTORY_IDENTITY_ADJUDICATION_SCHEMA_VERSION,
)
from geotask_core.v1.identity_merge_proposal import (
    IDENTITY_MERGE_PROPOSAL_SCHEMA_ID,
    IDENTITY_MERGE_PROPOSAL_SCHEMA_VERSION,
)
from geotask_core.v1.identity_merge_approval_record import (
    IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_ID,
    IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_VERSION,
)
from geotask_core.v1.object_graph_change_request import (
    OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_ID,
    OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_VERSION,
)
from geotask_core.v1.object_graph_change_application_approval_record import (
    OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_ID,
    OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_VERSION,
)
from geotask_core.v1.result import (
    GEOTASK_RESULT_SCHEMA_ID,
    GEOTASK_RESULT_SCHEMA_VERSION,
)
from geotask_core.v1.runtime_interface import (
    RUNTIME_DESCRIPTOR_SCHEMA_ID,
    RUNTIME_DESCRIPTOR_SCHEMA_VERSION,
    RUNTIME_REQUEST_SCHEMA_ID,
    RUNTIME_REQUEST_SCHEMA_VERSION,
    RUNTIME_RESPONSE_SCHEMA_ID,
    RUNTIME_RESPONSE_SCHEMA_VERSION,
)
from geotask_core.v1.verification_provider import (
    ASSURANCE_PROFILE_SCHEMA_ID,
    ASSURANCE_PROFILE_SCHEMA_VERSION,
    VERIFICATION_PROVIDER_DESCRIPTOR_SCHEMA_ID,
    VERIFICATION_PROVIDER_DESCRIPTOR_SCHEMA_VERSION,
    VERIFICATION_REQUEST_SCHEMA_ID,
    VERIFICATION_REQUEST_SCHEMA_VERSION,
    VERIFICATION_RESPONSE_SCHEMA_ID,
    VERIFICATION_RESPONSE_SCHEMA_VERSION,
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


_IDE_FILE_PATTERNS: dict[str, tuple[str, ...]] = {
    "geotask.document": (
        "*.geotask.yaml",
        "*.geotask.yml",
        "examples/core/**/*.yaml",
        "examples/core/**/*.yml",
    ),
    "geotask.observation": (
        "*.geotask-observation.json",
        "observation*.json",
        "examples/core/observation*.json",
    ),
    "geotask.world-state": (
        "*.geotask-world-state.json",
        "world-state*.json",
        "world_state*.json",
        "examples/core/world_state*.json",
    ),
    "geotask.state-transition": (
        "*.geotask-state-transition.json",
        "state-transition*.json",
        "state_transition*.json",
        "examples/core/state_transition*.json",
    ),
    "geotask.verification-session": (
        "*.geotask-verification-session.json",
        "verification-session*.json",
        "verification_session*.json",
        "examples/core/verification_session*.json",
    ),
    "geotask.discrepancy-report": (
        "*.geotask-discrepancy-report.json",
        "discrepancy-report*.json",
        "discrepancy_report*.json",
        "examples/core/discrepancy_report*.json",
    ),
    "geotask.correction-request": (
        "*.geotask-correction-request.json",
        "correction-request*.json",
        "correction_request*.json",
        "examples/core/correction_request*.json",
    ),
    "geotask.impact-graph": (
        "*.geotask-impact-graph.json",
        "impact-graph*.json",
        "impact_graph*.json",
        "examples/core/impact_graph*.json",
    ),
    "geotask.incremental-reevaluation-result": (
        "*.geotask-incremental-reevaluation-result.json",
        "incremental-reevaluation-result*.json",
        "incremental_reevaluation_result*.json",
        "examples/core/incremental_reevaluation_result*.json",
    ),
    "geotask.world-state-materialization-result": (
        "*.geotask-world-state-materialization-result.json",
        "world-state-materialization-result*.json",
        "world_state_materialization_result*.json",
        "examples/core/world_state_materialization_result*.json",
    ),
    "geotask.recompute-derivation-result": (
        "*.geotask-recompute-derivation-result.json",
        "recompute-derivation-result*.json",
        "recompute_derivation_result*.json",
        "examples/core/recompute_derivation_result*.json",
    ),
    "geotask.observation-merge-result": (
        "*.geotask-observation-merge-result.json",
        "observation-merge-result*.json",
        "observation_merge_result*.json",
        "examples/core/observation_merge_result*.json",
    ),
    "geotask.trajectory-identity-adjudication": (
        "*.geotask-trajectory-identity-adjudication.json",
        "trajectory-identity-adjudication*.json",
        "trajectory_identity_adjudication*.json",
        "examples/core/trajectory_identity_adjudication*.json",
    ),
    "geotask.identity-merge-proposal": (
        "*.geotask-identity-merge-proposal.json",
        "identity-merge-proposal*.json",
        "identity_merge_proposal*.json",
        "examples/core/identity_merge_proposal*.json",
    ),
    "geotask.identity-merge-approval-record": (
        "*.geotask-identity-merge-approval-record.json",
        "identity-merge-approval-record*.json",
        "identity_merge_approval_record*.json",
        "examples/core/identity_merge_approval_record*.json",
    ),
    "geotask.object-graph-change-request": (
        "*.geotask-object-graph-change-request.json",
        "object-graph-change-request*.json",
        "object_graph_change_request*.json",
        "examples/core/object_graph_change_request*.json",
    ),
    "geotask.object-graph-change-application-approval-record": (
        "*.geotask-object-graph-change-application-approval-record.json",
        "object-graph-change-application-approval-record*.json",
        "object_graph_change_application_approval_record*.json",
        "examples/core/object_graph_change_application_approval_record*.json",
    ),
    "geotask.execution-result": ("*.geotask-result.json", "execution-result*.json"),
    "geotask.control-evaluation": ("*control-evaluation*.json",),
    "geotask.agent-generation-preparation": ("*preparation-report*.json",),
    "geotask.agent-revision-verification": ("*revision-verification*.json",),
    "geotask.agent-revision-retry": ("*retry-report*.json",),
    "geotask.agent-evidence-recovery": ("*recovery-report*.json",),
    "geotask.runtime-descriptor": ("*runtime-descriptor*.json",),
    "geotask.runtime-request": ("*runtime-request*.json",),
    "geotask.runtime-response": ("*runtime-response*.json",),
    "geotask.verification-provider-descriptor": ("*verification-provider-descriptor*.json",),
    "geotask.verification-request": ("*verification-request*.json",),
    "geotask.verification-response": ("*verification-response*.json",),
    "geotask.assurance-profile": ("*assurance-profile*.json",),
    "geotask.core-benchmark-report": ("*core-benchmark*.json",),
    "geotask.artifact-validation-report": ("*artifact-validation*.json",),
}


def _ide_file_patterns(artifact_id: str) -> list[str]:
    """Return portable glob patterns suitable for IDE Schema association."""
    return list(_IDE_FILE_PATTERNS.get(artifact_id, ()))


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
            "ide_file_patterns": _ide_file_patterns(self.artifact_id),
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
        artifact_id="geotask.observation",
        title="GeoTask Observation v0.1",
        kind="world_observation",
        schema_id=OBSERVATION_SCHEMA_ID,
        schema_version=OBSERVATION_SCHEMA_VERSION,
        schema_path="schemas/geotask-observation-v0.1.schema.json",
        specification_path="docs/spec/geotask-observation-v0.1.md",
        wrapper_key="observation",
        generation_command=None,
        generation_note=(
            "Authored by a model, sensor adapter, external system, or human-facing "
            "tool. Core does not synthesize observations or fetch their sources."
        ),
        validation_command=(
            "geotask artifact validate geotask.observation <observation.json>"
        ),
        description=(
            "Source-bound, timestamped world claims with producer identity, declared "
            "uncertainty, evidence references, and optional supersession links."
        ),
        execution_boundary=(
            "Validation does not verify claim truth, resolve references, update a "
            "WorldState, invoke a Provider, or authorize action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.world-state",
        title="GeoTask World State v0.1",
        kind="world_state_snapshot",
        schema_id=WORLD_STATE_SCHEMA_ID,
        schema_version=WORLD_STATE_SCHEMA_VERSION,
        schema_path="schemas/geotask-world-state-v0.1.schema.json",
        specification_path="docs/spec/geotask-world-state-v0.1.md",
        wrapper_key="world_state",
        generation_command=None,
        generation_note=(
            "Authored or materialized by an Agent or Runtime from explicit inputs. "
            "Core validates snapshots but does not ingest observations or compute transitions."
        ),
        validation_command=(
            "geotask artifact validate geotask.world-state <world-state.json>"
        ),
        description=(
            "Versioned point-in-time snapshot of world objects, attributes, relations, "
            "validity, uncertainty, and closed Observation/Evidence references."
        ),
        execution_boundary=(
            "Validation does not fetch evidence, verify external truth, merge observations, "
            "compute a State Transition, rerun tasks, or authorize action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.state-transition",
        title="GeoTask State Transition v0.1",
        kind="world_state_transition",
        schema_id=STATE_TRANSITION_SCHEMA_ID,
        schema_version=STATE_TRANSITION_SCHEMA_VERSION,
        schema_path="schemas/geotask-state-transition-v0.1.schema.json",
        specification_path="docs/spec/geotask-state-transition-v0.1.md",
        wrapper_key="state_transition",
        generation_command=None,
        generation_note=(
            "Authored or materialized by an Agent or Runtime after explicit state comparison. "
            "Core validates transition records and snapshot bindings but does not compute or apply changes."
        ),
        validation_command=(
            "geotask artifact validate geotask.state-transition <state-transition.json>"
        ),
        description=(
            "Auditable binding between two World State snapshots with Observation-traced "
            "object, attribute, relation, and action-eligibility changes."
        ),
        execution_boundary=(
            "Validation does not compare snapshots, apply changes, materialize a World State, "
            "verify external truth, rerun tasks, or authorize action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.verification-session",
        title="GeoTask Verification Session v0.1",
        kind="verification_session",
        schema_id=VERIFICATION_SESSION_SCHEMA_ID,
        schema_version=VERIFICATION_SESSION_SCHEMA_VERSION,
        schema_path="schemas/geotask-verification-session-v0.1.schema.json",
        specification_path="docs/spec/geotask-verification-session-v0.1.md",
        wrapper_key="verification_session",
        generation_command=None,
        generation_note=(
            "Authored or materialized by an Agent or Runtime after the referenced World State "
            "and artifacts already exist. Core validates the audit snapshot and explicit bindings."
        ),
        validation_command=(
            "geotask artifact validate geotask.verification-session <verification-session.json>"
        ),
        description=(
            "Immutable verification audit snapshot binding one World State to exact serialized "
            "tasks, results, controls, transitions, discrepancies, eligibility, and recheck triggers."
        ),
        execution_boundary=(
            "Validation does not validate linked artifact semantics, execute tasks, evaluate controls, "
            "run rechecks, verify external truth, materialize state, or authorize action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.discrepancy-report",
        title="GeoTask Discrepancy Report v0.1",
        kind="discrepancy_report",
        schema_id=DISCREPANCY_REPORT_SCHEMA_ID,
        schema_version=DISCREPANCY_REPORT_SCHEMA_VERSION,
        schema_path="schemas/geotask-discrepancy-report-v0.1.schema.json",
        specification_path="docs/spec/geotask-discrepancy-report-v0.1.md",
        wrapper_key="discrepancy_report",
        generation_command=None,
        generation_note=(
            "Authored or materialized by an Agent or Runtime after explicit source comparison. "
            "Core validates the report and explicit bindings but does not discover discrepancies."
        ),
        validation_command=(
            "geotask artifact validate geotask.discrepancy-report <discrepancy-report.json>"
        ),
        description=(
            "Auditable discrepancy findings bound to one World State and exact source artifacts, "
            "including expected/observed values, downstream impact, and bounded correction scope."
        ),
        execution_boundary=(
            "Validation does not compare source contents, create a Correction Request, apply a "
            "correction, materialize state, run rechecks, verify external truth, or authorize action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.correction-request",
        title="GeoTask Correction Request v0.1",
        kind="correction_request",
        schema_id=CORRECTION_REQUEST_SCHEMA_ID,
        schema_version=CORRECTION_REQUEST_SCHEMA_VERSION,
        schema_path="schemas/geotask-correction-request-v0.1.schema.json",
        specification_path="docs/spec/geotask-correction-request-v0.1.md",
        wrapper_key="correction_request",
        generation_command=None,
        generation_note=(
            "Authored or materialized by an Agent or Runtime after a bound Discrepancy Report exists. "
            "Core validates the request and explicit bindings but does not apply corrections."
        ),
        validation_command=(
            "geotask artifact validate geotask.correction-request <correction-request.json>"
        ),
        description=(
            "Bounded successor-World-State request with exact base/report bindings, allowed changes, "
            "acceptance criteria, immutable-path preservation, and output/action gates."
        ),
        execution_boundary=(
            "Validation does not edit the base snapshot, materialize a successor World State, "
            "evaluate acceptance criteria, resolve discrepancies, rerun tasks, release outputs, "
            "or authorize actions."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.impact-graph",
        title="GeoTask Impact Graph v0.1",
        kind="impact_graph",
        schema_id=IMPACT_GRAPH_SCHEMA_ID,
        schema_version=IMPACT_GRAPH_SCHEMA_VERSION,
        schema_path="schemas/geotask-impact-graph-v0.1.schema.json",
        specification_path="docs/spec/geotask-impact-graph-v0.1.md",
        wrapper_key="impact_graph",
        generation_command=None,
        generation_note=(
            "Authored or materialized by an Agent or Runtime after explicit impact analysis. "
            "Core validates the declared DAG and source bindings but does not compute propagation."
        ),
        validation_command=(
            "geotask artifact validate geotask.impact-graph <impact-graph.json>"
        ),
        description=(
            "Finite source-bound impact DAG connecting discrepancies and bounded corrections to "
            "affected state paths, assertions, outputs, actions, and reevaluation targets."
        ),
        execution_boundary=(
            "Validation does not discover impact, execute propagation, apply correction, materialize "
            "state, evaluate reevaluation targets, release outputs, or authorize actions."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.incremental-reevaluation-result",
        title="GeoTask Incremental Reevaluation Result v0.1",
        kind="incremental_reevaluation_result",
        schema_id=INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID,
        schema_version=INCREMENTAL_REEVALUATION_RESULT_SCHEMA_VERSION,
        schema_path=(
            "schemas/geotask-incremental-reevaluation-result-v0.1.schema.json"
        ),
        specification_path=(
            "docs/spec/geotask-incremental-reevaluation-result-v0.1.md"
        ),
        wrapper_key="incremental_reevaluation_result",
        generation_command=None,
        generation_note=(
            "Authored or materialized by an Agent or Runtime after bounded reevaluation. "
            "Core validates the result and explicit bindings but does not execute reevaluation."
        ),
        validation_command=(
            "geotask artifact validate geotask.incremental-reevaluation-result "
            "<incremental-reevaluation-result.json>"
        ),
        description=(
            "Immutable bounded result covering an Impact Graph, successor World State, node and "
            "target outcomes, acceptance criteria, discrepancy resolution, and output/action gates."
        ),
        execution_boundary=(
            "Validation does not run reevaluation, generate a successor World State, discover "
            "impact, execute propagation, authorize an action, or execute an action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.world-state-materialization-result",
        title="GeoTask World State Materialization Result v0.1",
        kind="world_state_materialization_result",
        schema_id=WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_ID,
        schema_version=WORLD_STATE_MATERIALIZATION_RESULT_SCHEMA_VERSION,
        schema_path=(
            "schemas/geotask-world-state-materialization-result-v0.1.schema.json"
        ),
        specification_path=(
            "docs/spec/geotask-world-state-materialization-result-v0.1.md"
        ),
        wrapper_key="world_state_materialization_result",
        generation_command=None,
        generation_note=(
            "Produced by bounded Core materialization from one exact base World State, "
            "one required Correction Request, and explicit recompute values."
        ),
        validation_command=(
            "geotask artifact validate geotask.world-state-materialization-result "
            "<world-state-materialization-result.json>"
        ),
        description=(
            "Immutable result binding exact base/request/successor bytes and every applied "
            "bounded change while preserving output and action gates for later reevaluation."
        ),
        execution_boundary=(
            "Validation does not prove exact bindings or execution; materialization does not "
            "guess recompute values, merge observations, run reevaluation, release outputs, "
            "verify external truth, authorize actions, or execute actions."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.recompute-derivation-result",
        title="GeoTask Recompute Derivation Result v0.1",
        kind="recompute_derivation_result",
        schema_id=RECOMPUTE_DERIVATION_RESULT_SCHEMA_ID,
        schema_version=RECOMPUTE_DERIVATION_RESULT_SCHEMA_VERSION,
        schema_path="schemas/geotask-recompute-derivation-result-v0.1.schema.json",
        specification_path="docs/spec/geotask-recompute-derivation-result-v0.1.md",
        wrapper_key="recompute_derivation_result",
        generation_command=None,
        generation_note=(
            "Produced by deterministic Core derivation from one exact base World State, "
            "one required Correction Request, and exact Observation/GeoTask source paths."
        ),
        validation_command=(
            "geotask artifact validate geotask.recompute-derivation-result "
            "<recompute-derivation-result.json>"
        ),
        description=(
            "Immutable source-bound result that derives every requested recompute value through "
            "small allowlisted deterministic methods and provides a complete materializer input map."
        ),
        execution_boundary=(
            "Validation does not prove exact source bindings or evaluate derivations. Explicit binding "
            "validation and evaluation never execute arbitrary code, fetch evidence, call a model, "
            "materialize state, run reevaluation, release outputs, verify truth, or authorize actions."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.observation-merge-result",
        title="GeoTask Observation Merge Result v0.1",
        kind="observation_merge_result",
        schema_id=OBSERVATION_MERGE_RESULT_SCHEMA_ID,
        schema_version=OBSERVATION_MERGE_RESULT_SCHEMA_VERSION,
        schema_path="schemas/geotask-observation-merge-result-v0.1.schema.json",
        specification_path="docs/spec/geotask-observation-merge-result-v0.1.md",
        wrapper_key="observation_merge_result",
        generation_command=None,
        generation_note=(
            "Produced by bounded Core merge from one exact base World State, exact Observation "
            "bytes, complete explicit claim-to-existing-target mappings, and an explicit target-scoped "
            "conflict policy whenever multiple claims target the same path."
        ),
        validation_command=(
            "geotask artifact validate geotask.observation-merge-result "
            "<observation-merge-result.json>"
        ),
        description=(
            "Immutable result binding exact base, Observation, and successor bytes while applying "
            "every claim once to an existing attribute or relation target and auditing caller-declared "
            "same-target semantic equality or complete explicit precedence."
        ),
        execution_boundary=(
            "Validation does not prove exact bindings or replay the merge. Merge does not create "
            "objects or relations, infer identities, invent precedence, rank sources, resolve an "
            "undeclared ambiguous conflict, compute a State Transition, propagate impact, run "
            "reevaluation, release outputs, verify truth, or authorize actions."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.trajectory-identity-adjudication",
        title="GeoTask Trajectory Identity Adjudication v0.1",
        kind="trajectory_identity_adjudication",
        schema_id=TRAJECTORY_IDENTITY_ADJUDICATION_SCHEMA_ID,
        schema_version=TRAJECTORY_IDENTITY_ADJUDICATION_SCHEMA_VERSION,
        schema_path=(
            "schemas/geotask-trajectory-identity-adjudication-v0.1.schema.json"
        ),
        specification_path=(
            "docs/spec/geotask-trajectory-identity-adjudication-v0.1.md"
        ),
        wrapper_key="trajectory_identity_adjudication",
        generation_command=None,
        generation_note=(
            "Produced by exact-bound Core adjudication from one GT37 identity candidate, "
            "one Verification Request, one Assurance Profile, and matching Provider "
            "Descriptor/Verification Response pairs."
        ),
        validation_command=(
            "geotask artifact validate geotask.trajectory-identity-adjudication "
            "<trajectory-identity-adjudication.json>"
        ),
        description=(
            "Auditable identity decision that records independent evidence and may recommend "
            "identity-merge review while preserving both original subjects and references."
        ),
        execution_boundary=(
            "Generic validation does not recheck exact source bytes. Binding validation and "
            "adjudication do not fetch external truth, merge identities, mutate subject_ref, "
            "release production output, authorize action, or execute action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.identity-merge-proposal",
        title="GeoTask Identity Merge Proposal v0.1",
        kind="identity_merge_proposal",
        schema_id=IDENTITY_MERGE_PROPOSAL_SCHEMA_ID,
        schema_version=IDENTITY_MERGE_PROPOSAL_SCHEMA_VERSION,
        schema_path="schemas/geotask-identity-merge-proposal-v0.1.schema.json",
        specification_path="docs/spec/geotask-identity-merge-proposal-v0.1.md",
        wrapper_key="identity_merge_proposal",
        generation_command=None,
        generation_note=(
            "Produced by bounded Core proposal generation from one exact GT38 identity "
            "adjudication plus caller-declared canonical-subject selection, rationale, "
            "and approval roles."
        ),
        validation_command=(
            "geotask artifact validate geotask.identity-merge-proposal "
            "<identity-merge-proposal.json>"
        ),
        description=(
            "Review-only proposal that selects one existing canonical subject, scopes one "
            "subject-reference rewrite, preserves the other subject as an alias, and records "
            "blocking, withdrawal, approval, and reversal requirements."
        ),
        execution_boundary=(
            "Generic validation does not recheck exact source bytes. Proposal generation and "
            "binding validation do not approve or apply the proposal, create a new identity, "
            "delete aliases, mutate the object graph or World State, release production output, "
            "authorize action, or execute action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.identity-merge-approval-record",
        title="GeoTask Identity Merge Approval Record v0.1",
        kind="identity_merge_approval_record",
        schema_id=IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_ID,
        schema_version=IDENTITY_MERGE_APPROVAL_RECORD_SCHEMA_VERSION,
        schema_path=(
            "schemas/geotask-identity-merge-approval-record-v0.1.schema.json"
        ),
        specification_path=(
            "docs/spec/geotask-identity-merge-approval-record-v0.1.md"
        ),
        wrapper_key="identity_merge_approval_record",
        generation_command=None,
        generation_note=(
            "Produced from one exact GT39 proposal and one explicit decision for every "
            "required approval role."
        ),
        validation_command=(
            "geotask artifact validate geotask.identity-merge-approval-record "
            "<identity-merge-approval-record.json>"
        ),
        description=(
            "Auditable approval record that aggregates approved, rejected, or "
            "evidence-required role decisions and may make a later bounded change "
            "request eligible."
        ),
        execution_boundary=(
            "Generic validation does not recheck exact proposal bytes. Approval does "
            "not apply the merge, rewrite subject references, mutate the object graph "
            "or World State, release production output, authorize action, or execute action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.object-graph-change-request",
        title="GeoTask Object Graph Change Request v0.1",
        kind="object_graph_change_request",
        schema_id=OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_ID,
        schema_version=OBJECT_GRAPH_CHANGE_REQUEST_SCHEMA_VERSION,
        schema_path="schemas/geotask-object-graph-change-request-v0.1.schema.json",
        specification_path="docs/spec/geotask-object-graph-change-request-v0.1.md",
        wrapper_key="object_graph_change_request",
        generation_command=None,
        generation_note=(
            "Produced from exact GT39 proposal and GT40 approved-record bytes. Core "
            "derives the closed rewrite scope rather than accepting arbitrary paths."
        ),
        validation_command=(
            "geotask artifact validate geotask.object-graph-change-request "
            "<object-graph-change-request.json>"
        ),
        description=(
            "Bounded request for one trajectory subject-reference rewrite with retained "
            "alias history, preconditions, acceptance criteria, and rollback requirements."
        ),
        execution_boundary=(
            "Generic validation does not recheck exact GT39/GT40 bytes. The request does "
            "not authorize or apply a change, mutate the object graph or World State, "
            "release production output, authorize action, or execute action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.object-graph-change-application-approval-record",
        title="GeoTask Object Graph Change Application Approval Record v0.1",
        kind="object_graph_change_application_approval_record",
        schema_id=OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_ID,
        schema_version=OBJECT_GRAPH_CHANGE_APPLICATION_APPROVAL_RECORD_SCHEMA_VERSION,
        schema_path=(
            "schemas/geotask-object-graph-change-application-approval-record-v0.1.schema.json"
        ),
        specification_path=(
            "docs/spec/geotask-object-graph-change-application-approval-record-v0.1.md"
        ),
        wrapper_key="object_graph_change_application_approval_record",
        generation_command=None,
        generation_note=(
            "Produced from exact GT41 request bytes, caller-declared required "
            "application-approval roles, and one explicit decision per role."
        ),
        validation_command=(
            "geotask artifact validate "
            "geotask.object-graph-change-application-approval-record "
            "<object-graph-change-application-approval-record.json>"
        ),
        description=(
            "Auditable application-approval record that aggregates approved, "
            "rejected, or evidence-required decisions and may make a later bounded "
            "change application eligible."
        ),
        execution_boundary=(
            "Generic validation does not recheck exact GT41 bytes. Approval does not "
            "authorize or apply the change, mutate subject references, the object graph "
            "or World State, release production output, authorize action, or execute action."
        ),
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
        artifact_id="geotask.agent-generation-preparation",
        title="GeoTask Agent Generation Preparation Report v0.1",
        kind="agent_generation_preparation_report",
        schema_id=AGENT_GENERATION_PREPARATION_SCHEMA_ID,
        schema_version=AGENT_GENERATION_PREPARATION_SCHEMA_VERSION,
        schema_path=(
            "schemas/geotask-agent-generation-preparation-v0.1.schema.json"
        ),
        specification_path="docs/spec/geotask-agent-integration-profile-v0.1.md",
        wrapper_key="agent_generation_preparation",
        generation_command=(
            "geotask agent prepare <generated.yaml> "
            "--output <preparation-report.json>"
        ),
        generation_note=(
            "Produced by fail-closed validation, mechanical protocol repair, "
            "revalidation, and optional deterministic local execution."
        ),
        validation_command=(
            "geotask artifact validate geotask.agent-generation-preparation "
            "<preparation-report.json>"
        ),
        description=(
            "Versioned Agent draft preparation trace containing diagnostics, "
            "mechanical repairs, revision request, prepared document, and result."
        ),
        execution_boundary=(
            "Validating the report does not prepare or execute the embedded task."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.agent-revision-verification",
        title="GeoTask Agent Revision Verification Report v0.1",
        kind="agent_revision_verification_report",
        schema_id=AGENT_REVISION_VERIFICATION_SCHEMA_ID,
        schema_version=AGENT_REVISION_VERIFICATION_SCHEMA_VERSION,
        schema_path=(
            "schemas/geotask-agent-revision-verification-v0.1.schema.json"
        ),
        specification_path="docs/spec/geotask-agent-integration-profile-v0.1.md",
        wrapper_key="agent_revision_verification",
        generation_command=(
            "geotask agent retry <blocked-report.json> <revised.yaml> "
            "--verification-output <revision-verification.json>"
        ),
        generation_note=(
            "Produced directly by agent retry after deterministic changed-path "
            "verification and before any re-execution."
        ),
        validation_command=(
            "geotask artifact validate geotask.agent-revision-verification "
            "<revision-verification.json>"
        ),
        description=(
            "Requested-path diff decision with stable document fingerprints, "
            "resolved changes, and fail-closed violations."
        ),
        execution_boundary=(
            "Validating the report does not rerun diff verification or execute a task."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.agent-revision-retry",
        title="GeoTask Agent Revision Retry Report v0.1",
        kind="agent_revision_retry_report",
        schema_id=AGENT_REVISION_RETRY_SCHEMA_ID,
        schema_version=AGENT_REVISION_RETRY_SCHEMA_VERSION,
        schema_path="schemas/geotask-agent-revision-retry-v0.1.schema.json",
        specification_path="docs/spec/geotask-agent-integration-profile-v0.1.md",
        wrapper_key="agent_revision_retry",
        generation_command=(
            "geotask agent retry <blocked-report.json> <revised.yaml> "
            "--output <retry-report.json>"
        ),
        generation_note=(
            "Produced by guarded revision verification followed by fail-closed "
            "preparation and deterministic execution only after acceptance."
        ),
        validation_command=(
            "geotask artifact validate geotask.agent-revision-retry "
            "<retry-report.json>"
        ),
        description=(
            "Composite guarded retry trace containing the revision decision and "
            "optional preparation/execution report."
        ),
        execution_boundary=(
            "Validating the report does not repeat the retry, preparation, or task."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.agent-evidence-recovery",
        title="GeoTask Agent Evidence Recovery Report v0.1",
        kind="agent_evidence_recovery_report",
        schema_id=AGENT_EVIDENCE_RECOVERY_SCHEMA_ID,
        schema_version=AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION,
        schema_path="schemas/geotask-agent-integration-v0.1.schema.json",
        specification_path="docs/spec/geotask-agent-integration-profile-v0.1.md",
        wrapper_key="agent_integration",
        generation_command=(
            "geotask agent recover <task.yaml> --evidence <state.yaml> "
            "--output <recovery-report.json>"
        ),
        generation_note=(
            "Produced by fail-closed evidence completeness checks, read-only control "
            "evaluation, and deterministic re-execution only after resume conditions pass."
        ),
        validation_command=(
            "geotask artifact validate geotask.agent-evidence-recovery "
            "<recovery-report.json>"
        ),
        description=(
            "Auditable before/resume/after evidence-recovery trace containing execution "
            "results, control evaluations, blocked outputs, and explicit safety flags."
        ),
        execution_boundary=(
            "Validating the report does not reacquire evidence, rerun recovery, execute "
            "next_action, or release outputs."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.runtime-descriptor",
        title="GeoTask Runtime Descriptor v0.1",
        kind="runtime_descriptor",
        schema_id=RUNTIME_DESCRIPTOR_SCHEMA_ID,
        schema_version=RUNTIME_DESCRIPTOR_SCHEMA_VERSION,
        schema_path="schemas/geotask-runtime-descriptor-v0.1.schema.json",
        specification_path="docs/spec/geotask-runtime-interface-profile-v0.1.md",
        wrapper_key="runtime_descriptor",
        generation_command="geotask runtime inspect --format json",
        generation_note=(
            "Produced by a RuntimeAdapter capability advertisement. The public "
            "reference descriptor is deterministic and fail-closed."
        ),
        validation_command=(
            "geotask artifact validate geotask.runtime-descriptor "
            "<runtime-descriptor.json>"
        ),
        description=(
            "Versioned Runtime identity, capability, operation, authorization, "
            "side-effect, and audit boundary advertisement."
        ),
        execution_boundary=(
            "Validating a descriptor does not connect to or invoke a Runtime."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.runtime-request",
        title="GeoTask Runtime Request v0.1",
        kind="runtime_request",
        schema_id=RUNTIME_REQUEST_SCHEMA_ID,
        schema_version=RUNTIME_REQUEST_SCHEMA_VERSION,
        schema_path="schemas/geotask-runtime-request-v0.1.schema.json",
        specification_path="docs/spec/geotask-runtime-interface-profile-v0.1.md",
        wrapper_key="runtime_request",
        generation_command=None,
        generation_note=(
            "Authored by a caller after inspecting a Runtime Descriptor. Core does "
            "not synthesize credentials, authorization, or production requests."
        ),
        validation_command=(
            "geotask artifact validate geotask.runtime-request "
            "<runtime-request.json>"
        ),
        description=(
            "Idempotent operation request carrying registered input Artifacts, an "
            "explicit output contract, and an opaque authorization reference."
        ),
        execution_boundary=(
            "Validating a request never submits it to a Runtime or executes side effects."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.runtime-response",
        title="GeoTask Runtime Response v0.1",
        kind="runtime_response",
        schema_id=RUNTIME_RESPONSE_SCHEMA_ID,
        schema_version=RUNTIME_RESPONSE_SCHEMA_VERSION,
        schema_path="schemas/geotask-runtime-response-v0.1.schema.json",
        specification_path="docs/spec/geotask-runtime-interface-profile-v0.1.md",
        wrapper_key="runtime_response",
        generation_command=(
            "geotask runtime mock <runtime-request.json> "
            "--output <runtime-response.json>"
        ),
        generation_note=(
            "Produced by a RuntimeAdapter. The public reference adapter supports only "
            "read-only Artifact validation and rejects all private operations."
        ),
        validation_command=(
            "geotask artifact validate geotask.runtime-response "
            "<runtime-response.json>"
        ),
        description=(
            "Versioned Runtime state, output Artifacts, diagnostics, audit reference, "
            "retryability, and side-effect declaration."
        ),
        execution_boundary=(
            "Validating a response does not repeat the Runtime operation or side effects."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.verification-provider-descriptor",
        title="GeoTask Verification Provider Descriptor v0.1",
        kind="verification_provider_descriptor",
        schema_id=VERIFICATION_PROVIDER_DESCRIPTOR_SCHEMA_ID,
        schema_version=VERIFICATION_PROVIDER_DESCRIPTOR_SCHEMA_VERSION,
        schema_path="schemas/geotask-verification-provider-descriptor-v0.1.schema.json",
        specification_path="docs/spec/geotask-verification-provider-profile-v0.1.md",
        wrapper_key="verification_provider_descriptor",
        generation_command="geotask provider inspect --profile --format json",
        generation_note=(
            "Authored by a Provider implementation. Public descriptors advertise only "
            "read-only capabilities and cannot authorize side effects."
        ),
        validation_command=(
            "geotask artifact validate geotask.verification-provider-descriptor "
            "<provider-descriptor.json>"
        ),
        description=(
            "Provider identity, capability, method, independence group, reproducibility, "
            "calibration, validity, and audit declarations."
        ),
        execution_boundary=(
            "Validating a descriptor does not invoke a Provider or verify external truth."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.verification-request",
        title="GeoTask Verification Request v0.1",
        kind="verification_request",
        schema_id=VERIFICATION_REQUEST_SCHEMA_ID,
        schema_version=VERIFICATION_REQUEST_SCHEMA_VERSION,
        schema_path="schemas/geotask-verification-request-v0.1.schema.json",
        specification_path="docs/spec/geotask-verification-provider-profile-v0.1.md",
        wrapper_key="verification_request",
        generation_command=None,
        generation_note=(
            "Authored by a caller with exact Artifact bindings and an Assurance Profile. "
            "Core does not submit it to an external Provider."
        ),
        validation_command=(
            "geotask artifact validate geotask.verification-request "
            "<verification-request.json>"
        ),
        description=(
            "Source-bound verification subject, required capabilities, allowed Provider "
            "types, deadline, and Assurance Profile binding."
        ),
        execution_boundary=(
            "Validating a request does not call a Provider, release output, or authorize action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.verification-response",
        title="GeoTask Verification Response v0.1",
        kind="verification_response",
        schema_id=VERIFICATION_RESPONSE_SCHEMA_ID,
        schema_version=VERIFICATION_RESPONSE_SCHEMA_VERSION,
        schema_path="schemas/geotask-verification-response-v0.1.schema.json",
        specification_path="docs/spec/geotask-verification-provider-profile-v0.1.md",
        wrapper_key="verification_response",
        generation_command=None,
        generation_note=(
            "Produced by a Provider and bound to exact Request and Descriptor bytes. "
            "The Provider cannot self-assign independent assurance."
        ),
        validation_command=(
            "geotask artifact validate geotask.verification-response "
            "<verification-response.json>"
        ),
        description=(
            "Provider result, source validity, evidence references, declared assurance "
            "properties, diagnostics, and immutable safety flags."
        ),
        execution_boundary=(
            "Validating a response does not prove independent verification, publish output, "
            "authorize action, or repeat the Provider operation."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.assurance-profile",
        title="GeoTask Assurance Profile v0.1",
        kind="assurance_profile",
        schema_id=ASSURANCE_PROFILE_SCHEMA_ID,
        schema_version=ASSURANCE_PROFILE_SCHEMA_VERSION,
        schema_path="schemas/geotask-assurance-profile-v0.1.schema.json",
        specification_path="docs/spec/geotask-verification-provider-profile-v0.1.md",
        wrapper_key="assurance_profile",
        generation_command=None,
        generation_note=(
            "Authored by a caller or Domain Pack. Providers cannot modify or self-select "
            "the Assurance Profile used to evaluate their responses."
        ),
        validation_command=(
            "geotask artifact validate geotask.assurance-profile <assurance-profile.json>"
        ),
        description=(
            "Minimum Provider count, independence, freshness, reproducibility, calibration, "
            "conflict policy, output gates, and next action."
        ),
        execution_boundary=(
            "Validating a profile does not evaluate responses, release output, or authorize action."
        ),
    ),
    ArtifactDescriptor(
        artifact_id="geotask.core-benchmark-report",
        title="GeoTask Core Benchmark Report v0.1",
        kind="core_benchmark_report",
        schema_id=CORE_BENCHMARK_SCHEMA_ID,
        schema_version=CORE_BENCHMARK_SCHEMA_VERSION,
        schema_path="schemas/geotask-core-benchmark-v0.1.schema.json",
        specification_path="docs/spec/geotask-core-benchmark-v0.1.md",
        wrapper_key="core_benchmark",
        generation_command=(
            "geotask benchmark core --format json --output core-benchmark.json"
        ),
        generation_note=(
            "Produced offline from fixed fictional cases using production GeoTask Core "
            "Parser, Canonical IR, Validator, Executor, and Result contracts."
        ),
        validation_command=(
            "geotask artifact validate geotask.core-benchmark-report "
            "<core-benchmark.json>"
        ),
        description=(
            "Versioned conformance and local performance-regression report covering "
            "all public deterministic operators, result round trips, and evidence bindings."
        ),
        execution_boundary=(
            "The benchmark performs no model call, network access, external evidence read, "
            "or production action. Timing values are not comparable across hardware."
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
    "OBSERVATION_SCHEMA_ID",
    "OBSERVATION_SCHEMA_VERSION",
    "WORLD_STATE_SCHEMA_ID",
    "WORLD_STATE_SCHEMA_VERSION",
    "STATE_TRANSITION_SCHEMA_ID",
    "STATE_TRANSITION_SCHEMA_VERSION",
    "VERIFICATION_SESSION_SCHEMA_ID",
    "VERIFICATION_SESSION_SCHEMA_VERSION",
    "DISCREPANCY_REPORT_SCHEMA_ID",
    "DISCREPANCY_REPORT_SCHEMA_VERSION",
    "CORRECTION_REQUEST_SCHEMA_ID",
    "CORRECTION_REQUEST_SCHEMA_VERSION",
    "IMPACT_GRAPH_SCHEMA_ID",
    "IMPACT_GRAPH_SCHEMA_VERSION",
    "INCREMENTAL_REEVALUATION_RESULT_SCHEMA_ID",
    "INCREMENTAL_REEVALUATION_RESULT_SCHEMA_VERSION",
    "ARTIFACT_VALIDATION_SCHEMA_ID",
    "ARTIFACT_VALIDATION_SCHEMA_VERSION",
    "AGENT_GENERATION_PREPARATION_SCHEMA_ID",
    "AGENT_GENERATION_PREPARATION_SCHEMA_VERSION",
    "AGENT_REVISION_VERIFICATION_SCHEMA_ID",
    "AGENT_REVISION_VERIFICATION_SCHEMA_VERSION",
    "AGENT_REVISION_RETRY_SCHEMA_ID",
    "AGENT_REVISION_RETRY_SCHEMA_VERSION",
    "AGENT_EVIDENCE_RECOVERY_SCHEMA_ID",
    "AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION",
    "RUNTIME_DESCRIPTOR_SCHEMA_ID",
    "RUNTIME_DESCRIPTOR_SCHEMA_VERSION",
    "RUNTIME_REQUEST_SCHEMA_ID",
    "RUNTIME_REQUEST_SCHEMA_VERSION",
    "RUNTIME_RESPONSE_SCHEMA_ID",
    "RUNTIME_RESPONSE_SCHEMA_VERSION",
    "ArtifactDescriptor",
    "list_artifact_descriptors",
    "get_artifact_descriptor",
    "artifact_registry_payload",
]
