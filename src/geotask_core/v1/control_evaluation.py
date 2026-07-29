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


CONTROL_EVALUATION_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-control-evaluation-v1.0.schema.json"
)
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
_CONTROL_BLOCKS = set(_CONTROL_EXPRESSION_FIELDS)
_CONTROL_BLOCK_STATES = {
    "satisfied",
    "not_satisfied",
    "blocked",
    "unknown",
    "error",
}
_CONTROL_RESULT_STATES = _CONTROL_BLOCK_STATES | {"not_applicable"}
_CONTROL_CONTEXT_SOURCES = {"assertion_result", "domain_state"}


class ControlContextError(ValueError):
    """Raised when explicit state cannot be bound without ambiguity."""


class ControlEvaluationFormatError(ValueError):
    """Raised when serialized control-evaluation data violates v1.0."""


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


def _format_mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ControlEvaluationFormatError(f"{path} must be an object")
    return value


def _format_list(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ControlEvaluationFormatError(f"{path} must be an array")
    return value


def _format_string(value: object, path: str, *, nonempty: bool = False) -> str:
    if not isinstance(value, str):
        raise ControlEvaluationFormatError(f"{path} must be a string")
    if nonempty and not value:
        raise ControlEvaluationFormatError(f"{path} must not be empty")
    return value


def _format_bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise ControlEvaluationFormatError(f"{path} must be a boolean")
    return value


def _format_nullable_bool(value: object, path: str) -> bool | None:
    if value is None:
        return None
    return _format_bool(value, path)


def _format_enum(value: object, path: str, allowed: set[str]) -> str:
    text = _format_string(value, path)
    if text not in allowed:
        raise ControlEvaluationFormatError(
            f"{path} must be one of: {', '.join(sorted(allowed))}"
        )
    return text


def _format_exact_keys(
    value: Mapping[str, Any],
    *,
    path: str,
    required: set[str],
) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required)
    if missing:
        raise ControlEvaluationFormatError(
            f"{path} missing required field(s): {', '.join(missing)}"
        )
    if unknown:
        raise ControlEvaluationFormatError(
            f"{path} contains unknown field(s): {', '.join(unknown)}"
        )


def _format_string_list(value: object, path: str) -> tuple[str, ...]:
    items = _format_list(value, path)
    result = tuple(
        _format_string(item, f"{path}[{index}]")
        for index, item in enumerate(items)
    )
    if len(set(result)) != len(result):
        raise ControlEvaluationFormatError(f"{path} must contain unique strings")
    return result


def _format_scalar(value: object, path: str) -> bool | int | float | str | None:
    try:
        return _validate_scalar(value, path)
    except ControlContextError as exc:
        raise ControlEvaluationFormatError(str(exc)) from exc


def _format_context_value(
    value: object,
    *,
    path: str,
    leaves: dict[str, bool | int | float | str | None],
) -> object:
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for raw_key, child in value.items():
            try:
                key = _validate_key(raw_key, path)
            except ControlContextError as exc:
                raise ControlEvaluationFormatError(str(exc)) from exc
            child_path = f"{path}.{key}" if path else key
            frozen[key] = _format_context_value(
                child,
                path=child_path,
                leaves=leaves,
            )
        return MappingProxyType(frozen)
    scalar = _format_scalar(value, path)
    leaves[path] = scalar
    return scalar


