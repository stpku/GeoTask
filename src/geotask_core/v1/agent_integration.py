"""Model-neutral Agent integration contracts and evidence recovery.

The public Agent profile composes existing GeoTask Core capabilities. It does
not call a model, execute declared ``next_action`` values, or release blocked
outputs. Evidence recovery is deliberately narrow: a named assertion condition
may be materialized to the literal ``true`` only after every declared evidence
field is present and the public control profile reports ``resume_when`` as
satisfied. The affected task is then executed again from the updated document.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import re
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
from geotask_core.v1.agent_generation import (
    AGENT_GENERATION_REPORT_VERSION,
    AGENT_REVISION_REQUEST_VERSION,
    AGENT_REVISION_VERIFICATION_VERSION,
)

AGENT_INTEGRATION_PROFILE_ID = "geotask.agent-integration"
AGENT_INTEGRATION_PROFILE_VERSION = "0.1"
AGENT_INTEGRATION_REPORT_VERSION = "0.1"

_CONDITION_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


class AgentIntegrationError(ValueError):
    """Raised when an Agent recovery request cannot be handled safely."""


@dataclass(frozen=True)
class AgentToolDescriptor:
    """One model-neutral tool exposed by the Agent integration profile."""

    name: str
    purpose: str
    python_api: str
    cli: str
    input_contract: str
    output_contract: str
    execution_boundary: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "python_api": self.python_api,
            "cli": self.cli,
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "execution_boundary": self.execution_boundary,
        }


_AGENT_TOOLS = (
    AgentToolDescriptor(
        name="inspect_artifacts",
        purpose="Discover stable public Artifact IDs and their Schemas.",
        python_api="geotask_core.artifact_registry_payload",
        cli="geotask inspect schemas --format json",
        input_contract="No task input.",
        output_contract="artifact_registry/1.0",
        execution_boundary="Discovery does not scan arbitrary files or execute a task.",
    ),
    AgentToolDescriptor(
        name="validate_artifact",
        purpose="Validate one registered public artifact before it is trusted.",
        python_api="geotask_core.validate_artifact_file",
        cli="geotask artifact validate <artifact-id> <file> --format json",
        input_contract="Registered Artifact ID plus a local artifact file.",
        output_contract="artifact_validation/1.0",
        execution_boundary="Validation is read-only and does not rerun a task.",
    ),
    AgentToolDescriptor(
        name="execute_task",
        purpose="Execute a validated GeoTask document with deterministic Core operators.",
        python_api="geotask_core.execute_canonical",
        cli="geotask run <task.yaml> --format v1-json",
        input_contract="Valid geotask.document/1.0 payload.",
        output_contract="geotask_result/1.0",
        execution_boundary="Core executes declared operators only; it does not call a hosted model.",
    ),
    AgentToolDescriptor(
        name="evaluate_control",
        purpose="Evaluate evidence, blocking, and resume conditions without executing actions.",
        python_api="geotask_core.evaluate_control_profile",
        cli=(
            "geotask control evaluate <task.yaml> --result <result.json> "
            "--state <state.yaml>"
        ),
        input_contract="GeoTask document, canonical execution result, and explicit domain state.",
        output_contract="control_evaluation/1.0",
        execution_boundary="Evaluation never executes next_action or releases outputs.",
    ),
)


def list_agent_tool_descriptors() -> tuple[AgentToolDescriptor, ...]:
    """Return the stable tool catalog for the preview Agent profile."""

    return _AGENT_TOOLS


def agent_integration_profile_payload() -> dict[str, Any]:
    """Return the machine-readable GeoTask Agent integration profile."""

    return {
        "agent_integration_profile": {
            "id": AGENT_INTEGRATION_PROFILE_ID,
            "version": AGENT_INTEGRATION_PROFILE_VERSION,
            "status": "preview",
            "tools": [item.to_dict() for item in _AGENT_TOOLS],
            "required_sequence": [
                "inspect_artifacts",
                "validate_artifact",
                "execute_task",
                "evaluate_control",
            ],
            "decision_rules": [
                {
                    "id": "validate_before_use",
                    "requirement": "Validate each input or generated artifact before trusting it.",
                },
                {
                    "id": "unknown_is_not_boolean",
                    "requirement": (
                        "Do not coerce unverifiable, need_data, or unknown values to true or false."
                    ),
                },
                {
                    "id": "block_before_recovery",
                    "requirement": (
                        "Do not release blocked outputs before the declared resume condition is satisfied."
                    ),
                },
                {
                    "id": "recompute_after_recovery",
                    "requirement": (
                        "After evidence recovery, rerun affected deterministic assertions before deciding."
                    ),
                },
                {
                    "id": "no_implicit_actions",
                    "requirement": (
                        "Treat next_action as a routing instruction; Core evaluation never executes it."
                    ),
                },
            ],
            "generated_document_preparation": {
                "report_version": AGENT_GENERATION_REPORT_VERSION,
                "helper": "geotask agent prepare <generated.yaml>",
                "repair_policy": "mechanical_only",
                "safe_repairs": [
                    "add v1 schema_version",
                    "copy explicit geotask.id to missing geotask.name",
                    "add stable task and assertion ids from list position",
                    "derive operator_set from explicit assertion operators",
                    "add local_only execution defaults",
                    "add structured output defaults with model inference disabled",
                ],
                "forbidden_repairs": [
                    "change coordinates or intervals",
                    "choose or replace an operator",
                    "infer object_refs",
                    "invent evidence or domain policy",
                    "execute non-local modes",
                ],
                "revision_request": {
                    "version": AGENT_REVISION_REQUEST_VERSION,
                    "candidate_values_are_inventory_only": True,
                    "selected_value": None,
                    "automatic_revision_applied": False,
                    "retry_command": (
                        "geotask agent retry <blocked-report.json> <revised.yaml>"
                    ),
                    "resume_when": "final_validation.valid == true",
                },
                "revision_verification": {
                    "version": AGENT_REVISION_VERIFICATION_VERSION,
                    "requested_paths_only": True,
                    "revision_request_recomputed": True,
                    "revision_base_sha256_required": True,
                    "coordinates_immutable_unless_requested": True,
                    "evidence_immutable_unless_requested": True,
                    "task_executed_before_acceptance": False,
                    "output_option": (
                        "--verification-output <revision-verification.json>"
                    ),
                },
                "report_artifacts": [
                    {
                        "artifact_id": "geotask.agent-generation-preparation",
                        "wrapper": "agent_generation_preparation",
                        "schema_id": AGENT_GENERATION_PREPARATION_SCHEMA_ID,
                        "schema_version": AGENT_GENERATION_PREPARATION_SCHEMA_VERSION,
                        "validation_command": (
                            "geotask artifact validate "
                            "geotask.agent-generation-preparation <report.json>"
                        ),
                    },
                    {
                        "artifact_id": "geotask.agent-revision-verification",
                        "wrapper": "agent_revision_verification",
                        "schema_id": AGENT_REVISION_VERIFICATION_SCHEMA_ID,
                        "schema_version": AGENT_REVISION_VERIFICATION_SCHEMA_VERSION,
                        "validation_command": (
                            "geotask artifact validate "
                            "geotask.agent-revision-verification <report.json>"
                        ),
                    },
                    {
                        "artifact_id": "geotask.agent-revision-retry",
                        "wrapper": "agent_revision_retry",
                        "schema_id": AGENT_REVISION_RETRY_SCHEMA_ID,
                        "schema_version": AGENT_REVISION_RETRY_SCHEMA_VERSION,
                        "validation_command": (
                            "geotask artifact validate "
                            "geotask.agent-revision-retry <report.json>"
                        ),
                    },
                ],
                "artifact_validity_is_distinct_from_business_state": True,
                "domain_inference_used": False,
                "model_called": False,
            },
            "evidence_recovery": {
                "report_version": AGENT_INTEGRATION_REPORT_VERSION,
                "artifact_id": "geotask.agent-evidence-recovery",
                "schema_id": AGENT_EVIDENCE_RECOVERY_SCHEMA_ID,
                "schema_version": AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION,
                "validation_command": (
                    "geotask artifact validate geotask.agent-evidence-recovery "
                    "<recovery-report.json>"
                ),
                "artifact_validity_is_distinct_from_business_state": True,
                "supported_condition": "single named boolean condition",
                "required_checks": [
                    "trigger assertion is initially unverifiable",
                    "all evidence_request.required_fields are present",
                    "evidence state sets the named condition to true",
                    "evidence_request.resume_when evaluates to true",
                    "affected task is executed again",
                ],
                "model_guess_used": False,
                "next_action_executed": False,
            },
        }
    }


@dataclass(frozen=True)
class EvidenceRecoveryResult:
    """Auditable before/resume/after record for one evidence request."""

    task_id: str
    state: str
    request: Mapping[str, Any]
    condition_identifier: str
    condition_value: bool | None
    initial_result: Mapping[str, Any]
    initial_control: Mapping[str, Any]
    resume_control: Mapping[str, Any]
    resumed_result: Mapping[str, Any] | None
    final_control: Mapping[str, Any] | None
    task_reexecuted: bool
    diagnostics: tuple[Mapping[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        active_control = self.final_control or self.resume_control or self.initial_control
        control_body = active_control.get("control_evaluation", {})
        decision_value = _control_block_value(active_control, "decision_rule")
        blocked_outputs = list(control_body.get("blocked_outputs", []))
        eligible_outputs = list(control_body.get("eligible_outputs", []))
        if self.state != "recovered":
            blocked_outputs = list(self.request.get("blocked_outputs", []))
            eligible_outputs = []

        return {
            "agent_integration": {
                "report_version": AGENT_INTEGRATION_REPORT_VERSION,
                "profile": {
                    "id": AGENT_INTEGRATION_PROFILE_ID,
                    "version": AGENT_INTEGRATION_PROFILE_VERSION,
                },
                "task_id": self.task_id,
                "state": self.state,
                "request": dict(self.request),
                "materialization": {
                    "condition_identifier": self.condition_identifier,
                    "condition_value": self.condition_value,
                    "condition_rewritten_to_literal": self.task_reexecuted,
                    "task_reexecuted": self.task_reexecuted,
                    "next_action_executed": False,
                    "model_guess_used": False,
                },
                "initial_execution": dict(self.initial_result),
                "initial_control_evaluation": dict(self.initial_control),
                "resume_control_evaluation": dict(self.resume_control),
                "resumed_execution": (
                    None if self.resumed_result is None else dict(self.resumed_result)
                ),
                "final_control_evaluation": (
                    None if self.final_control is None else dict(self.final_control)
                ),
                "summary": {
                    "decision_value": decision_value,
                    "blocked_outputs": blocked_outputs,
                    "eligible_outputs": eligible_outputs,
                },
                "diagnostics": [dict(item) for item in self.diagnostics],
            }
        }


def _as_mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AgentIntegrationError(f"{path} must be an object or mapping")
    return value


def _find_assertion(document: Mapping[str, Any], assertion_id: str) -> dict[str, Any]:
    candidates: list[object] = []
    top_level = document.get("assertions")
    if isinstance(top_level, list):
        candidates.extend(top_level)
    tasks = document.get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, Mapping) and isinstance(task.get("assertions"), list):
                candidates.extend(task["assertions"])

    matches = [
        item
        for item in candidates
        if isinstance(item, dict) and item.get("id") == assertion_id
    ]
    if len(matches) != 1:
        raise AgentIntegrationError(
            f"evidence_request.trigger must resolve to exactly one assertion: {assertion_id!r}"
        )
    return matches[0]


def _lookup_path(mapping: Mapping[str, Any], path: str) -> tuple[bool, object]:
    if path in mapping:
        return True, mapping[path]
    current: object = mapping
    for segment in path.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            return False, None
        current = current[segment]
    return True, current


def _has_evidence_value(mapping: Mapping[str, Any], path: str) -> bool:
    found, value = _lookup_path(mapping, path)
    if not found or value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, Mapping)):
        return bool(value)
    return True


def _check_by_assertion_id(payload: Mapping[str, Any], assertion_id: str) -> Mapping[str, Any]:
    result = _as_mapping(payload.get("geotask_result"), "geotask_result")
    checks = result.get("checks")
    if not isinstance(checks, list):
        raise AgentIntegrationError("geotask_result.checks must be an array")
    matches = [
        item
        for item in checks
        if isinstance(item, Mapping) and item.get("assertion_id") == assertion_id
    ]
    if len(matches) != 1:
        raise AgentIntegrationError(
            f"execution result must contain exactly one check for {assertion_id!r}"
        )
    return matches[0]


def _control_block(payload: Mapping[str, Any], block_name: str) -> Mapping[str, Any] | None:
    body = payload.get("control_evaluation")
    if not isinstance(body, Mapping):
        return None
    evaluations = body.get("evaluations")
    if not isinstance(evaluations, list):
        return None
    for item in evaluations:
        if isinstance(item, Mapping) and item.get("block") == block_name:
            return item
    return None


def _control_block_value(payload: Mapping[str, Any], block_name: str) -> bool | None:
    block = _control_block(payload, block_name)
    if block is None:
        return None
    value = block.get("value")
    return value if isinstance(value, bool) else None


def recover_evidence_request(
    document: Mapping[str, Any],
    evidence_state: Mapping[str, Any],
) -> EvidenceRecoveryResult:
    """Resolve one ``evidence_request`` and rerun its trigger assertion safely.

    The function is intentionally fail-closed. It supports only a trigger
    assertion whose condition is one plain identifier, such as
    ``restricted_schedule_verified``. Missing evidence or an unsatisfied resume
    expression returns a structured ``blocked`` result; malformed contracts
    raise :class:`AgentIntegrationError`.
    """

    from geotask_core.parser import validate_document
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.control_evaluation import evaluate_control_profile
    from geotask_core.v1.executor import execute_canonical

    if not isinstance(document, Mapping):
        raise TypeError("document must be a mapping")
    if not isinstance(evidence_state, Mapping):
        raise TypeError("evidence_state must be a mapping")

    data = deepcopy(dict(document))
    errors = [
        item
        for item in validate_document(data)
        if item.get("severity", "error") == "error"
    ]
    if errors:
        first = errors[0]
        raise AgentIntegrationError(
            f"invalid GeoTask document at {first.get('path', '')}: "
            f"{first.get('message', 'validation failed')}"
        )

    extensions = _as_mapping(data.get("extensions"), "extensions")
    request = _as_mapping(
        extensions.get("evidence_request"),
        "extensions.evidence_request",
    )
    trigger = request.get("trigger")
    if not isinstance(trigger, str) or not trigger:
        raise AgentIntegrationError("extensions.evidence_request.trigger must be a string")

    assertion = _find_assertion(data, trigger)
    raw_condition = assertion.get("condition")
    if not isinstance(raw_condition, str) or not _CONDITION_IDENTIFIER.fullmatch(
        raw_condition.strip()
    ):
        raise AgentIntegrationError(
            "evidence recovery supports only a single named assertion condition"
        )
    condition_identifier = raw_condition.strip()

    canonical = canonicalize(data)
    initial = execute_canonical(canonical)
    initial_payload = initial.to_dict()
    initial_check = _check_by_assertion_id(initial_payload, trigger)
    expected_trigger_status = request.get("trigger_status", "unverifiable")
    if initial_check.get("status") != expected_trigger_status:
        raise AgentIntegrationError(
            f"trigger assertion {trigger!r} has status {initial_check.get('status')!r}; "
            f"expected {expected_trigger_status!r}"
        )

    initial_control = evaluate_control_profile(canonical, initial, {}).to_dict()
    resume_control = evaluate_control_profile(
        canonical,
        initial,
        evidence_state,
    ).to_dict()

    required_fields = request.get("required_fields", [])
    if not isinstance(required_fields, list) or not all(
        isinstance(item, str) and item for item in required_fields
    ):
        raise AgentIntegrationError(
            "extensions.evidence_request.required_fields must be an array of strings"
        )
    missing_fields = [
        item for item in required_fields if not _has_evidence_value(evidence_state, item)
    ]
    condition_found, condition_value = _lookup_path(
        evidence_state,
        condition_identifier,
    )
    normalized_condition_value = condition_value if isinstance(condition_value, bool) else None
    resume_block = _control_block(resume_control, "evidence_request")
    resume_satisfied = bool(
        resume_block
        and resume_block.get("state") == "satisfied"
        and resume_block.get("value") is True
    )

    request_payload = {
        "id": request.get("id", ""),
        "trigger": trigger,
        "trigger_status": expected_trigger_status,
        "reason": request.get("reason", ""),
        "required_fields": list(required_fields),
        "missing_fields": missing_fields,
        "evidence_complete": not missing_fields,
        "blocked_outputs": list(request.get("blocked_outputs", [])),
        "resume_when": request.get("resume_when", ""),
        "next_action": request.get("next_action", ""),
    }

    diagnostics: list[Mapping[str, str]] = []
    if missing_fields:
        diagnostics.append(
            {
                "code": "missing_required_evidence",
                "path": "evidence_state",
                "message": "Missing required evidence fields: " + ", ".join(missing_fields),
            }
        )
    if not condition_found or normalized_condition_value is not True:
        diagnostics.append(
            {
                "code": "resume_condition_not_verified",
                "path": condition_identifier,
                "message": f"Evidence state must set {condition_identifier} to true.",
            }
        )
    if not resume_satisfied:
        diagnostics.append(
            {
                "code": "resume_expression_not_satisfied",
                "path": "extensions.evidence_request.resume_when",
                "message": "The declared resume_when expression is not satisfied.",
            }
        )

    if diagnostics:
        return EvidenceRecoveryResult(
            task_id=canonical.metadata.id,
            state="blocked",
            request=request_payload,
            condition_identifier=condition_identifier,
            condition_value=normalized_condition_value,
            initial_result=initial_payload,
            initial_control=initial_control,
            resume_control=resume_control,
            resumed_result=None,
            final_control=None,
            task_reexecuted=False,
            diagnostics=tuple(diagnostics),
        )

    assertion["condition"] = "true"
    resumed_canonical = canonicalize(data)
    resumed = execute_canonical(resumed_canonical)
    resumed_payload = resumed.to_dict()
    resumed_check = _check_by_assertion_id(resumed_payload, trigger)
    if resumed_check.get("status") != "verified":
        raise AgentIntegrationError(
            f"trigger assertion {trigger!r} did not verify after evidence recovery"
        )
    final_control = evaluate_control_profile(
        resumed_canonical,
        resumed,
        evidence_state,
    ).to_dict()

    return EvidenceRecoveryResult(
        task_id=resumed_canonical.metadata.id,
        state="recovered",
        request=request_payload,
        condition_identifier=condition_identifier,
        condition_value=True,
        initial_result=initial_payload,
        initial_control=initial_control,
        resume_control=resume_control,
        resumed_result=resumed_payload,
        final_control=final_control,
        task_reexecuted=True,
        diagnostics=(),
    )
