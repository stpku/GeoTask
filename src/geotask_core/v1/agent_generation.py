"""Fail-closed preparation of Agent-generated GeoTask documents.

The preview repairs only protocol-level omissions that can be derived without
spatial, temporal, evidential, or domain inference. It never changes coordinates,
chooses object references, substitutes operators, calls a model, or executes a
non-local Runtime. A prepared document is executed only after strict validation
returns no error diagnostics.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


AGENT_GENERATION_REPORT_VERSION = "0.1"
AGENT_REVISION_REQUEST_VERSION = "0.1"
AGENT_REVISION_VERIFICATION_VERSION = "0.1"
AGENT_REVISION_RETRY_VERSION = "0.1"


class AgentGenerationError(ValueError):
    """Raised when a generated-document preparation request is malformed."""


@dataclass(frozen=True)
class DocumentRepairAction:
    """One deterministic, protocol-level modification."""

    code: str
    path: str
    before: object
    after: object
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "path": self.path,
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
            "domain_inference_used": False,
            "model_called": False,
        }


@dataclass(frozen=True)
class GeneratedDocumentRevisionItem:
    """One unresolved change that must be made outside deterministic Core repair."""

    code: str
    path: str
    action: str
    instruction: str
    candidate_values: tuple[str, ...] = ()
    retryable: bool = True
    requires_external_input: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "path": self.path,
            "action": self.action,
            "instruction": self.instruction,
            "candidate_values": list(self.candidate_values),
            "selected_value": None,
            "automatic_change_allowed": False,
            "retryable": self.retryable,
            "requires_external_input": self.requires_external_input,
        }


@dataclass(frozen=True)
class GeneratedDocumentRevisionVerificationResult:
    """Auditable proof that a revision changed only requested paths."""

    state: str
    revision_base_sha256: str
    revised_document_sha256: str
    changed_paths: tuple[str, ...]
    allowed_paths: tuple[Mapping[str, Any], ...]
    resolved_changes: tuple[Mapping[str, Any], ...]
    violations: tuple[Mapping[str, str], ...]

    @property
    def accepted(self) -> bool:
        return self.state == "accepted"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_revision_verification": {
                "report_version": AGENT_REVISION_VERIFICATION_VERSION,
                "state": self.state,
                "revision_base_sha256": self.revision_base_sha256,
                "revised_document_sha256": self.revised_document_sha256,
                "policy": {
                    "requested_paths_only": True,
                    "candidate_values_are_inventory_only": True,
                    "coordinates_immutable_unless_requested": True,
                    "evidence_immutable_unless_requested": True,
                    "domain_policy_immutable_unless_requested": True,
                    "model_called": False,
                    "automatic_revision_applied": False,
                    "task_executed": False,
                },
                "changed_paths": list(self.changed_paths),
                "allowed_paths": [dict(item) for item in self.allowed_paths],
                "resolved_changes": [dict(item) for item in self.resolved_changes],
                "violations": [dict(item) for item in self.violations],
                "summary": {
                    "changed_path_count": len(self.changed_paths),
                    "resolved_change_count": len(self.resolved_changes),
                    "violation_count": len(self.violations),
                    "accepted": self.accepted,
                },
            }
        }


@dataclass(frozen=True)
class GeneratedDocumentRevisionRetryResult:
    """Revision verification followed by fail-closed document preparation."""

    state: str
    verification: GeneratedDocumentRevisionVerificationResult
    preparation: "GeneratedDocumentPreparationResult | None"

    def to_dict(self) -> dict[str, Any]:
        preparation_body = None
        if self.preparation is not None:
            preparation_body = self.preparation.to_dict()[
                "agent_generation_preparation"
            ]
        execution_result = (
            preparation_body.get("execution_result")
            if isinstance(preparation_body, Mapping)
            else None
        )
        result_body = (
            execution_result.get("geotask_result", {})
            if isinstance(execution_result, Mapping)
            else {}
        )
        overall = result_body.get("overall", {})
        return {
            "agent_revision_retry": {
                "report_version": AGENT_REVISION_RETRY_VERSION,
                "state": self.state,
                "revision_verification": self.verification.to_dict()[
                    "agent_revision_verification"
                ],
                "preparation": preparation_body,
                "summary": {
                    "revision_accepted": self.verification.accepted,
                    "task_executed": bool(
                        preparation_body
                        and preparation_body.get("summary", {}).get(
                            "task_executed", False
                        )
                    ),
                    "preparation_state": (
                        preparation_body.get("state", "")
                        if isinstance(preparation_body, Mapping)
                        else ""
                    ),
                    "overall_status": (
                        overall.get("status", "")
                        if isinstance(overall, Mapping)
                        else ""
                    ),
                },
            }
        }


@dataclass(frozen=True)
class GeneratedDocumentPreparationResult:
    """Validation, repair, revalidation, and optional execution trace."""

    state: str
    initial_diagnostics: tuple[Mapping[str, Any], ...]
    repairs: tuple[DocumentRepairAction, ...]
    residual_diagnostics: tuple[Mapping[str, Any], ...]
    prepared_document: Mapping[str, Any]
    execution_result: Mapping[str, Any] | None
    task_executed: bool

    def to_dict(self) -> dict[str, Any]:
        result_body: Mapping[str, Any] = {}
        if self.execution_result is not None:
            candidate = self.execution_result.get("geotask_result", {})
            if isinstance(candidate, Mapping):
                result_body = candidate
        checks = result_body.get("checks", [])
        execution = result_body.get("execution", {})
        overall = result_body.get("overall", {})
        revision_request = build_generated_document_revision_request(
            self.prepared_document,
            self.residual_diagnostics,
        )
        return {
            "agent_generation_preparation": {
                "report_version": AGENT_GENERATION_REPORT_VERSION,
                "state": self.state,
                "repair_policy": {
                    "mechanical_only": True,
                    "source_mutated": False,
                    "domain_inference_used": False,
                    "model_called": False,
                    "non_local_execution_allowed": False,
                },
                "initial_validation": {
                    "valid": not _error_diagnostics(self.initial_diagnostics),
                    "diagnostics": [dict(item) for item in self.initial_diagnostics],
                },
                "repairs": [item.to_dict() for item in self.repairs],
                "final_validation": {
                    "valid": not _error_diagnostics(self.residual_diagnostics),
                    "diagnostics": [dict(item) for item in self.residual_diagnostics],
                },
                "revision_request": revision_request,
                "prepared_document": deepcopy(dict(self.prepared_document)),
                "execution_result": (
                    None if self.execution_result is None else dict(self.execution_result)
                ),
                "summary": {
                    "repair_count": len(self.repairs),
                    "initial_error_count": len(
                        _error_diagnostics(self.initial_diagnostics)
                    ),
                    "residual_error_count": len(
                        _error_diagnostics(self.residual_diagnostics)
                    ),
                    "task_executed": self.task_executed,
                    "execution_status": (
                        execution.get("status", "")
                        if isinstance(execution, Mapping)
                        else ""
                    ),
                    "overall_status": (
                        overall.get("status", "")
                        if isinstance(overall, Mapping)
                        else ""
                    ),
                    "check_count": len(checks) if isinstance(checks, list) else 0,
                },
            }
        }


def _diagnostic(
    path: str,
    code: str,
    message: str,
    suggested_fix: str,
) -> dict[str, str]:
    return {
        "path": path,
        "code": code,
        "message": message,
        "suggested_fix": suggested_fix,
        "severity": "error",
    }


def _error_diagnostics(
    diagnostics: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    return [
        item for item in diagnostics if item.get("severity", "error") == "error"
    ]


def _deduplicate_diagnostics(
    diagnostics: list[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    seen: set[tuple[str, str]] = set()
    result: list[Mapping[str, Any]] = []
    for item in diagnostics:
        key = (str(item.get("path", "")), str(item.get("code", "")))
        if key in seen:
            continue
        seen.add(key)
        result.append(dict(item))
    return tuple(result)


def _document_fingerprint(document: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _revision_item(
    diagnostic: Mapping[str, Any],
    document: Mapping[str, Any],
) -> GeneratedDocumentRevisionItem:
    """Classify one residual diagnostic without selecting a semantic correction."""

    from geotask_core.operator_registry import operator_names
    from geotask_core.v1.enums import VALID_OBJECT_TYPES

    code = str(diagnostic.get("code", "validation_error"))
    path = str(diagnostic.get("path", ""))
    instruction = str(
        diagnostic.get("suggested_fix")
        or diagnostic.get("message")
        or "Revise the generated document and run agent prepare again."
    )
    objects = document.get("objects", {})
    object_ids = tuple(
        sorted(str(item) for item in objects.keys())
        if isinstance(objects, Mapping)
        else ()
    )

    if code in {"non_local_execution_forbidden", "unsupported_execution_mode"}:
        return GeneratedDocumentRevisionItem(
            code=code,
            path=path,
            action="route_to_authorized_runtime",
            instruction=(
                "Route this document to an authorized Runtime, or explicitly revise "
                "execution.mode to local_only only when Core supports the full task."
            ),
            candidate_values=("local_only",),
            retryable=False,
        )
    if "operator" in path or code in {
        "invalid_operator",
        "operator_inference_forbidden",
    }:
        return GeneratedDocumentRevisionItem(
            code=code,
            path=path,
            action="select_registered_operator",
            instruction=(
                "Select one registered operator that matches the intended task. "
                "Core lists candidates but does not choose one."
            ),
            candidate_values=tuple(operator_names()),
        )
    if "object_refs" in path or code in {
        "invalid_reference",
        "object_type_mismatch",
        "arity_mismatch",
        "object_binding_inference_forbidden",
    }:
        return GeneratedDocumentRevisionItem(
            code=code,
            path=path,
            action="bind_explicit_objects",
            instruction=(
                "Bind operator arguments to explicit compatible object ids. "
                "Core lists existing ids but does not select or reorder them."
            ),
            candidate_values=object_ids,
        )
    if code == "unknown_object_type" or path.endswith(".type"):
        return GeneratedDocumentRevisionItem(
            code=code,
            path=path,
            action="select_supported_object_type",
            instruction=(
                "Choose the supported object type that matches supplied data; "
                "Core does not infer the type."
            ),
            candidate_values=tuple(sorted(VALID_OBJECT_TYPES)),
        )
    if code in {
        "invalid_coordinates",
        "invalid_geometry",
        "invalid_interval",
        "missing_data",
        "missing_space_definition",
        "missing_objects_definition",
    }:
        return GeneratedDocumentRevisionItem(
            code=code,
            path=path,
            action="supply_explicit_spatial_data",
            instruction=instruction,
            requires_external_input=True,
        )
    if code in {"missing_semantic_identity", "unrepairable_metadata"}:
        return GeneratedDocumentRevisionItem(
            code=code,
            path=path,
            action="supply_explicit_task_identity",
            instruction=instruction,
            requires_external_input=True,
        )
    if code in {"missing_generated_tasks", "missing_generated_assertions"}:
        return GeneratedDocumentRevisionItem(
            code=code,
            path=path,
            action="generate_explicit_task_structure",
            instruction=instruction,
        )
    return GeneratedDocumentRevisionItem(
        code=code,
        path=path,
        action="revise_document_structure",
        instruction=instruction,
        requires_external_input=code in {"missing_field", "missing_data"},
    )


def build_generated_document_revision_request(
    prepared_document: Mapping[str, Any],
    diagnostics: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a machine-readable retry request from unresolved validation errors.

    Candidate values are inventories only. The request never selects a value,
    edits the document, calls a model, or authorizes execution.
    """

    errors = _error_diagnostics(diagnostics)
    items = tuple(_revision_item(item, prepared_document) for item in errors)
    if not items:
        state = "not_required"
        next_action = "none"
    elif all(item.retryable for item in items):
        state = "required"
        next_action = "revise_generated_document"
    elif all(not item.retryable for item in items):
        state = "routing_required"
        next_action = "route_to_authorized_runtime"
    else:
        state = "mixed"
        next_action = "revise_document_and_route_remaining_requirements"

    return {
        "request_version": AGENT_REVISION_REQUEST_VERSION,
        "state": state,
        "next_action": next_action,
        "revision_base": "prepared_document",
        "revision_base_sha256": _document_fingerprint(prepared_document),
        "required_changes": [item.to_dict() for item in items],
        "forbidden_changes": [
            "Do not invent coordinates, intervals, evidence, authorities, or domain policy.",
            "Do not treat candidate_values as an automatically selected answer.",
            "Do not bypass final validation or execute a blocked document.",
        ],
        "retry_command": (
            "geotask agent retry <blocked-report.json> <revised.yaml>"
        ),
        "resume_when": "final_validation.valid == true",
        "model_called": False,
        "automatic_revision_applied": False,
    }


