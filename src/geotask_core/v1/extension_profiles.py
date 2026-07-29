"""Versioned validation for public GeoTask extension profiles.

Core extensions remain open by default. A document opts into strict validation
by declaring ``extensions.extension_profile``. The first public profile,
``geotask.control/1.0``, standardises reusable control-flow structures without
claiming ownership of domain-specific state fields.
"""

from __future__ import annotations

from collections.abc import Iterable

from geotask_core.v1.enums import (
    EXTENSION_PROFILE_VIOLATION,
    INVALID_REFERENCE,
    INVALID_TYPE,
    MISSING_FIELD,
    UNKNOWN_FIELD,
    UNSUPPORTED_EXTENSION_PROFILE,
    is_valid_geotask_id,
)

CONTROL_PROFILE_ID = "geotask.control"
CONTROL_PROFILE_VERSION = "1.0"
CONTROL_BLOCKS = (
    "decision_rule",
    "evidence_request",
    "evidence_conflict",
    "task_gate",
)

_PROFILE_FIELDS = {"id", "version"}
_DECISION_RULE_FIELDS = {
    "id",
    "logic",
    "expression",
    "unknown_policy",
    "expected_status",
}
_EVIDENCE_REQUEST_FIELDS = {
    "id",
    "trigger",
    "trigger_status",
    "reason",
    "required_fields",
    "blocked_outputs",
    "resume_when",
    "next_action",
}
_EVIDENCE_CONFLICT_FIELDS = {
    "id",
    "subject",
    "conflict_type",
    "conflicting_assertions",
    "source_refs",
    "compared_fields",
    "blocked_outputs",
    "resolution_required_fields",
    "resume_when",
    "next_action",
    "expected_status",
}
_TASK_GATE_FIELDS = {
    "status",
    "selected_action",
    "rejected_actions",
    "blocked_outputs",
    "required_controls",
    "resume_when",
    "next_action",
    "expected_status",
}


def _diagnostic(
    path: str,
    code: str,
    message: str,
    suggested_fix: str,
    severity: str = "error",
) -> dict:
    return {
        "path": path,
        "code": code,
        "message": message,
        "suggested_fix": suggested_fix,
        "severity": severity,
    }


def _check_mapping(value: object, path: str) -> tuple[dict | None, list[dict]]:
    if isinstance(value, dict):
        return value, []
    return None, [
        _diagnostic(
            path,
            INVALID_TYPE,
            f"{path} must be a mapping, got {type(value).__name__}.",
            "Use a YAML mapping with the fields defined by the declared extension profile.",
        )
    ]


def _check_unknown_fields(mapping: dict, path: str, allowed: set[str]) -> list[dict]:
    diagnostics: list[dict] = []
    for field in mapping:
        if field not in allowed:
            diagnostics.append(
                _diagnostic(
                    f"{path}.{field}",
                    UNKNOWN_FIELD,
                    f"Field '{field}' is not defined by geotask.control/1.0 for {path}.",
                    f"Remove it or use one of: {', '.join(sorted(allowed))}.",
                )
            )
    return diagnostics


def _check_required_string(mapping: dict, path: str, field: str) -> list[dict]:
    value = mapping.get(field)
    if value is None:
        return [
            _diagnostic(
                f"{path}.{field}",
                MISSING_FIELD,
                f"Required field '{field}' is missing from {path}.",
                f"Add a non-empty string at {path}.{field}.",
            )
        ]
    if not isinstance(value, str) or not value.strip():
        return [
            _diagnostic(
                f"{path}.{field}",
                INVALID_TYPE,
                f"{path}.{field} must be a non-empty string.",
                f"Set {path}.{field} to a stable non-empty string.",
            )
        ]
    return []


def _check_optional_string(mapping: dict, path: str, field: str) -> list[dict]:
    if field not in mapping:
        return []
    value = mapping[field]
    if isinstance(value, str) and value.strip():
        return []
    return [
        _diagnostic(
            f"{path}.{field}",
            INVALID_TYPE,
            f"{path}.{field} must be a non-empty string when present.",
            f"Remove {field} or set it to a non-empty string.",
        )
    ]


