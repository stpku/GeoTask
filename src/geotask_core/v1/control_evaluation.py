"""Read-only control contexts and structured control-profile evaluation.

This module binds executed assertion values and explicit domain state into a
read-only context, then evaluates the finite expressions declared by
``geotask.control/1.0``. Evaluation is observational only: it never mutates the
GeoTask result, releases an output in the executor, or executes ``next_action``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
import re
from types import MappingProxyType
from typing import Any

from geotask_core.v1.control_expressions import (
    ExpressionEvaluationError,
    _resolve_identifier,
    evaluate_control_expression,
    referenced_identifiers,
)
from geotask_core.v1.enums import is_valid_geotask_id
from geotask_core.v1.extension_profiles import validate_extension_profiles
from geotask_core.v1.ir import CanonicalDocument
from geotask_core.v1.result import GeotaskResult


CONTROL_EVALUATION_SCHEMA_VERSION = "1.0"

_CONTEXT_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_CONTROL_EXPRESSION_FIELDS = {
    "decision_rule": "expression",
    "evidence_request": "resume_when",
    "evidence_conflict": "resume_when",
    "task_gate": "resume_when",
}
_BLOCKING_CONTROL_BLOCKS = {
    "evidence_request",
    "evidence_conflict",
    "task_gate",
}


class ControlContextError(ValueError):
    """Raised when explicit state cannot be bound without ambiguity."""


@dataclass(frozen=True)
class ControlContextEntry:
    """Provenance for one addressable control-context value."""

    name: str
    value: bool | int | float | str | None
    source: str
    assertion_status: str = ""
    assurance_level: str = ""
    deterministic: bool = False
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "source": self.source,
            "assertion_status": self.assertion_status,
            "assurance_level": self.assurance_level,
            "deterministic": self.deterministic,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class ControlContext:
    """Immutable values and provenance used by control expressions."""

    values: Mapping[str, object]
    entries: Mapping[str, ControlContextEntry]

    def to_dict(self) -> dict[str, Any]:
        return {
            "values": _thaw_value(self.values),
            "entries": {
                name: entry.to_dict()
                for name, entry in sorted(self.entries.items())
            },
        }


@dataclass(frozen=True)
class ControlBlockEvaluation:
    """Evaluation result for one profiled control block."""

    block: str
    expression_field: str
    expression: str
    value: bool | None
    state: str
    referenced_identifiers: tuple[str, ...] = ()
    unknown_identifiers: tuple[str, ...] = ()
    blocked_outputs: tuple[str, ...] = ()
    eligible_outputs: tuple[str, ...] = ()
    selected_action: str = ""
    next_action: str = ""
    required_controls: tuple[str, ...] = ()
    rejected_actions: tuple[str, ...] = ()
    declared_status: str = ""
    evaluation_error: str = ""
    action_executed: bool = False

    @property
    def satisfied(self) -> bool:
        return self.value is True and not self.evaluation_error

    def to_dict(self) -> dict[str, Any]:
        return {
            "block": self.block,
            "expression_field": self.expression_field,
            "expression": self.expression,
            "value": self.value,
            "state": self.state,
            "satisfied": self.satisfied,
            "referenced_identifiers": list(self.referenced_identifiers),
            "unknown_identifiers": list(self.unknown_identifiers),
            "blocked_outputs": list(self.blocked_outputs),
            "eligible_outputs": list(self.eligible_outputs),
            "selected_action": self.selected_action,
            "next_action": self.next_action,
            "required_controls": list(self.required_controls),
            "rejected_actions": list(self.rejected_actions),
            "declared_status": self.declared_status,
            "evaluation_error": self.evaluation_error,
            "action_executed": self.action_executed,
        }


@dataclass(frozen=True)
class ControlEvaluationResult:
    """Structured, non-executing evaluation of a control profile."""

    schema_version: str
    task_id: str
    profile_id: str
    profile_version: str
    state: str
    context: ControlContext
    evaluations: tuple[ControlBlockEvaluation, ...] = ()
    unknown_identifiers: tuple[str, ...] = ()
    blocked_outputs: tuple[str, ...] = ()
    eligible_outputs: tuple[str, ...] = ()
    diagnostics: tuple[dict[str, str], ...] = ()
    action_executed: bool = False

    @property
    def gate_satisfied(self) -> bool | None:
        blocking = [
            item
            for item in self.evaluations
            if item.block in _BLOCKING_CONTROL_BLOCKS
        ]
        if not blocking:
            return None
        if any(item.evaluation_error for item in blocking):
            return None
        if any(item.value is False for item in blocking):
            return False
        if any(item.value is None for item in blocking):
            return None
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_evaluation": {
                "schema_version": self.schema_version,
                "task_id": self.task_id,
                "profile": {
                    "id": self.profile_id,
                    "version": self.profile_version,
                },
                "state": self.state,
                "gate_satisfied": self.gate_satisfied,
                "control_context": self.context.to_dict(),
                "evaluations": [item.to_dict() for item in self.evaluations],
                "unknown_identifiers": list(self.unknown_identifiers),
                "blocked_outputs": list(self.blocked_outputs),
                "eligible_outputs": list(self.eligible_outputs),
                "diagnostics": [dict(item) for item in self.diagnostics],
                "action_executed": self.action_executed,
            }
        }


def _validate_scalar(value: object, path: str) -> bool | int | float | str | None:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ControlContextError(
        f"{path} must be a finite scalar (boolean, number, string, or null), "
        f"got {type(value).__name__}"
    )


def _validate_key(key: object, path: str) -> str:
    if not isinstance(key, str) or not _CONTEXT_KEY_PATTERN.fullmatch(key):
        raise ControlContextError(
            f"{path} key {key!r} must match {_CONTEXT_KEY_PATTERN.pattern}"
        )
    return key


def _freeze_domain_state(
    value: object,
    *,
    path: str,
    entries: dict[str, ControlContextEntry],
) -> object:
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for raw_key, child in value.items():
            key = _validate_key(raw_key, path)
            child_path = f"{path}.{key}" if path else key
            frozen[key] = _freeze_domain_state(
                child,
                path=child_path,
                entries=entries,
            )
        return MappingProxyType(frozen)

    scalar = _validate_scalar(value, path)
    entries[path] = ControlContextEntry(
        name=path,
        value=scalar,
        source="domain_state",
    )
    return scalar


def _thaw_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_value(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(child) for child in value]
    return value


def build_control_context(
    result: GeotaskResult,
    domain_state: Mapping[str, object] | None = None,
) -> ControlContext:
    """Bind assertion values and explicit domain state into an immutable context.

    Assertion IDs are exposed as direct identifiers. Explicit domain state may
    contain nested mappings but cannot override assertion IDs or use the
    reserved top-level key ``assertions``. Only finite scalar leaves are
    accepted, which keeps evaluation deterministic and serializable.
    """

    if not isinstance(result, GeotaskResult):
        raise TypeError("result must be a GeotaskResult")
    if domain_state is not None and not isinstance(domain_state, Mapping):
        raise TypeError("domain_state must be a mapping or None")

    entries: dict[str, ControlContextEntry] = {}
    top_level: dict[str, object] = {}
    assertion_ids: set[str] = set()

    for check in result.checks:
        assertion_id = check.assertion_id
        if not isinstance(assertion_id, str) or not is_valid_geotask_id(assertion_id):
            raise ControlContextError(
                f"assertion id {assertion_id!r} is not a valid GeoTask identifier"
            )
        if assertion_id in assertion_ids:
            raise ControlContextError(
                f"duplicate assertion id {assertion_id!r} in execution result"
            )
        assertion_ids.add(assertion_id)
        value = _validate_scalar(check.value, f"assertion.{assertion_id}")
        top_level[assertion_id] = value
        entries[assertion_id] = ControlContextEntry(
            name=assertion_id,
            value=value,
            source="assertion_result",
            assertion_status=check.status,
            assurance_level=check.assurance_level,
            deterministic=check.deterministic,
            evidence_refs=tuple(str(item) for item in check.evidence_refs),
        )

    state = domain_state or {}
    for raw_key, raw_value in state.items():
        key = _validate_key(raw_key, "domain_state")
        if key == "assertions":
            raise ControlContextError(
                "domain_state key 'assertions' is reserved for future result metadata"
            )
        if key in assertion_ids:
            raise ControlContextError(
                f"domain_state key {key!r} conflicts with assertion result {key!r}"
            )
        top_level[key] = _freeze_domain_state(
            raw_value,
            path=key,
            entries=entries,
        )

    return ControlContext(
        values=MappingProxyType(top_level),
        entries=MappingProxyType(entries),
    )


def _block_state(
    *,
    block: str,
    value: bool | None,
    evaluation_error: str,
) -> str:
    if evaluation_error:
        return "error"
    if block == "decision_rule":
        if value is True:
            return "satisfied"
        if value is False:
            return "not_satisfied"
        return "unknown"
    if value is True:
        return "satisfied"
    if value is False:
        return "blocked"
    return "unknown"


def _evaluate_block(
    block_name: str,
    block: Mapping[str, object],
    context: ControlContext,
) -> ControlBlockEvaluation:
    field_name = _CONTROL_EXPRESSION_FIELDS[block_name]
    expression = str(block[field_name])
    identifiers = tuple(sorted(referenced_identifiers(expression)))
    unknown = tuple(
        name
        for name in identifiers
        if _resolve_identifier(context.values, name) is None
    )

    value: bool | None = None
    evaluation_error = ""
    try:
        value = evaluate_control_expression(expression, context.values)
    except ExpressionEvaluationError as exc:
        evaluation_error = str(exc)

    state = _block_state(
        block=block_name,
        value=value,
        evaluation_error=evaluation_error,
    )
    declared_outputs = tuple(str(item) for item in block.get("blocked_outputs", []))
    if block_name in _BLOCKING_CONTROL_BLOCKS and state != "satisfied":
        blocked_outputs = declared_outputs
        eligible_outputs: tuple[str, ...] = ()
    elif block_name in _BLOCKING_CONTROL_BLOCKS:
        blocked_outputs = ()
        eligible_outputs = declared_outputs
    else:
        blocked_outputs = ()
        eligible_outputs = ()

    return ControlBlockEvaluation(
        block=block_name,
        expression_field=field_name,
        expression=expression,
        value=value,
        state=state,
        referenced_identifiers=identifiers,
        unknown_identifiers=unknown,
        blocked_outputs=blocked_outputs,
        eligible_outputs=eligible_outputs,
        selected_action=str(block.get("selected_action", "")),
        next_action=str(block.get("next_action", "")),
        required_controls=tuple(
            str(item) for item in block.get("required_controls", [])
        ),
        rejected_actions=tuple(
            str(item) for item in block.get("rejected_actions", [])
        ),
        declared_status=str(block.get("status", block.get("expected_status", ""))),
        evaluation_error=evaluation_error,
        action_executed=False,
    )


def _aggregate_state(evaluations: tuple[ControlBlockEvaluation, ...]) -> str:
    blocking = [
        item for item in evaluations if item.block in _BLOCKING_CONTROL_BLOCKS
    ]
    if not evaluations:
        return "not_applicable"
    if any(item.evaluation_error for item in evaluations):
        return "error"
    if not blocking:
        decision = evaluations[0]
        return decision.state
    if any(item.value is False for item in blocking):
        return "blocked"
    if any(item.value is None for item in blocking):
        return "unknown"
    return "satisfied"


def evaluate_control_profile(
    doc: CanonicalDocument,
    result: GeotaskResult,
    domain_state: Mapping[str, object] | None = None,
) -> ControlEvaluationResult:
    """Evaluate declared public control expressions without executing actions."""

    if not isinstance(doc, CanonicalDocument):
        raise TypeError("doc must be a CanonicalDocument")
    if not isinstance(result, GeotaskResult):
        raise TypeError("result must be a GeotaskResult")
    if result.task_id != doc.metadata.id:
        raise ControlContextError(
            f"result task_id {result.task_id!r} does not match document id "
            f"{doc.metadata.id!r}"
        )

    assertion_ids = {
        assertion.id
        for task in doc.tasks
        for assertion in task.assertions
        if assertion.id
    }
    unexpected_checks = sorted(
        {
            check.assertion_id
            for check in result.checks
            if check.assertion_id not in assertion_ids
        }
    )
    if unexpected_checks:
        raise ControlContextError(
            "execution result contains checks not declared by the document: "
            + ", ".join(unexpected_checks)
        )

    context = build_control_context(result, domain_state)
    profile = doc.extensions.get("extension_profile")

    if not isinstance(profile, Mapping):
        return ControlEvaluationResult(
            schema_version=CONTROL_EVALUATION_SCHEMA_VERSION,
            task_id=doc.metadata.id,
            profile_id="",
            profile_version="",
            state="not_applicable",
            context=context,
            diagnostics=(
                {
                    "code": "control_profile_not_declared",
                    "path": "extensions.extension_profile",
                    "message": "No control extension profile is declared.",
                },
            ),
        )

    profile_id = str(profile.get("id", ""))
    profile_version = str(profile.get("version", ""))
    profile_diagnostics = validate_extension_profiles(
        doc.extensions,
        assertion_ids=assertion_ids,
    )
    if profile_diagnostics:
        return ControlEvaluationResult(
            schema_version=CONTROL_EVALUATION_SCHEMA_VERSION,
            task_id=doc.metadata.id,
            profile_id=profile_id,
            profile_version=profile_version,
            state="error",
            context=context,
            diagnostics=tuple(
                {
                    "code": str(item.get("code", "extension_profile_violation")),
                    "path": str(item.get("path", "extensions")),
                    "message": str(item.get("message", "Invalid control profile.")),
                }
                for item in profile_diagnostics
            ),
        )

    evaluations = tuple(
        _evaluate_block(block_name, doc.extensions[block_name], context)
        for block_name in _CONTROL_EXPRESSION_FIELDS
        if isinstance(doc.extensions.get(block_name), Mapping)
    )
    unknown_identifiers = tuple(
        sorted(
            {
                name
                for evaluation in evaluations
                for name in evaluation.unknown_identifiers
            }
        )
    )
    blocked_outputs = tuple(
        sorted(
            {
                output
                for evaluation in evaluations
                for output in evaluation.blocked_outputs
            }
        )
    )
    eligible_outputs = tuple(
        sorted(
            {
                output
                for evaluation in evaluations
                for output in evaluation.eligible_outputs
                if output not in blocked_outputs
            }
        )
    )
    diagnostics = tuple(
        {
            "code": "control_expression_evaluation_error",
            "path": f"extensions.{evaluation.block}.{evaluation.expression_field}",
            "message": evaluation.evaluation_error,
        }
        for evaluation in evaluations
        if evaluation.evaluation_error
    )

    return ControlEvaluationResult(
        schema_version=CONTROL_EVALUATION_SCHEMA_VERSION,
        task_id=doc.metadata.id,
        profile_id=profile_id,
        profile_version=profile_version,
        state=_aggregate_state(evaluations),
        context=context,
        evaluations=evaluations,
        unknown_identifiers=unknown_identifiers,
        blocked_outputs=blocked_outputs,
        eligible_outputs=eligible_outputs,
        diagnostics=diagnostics,
        action_executed=False,
    )