def _format_control_context(value: object, path: str) -> ControlContext:
    data = _format_mapping(value, path)
    _format_exact_keys(data, path=path, required={"values", "entries"})

    raw_values = _format_mapping(data["values"], f"{path}.values")
    leaves: dict[str, bool | int | float | str | None] = {}
    values = _format_context_value(raw_values, path="", leaves=leaves)

    raw_entries = _format_mapping(data["entries"], f"{path}.entries")
    entries: dict[str, ControlContextEntry] = {}
    required_entry_fields = {
        "name",
        "value",
        "source",
        "assertion_status",
        "assurance_level",
        "deterministic",
        "evidence_refs",
    }
    for raw_name, raw_entry in raw_entries.items():
        name = _format_string(raw_name, f"{path}.entries key", nonempty=True)
        entry_path = f"{path}.entries.{name}"
        entry = _format_mapping(raw_entry, entry_path)
        _format_exact_keys(entry, path=entry_path, required=required_entry_fields)
        declared_name = _format_string(
            entry["name"], f"{entry_path}.name", nonempty=True
        )
        if declared_name != name:
            raise ControlEvaluationFormatError(
                f"{entry_path}.name must equal its entries key {name!r}"
            )
        entries[name] = ControlContextEntry(
            name=name,
            value=_format_scalar(entry["value"], f"{entry_path}.value"),
            source=_format_enum(
                entry["source"],
                f"{entry_path}.source",
                _CONTROL_CONTEXT_SOURCES,
            ),
            assertion_status=_format_string(
                entry["assertion_status"], f"{entry_path}.assertion_status"
            ),
            assurance_level=_format_string(
                entry["assurance_level"], f"{entry_path}.assurance_level"
            ),
            deterministic=_format_bool(
                entry["deterministic"], f"{entry_path}.deterministic"
            ),
            evidence_refs=_format_string_list(
                entry["evidence_refs"], f"{entry_path}.evidence_refs"
            ),
        )

    if set(entries) != set(leaves):
        raise ControlEvaluationFormatError(
            f"{path}.entries keys must exactly match scalar leaves in {path}.values"
        )
    for name, entry in entries.items():
        if entry.value != leaves[name] or type(entry.value) is not type(leaves[name]):
            raise ControlEvaluationFormatError(
                f"{path}.entries.{name}.value must equal {path}.values leaf {name!r}"
            )

    return ControlContext(
        values=values,
        entries=MappingProxyType(entries),
    )


def _format_block_evaluation(
    value: object,
    *,
    path: str,
    context: ControlContext,
) -> ControlBlockEvaluation:
    data = _format_mapping(value, path)
    required = {
        "block",
        "expression_field",
        "expression",
        "value",
        "state",
        "satisfied",
        "referenced_identifiers",
        "unknown_identifiers",
        "blocked_outputs",
        "eligible_outputs",
        "selected_action",
        "next_action",
        "required_controls",
        "rejected_actions",
        "declared_status",
        "evaluation_error",
        "action_executed",
    }
    _format_exact_keys(data, path=path, required=required)
    block = _format_enum(data["block"], f"{path}.block", _CONTROL_BLOCKS)
    expression_field = _format_enum(
        data["expression_field"],
        f"{path}.expression_field",
        {"expression", "resume_when"},
    )
    if expression_field != _CONTROL_EXPRESSION_FIELDS[block]:
        raise ControlEvaluationFormatError(
            f"{path}.expression_field is inconsistent with block {block!r}"
        )
    expression = _format_string(
        data["expression"], f"{path}.expression", nonempty=True
    )
    if len(expression) > 4096:
        raise ControlEvaluationFormatError(
            f"{path}.expression must not exceed 4096 characters"
        )
    try:
        actual_identifiers = tuple(sorted(referenced_identifiers(expression)))
    except ValueError as exc:
        raise ControlEvaluationFormatError(
            f"{path}.expression is invalid: {exc}"
        ) from exc
    declared_identifiers = _format_string_list(
        data["referenced_identifiers"], f"{path}.referenced_identifiers"
    )
    if set(declared_identifiers) != set(actual_identifiers):
        raise ControlEvaluationFormatError(
            f"{path}.referenced_identifiers must match expression identifiers"
        )
    declared_unknown = _format_string_list(
        data["unknown_identifiers"], f"{path}.unknown_identifiers"
    )
    expected_unknown = {
        name
        for name in actual_identifiers
        if _resolve_identifier(context.values, name) is None
    }
    if set(declared_unknown) != expected_unknown:
        raise ControlEvaluationFormatError(
            f"{path}.unknown_identifiers must match unresolved context identifiers"
        )
    evaluation_error = _format_string(
        data["evaluation_error"], f"{path}.evaluation_error"
    )
    block_value = _format_nullable_bool(data["value"], f"{path}.value")
    state = _format_enum(data["state"], f"{path}.state", _CONTROL_BLOCK_STATES)
    expected_state = _block_state(
        block=block,
        value=block_value,
        evaluation_error=evaluation_error,
    )
    if state != expected_state:
        raise ControlEvaluationFormatError(
            f"{path}.state must be {expected_state!r} for its block value"
        )
    declared_satisfied = _format_bool(data["satisfied"], f"{path}.satisfied")
    expected_satisfied = block_value is True and not evaluation_error
    if declared_satisfied is not expected_satisfied:
        raise ControlEvaluationFormatError(
            f"{path}.satisfied is inconsistent with value and evaluation_error"
        )
    if _format_bool(data["action_executed"], f"{path}.action_executed"):
        raise ControlEvaluationFormatError(f"{path}.action_executed must be false")

    blocked_outputs = _format_string_list(
        data["blocked_outputs"], f"{path}.blocked_outputs"
    )
    eligible_outputs = _format_string_list(
        data["eligible_outputs"], f"{path}.eligible_outputs"
    )
    if block in _BLOCKING_CONTROL_BLOCKS:
        if state == "satisfied" and blocked_outputs:
            raise ControlEvaluationFormatError(
                f"{path}.blocked_outputs must be empty when the gate is satisfied"
            )
        if state != "satisfied" and eligible_outputs:
            raise ControlEvaluationFormatError(
                f"{path}.eligible_outputs must be empty while the gate is not satisfied"
            )
    elif blocked_outputs or eligible_outputs:
        raise ControlEvaluationFormatError(
            f"{path} decision_rule cannot declare blocked or eligible outputs"
        )

    return ControlBlockEvaluation(
        block=block,
        expression_field=expression_field,
        expression=expression,
        value=block_value,
        state=state,
        referenced_identifiers=declared_identifiers,
        unknown_identifiers=declared_unknown,
        blocked_outputs=blocked_outputs,
        eligible_outputs=eligible_outputs,
        selected_action=_format_string(
            data["selected_action"], f"{path}.selected_action"
        ),
        next_action=_format_string(data["next_action"], f"{path}.next_action"),
        required_controls=_format_string_list(
            data["required_controls"], f"{path}.required_controls"
        ),
        rejected_actions=_format_string_list(
            data["rejected_actions"], f"{path}.rejected_actions"
        ),
        declared_status=_format_string(
            data["declared_status"], f"{path}.declared_status"
        ),
        evaluation_error=evaluation_error,
        action_executed=False,
    )