def _check_string_list(
    mapping: dict,
    path: str,
    field: str,
    *,
    required: bool = True,
    min_items: int = 1,
) -> list[dict]:
    if field not in mapping:
        if not required:
            return []
        return [
            _diagnostic(
                f"{path}.{field}",
                MISSING_FIELD,
                f"Required list '{field}' is missing from {path}.",
                f"Add {path}.{field} as a list of non-empty strings.",
            )
        ]

    value = mapping[field]
    if not isinstance(value, list):
        return [
            _diagnostic(
                f"{path}.{field}",
                INVALID_TYPE,
                f"{path}.{field} must be a list.",
                "Use a YAML sequence of unique non-empty strings.",
            )
        ]

    diagnostics: list[dict] = []
    if len(value) < min_items:
        diagnostics.append(
            _diagnostic(
                f"{path}.{field}",
                EXTENSION_PROFILE_VIOLATION,
                f"{path}.{field} must contain at least {min_items} item(s).",
                "Add the required control identifiers or fields.",
            )
        )

    seen: set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{path}.{field}[{index}]"
        if not isinstance(item, str) or not item.strip():
            diagnostics.append(
                _diagnostic(
                    item_path,
                    INVALID_TYPE,
                    f"{item_path} must be a non-empty string.",
                    "Replace it with a stable non-empty identifier or field name.",
                )
            )
            continue
        if item in seen:
            diagnostics.append(
                _diagnostic(
                    item_path,
                    EXTENSION_PROFILE_VIOLATION,
                    f"Duplicate value '{item}' in {path}.{field}.",
                    "Remove duplicate list entries.",
                )
            )
        seen.add(item)
    return diagnostics


def _check_identifier(mapping: dict, path: str, field: str = "id") -> list[dict]:
    diagnostics = _check_required_string(mapping, path, field)
    if diagnostics:
        return diagnostics
    value = mapping[field]
    if is_valid_geotask_id(value):
        return []
    return [
        _diagnostic(
            f"{path}.{field}",
            INVALID_TYPE,
            f"{path}.{field} '{value}' is not a valid GeoTask identifier.",
            "Use a value beginning with a letter and containing only letters, digits, '.', '_', or '-'.",
        )
    ]


def _check_assertion_references(
    mapping: dict,
    path: str,
    field: str,
    assertion_ids: set[str],
) -> list[dict]:
    diagnostics: list[dict] = []
    value = mapping.get(field)
    if isinstance(value, str):
        references: Iterable[tuple[str, str]] = ((f"{path}.{field}", value),)
    elif isinstance(value, list):
        references = (
            (f"{path}.{field}[{index}]", item)
            for index, item in enumerate(value)
            if isinstance(item, str) and item.strip()
        )
    else:
        return diagnostics

    for reference_path, reference in references:
        if reference not in assertion_ids:
            diagnostics.append(
                _diagnostic(
                    reference_path,
                    INVALID_REFERENCE,
                    f"Unknown assertion reference '{reference}' in the control profile.",
                    f"Reference one of: {', '.join(sorted(assertion_ids))}.",
                )
            )
    return diagnostics


def _validate_decision_rule(value: object) -> list[dict]:
    path = "extensions.decision_rule"
    mapping, diagnostics = _check_mapping(value, path)
    if mapping is None:
        return diagnostics
    diagnostics.extend(_check_unknown_fields(mapping, path, _DECISION_RULE_FIELDS))
    diagnostics.extend(_check_identifier(mapping, path))
    diagnostics.extend(_check_required_string(mapping, path, "logic"))
    diagnostics.extend(_check_required_string(mapping, path, "expression"))
    diagnostics.extend(_check_optional_string(mapping, path, "unknown_policy"))
    diagnostics.extend(_check_optional_string(mapping, path, "expected_status"))
    return diagnostics


def _validate_evidence_request(value: object, assertion_ids: set[str]) -> list[dict]:
    path = "extensions.evidence_request"
    mapping, diagnostics = _check_mapping(value, path)
    if mapping is None:
        return diagnostics
    diagnostics.extend(_check_unknown_fields(mapping, path, _EVIDENCE_REQUEST_FIELDS))
    diagnostics.extend(_check_identifier(mapping, path))
    for field in ("trigger", "reason", "resume_when", "next_action"):
        diagnostics.extend(_check_required_string(mapping, path, field))
    diagnostics.extend(_check_optional_string(mapping, path, "trigger_status"))
    diagnostics.extend(_check_string_list(mapping, path, "required_fields"))
    diagnostics.extend(_check_string_list(mapping, path, "blocked_outputs"))
    diagnostics.extend(_check_assertion_references(mapping, path, "trigger", assertion_ids))
    return diagnostics


