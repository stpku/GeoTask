"""Strict loaders for versioned Agent preview report artifacts.

Artifact validity is distinct from the business outcome recorded by a report. A
well-formed preparation report may be ``blocked`` and a well-formed retry report
may be ``rejected``. These loaders validate the serialized contract and its
cross-field invariants without rerunning preparation, revision verification, or
execution.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import math
import re
from typing import Any

from geotask_core.v1.agent_generation import (
    AGENT_GENERATION_REPORT_VERSION,
    AGENT_REVISION_REQUEST_VERSION,
    AGENT_REVISION_RETRY_VERSION,
    AGENT_REVISION_VERIFICATION_VERSION,
)
from geotask_core.v1.control_evaluation import (
    ControlEvaluationFormatError,
    ControlEvaluationResult,
    load_control_evaluation,
)
from geotask_core.v1.result import GeotaskResult, ResultFormatError


_AGENT_SCHEMA_ROOT = "https://stpku.github.io/GeoTask/schemas/"
AGENT_GENERATION_PREPARATION_SCHEMA_ID = (
    _AGENT_SCHEMA_ROOT + "geotask-agent-generation-preparation-v0.1.schema.json"
)
AGENT_GENERATION_PREPARATION_SCHEMA_VERSION = "0.1"
AGENT_REVISION_VERIFICATION_SCHEMA_ID = (
    _AGENT_SCHEMA_ROOT + "geotask-agent-revision-verification-v0.1.schema.json"
)
AGENT_REVISION_VERIFICATION_SCHEMA_VERSION = "0.1"
AGENT_REVISION_RETRY_SCHEMA_ID = (
    _AGENT_SCHEMA_ROOT + "geotask-agent-revision-retry-v0.1.schema.json"
)
AGENT_REVISION_RETRY_SCHEMA_VERSION = "0.1"
AGENT_EVIDENCE_RECOVERY_SCHEMA_ID = (
    _AGENT_SCHEMA_ROOT + "geotask-agent-integration-v0.1.schema.json"
)
AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION = "0.1"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CONDITION_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


class AgentArtifactFormatError(ValueError):
    """Raised when a serialized Agent report violates its public contract."""


def _fail(message: str) -> None:
    raise AgentArtifactFormatError(message)


def _mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{path} must be an object")
    return dict(value)


def _exact_fields(
    value: Mapping[str, Any],
    *,
    path: str,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    keys = set(value)
    missing = sorted(required - keys)
    unknown = sorted(keys - required - optional)
    if missing:
        _fail(f"{path} is missing fields: {', '.join(missing)}")
    if unknown:
        _fail(f"{path} contains unknown fields: {', '.join(unknown)}")


def _string(value: object, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        _fail(f"{path} must be a string")
    if not allow_empty and not value:
        _fail(f"{path} must not be empty")
    return value


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        _fail(f"{path} must be a boolean")
    return bool(value)


def _integer(value: object, path: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{path} must be a non-negative integer")
    return int(value)


def _const(value: object, expected: object, path: str) -> None:
    if value != expected or type(value) is not type(expected):
        _fail(f"{path} must equal {expected!r}")


def _enum(value: object, allowed: set[str], path: str) -> str:
    text = _string(value, path)
    if text not in allowed:
        _fail(f"{path} must be one of: {', '.join(sorted(allowed))}")
    return text


def _json_value(value: object, path: str) -> None:
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            _fail(f"{path} must not contain a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(f"{path} object keys must be strings")
            _json_value(item, f"{path}.{key}")
        return
    _fail(f"{path} must contain JSON-compatible values")


def _string_list(value: object, path: str, *, unique: bool = False) -> list[str]:
    if not isinstance(value, list):
        _fail(f"{path} must be an array")
    result = [_string(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if unique and len(set(result)) != len(result):
        _fail(f"{path} must not contain duplicate values")
    return result


def _sha256(value: object, path: str) -> str:
    text = _string(value, path)
    if not _SHA256_RE.fullmatch(text):
        _fail(f"{path} must be a lowercase SHA-256 digest")
    return text


def _diagnostic(value: object, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    _exact_fields(
        item,
        path=path,
        required={"path", "code", "message", "severity"},
        optional={"suggested_fix"},
    )
    _string(item["path"], f"{path}.path", allow_empty=True)
    _string(item["code"], f"{path}.code")
    _string(item["message"], f"{path}.message")
    _enum(item["severity"], {"error", "warning"}, f"{path}.severity")
    if "suggested_fix" in item:
        _string(item["suggested_fix"], f"{path}.suggested_fix", allow_empty=True)
    return item


def _validation_block(value: object, path: str) -> dict[str, Any]:
    block = _mapping(value, path)
    _exact_fields(block, path=path, required={"valid", "diagnostics"})
    valid = _boolean(block["valid"], f"{path}.valid")
    diagnostics_raw = block["diagnostics"]
    if not isinstance(diagnostics_raw, list):
        _fail(f"{path}.diagnostics must be an array")
    diagnostics = [
        _diagnostic(item, f"{path}.diagnostics[{index}]")
        for index, item in enumerate(diagnostics_raw)
    ]
    error_count = sum(item["severity"] == "error" for item in diagnostics)
    if valid and error_count:
        _fail(f"{path}.valid cannot be true when error diagnostics exist")
    if not valid and error_count == 0:
        _fail(f"{path}.valid=false requires at least one error diagnostic")
    return block


def _repair(value: object, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    _exact_fields(
        item,
        path=path,
        required={
            "code",
            "path",
            "before",
            "after",
            "reason",
            "domain_inference_used",
            "model_called",
        },
    )
    _string(item["code"], f"{path}.code")
    _string(item["path"], f"{path}.path")
    _json_value(item["before"], f"{path}.before")
    _json_value(item["after"], f"{path}.after")
    _string(item["reason"], f"{path}.reason")
    _const(item["domain_inference_used"], False, f"{path}.domain_inference_used")
    _const(item["model_called"], False, f"{path}.model_called")
    return item


def _revision_change(value: object, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    _exact_fields(
        item,
        path=path,
        required={
            "code",
            "path",
            "action",
            "instruction",
            "candidate_values",
            "selected_value",
            "automatic_change_allowed",
            "retryable",
            "requires_external_input",
        },
    )
    for field in ("code", "path", "action", "instruction"):
        _string(item[field], f"{path}.{field}")
    _string_list(item["candidate_values"], f"{path}.candidate_values", unique=True)
    _const(item["selected_value"], None, f"{path}.selected_value")
    _const(
        item["automatic_change_allowed"],
        False,
        f"{path}.automatic_change_allowed",
    )
    _boolean(item["retryable"], f"{path}.retryable")
    _boolean(item["requires_external_input"], f"{path}.requires_external_input")
    return item


def _revision_request(value: object, path: str) -> dict[str, Any]:
    request = _mapping(value, path)
    _exact_fields(
        request,
        path=path,
        required={
            "request_version",
            "state",
            "next_action",
            "revision_base",
            "revision_base_sha256",
            "required_changes",
            "forbidden_changes",
            "retry_command",
            "resume_when",
            "model_called",
            "automatic_revision_applied",
        },
    )
    _const(
        request["request_version"],
        AGENT_REVISION_REQUEST_VERSION,
        f"{path}.request_version",
    )
    state = _enum(
        request["state"],
        {"not_required", "required", "routing_required"},
        f"{path}.state",
    )
    next_action = _enum(
        request["next_action"],
        {"none", "revise_generated_document", "route_to_authorized_runtime"},
        f"{path}.next_action",
    )
    _const(request["revision_base"], "prepared_document", f"{path}.revision_base")
    _sha256(request["revision_base_sha256"], f"{path}.revision_base_sha256")
    changes_raw = request["required_changes"]
    if not isinstance(changes_raw, list):
        _fail(f"{path}.required_changes must be an array")
    changes = [
        _revision_change(item, f"{path}.required_changes[{index}]")
        for index, item in enumerate(changes_raw)
    ]
    _string_list(request["forbidden_changes"], f"{path}.forbidden_changes")
    _const(
        request["retry_command"],
        "geotask agent retry <blocked-report.json> <revised.yaml>",
        f"{path}.retry_command",
    )
    _const(
        request["resume_when"],
        "final_validation.valid == true",
        f"{path}.resume_when",
    )
    _const(request["model_called"], False, f"{path}.model_called")
    _const(
        request["automatic_revision_applied"],
        False,
        f"{path}.automatic_revision_applied",
    )
    if state == "not_required":
        if next_action != "none" or changes:
            _fail(f"{path} not_required state must have next_action=none and no changes")
    elif state == "required":
        if next_action != "revise_generated_document" or not changes:
            _fail(
                f"{path} required state must request document revision with changes"
            )
        if any(item["retryable"] is not True for item in changes):
            _fail(f"{path} required changes must all be locally retryable")
    else:
        if next_action != "route_to_authorized_runtime" or not changes:
            _fail(f"{path} routing_required state must route with changes")
        if not any(item["retryable"] is False for item in changes):
            _fail(f"{path} routing_required state requires a non-retryable change")
    return request


def _preparation_body(value: object, path: str) -> dict[str, Any]:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path=path,
        required={
            "report_version",
            "state",
            "repair_policy",
            "initial_validation",
            "repairs",
            "final_validation",
            "revision_request",
            "prepared_document",
            "execution_result",
            "summary",
        },
    )
    _const(
        body["report_version"],
        AGENT_GENERATION_REPORT_VERSION,
        f"{path}.report_version",
    )
    state = _enum(body["state"], {"valid", "repaired", "blocked"}, f"{path}.state")

    policy = _mapping(body["repair_policy"], f"{path}.repair_policy")
    _exact_fields(
        policy,
        path=f"{path}.repair_policy",
        required={
            "mechanical_only",
            "source_mutated",
            "domain_inference_used",
            "model_called",
            "non_local_execution_allowed",
        },
    )
    _const(policy["mechanical_only"], True, f"{path}.repair_policy.mechanical_only")
    for field in (
        "source_mutated",
        "domain_inference_used",
        "model_called",
        "non_local_execution_allowed",
    ):
        _const(policy[field], False, f"{path}.repair_policy.{field}")

    initial = _validation_block(body["initial_validation"], f"{path}.initial_validation")
    repairs_raw = body["repairs"]
    if not isinstance(repairs_raw, list):
        _fail(f"{path}.repairs must be an array")
    repairs = [_repair(item, f"{path}.repairs[{index}]") for index, item in enumerate(repairs_raw)]
    final = _validation_block(body["final_validation"], f"{path}.final_validation")
    revision = _revision_request(body["revision_request"], f"{path}.revision_request")
    prepared_document = _mapping(body["prepared_document"], f"{path}.prepared_document")
    _json_value(prepared_document, f"{path}.prepared_document")

    execution_result = body["execution_result"]
    if execution_result is not None:
        result = _mapping(execution_result, f"{path}.execution_result")
        _exact_fields(result, path=f"{path}.execution_result", required={"geotask_result"})
        _mapping(result["geotask_result"], f"{path}.execution_result.geotask_result")
        _json_value(result, f"{path}.execution_result")

    summary = _mapping(body["summary"], f"{path}.summary")
    _exact_fields(
        summary,
        path=f"{path}.summary",
        required={
            "repair_count",
            "initial_error_count",
            "residual_error_count",
            "task_executed",
            "execution_status",
            "overall_status",
            "check_count",
        },
    )
    repair_count = _integer(summary["repair_count"], f"{path}.summary.repair_count")
    initial_count = _integer(
        summary["initial_error_count"], f"{path}.summary.initial_error_count"
    )
    residual_count = _integer(
        summary["residual_error_count"], f"{path}.summary.residual_error_count"
    )
    task_executed = _boolean(summary["task_executed"], f"{path}.summary.task_executed")
    execution_status = _string(
        summary["execution_status"], f"{path}.summary.execution_status", allow_empty=True
    )
    overall_status = _string(
        summary["overall_status"], f"{path}.summary.overall_status", allow_empty=True
    )
    check_count = _integer(summary["check_count"], f"{path}.summary.check_count")

    initial_errors = sum(
        item["severity"] == "error" for item in initial["diagnostics"]
    )
    residual_errors = sum(
        item["severity"] == "error" for item in final["diagnostics"]
    )
    if repair_count != len(repairs):
        _fail(f"{path}.summary.repair_count does not match repairs")
    if initial_count != initial_errors:
        _fail(f"{path}.summary.initial_error_count does not match diagnostics")
    if residual_count != residual_errors:
        _fail(f"{path}.summary.residual_error_count does not match diagnostics")

    if state == "blocked":
        if final["valid"] is not False or execution_result is not None or task_executed:
            _fail(f"{path} blocked state must remain invalid and unexecuted")
        if execution_status or overall_status or check_count:
            _fail(f"{path} blocked summary must not claim execution output")
        if revision["state"] == "not_required":
            _fail(f"{path} blocked state requires a revision or routing request")
    else:
        if final["valid"] is not True or execution_result is None or not task_executed:
            _fail(f"{path} {state} state must be valid and executed")
        if revision["state"] != "not_required":
            _fail(f"{path} successful state must not require revision")
        if not execution_status or not overall_status:
            _fail(f"{path} successful state requires execution and overall status")
        result_body = execution_result["geotask_result"]
        checks = result_body.get("checks") if isinstance(result_body, Mapping) else None
        if isinstance(checks, list) and check_count != len(checks):
            _fail(f"{path}.summary.check_count does not match execution checks")
        if state == "valid" and repairs:
            _fail(f"{path} valid state must not contain mechanical repairs")
        if state == "repaired" and not repairs:
            _fail(f"{path} repaired state requires at least one repair")
    return body


def _allowed_path(value: object, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    _exact_fields(item, path=path, required={"path", "scope", "reason"})
    _string(item["path"], f"{path}.path")
    _enum(item["scope"], {"exact", "subtree"}, f"{path}.scope")
    _string(item["reason"], f"{path}.reason")
    return item


def _resolved_change(value: object, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    _exact_fields(
        item,
        path=path,
        required={
            "code",
            "path",
            "action",
            "before_present",
            "before",
            "after",
            "candidate_inventory_used",
            "selected_by_core",
        },
    )
    for field in ("code", "path", "action"):
        _string(item[field], f"{path}.{field}")
    _boolean(item["before_present"], f"{path}.before_present")
    _json_value(item["before"], f"{path}.before")
    _json_value(item["after"], f"{path}.after")
    _boolean(item["candidate_inventory_used"], f"{path}.candidate_inventory_used")
    _const(item["selected_by_core"], False, f"{path}.selected_by_core")
    return item


def _violation(value: object, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    _exact_fields(item, path=path, required={"code", "path", "message"})
    for field in ("code", "message"):
        _string(item[field], f"{path}.{field}")
    _string(item["path"], f"{path}.path", allow_empty=True)
    return item


def _recovery_diagnostic(value: object, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    _exact_fields(item, path=path, required={"code", "path", "message"})
    _string(item["code"], f"{path}.code")
    _string(item["path"], f"{path}.path", allow_empty=True)
    _string(item["message"], f"{path}.message")
    return item


def _execution_payload(
    value: object,
    path: str,
) -> tuple[dict[str, Any], GeotaskResult]:
    payload = _mapping(value, path)
    try:
        loaded = GeotaskResult.from_dict(payload)
    except ResultFormatError as exc:
        _fail(f"{path} is not a valid GeoTask Execution Result: {exc}")
    return payload, loaded


def _control_payload(
    value: object,
    path: str,
) -> tuple[dict[str, Any], ControlEvaluationResult]:
    payload = _mapping(value, path)
    try:
        loaded = load_control_evaluation(payload)
    except ControlEvaluationFormatError as exc:
        _fail(f"{path} is not a valid Control Evaluation Result: {exc}")
    return payload, loaded


def _control_block_value(
    control: ControlEvaluationResult,
    block: str,
) -> bool | None:
    for item in control.evaluations:
        if item.block == block:
            return item.value if isinstance(item.value, bool) else None
    return None


def _trigger_status(result: GeotaskResult, trigger: str, path: str) -> str:
    matches = [item for item in result.checks if item.assertion_id == trigger]
    if len(matches) != 1:
        _fail(f"{path} must contain exactly one check for trigger {trigger!r}")
    return str(matches[0].status)


def _evidence_recovery_body(value: object, path: str) -> dict[str, Any]:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path=path,
        required={
            "report_version",
            "profile",
            "task_id",
            "state",
            "request",
            "materialization",
            "initial_execution",
            "initial_control_evaluation",
            "resume_control_evaluation",
            "resumed_execution",
            "final_control_evaluation",
            "summary",
            "diagnostics",
        },
    )
    _const(
        body["report_version"],
        AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION,
        f"{path}.report_version",
    )

    profile = _mapping(body["profile"], f"{path}.profile")
    _exact_fields(profile, path=f"{path}.profile", required={"id", "version"})
    _const(profile["id"], "geotask.agent-integration", f"{path}.profile.id")
    _const(profile["version"], "0.1", f"{path}.profile.version")

    task_id = _string(body["task_id"], f"{path}.task_id")
    state = _enum(body["state"], {"blocked", "recovered"}, f"{path}.state")

    request = _mapping(body["request"], f"{path}.request")
    _exact_fields(
        request,
        path=f"{path}.request",
        required={
            "id",
            "trigger",
            "trigger_status",
            "reason",
            "required_fields",
            "missing_fields",
            "evidence_complete",
            "blocked_outputs",
            "resume_when",
            "next_action",
        },
    )
    _string(request["id"], f"{path}.request.id", allow_empty=True)
    trigger = _string(request["trigger"], f"{path}.request.trigger")
    trigger_status = _string(
        request["trigger_status"], f"{path}.request.trigger_status"
    )
    _string(request["reason"], f"{path}.request.reason", allow_empty=True)
    required_fields = _string_list(
        request["required_fields"], f"{path}.request.required_fields", unique=True
    )
    missing_fields = _string_list(
        request["missing_fields"], f"{path}.request.missing_fields", unique=True
    )
    if any(item not in required_fields for item in missing_fields):
        _fail(f"{path}.request.missing_fields must be a subset of required_fields")
    missing_set = set(missing_fields)
    if missing_fields != [item for item in required_fields if item in missing_set]:
        _fail(f"{path}.request.missing_fields must preserve required_fields order")
    evidence_complete = _boolean(
        request["evidence_complete"], f"{path}.request.evidence_complete"
    )
    if evidence_complete != (not missing_fields):
        _fail(f"{path}.request.evidence_complete must match missing_fields")
    request_blocked_outputs = _string_list(
        request["blocked_outputs"],
        f"{path}.request.blocked_outputs",
        unique=True,
    )
    _string(request["resume_when"], f"{path}.request.resume_when")
    _string(request["next_action"], f"{path}.request.next_action")

    materialization = _mapping(
        body["materialization"], f"{path}.materialization"
    )
    _exact_fields(
        materialization,
        path=f"{path}.materialization",
        required={
            "condition_identifier",
            "condition_value",
            "condition_rewritten_to_literal",
            "task_reexecuted",
            "next_action_executed",
            "model_guess_used",
        },
    )
    condition_identifier = _string(
        materialization["condition_identifier"],
        f"{path}.materialization.condition_identifier",
    )
    if not _CONDITION_IDENTIFIER_RE.fullmatch(condition_identifier):
        _fail(
            f"{path}.materialization.condition_identifier must be a plain identifier"
        )
    condition_value = materialization["condition_value"]
    if condition_value is not None and type(condition_value) is not bool:
        _fail(f"{path}.materialization.condition_value must be boolean or null")
    rewritten = _boolean(
        materialization["condition_rewritten_to_literal"],
        f"{path}.materialization.condition_rewritten_to_literal",
    )
    task_reexecuted = _boolean(
        materialization["task_reexecuted"],
        f"{path}.materialization.task_reexecuted",
    )
    if rewritten != task_reexecuted:
        _fail(
            f"{path}.materialization.condition_rewritten_to_literal must match task_reexecuted"
        )
    _const(
        materialization["next_action_executed"],
        False,
        f"{path}.materialization.next_action_executed",
    )
    _const(
        materialization["model_guess_used"],
        False,
        f"{path}.materialization.model_guess_used",
    )

    _, initial_execution = _execution_payload(
        body["initial_execution"], f"{path}.initial_execution"
    )
    _, initial_control = _control_payload(
        body["initial_control_evaluation"],
        f"{path}.initial_control_evaluation",
    )
    _, resume_control = _control_payload(
        body["resume_control_evaluation"],
        f"{path}.resume_control_evaluation",
    )
    resumed_execution = None
    if body["resumed_execution"] is not None:
        _, resumed_execution = _execution_payload(
            body["resumed_execution"], f"{path}.resumed_execution"
        )
    final_control = None
    if body["final_control_evaluation"] is not None:
        _, final_control = _control_payload(
            body["final_control_evaluation"], f"{path}.final_control_evaluation"
        )

    for label, nested_task_id in (
        ("initial_execution", initial_execution.task_id),
        ("initial_control_evaluation", initial_control.task_id),
        ("resume_control_evaluation", resume_control.task_id),
        (
            "resumed_execution",
            None if resumed_execution is None else resumed_execution.task_id,
        ),
        (
            "final_control_evaluation",
            None if final_control is None else final_control.task_id,
        ),
    ):
        if nested_task_id is not None and nested_task_id != task_id:
            _fail(f"{path}.{label}.task_id must match {path}.task_id")
    if _trigger_status(
        initial_execution, trigger, f"{path}.initial_execution"
    ) != trigger_status:
        _fail(
            f"{path}.initial_execution trigger status must match request.trigger_status"
        )

    summary = _mapping(body["summary"], f"{path}.summary")
    _exact_fields(
        summary,
        path=f"{path}.summary",
        required={"decision_value", "blocked_outputs", "eligible_outputs"},
    )
    decision_value = summary["decision_value"]
    if decision_value is not None and type(decision_value) is not bool:
        _fail(f"{path}.summary.decision_value must be boolean or null")
    summary_blocked = _string_list(
        summary["blocked_outputs"], f"{path}.summary.blocked_outputs", unique=True
    )
    summary_eligible = _string_list(
        summary["eligible_outputs"], f"{path}.summary.eligible_outputs", unique=True
    )

    diagnostics_raw = body["diagnostics"]
    if not isinstance(diagnostics_raw, list):
        _fail(f"{path}.diagnostics must be an array")
    diagnostics = [
        _recovery_diagnostic(item, f"{path}.diagnostics[{index}]")
        for index, item in enumerate(diagnostics_raw)
    ]

    if state == "blocked":
        if rewritten or task_reexecuted:
            _fail(f"{path} blocked state must not rewrite or reexecute the task")
        if resumed_execution is not None or final_control is not None:
            _fail(
                f"{path} blocked state must not contain resumed execution or final control"
            )
        if not diagnostics:
            _fail(f"{path} blocked state requires at least one diagnostic")
        if summary_eligible:
            _fail(f"{path} blocked state cannot declare eligible outputs")
        if summary_blocked != request_blocked_outputs:
            _fail(f"{path} blocked summary must preserve request.blocked_outputs")
        if decision_value != _control_block_value(resume_control, "decision_rule"):
            _fail(f"{path}.summary.decision_value must match active decision_rule")
    else:
        if diagnostics:
            _fail(f"{path} recovered state cannot contain diagnostics")
        if not evidence_complete or missing_fields:
            _fail(f"{path} recovered state requires complete evidence")
        if condition_value is not True or not rewritten or not task_reexecuted:
            _fail(
                f"{path} recovered state requires verified materialization and reexecution"
            )
        if resumed_execution is None or final_control is None:
            _fail(
                f"{path} recovered state requires resumed execution and final control"
            )
        if _trigger_status(
            resumed_execution, trigger, f"{path}.resumed_execution"
        ) != "verified":
            _fail(f"{path}.resumed_execution trigger must be verified")
        if summary_blocked != list(final_control.blocked_outputs):
            _fail(f"{path}.summary.blocked_outputs must match final control")
        if summary_eligible != list(final_control.eligible_outputs):
            _fail(f"{path}.summary.eligible_outputs must match final control")
        if decision_value != _control_block_value(final_control, "decision_rule"):
            _fail(f"{path}.summary.decision_value must match active decision_rule")
        if _control_block_value(resume_control, "evidence_request") is not True:
            _fail(
                f"{path}.resume_control_evaluation must satisfy evidence_request"
            )
    return body


def _revision_verification_body(value: object, path: str) -> dict[str, Any]:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path=path,
        required={
            "report_version",
            "state",
            "revision_base_sha256",
            "revised_document_sha256",
            "policy",
            "changed_paths",
            "allowed_paths",
            "resolved_changes",
            "violations",
            "summary",
        },
    )
    _const(
        body["report_version"],
        AGENT_REVISION_VERIFICATION_VERSION,
        f"{path}.report_version",
    )
    state = _enum(body["state"], {"accepted", "rejected"}, f"{path}.state")
    _sha256(body["revision_base_sha256"], f"{path}.revision_base_sha256")
    _sha256(body["revised_document_sha256"], f"{path}.revised_document_sha256")

    policy = _mapping(body["policy"], f"{path}.policy")
    _exact_fields(
        policy,
        path=f"{path}.policy",
        required={
            "requested_paths_only",
            "candidate_values_are_inventory_only",
            "coordinates_immutable_unless_requested",
            "evidence_immutable_unless_requested",
            "domain_policy_immutable_unless_requested",
            "model_called",
            "automatic_revision_applied",
            "task_executed",
        },
    )
    for field in (
        "requested_paths_only",
        "candidate_values_are_inventory_only",
        "coordinates_immutable_unless_requested",
        "evidence_immutable_unless_requested",
        "domain_policy_immutable_unless_requested",
    ):
        _const(policy[field], True, f"{path}.policy.{field}")
    for field in ("model_called", "automatic_revision_applied", "task_executed"):
        _const(policy[field], False, f"{path}.policy.{field}")

    changed_paths = _string_list(
        body["changed_paths"], f"{path}.changed_paths", unique=True
    )
    if changed_paths != sorted(changed_paths):
        _fail(f"{path}.changed_paths must use stable sorted order")

    allowed_raw = body["allowed_paths"]
    resolved_raw = body["resolved_changes"]
    violations_raw = body["violations"]
    if not isinstance(allowed_raw, list):
        _fail(f"{path}.allowed_paths must be an array")
    if not isinstance(resolved_raw, list):
        _fail(f"{path}.resolved_changes must be an array")
    if not isinstance(violations_raw, list):
        _fail(f"{path}.violations must be an array")
    allowed = [_allowed_path(item, f"{path}.allowed_paths[{index}]") for index, item in enumerate(allowed_raw)]
    resolved = [_resolved_change(item, f"{path}.resolved_changes[{index}]") for index, item in enumerate(resolved_raw)]
    violations = [_violation(item, f"{path}.violations[{index}]") for index, item in enumerate(violations_raw)]

    summary = _mapping(body["summary"], f"{path}.summary")
    _exact_fields(
        summary,
        path=f"{path}.summary",
        required={
            "changed_path_count",
            "resolved_change_count",
            "violation_count",
            "accepted",
        },
    )
    if _integer(summary["changed_path_count"], f"{path}.summary.changed_path_count") != len(changed_paths):
        _fail(f"{path}.summary.changed_path_count does not match changed_paths")
    if _integer(summary["resolved_change_count"], f"{path}.summary.resolved_change_count") != len(resolved):
        _fail(f"{path}.summary.resolved_change_count does not match resolved_changes")
    if _integer(summary["violation_count"], f"{path}.summary.violation_count") != len(violations):
        _fail(f"{path}.summary.violation_count does not match violations")
    accepted = _boolean(summary["accepted"], f"{path}.summary.accepted")
    if accepted != (state == "accepted"):
        _fail(f"{path}.summary.accepted must match state")
    if state == "accepted" and violations:
        _fail(f"{path} accepted state cannot contain violations")
    if state == "rejected" and not violations:
        _fail(f"{path} rejected state requires at least one violation")
    return body


def _revision_retry_body(value: object, path: str) -> dict[str, Any]:
    body = _mapping(value, path)
    _exact_fields(
        body,
        path=path,
        required={
            "report_version",
            "state",
            "revision_verification",
            "preparation",
            "summary",
        },
    )
    _const(
        body["report_version"],
        AGENT_REVISION_RETRY_VERSION,
        f"{path}.report_version",
    )
    state = _enum(body["state"], {"accepted", "rejected", "blocked"}, f"{path}.state")
    verification = _revision_verification_body(
        body["revision_verification"], f"{path}.revision_verification"
    )
    preparation_value = body["preparation"]
    preparation = (
        None
        if preparation_value is None
        else _preparation_body(preparation_value, f"{path}.preparation")
    )

    summary = _mapping(body["summary"], f"{path}.summary")
    _exact_fields(
        summary,
        path=f"{path}.summary",
        required={
            "revision_accepted",
            "task_executed",
            "preparation_state",
            "overall_status",
        },
    )
    revision_accepted = _boolean(
        summary["revision_accepted"], f"{path}.summary.revision_accepted"
    )
    task_executed = _boolean(summary["task_executed"], f"{path}.summary.task_executed")
    preparation_state = _string(
        summary["preparation_state"], f"{path}.summary.preparation_state", allow_empty=True
    )
    overall_status = _string(
        summary["overall_status"], f"{path}.summary.overall_status", allow_empty=True
    )

    verification_accepted = verification["state"] == "accepted"
    if revision_accepted != verification_accepted:
        _fail(f"{path}.summary.revision_accepted must match revision verification")
    if state == "rejected":
        if verification_accepted or preparation is not None or task_executed:
            _fail(f"{path} rejected state must not contain preparation or execution")
        if preparation_state or overall_status:
            _fail(f"{path} rejected summary must not claim preparation output")
    elif state == "accepted":
        if not verification_accepted or preparation is None:
            _fail(f"{path} accepted state requires accepted verification and preparation")
        if preparation["state"] not in {"valid", "repaired"} or not task_executed:
            _fail(f"{path} accepted state requires successful executed preparation")
        if preparation_state != preparation["state"]:
            _fail(f"{path}.summary.preparation_state must match preparation")
        expected_overall = preparation["summary"]["overall_status"]
        if overall_status != expected_overall:
            _fail(f"{path}.summary.overall_status must match preparation")
    else:
        if not verification_accepted or preparation is None:
            _fail(f"{path} blocked state requires accepted verification and preparation")
        if preparation["state"] != "blocked" or task_executed:
            _fail(f"{path} blocked state requires an unexecuted blocked preparation")
        if preparation_state != "blocked" or overall_status:
            _fail(f"{path} blocked summary must match blocked preparation")
    return body


def load_agent_generation_preparation_report(
    payload: Mapping[str, object],
) -> dict[str, Any]:
    """Strictly load ``agent_generation_preparation/0.1`` without executing it."""

    root = _mapping(payload, "root")
    _exact_fields(root, path="root", required={"agent_generation_preparation"})
    body = _preparation_body(
        root["agent_generation_preparation"], "agent_generation_preparation"
    )
    return {"agent_generation_preparation": deepcopy(body)}


def load_agent_revision_verification_report(
    payload: Mapping[str, object],
) -> dict[str, Any]:
    """Strictly load ``agent_revision_verification/0.1`` without retrying."""

    root = _mapping(payload, "root")
    _exact_fields(root, path="root", required={"agent_revision_verification"})
    body = _revision_verification_body(
        root["agent_revision_verification"], "agent_revision_verification"
    )
    return {"agent_revision_verification": deepcopy(body)}


def load_agent_revision_retry_report(
    payload: Mapping[str, object],
) -> dict[str, Any]:
    """Strictly load ``agent_revision_retry/0.1`` without repeating the retry."""

    root = _mapping(payload, "root")
    _exact_fields(root, path="root", required={"agent_revision_retry"})
    body = _revision_retry_body(root["agent_revision_retry"], "agent_revision_retry")
    return {"agent_revision_retry": deepcopy(body)}


def load_agent_evidence_recovery_report(
    payload: Mapping[str, object],
) -> dict[str, Any]:
    """Strictly load ``agent_integration/0.1`` without repeating recovery."""

    root = _mapping(payload, "root")
    _exact_fields(root, path="root", required={"agent_integration"})
    body = _evidence_recovery_body(root["agent_integration"], "agent_integration")
    return {"agent_integration": deepcopy(body)}


__all__ = [
    "AGENT_GENERATION_PREPARATION_SCHEMA_ID",
    "AGENT_GENERATION_PREPARATION_SCHEMA_VERSION",
    "AGENT_REVISION_VERIFICATION_SCHEMA_ID",
    "AGENT_REVISION_VERIFICATION_SCHEMA_VERSION",
    "AGENT_REVISION_RETRY_SCHEMA_ID",
    "AGENT_REVISION_RETRY_SCHEMA_VERSION",
    "AGENT_EVIDENCE_RECOVERY_SCHEMA_ID",
    "AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION",
    "AgentArtifactFormatError",
    "load_agent_generation_preparation_report",
    "load_agent_revision_verification_report",
    "load_agent_revision_retry_report",
    "load_agent_evidence_recovery_report",
]