_PATH_PART = re.compile(r"([^.\[\]]+)|\[(\d+)\]")
_MISSING = object()


def _revision_violation(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _path_segments(path: str) -> tuple[str | int, ...]:
    segments: list[str | int] = []
    for match in _PATH_PART.finditer(path):
        name, index = match.groups()
        segments.append(int(index) if index is not None else str(name))
    if not segments or "".join(
        f"[{item}]" if isinstance(item, int) else item for item in segments
    ).replace("[", "").replace("]", "") == "":
        raise AgentGenerationError(f"invalid revision path {path!r}")
    return tuple(segments)


def _value_at_path(document: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = document
    for segment in _path_segments(path):
        if isinstance(current, Mapping):
            if not isinstance(segment, str) or segment not in current:
                return False, None
            current = current[segment]
            continue
        if isinstance(current, list):
            if isinstance(segment, int):
                if segment < 0 or segment >= len(current):
                    return False, None
                current = current[segment]
                continue
            match = next(
                (
                    item
                    for item in current
                    if isinstance(item, Mapping) and item.get("id") == segment
                ),
                _MISSING,
            )
            if match is _MISSING:
                return False, None
            current = match
            continue
        return False, None
    return True, current


def _task_items_by_id(value: Any) -> tuple[list[str], dict[str, Mapping[str, Any]]] | None:
    if not isinstance(value, list):
        return None
    identifiers: list[str] = []
    items: dict[str, Mapping[str, Any]] = {}
    for item in value:
        if not isinstance(item, Mapping):
            return None
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in items:
            return None
        identifiers.append(identifier)
        items[identifier] = item
    return identifiers, items


def _join_mapping_path(path: str, key: object) -> str:
    return f"{path}.{key}" if path else str(key)


def _join_index_path(path: str, index: int) -> str:
    return f"{path}[{index}]" if path else f"[{index}]"


def _document_diff_paths(base: Any, revised: Any, path: str = "") -> list[str]:
    if isinstance(base, Mapping) and isinstance(revised, Mapping):
        changes: list[str] = []
        keys = sorted(set(base) | set(revised), key=str)
        for key in keys:
            child_path = _join_mapping_path(path, key)
            if key not in base or key not in revised:
                changes.append(child_path)
                continue
            changes.extend(_document_diff_paths(base[key], revised[key], child_path))
        return changes

    if isinstance(base, list) and isinstance(revised, list):
        if path == "tasks":
            base_tasks = _task_items_by_id(base)
            revised_tasks = _task_items_by_id(revised)
            if base_tasks is not None and revised_tasks is not None:
                base_order, base_items = base_tasks
                revised_order, revised_items = revised_tasks
                changes = []
                if base_order != revised_order:
                    changes.append("tasks.__order__")
                for identifier in sorted(set(base_items) | set(revised_items)):
                    child_path = f"tasks.{identifier}"
                    if identifier not in base_items or identifier not in revised_items:
                        changes.append(child_path)
                        continue
                    changes.extend(
                        _document_diff_paths(
                            base_items[identifier],
                            revised_items[identifier],
                            child_path,
                        )
                    )
                return changes

        changes = []
        if len(base) != len(revised):
            changes.append(f"{path}.__length__" if path else "$.__length__")
        for index in range(min(len(base), len(revised))):
            changes.extend(
                _document_diff_paths(
                    base[index],
                    revised[index],
                    _join_index_path(path, index),
                )
            )
        for index in range(min(len(base), len(revised)), max(len(base), len(revised))):
            changes.append(_join_index_path(path, index))
        return changes

    if type(base) is not type(revised) or base != revised:
        return [path or "$"]
    return []


def _allowed_revision_paths(
    required_changes: list[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    rules: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    subtree_actions = {
        "supply_explicit_spatial_data",
        "generate_explicit_task_structure",
        "revise_document_structure",
    }
    for item in required_changes:
        path = str(item.get("path", ""))
        action = str(item.get("action", ""))
        scope = "subtree" if action in subtree_actions else "exact"
        key = (path, scope)
        if path and key not in seen:
            seen.add(key)
            rules.append(
                {
                    "path": path,
                    "scope": scope,
                    "reason": f"requested by {item.get('code', 'validation_error')}",
                }
            )
        if action == "select_registered_operator":
            key = ("operator_set", "subtree")
            if key not in seen:
                seen.add(key)
                rules.append(
                    {
                        "path": "operator_set",
                        "scope": "subtree",
                        "reason": "derived inventory for an explicitly revised operator",
                    }
                )
    return tuple(rules)


def _change_is_allowed(change_path: str, rules: tuple[Mapping[str, Any], ...]) -> bool:
    for rule in rules:
        allowed = str(rule.get("path", ""))
        if change_path == allowed:
            return True
        if rule.get("scope") == "subtree" and (
            change_path.startswith(f"{allowed}.")
            or change_path.startswith(f"{allowed}[")
        ):
            return True
    return False


def _extract_revision_contract(
    preparation_report: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    body: Any = preparation_report.get(
        "agent_generation_preparation", preparation_report
    )
    if not isinstance(body, Mapping):
        raise AgentGenerationError(
            "preparation report must contain agent_generation_preparation"
        )
    if body.get("state") != "blocked":
        raise AgentGenerationError(
            "revision retry requires a blocked preparation report"
        )
    prepared_document = body.get("prepared_document")
    if not isinstance(prepared_document, Mapping):
        raise AgentGenerationError(
            "blocked preparation report is missing prepared_document"
        )
    final_validation = body.get("final_validation")
    diagnostics = (
        final_validation.get("diagnostics")
        if isinstance(final_validation, Mapping)
        else None
    )
    if not isinstance(diagnostics, list):
        raise AgentGenerationError(
            "blocked preparation report is missing final diagnostics"
        )
    revision_request = body.get("revision_request")
    if not isinstance(revision_request, Mapping):
        raise AgentGenerationError(
            "blocked preparation report is missing revision_request"
        )
    expected_request = build_generated_document_revision_request(
        prepared_document,
        diagnostics,
    )
    if dict(revision_request) != expected_request:
        raise AgentGenerationError(
            "revision_request does not match the blocked document diagnostics"
        )
    expected_fingerprint = _document_fingerprint(prepared_document)
    if revision_request.get("revision_base_sha256") != expected_fingerprint:
        raise AgentGenerationError(
            "revision_base_sha256 does not match prepared_document"
        )
    return prepared_document, revision_request


def _candidate_selection_valid(
    action: str,
    revised_value: Any,
    candidate_values: list[Any],
) -> bool:
    if not candidate_values:
        return True
    if action == "bind_explicit_objects" and isinstance(revised_value, list):
        return bool(revised_value) and all(
            item in candidate_values for item in revised_value
        )
    return revised_value in candidate_values


def verify_generated_document_revision(
    preparation_report: Mapping[str, Any],
    revised_document: Mapping[str, Any],
) -> GeneratedDocumentRevisionVerificationResult:
    """Reject any revision that changes fields outside the generated request."""

    if not isinstance(preparation_report, Mapping):
        raise TypeError("preparation_report must be a mapping")
    if not isinstance(revised_document, Mapping):
        raise TypeError("revised_document must be a mapping")

    base_document, revision_request = _extract_revision_contract(preparation_report)
    required_changes = revision_request.get("required_changes")
    if not isinstance(required_changes, list) or not required_changes:
        raise AgentGenerationError(
            "blocked revision_request must contain required_changes"
        )
    if not all(isinstance(item, Mapping) for item in required_changes):
        raise AgentGenerationError(
            "revision_request.required_changes must contain objects"
        )

    rules = _allowed_revision_paths(required_changes)
    changed_paths = tuple(
        sorted(set(_document_diff_paths(base_document, revised_document)))
    )
    violations: list[Mapping[str, str]] = []
    resolved: list[Mapping[str, Any]] = []

    if revision_request.get("state") != "required":
        violations.append(
            _revision_violation(
                "revision_not_locally_retryable",
                "revision_request.state",
                "Only a required revision request may be retried in Core.",
            )
        )

    for change_path in changed_paths:
        if not _change_is_allowed(change_path, rules):
            violations.append(
                _revision_violation(
                    "unauthorized_revision_path",
                    change_path,
                    "The Agent changed a field not authorized by revision_request.",
                )
            )

    for item in required_changes:
        path = str(item.get("path", ""))
        action = str(item.get("action", ""))
        if item.get("retryable") is not True:
            violations.append(
                _revision_violation(
                    "non_retryable_revision_change",
                    path,
                    "This requirement must be routed rather than retried in Core.",
                )
            )
            continue
        base_exists, base_value = _value_at_path(base_document, path)
        revised_exists, revised_value = _value_at_path(revised_document, path)
        if not revised_exists:
            violations.append(
                _revision_violation(
                    "required_revision_missing",
                    path,
                    "The revised document does not supply the requested value.",
                )
            )
            continue
        if base_exists and base_value == revised_value:
            violations.append(
                _revision_violation(
                    "required_revision_unchanged",
                    path,
                    "The requested field was not changed from the blocked revision base.",
                )
            )
            continue
        candidates = item.get("candidate_values", [])
        if not isinstance(candidates, list):
            raise AgentGenerationError(
                f"candidate_values for revision path {path!r} must be an array"
            )
        if not _candidate_selection_valid(action, revised_value, candidates):
            violations.append(
                _revision_violation(
                    "revision_value_not_in_candidates",
                    path,
                    "The selected value is not present in the declared candidate inventory.",
                )
            )
            continue
        resolved.append(
            {
                "code": str(item.get("code", "validation_error")),
                "path": path,
                "action": action,
                "before_present": base_exists,
                "before": deepcopy(base_value) if base_exists else None,
                "after": deepcopy(revised_value),
                "candidate_inventory_used": bool(candidates),
                "selected_by_core": False,
            }
        )

    if any(
        str(item.get("action", "")) == "select_registered_operator"
        for item in required_changes
    ):
        expected_operator_set = _collect_assertion_operators(revised_document)
        if revised_document.get("operator_set") != expected_operator_set:
            violations.append(
                _revision_violation(
                    "revision_operator_set_mismatch",
                    "operator_set",
                    "operator_set must exactly match operators used by revised assertions.",
                )
            )

    return GeneratedDocumentRevisionVerificationResult(
        state="accepted" if not violations else "rejected",
        revision_base_sha256=_document_fingerprint(base_document),
        revised_document_sha256=_document_fingerprint(revised_document),
        changed_paths=changed_paths,
        allowed_paths=rules,
        resolved_changes=tuple(resolved),
        violations=tuple(violations),
    )


def retry_generated_document(
    preparation_report: Mapping[str, Any],
    revised_document: Mapping[str, Any],
) -> GeneratedDocumentRevisionRetryResult:
    """Verify a revision before revalidation and deterministic execution."""

    verification = verify_generated_document_revision(
        preparation_report,
        revised_document,
    )
    if not verification.accepted:
        return GeneratedDocumentRevisionRetryResult(
            state="rejected",
            verification=verification,
            preparation=None,
        )
    preparation = prepare_generated_document(revised_document)
    return GeneratedDocumentRevisionRetryResult(
        state=(
            "accepted"
            if preparation.state in {"valid", "repaired"}
            else "blocked"
        ),
        verification=verification,
        preparation=preparation,
    )


def _is_v1_generated_shape(document: Mapping[str, Any]) -> bool:
    if "tasks" in document or "execution" in document:
        return True
    metadata = document.get("geotask")
    if not isinstance(metadata, Mapping):
        return False
    version = str(metadata.get("schema_version", metadata.get("version", "")))
    return version.startswith("1.")


def _record_repair(
    repairs: list[DocumentRepairAction],
    *,
    code: str,
    path: str,
    before: object,
    after: object,
    reason: str,
) -> None:
    repairs.append(
        DocumentRepairAction(
            code=code,
            path=path,
            before=deepcopy(before),
            after=deepcopy(after),
            reason=reason,
        )
    )


def _next_identifier(prefix: str, used: set[str]) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", prefix).strip("_-")
    if not normalized or not normalized[0].isalpha():
        normalized = f"item_{normalized}" if normalized else "item"
    normalized = normalized[:110]
    candidate = normalized
    index = 2
    while candidate in used:
        candidate = f"{normalized}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def _collect_assertion_operators(document: Mapping[str, Any]) -> list[str]:
    operators: list[str] = []
    tasks = document.get("tasks")
    if not isinstance(tasks, list):
        return operators
    for task in tasks:
        if not isinstance(task, Mapping):
            continue
        assertions = task.get("assertions")
        if not isinstance(assertions, list):
            continue
        for assertion in assertions:
            if not isinstance(assertion, Mapping):
                continue
            operator = assertion.get("operator")
            if isinstance(operator, str) and operator and operator not in operators:
                operators.append(operator)
    return operators


def _repair_metadata(
    prepared: dict[str, Any],
    repairs: list[DocumentRepairAction],
    blockers: list[Mapping[str, Any]],
) -> None:
    metadata = prepared.get("geotask")
    if not isinstance(metadata, dict):
        blockers.append(
            _diagnostic(
                "geotask",
                "unrepairable_metadata",
                "Agent preparation requires a native v1 geotask metadata mapping.",
                "Provide geotask.id or geotask.name in a mapping.",
            )
        )
        return

    if "schema_version" not in metadata and "version" not in metadata:
        metadata["schema_version"] = "1.0"
        _record_repair(
            repairs,
            code="add_schema_version",
            path="geotask.schema_version",
            before=None,
            after="1.0",
            reason="The v1 document shape determines the public Schema version.",
        )

    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        identifier = metadata.get("id")
        if isinstance(identifier, str) and identifier.strip():
            metadata["name"] = identifier.strip()
            _record_repair(
                repairs,
                code="derive_name_from_id",
                path="geotask.name",
                before=name,
                after=metadata["name"],
                reason="A display name may be copied mechanically from an explicit id.",
            )
        else:
            blockers.append(
                _diagnostic(
                    "geotask.name",
                    "missing_semantic_identity",
                    "Neither geotask.name nor a usable geotask.id was supplied.",
                    "Provide a task name or id; Core will not invent task identity.",
                )
            )


def _repair_task_identifiers(
    prepared: dict[str, Any],
    repairs: list[DocumentRepairAction],
    blockers: list[Mapping[str, Any]],
) -> None:
    tasks = prepared.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        blockers.append(
            _diagnostic(
                "tasks",
                "missing_generated_tasks",
                "Agent preparation requires a non-empty tasks array.",
                "Generate at least one task with one deterministic assertion.",
            )
        )
        return

    used_task_ids: set[str] = {
        str(task.get("id"))
        for task in tasks
        if isinstance(task, Mapping)
        and isinstance(task.get("id"), str)
        and task.get("id")
    }
    used_assertion_ids: set[str] = set()
    for task in tasks:
        if not isinstance(task, Mapping):
            continue
        assertions = task.get("assertions")
        if not isinstance(assertions, list):
            continue
        for assertion in assertions:
            if (
                isinstance(assertion, Mapping)
                and isinstance(assertion.get("id"), str)
                and assertion.get("id")
            ):
                used_assertion_ids.add(str(assertion["id"]))

    for task_index, task in enumerate(tasks):
        if not isinstance(task, dict):
            blockers.append(
                _diagnostic(
                    f"tasks[{task_index}]",
                    "unrepairable_task_type",
                    "Each generated task must be an object or mapping.",
                    "Replace the task entry with a mapping.",
                )
            )
            continue

        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id:
            generated = _next_identifier(f"task_{task_index + 1}", used_task_ids)
            task["id"] = generated
            task_id = generated
            _record_repair(
                repairs,
                code="add_task_id",
                path=f"tasks[{task_index}].id",
                before=None,
                after=generated,
                reason="List position provides a stable protocol identifier without domain inference.",
            )

        assertions = task.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            blockers.append(
                _diagnostic(
                    f"tasks[{task_index}].assertions",
                    "missing_generated_assertions",
                    "Each generated task must contain at least one assertion.",
                    "Generate an assertion with an operator and explicit object_refs.",
                )
            )
            continue

        for assertion_index, assertion in enumerate(assertions):
            path = f"tasks[{task_index}].assertions[{assertion_index}]"
            if not isinstance(assertion, dict):
                blockers.append(
                    _diagnostic(
                        path,
                        "unrepairable_assertion_type",
                        "Each generated assertion must be an object or mapping.",
                        "Replace the assertion entry with a mapping.",
                    )
                )
                continue
            assertion_id = assertion.get("id")
            if not isinstance(assertion_id, str) or not assertion_id:
                generated = _next_identifier(
                    f"{task_id}_assertion_{assertion_index + 1}",
                    used_assertion_ids,
                )
                assertion["id"] = generated
                _record_repair(
                    repairs,
                    code="add_assertion_id",
                    path=f"{path}.id",
                    before=None,
                    after=generated,
                    reason="Task identity and list position provide a stable protocol id.",
                )
            operator = assertion.get("operator")
            if not isinstance(operator, str) or not operator:
                blockers.append(
                    _diagnostic(
                        f"{path}.operator",
                        "operator_inference_forbidden",
                        "The assertion does not name an operator.",
                        "The Agent must select an explicit registered operator.",
                    )
                )
            refs = assertion.get("object_refs")
            if not isinstance(refs, list) or not refs:
                blockers.append(
                    _diagnostic(
                        f"{path}.object_refs",
                        "object_binding_inference_forbidden",
                        "The assertion does not provide explicit object_refs.",
                        "The Agent must bind every operator argument to an object id.",
                    )
                )


def _repair_operator_set(
    prepared: dict[str, Any],
    repairs: list[DocumentRepairAction],
) -> None:
    derived = _collect_assertion_operators(prepared)
    existing = prepared.get("operator_set")
    if isinstance(existing, list):
        normalized: list[str] = []
        for item in existing:
            if isinstance(item, str) and item and item not in normalized:
                normalized.append(item)
        for operator in derived:
            if operator not in normalized:
                normalized.append(operator)
    else:
        normalized = derived
    if existing != normalized:
        prepared["operator_set"] = normalized
        _record_repair(
            repairs,
            code="synchronize_operator_set",
            path="operator_set",
            before=existing,
            after=normalized,
            reason="operator_set is an inventory derived from explicit assertion operators.",
        )


def _repair_execution(
    prepared: dict[str, Any],
    repairs: list[DocumentRepairAction],
    blockers: list[Mapping[str, Any]],
) -> None:
    execution = prepared.get("execution")
    if execution is None:
        execution = {"mode": "local_only", "steps": []}
        prepared["execution"] = execution
        _record_repair(
            repairs,
            code="add_local_execution",
            path="execution",
            before=None,
            after=execution,
            reason="Agent preparation executes registered deterministic Core operators only.",
        )
    elif not isinstance(execution, dict):
        blockers.append(
            _diagnostic(
                "execution",
                "unrepairable_execution_type",
                "execution must be an object or mapping.",
                "Provide execution.mode and an optional steps array.",
            )
        )
        return

    if "mode" not in execution:
        execution["mode"] = "local_only"
        _record_repair(
            repairs,
            code="add_local_execution_mode",
            path="execution.mode",
            before=None,
            after="local_only",
            reason="The preparation helper permits deterministic local execution only.",
        )
    if execution.get("mode") != "local_only":
        blockers.append(
            _diagnostic(
                "execution.mode",
                "non_local_execution_forbidden",
                f"Agent preparation cannot execute mode {execution.get('mode')!r}.",
                "Use local_only or route the document to an authorized Runtime.",
            )
        )
    if "steps" not in execution:
        execution["steps"] = []
        _record_repair(
            repairs,
            code="add_execution_steps",
            path="execution.steps",
            before=None,
            after=[],
            reason="An empty steps array delegates to deterministic task-order execution.",
        )
    elif not isinstance(execution.get("steps"), list):
        blockers.append(
            _diagnostic(
                "execution.steps",
                "unrepairable_execution_steps",
                "execution.steps must be an array.",
                "Provide an array of explicit steps or an empty array.",
            )
        )


def _repair_output_contract(
    prepared: dict[str, Any],
    repairs: list[DocumentRepairAction],
    blockers: list[Mapping[str, Any]],
) -> None:
    contract = prepared.get("output_contract")
    if contract is None:
        contract = {
            "format": "structured",
            "required_fields": [],
            "allow_model_inference": False,
        }
        prepared["output_contract"] = contract
        _record_repair(
            repairs,
            code="add_fail_closed_output_contract",
            path="output_contract",
            before=None,
            after=contract,
            reason="Generated documents default to structured output without model inference.",
        )
        return
    if not isinstance(contract, dict):
        blockers.append(
            _diagnostic(
                "output_contract",
                "unrepairable_output_contract_type",
                "output_contract must be an object or mapping.",
                "Provide a structured output contract.",
            )
        )
        return

    defaults: tuple[tuple[str, object, str], ...] = (
        (
            "format",
            "structured",
            "Generated-document preparation emits structured results.",
        ),
        (
            "required_fields",
            [],
            "No domain-specific output fields may be invented by Core.",
        ),
        (
            "allow_model_inference",
            False,
            "Deterministic preparation does not permit model-completed result fields.",
        ),
    )
    for field, value, reason in defaults:
        if field not in contract:
            contract[field] = deepcopy(value)
            _record_repair(
                repairs,
                code=f"add_output_{field}",
                path=f"output_contract.{field}",
                before=None,
                after=value,
                reason=reason,
            )
    if contract.get("allow_model_inference") is True:
        contract["allow_model_inference"] = False
        _record_repair(
            repairs,
            code="disable_model_inference",
            path="output_contract.allow_model_inference",
            before=True,
            after=False,
            reason="The helper tightens generated documents to deterministic output only.",
        )


def prepare_generated_document(
    document: Mapping[str, Any],
) -> GeneratedDocumentPreparationResult:
    """Validate, mechanically repair, revalidate, and execute a generated document.

    Only native v1 document shapes are accepted. Protocol omissions are repaired
    on an in-memory copy. Spatial content, object bindings, operators, evidence,
    and domain policy are never inferred. Residual errors return ``blocked`` and
    prevent execution.
    """

    from geotask_core.parser import validate_document
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    if not isinstance(document, Mapping):
        raise TypeError("document must be a mapping")

    source = deepcopy(dict(document))
    initial_diagnostics = tuple(validate_document(deepcopy(source)))
    prepared = deepcopy(source)
    repairs: list[DocumentRepairAction] = []
    blockers: list[Mapping[str, Any]] = []

    if not _is_v1_generated_shape(prepared):
        blockers.append(
            _diagnostic(
                "geotask.schema_version",
                "unsupported_generated_document_shape",
                "Agent preparation supports native GeoTask v1 document shapes only.",
                "Generate a document with geotask metadata and a tasks array.",
            )
        )
    else:
        _repair_metadata(prepared, repairs, blockers)
        for path in ("space", "objects"):
            if not isinstance(prepared.get(path), Mapping):
                blockers.append(
                    _diagnostic(
                        path,
                        f"missing_{path}_definition",
                        f"{path} must be supplied as an explicit mapping.",
                        f"Generate an explicit {path} section; Core will not infer it.",
                    )
                )
        _repair_task_identifiers(prepared, repairs, blockers)
        _repair_operator_set(prepared, repairs)
        _repair_execution(prepared, repairs, blockers)
        _repair_output_contract(prepared, repairs, blockers)

    validation_input = deepcopy(prepared)
    residual = list(validate_document(validation_input))
    residual.extend(blockers)
    residual_diagnostics = _deduplicate_diagnostics(residual)

    if _error_diagnostics(residual_diagnostics):
        return GeneratedDocumentPreparationResult(
            state="blocked",
            initial_diagnostics=initial_diagnostics,
            repairs=tuple(repairs),
            residual_diagnostics=residual_diagnostics,
            prepared_document=prepared,
            execution_result=None,
            task_executed=False,
        )

    result = execute_canonical(canonicalize(prepared))
    result_payload = result.to_dict()
    execution_failed = result.execution.status == "failed"
    if execution_failed:
        residual_diagnostics = _deduplicate_diagnostics(
            list(residual_diagnostics)
            + [
                _diagnostic(
                    "execution",
                    "prepared_execution_failed",
                    "The repaired document passed validation but execution failed.",
                    "Inspect execution_result.errors and revise the generated task.",
                )
            ]
        )

    return GeneratedDocumentPreparationResult(
        state=(
            "blocked"
            if execution_failed
            else ("repaired" if repairs else "valid")
        ),
        initial_diagnostics=initial_diagnostics,
        repairs=tuple(repairs),
        residual_diagnostics=residual_diagnostics,
        prepared_document=prepared,
        execution_result=result_payload,
        task_executed=True,
    )