def _validate_evidence_conflict(value: object, assertion_ids: set[str]) -> list[dict]:
    path = "extensions.evidence_conflict"
    mapping, diagnostics = _check_mapping(value, path)
    if mapping is None:
        return diagnostics
    diagnostics.extend(_check_unknown_fields(mapping, path, _EVIDENCE_CONFLICT_FIELDS))
    diagnostics.extend(_check_identifier(mapping, path))
    for field in ("subject", "conflict_type", "resume_when", "next_action"):
        diagnostics.extend(_check_required_string(mapping, path, field))
    diagnostics.extend(_check_optional_string(mapping, path, "expected_status"))
    diagnostics.extend(_check_string_list(mapping, path, "conflicting_assertions", min_items=2))
    diagnostics.extend(_check_string_list(mapping, path, "source_refs", min_items=2))
    diagnostics.extend(_check_string_list(mapping, path, "compared_fields", required=False))
    diagnostics.extend(_check_string_list(mapping, path, "blocked_outputs"))
    diagnostics.extend(_check_string_list(mapping, path, "resolution_required_fields"))
    diagnostics.extend(
        _check_assertion_references(mapping, path, "conflicting_assertions", assertion_ids)
    )
    return diagnostics


def _validate_task_gate(value: object) -> list[dict]:
    path = "extensions.task_gate"
    mapping, diagnostics = _check_mapping(value, path)
    if mapping is None:
        return diagnostics
    diagnostics.extend(_check_unknown_fields(mapping, path, _TASK_GATE_FIELDS))
    for field in ("status", "selected_action", "resume_when", "next_action"):
        diagnostics.extend(_check_required_string(mapping, path, field))
    diagnostics.extend(_check_optional_string(mapping, path, "expected_status"))
    diagnostics.extend(_check_string_list(mapping, path, "rejected_actions", required=False))
    diagnostics.extend(_check_string_list(mapping, path, "blocked_outputs"))
    diagnostics.extend(_check_string_list(mapping, path, "required_controls"))
    return diagnostics


def validate_extension_profiles(
    extensions: object,
    *,
    assertion_ids: set[str],
) -> list[dict]:
    """Validate an explicitly declared public extension profile.

    Documents without ``extensions.extension_profile`` remain open and are not
    retroactively constrained. This keeps v1.0 extension compatibility while
    allowing profile-aware producers to opt into a stable contract.
    """

    if not isinstance(extensions, dict):
        return [
            _diagnostic(
                "extensions",
                INVALID_TYPE,
                "extensions must be a mapping.",
                "Use a mapping for extension data.",
            )
        ]

    profile_value = extensions.get("extension_profile")
    if profile_value is None:
        return []

    profile, diagnostics = _check_mapping(profile_value, "extensions.extension_profile")
    if profile is None:
        return diagnostics
    diagnostics.extend(
        _check_unknown_fields(profile, "extensions.extension_profile", _PROFILE_FIELDS)
    )
    diagnostics.extend(_check_required_string(profile, "extensions.extension_profile", "id"))
    diagnostics.extend(
        _check_required_string(profile, "extensions.extension_profile", "version")
    )
    if diagnostics:
        return diagnostics

    profile_id = profile["id"]
    version = profile["version"]
    if profile_id != CONTROL_PROFILE_ID or version != CONTROL_PROFILE_VERSION:
        return [
            _diagnostic(
                "extensions.extension_profile",
                UNSUPPORTED_EXTENSION_PROFILE,
                f"Unsupported extension profile '{profile_id}/{version}'.",
                f"Use {CONTROL_PROFILE_ID}/{CONTROL_PROFILE_VERSION} or omit extension_profile for open extensions.",
            )
        ]

    present_blocks = [name for name in CONTROL_BLOCKS if name in extensions]
    if not present_blocks:
        diagnostics.append(
            _diagnostic(
                "extensions",
                EXTENSION_PROFILE_VIOLATION,
                f"{CONTROL_PROFILE_ID}/{CONTROL_PROFILE_VERSION} requires at least one control block.",
                f"Add one of: {', '.join(CONTROL_BLOCKS)}.",
            )
        )
        return diagnostics

    if "decision_rule" in extensions:
        diagnostics.extend(_validate_decision_rule(extensions["decision_rule"]))
    if "evidence_request" in extensions:
        diagnostics.extend(
            _validate_evidence_request(extensions["evidence_request"], assertion_ids)
        )
    if "evidence_conflict" in extensions:
        diagnostics.extend(
            _validate_evidence_conflict(extensions["evidence_conflict"], assertion_ids)
        )
    if "task_gate" in extensions:
        diagnostics.extend(_validate_task_gate(extensions["task_gate"]))

    return diagnostics