def load_control_evaluation(payload: Mapping[str, object]) -> ControlEvaluationResult:
    """Strictly load a serialized Control Evaluation Result v1.0 payload."""

    wrapper = _format_mapping(payload, "payload")
    _format_exact_keys(wrapper, path="payload", required={"control_evaluation"})
    data = _format_mapping(wrapper["control_evaluation"], "control_evaluation")
    required = {
        "schema_version",
        "task_id",
        "profile",
        "state",
        "gate_satisfied",
        "control_context",
        "evaluations",
        "unknown_identifiers",
        "blocked_outputs",
        "eligible_outputs",
        "diagnostics",
        "action_executed",
    }
    _format_exact_keys(data, path="control_evaluation", required=required)

    schema_version = _format_string(
        data["schema_version"], "control_evaluation.schema_version"
    )
    if schema_version != CONTROL_EVALUATION_SCHEMA_VERSION:
        raise ControlEvaluationFormatError(
            "control_evaluation.schema_version must be '1.0'"
        )
    task_id = _format_string(
        data["task_id"], "control_evaluation.task_id", nonempty=True
    )
    profile = _format_mapping(data["profile"], "control_evaluation.profile")
    _format_exact_keys(
        profile,
        path="control_evaluation.profile",
        required={"id", "version"},
    )
    profile_id = _format_string(
        profile["id"], "control_evaluation.profile.id"
    )
    profile_version = _format_string(
        profile["version"], "control_evaluation.profile.version"
    )
    state = _format_enum(
        data["state"], "control_evaluation.state", _CONTROL_RESULT_STATES
    )
    if bool(profile_id) != bool(profile_version):
        raise ControlEvaluationFormatError(
            "control_evaluation.profile.id and version must both be empty or non-empty"
        )
    if not profile_id and state != "not_applicable":
        raise ControlEvaluationFormatError(
            "control_evaluation.profile may be empty only for not_applicable results"
        )
    declared_gate_satisfied = _format_nullable_bool(
        data["gate_satisfied"], "control_evaluation.gate_satisfied"
    )
    context = _format_control_context(
        data["control_context"], "control_evaluation.control_context"
    )

    evaluations = tuple(
        _format_block_evaluation(
            item,
            path=f"control_evaluation.evaluations[{index}]",
            context=context,
        )
        for index, item in enumerate(
            _format_list(data["evaluations"], "control_evaluation.evaluations")
        )
    )
    block_names = [item.block for item in evaluations]
    if len(set(block_names)) != len(block_names):
        raise ControlEvaluationFormatError(
            "control_evaluation.evaluations must not repeat a control block"
        )

    diagnostics_data = _format_list(
        data["diagnostics"], "control_evaluation.diagnostics"
    )
    diagnostics: list[dict[str, str]] = []
    for index, raw_diagnostic in enumerate(diagnostics_data):
        path = f"control_evaluation.diagnostics[{index}]"
        diagnostic = _format_mapping(raw_diagnostic, path)
        _format_exact_keys(
            diagnostic,
            path=path,
            required={"code", "path", "message"},
        )
        diagnostics.append(
            {
                "code": _format_string(
                    diagnostic["code"], f"{path}.code", nonempty=True
                ),
                "path": _format_string(diagnostic["path"], f"{path}.path"),
                "message": _format_string(
                    diagnostic["message"], f"{path}.message", nonempty=True
                ),
            }
        )

    if _format_bool(
        data["action_executed"], "control_evaluation.action_executed"
    ):
        raise ControlEvaluationFormatError(
            "control_evaluation.action_executed must be false"
        )

    result = ControlEvaluationResult(
        schema_version=schema_version,
        task_id=task_id,
        profile_id=profile_id,
        profile_version=profile_version,
        state=state,
        context=context,
        evaluations=evaluations,
        unknown_identifiers=_format_string_list(
            data["unknown_identifiers"], "control_evaluation.unknown_identifiers"
        ),
        blocked_outputs=_format_string_list(
            data["blocked_outputs"], "control_evaluation.blocked_outputs"
        ),
        eligible_outputs=_format_string_list(
            data["eligible_outputs"], "control_evaluation.eligible_outputs"
        ),
        diagnostics=tuple(diagnostics),
        action_executed=False,
    )

    if result.gate_satisfied is not declared_gate_satisfied:
        raise ControlEvaluationFormatError(
            "control_evaluation.gate_satisfied is inconsistent with evaluations"
        )
    if evaluations:
        expected_state = _aggregate_state(evaluations)
        if state != expected_state:
            raise ControlEvaluationFormatError(
                f"control_evaluation.state must be {expected_state!r} for evaluations"
            )
    elif diagnostics:
        if state not in {"error", "not_applicable"}:
            raise ControlEvaluationFormatError(
                "control_evaluation.state must be 'error' or 'not_applicable' "
                "when diagnostics exist without evaluations"
            )
    elif state != "not_applicable":
        raise ControlEvaluationFormatError(
            "control_evaluation.state must be 'not_applicable' without evaluations"
        )

    expected_unknown = {
        name for evaluation in evaluations for name in evaluation.unknown_identifiers
    }
    if set(result.unknown_identifiers) != expected_unknown:
        raise ControlEvaluationFormatError(
            "control_evaluation.unknown_identifiers must aggregate evaluations"
        )
    expected_blocked = {
        output for evaluation in evaluations for output in evaluation.blocked_outputs
    }
    if set(result.blocked_outputs) != expected_blocked:
        raise ControlEvaluationFormatError(
            "control_evaluation.blocked_outputs must aggregate evaluations"
        )
    expected_eligible = {
        output
        for evaluation in evaluations
        for output in evaluation.eligible_outputs
        if output not in expected_blocked
    }
    if set(result.eligible_outputs) != expected_eligible:
        raise ControlEvaluationFormatError(
            "control_evaluation.eligible_outputs must aggregate evaluations"
        )
    return result


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
