"""High-level, read-only checks for explicit world-state cycle bundles.

The helpers in this module lift existing public Artifact contracts into two
local bundle checks:

* ``verify_session_bundle`` validates one Verification Session together with
  its bound World State, exact Observation set, and every referenced Artifact.
* ``verify_incremental_recheck_bundle`` validates one already-authored
  Incremental Reevaluation Result together with every exact source Artifact.

Neither helper executes a task, evaluates a control, discovers impact,
materializes a state, performs reevaluation, releases an output, authorizes an
action, or executes an action. Missing, duplicate, or extra bindings fail
closed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from geotask_core.v1.artifact_validation import (
    ArtifactValidationReport,
    validate_artifact_file,
)
from geotask_core.v1.correction_request import load_correction_request
from geotask_core.v1.discrepancy_report import load_discrepancy_report
from geotask_core.v1.impact_graph import load_impact_graph
from geotask_core.v1.incremental_reevaluation_result import (
    INCREMENTAL_REEVALUATION_RESULT_ARTIFACT_ID,
    load_incremental_reevaluation_result,
    validate_incremental_reevaluation_result_bindings,
)
from geotask_core.v1.observation import (
    OBSERVATION_ARTIFACT_ID,
    load_observation,
)
from geotask_core.v1.result import GeotaskResult
from geotask_core.v1.verification_session import (
    VERIFICATION_SESSION_ARTIFACT_ID,
    load_verification_session,
    validate_verification_session_bindings,
)
from geotask_core.v1.world_state import (
    WORLD_STATE_ARTIFACT_ID,
    load_world_state,
)


class WorldStateCycleCommandError(ValueError):
    """Raised when an explicit verify/recheck bundle is incomplete or invalid."""


def _reject_nonfinite_json(value: str) -> None:
    raise WorldStateCycleCommandError(
        f"non-finite JSON number {value!r} is not allowed"
    )


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise WorldStateCycleCommandError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_json_bytes(
    path: str | Path,
    *,
    label: str,
) -> tuple[dict[str, object], bytes]:
    file_path = Path(path)
    try:
        raw = file_path.read_bytes()
    except OSError as exc:
        raise WorldStateCycleCommandError(
            f"cannot read {label} file {str(file_path)!r}: {exc}"
        ) from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorldStateCycleCommandError(
            f"{label} file {str(file_path)!r} must be UTF-8"
        ) from exc
    try:
        payload = json.loads(
            text,
            parse_constant=_reject_nonfinite_json,
            object_pairs_hook=_unique_json_object,
        )
    except json.JSONDecodeError as exc:
        raise WorldStateCycleCommandError(
            f"invalid JSON in {label} file {str(file_path)!r} at "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise WorldStateCycleCommandError(
            f"{label} file {str(file_path)!r} must contain a JSON object"
        )
    return dict(payload), raw


def _diagnostic_message(report: ArtifactValidationReport) -> str:
    if not report.diagnostics:
        return "registered Artifact validation failed"
    diagnostic = report.diagnostics[0]
    code = str(diagnostic.get("code", "artifact_invalid"))
    path = str(diagnostic.get("path", "root"))
    message = str(diagnostic.get("message", "validation failed"))
    return f"{code} at {path}: {message}"


def _validate_registered_file(
    artifact_id: str,
    path: str | Path,
    *,
    ref_id: str | None = None,
) -> dict[str, object]:
    report = validate_artifact_file(artifact_id, path)
    if not report.valid:
        label = f"binding {ref_id!r}" if ref_id is not None else "input"
        raise WorldStateCycleCommandError(
            f"{label} failed {artifact_id} validation: {_diagnostic_message(report)}"
        )
    return {
        "ref_id": ref_id,
        "artifact_id": artifact_id,
        "file": str(path),
        "schema_verified": report.schema_verified,
        "valid": report.valid,
    }


def _require_exact_bindings(
    expected_ref_ids: Sequence[str],
    artifact_paths: Mapping[str, str | Path],
    *,
    label: str,
) -> None:
    expected = set(expected_ref_ids)
    supplied = set(artifact_paths)
    missing = sorted(expected - supplied)
    extra = sorted(supplied - expected)
    if missing:
        raise WorldStateCycleCommandError(
            f"{label} bindings are missing ref_id values: {', '.join(missing)}"
        )
    if extra:
        raise WorldStateCycleCommandError(
            f"{label} bindings contain unknown ref_id values: {', '.join(extra)}"
        )


def verify_session_bundle(
    session_path: str | Path,
    world_state_path: str | Path,
    observation_paths: Sequence[str | Path],
    artifact_paths: Mapping[str, str | Path],
) -> dict[str, object]:
    """Validate a complete, explicitly bound Verification Session bundle.

    Every Observation declared by the session must be supplied exactly once.
    Every Artifact reference in the session must be supplied by ``ref_id``.
    Registered semantic validation runs before exact-byte binding validation.
    """

    session_validation = _validate_registered_file(
        VERIFICATION_SESSION_ARTIFACT_ID,
        session_path,
    )
    session_payload, _ = _load_json_bytes(
        session_path,
        label="Verification Session",
    )
    session = load_verification_session(session_payload)

    state_validation = _validate_registered_file(
        WORLD_STATE_ARTIFACT_ID,
        world_state_path,
    )
    world_state_payload, _ = _load_json_bytes(
        world_state_path,
        label="World State",
    )
    world_state = load_world_state(world_state_payload)

    if not observation_paths:
        raise WorldStateCycleCommandError(
            "verify requires at least one --observation file"
        )
    observations: dict[str, object] = {}
    observation_validations: list[dict[str, object]] = []
    for path in observation_paths:
        validation = _validate_registered_file(OBSERVATION_ARTIFACT_ID, path)
        payload, _ = _load_json_bytes(path, label="Observation")
        observation = load_observation(payload)
        if observation.observation_id in observations:
            raise WorldStateCycleCommandError(
                "duplicate Observation ID supplied: "
                f"{observation.observation_id!r}"
            )
        observations[observation.observation_id] = observation
        validation["observation_id"] = observation.observation_id
        observation_validations.append(validation)

    expected_observation_refs = set(session.observation_refs)
    supplied_observation_refs = set(observations)
    missing_observations = sorted(
        expected_observation_refs - supplied_observation_refs
    )
    extra_observations = sorted(
        supplied_observation_refs - expected_observation_refs
    )
    if missing_observations:
        raise WorldStateCycleCommandError(
            "Observation files are missing session refs: "
            + ", ".join(missing_observations)
        )
    if extra_observations:
        raise WorldStateCycleCommandError(
            "Observation files contain IDs not declared by the session: "
            + ", ".join(extra_observations)
        )

    artifact_refs = {item.ref_id: item for item in session.all_artifact_refs()}
    _require_exact_bindings(
        tuple(artifact_refs),
        artifact_paths,
        label="Verification Session",
    )

    artifact_contents: dict[str, bytes] = {}
    artifact_validations: list[dict[str, object]] = []
    for ref_id in sorted(artifact_refs):
        ref = artifact_refs[ref_id]
        path = artifact_paths[ref_id]
        artifact_validations.append(
            _validate_registered_file(ref.artifact_id, path, ref_id=ref_id)
        )
        try:
            artifact_contents[ref_id] = Path(path).read_bytes()
        except OSError as exc:
            raise WorldStateCycleCommandError(
                f"cannot read binding {ref_id!r} file {str(path)!r}: {exc}"
            ) from exc

    validate_verification_session_bindings(
        session,
        world_state,
        artifact_contents,
    )

    return {
        "verification_bundle_check": {
            "valid": True,
            "session_id": session.session_id,
            "session_state": session.state,
            "session_reason": session.reason,
            "world_state_id": world_state.world_state_id,
            "world_state_revision": world_state.revision,
            "world_state_semantic_fingerprint": world_state.semantic_fingerprint(),
            "observation_refs": sorted(session.observation_refs),
            "artifact_ref_count": len(artifact_refs),
            "session_validation": session_validation,
            "world_state_validation": state_validation,
            "observation_validations": sorted(
                observation_validations,
                key=lambda item: str(item["observation_id"]),
            ),
            "artifact_validations": artifact_validations,
            "semantic_validation_complete": True,
            "exact_bindings_verified": True,
            "task_executed_by_command": False,
            "control_evaluated_by_command": False,
            "recheck_executed_by_command": False,
            "action_authorized_by_command": False,
            "action_executed_by_command": False,
        }
    }


def verify_incremental_recheck_bundle(
    result_path: str | Path,
    artifact_paths: Mapping[str, str | Path],
) -> dict[str, object]:
    """Validate a complete Incremental Reevaluation Result source bundle.

    The function validates an already-authored result. It does not execute the
    reevaluation represented by that result.
    """

    result_validation = _validate_registered_file(
        INCREMENTAL_REEVALUATION_RESULT_ARTIFACT_ID,
        result_path,
    )
    result_payload, _ = _load_json_bytes(
        result_path,
        label="Incremental Reevaluation Result",
    )
    result = load_incremental_reevaluation_result(result_payload)

    refs = {item.ref_id: item for item in result.all_artifact_refs()}
    _require_exact_bindings(
        tuple(refs),
        artifact_paths,
        label="Incremental Reevaluation Result",
    )

    artifact_contents: dict[str, bytes] = {}
    artifact_payloads: dict[str, dict[str, object]] = {}
    artifact_validations: list[dict[str, object]] = []
    for ref_id in sorted(refs):
        ref = refs[ref_id]
        path = artifact_paths[ref_id]
        artifact_validations.append(
            _validate_registered_file(ref.artifact_id, path, ref_id=ref_id)
        )
        payload, raw = _load_json_bytes(path, label=f"binding {ref_id}")
        artifact_payloads[ref_id] = payload
        artifact_contents[ref_id] = raw

    base_world_state = load_world_state(
        artifact_payloads[result.base_world_state.ref_id]
    )
    successor_world_state = load_world_state(
        artifact_payloads[result.successor_world_state.ref_id]
    )
    impact_graph = load_impact_graph(
        artifact_payloads[result.impact_graph_ref.ref_id]
    )
    correction_requests = {
        ref.ref_id: load_correction_request(artifact_payloads[ref.ref_id])
        for ref in result.correction_request_refs
    }
    discrepancy_reports = {
        ref.ref_id: load_discrepancy_report(artifact_payloads[ref.ref_id])
        for ref in result.discrepancy_report_refs
    }
    execution_results = {
        ref.ref_id: GeotaskResult.from_dict(artifact_payloads[ref.ref_id])
        for ref in result.execution_result_refs
    }

    validate_incremental_reevaluation_result_bindings(
        result,
        base_world_state,
        successor_world_state,
        impact_graph,
        correction_requests,
        discrepancy_reports,
        execution_results,
        artifact_contents,
    )

    return {
        "recheck_bundle_check": {
            "valid": True,
            "result_id": result.result_id,
            "result_state": result.state,
            "result_reason": result.reason,
            "next_action": result.next_action,
            "base_world_state": {
                "world_state_id": base_world_state.world_state_id,
                "revision": base_world_state.revision,
                "semantic_fingerprint": base_world_state.semantic_fingerprint(),
            },
            "successor_world_state": {
                "world_state_id": successor_world_state.world_state_id,
                "revision": successor_world_state.revision,
                "semantic_fingerprint": successor_world_state.semantic_fingerprint(),
            },
            "impact_graph_id": impact_graph.graph_id,
            "correction_request_count": len(correction_requests),
            "discrepancy_report_count": len(discrepancy_reports),
            "execution_result_count": len(execution_results),
            "output_gates": [item.to_dict() for item in result.output_gates],
            "action_gates": [item.to_dict() for item in result.action_gates],
            "result_validation": result_validation,
            "artifact_validations": artifact_validations,
            "semantic_validation_complete": True,
            "exact_bindings_verified": True,
            "reevaluation_executed_by_command": False,
            "state_materialized_by_command": False,
            "output_released_by_command": False,
            "action_authorized_by_command": False,
            "action_executed_by_command": False,
        }
    }


__all__ = [
    "WorldStateCycleCommandError",
    "verify_session_bundle",
    "verify_incremental_recheck_bundle",
]
