"""Document-level provenance validation and evidence binding helpers."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from geotask_core.v1.enums import is_valid_geotask_id
from geotask_core.v1.ir import ProvenanceDefinition, Task


_SOURCE_KINDS = {"document", "dataset", "observation", "human", "artifact"}
_SOURCE_FIELDS = {
    "id",
    "kind",
    "title",
    "artifact_id",
    "uri",
    "version",
    "sha256",
    "issued_at",
    "retrieved_at",
    "verified_at",
}
_BINDING_FIELDS = {"assertion_id", "source_refs"}
_AUDIT_FIELDS = {
    "generated_by",
    "generator_version",
    "generated_at",
    "audit_ref",
    "source_refs",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _diagnostic(
    path: str,
    code: str,
    message: str,
    suggested_fix: str = "",
) -> dict[str, str]:
    result = {
        "path": path,
        "code": code,
        "message": message,
        "severity": "error",
    }
    if suggested_fix:
        result["suggested_fix"] = suggested_fix
    return result


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _parse_timestamp(value: object) -> datetime | None:
    if not _non_empty_string(value):
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _valid_timestamp(value: object) -> bool:
    return _parse_timestamp(value) is not None


def _check_unknown_fields(
    value: dict[str, Any], path: str, allowed: set[str]
) -> list[dict[str, str]]:
    return [
        _diagnostic(
            f"{path}.{field}",
            "unknown_field",
            f"Unexpected provenance field '{field}'.",
            f"Remove '{field}' or use a published provenance field.",
        )
        for field in sorted(set(value) - allowed)
    ]


def _validate_string_refs(
    value: object,
    path: str,
    *,
    source_ids: set[str],
) -> tuple[list[str], list[dict[str, str]]]:
    diagnostics: list[dict[str, str]] = []
    if not isinstance(value, list) or not value:
        return [], [
            _diagnostic(
                path,
                "missing_field",
                f"{path} must be a non-empty array of source IDs.",
                "Reference one or more IDs declared in provenance.sources.",
            )
        ]

    refs: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _non_empty_string(item):
            diagnostics.append(
                _diagnostic(
                    item_path,
                    "invalid_type",
                    "Source reference must be a non-empty string.",
                )
            )
            continue
        ref = str(item)
        if ref in seen:
            diagnostics.append(
                _diagnostic(
                    item_path,
                    "duplicate_id",
                    f"Duplicate source reference '{ref}'.",
                )
            )
            continue
        seen.add(ref)
        refs.append(ref)
        if ref not in source_ids:
            diagnostics.append(
                _diagnostic(
                    item_path,
                    "invalid_reference",
                    f"Unknown provenance source '{ref}'.",
                    "Reference an ID declared in provenance.sources.",
                )
            )
    return refs, diagnostics


def validate_provenance(
    provenance: ProvenanceDefinition | None,
    tasks: list[Task],
) -> list[dict[str, str]]:
    """Validate optional source, evidence-binding, and audit metadata."""
    if provenance is None:
        return []

    diagnostics: list[dict[str, str]] = []
    source_ids: set[str] = set()
    source_verified_at: dict[str, datetime] = {}

    if not isinstance(provenance.sources, list) or not provenance.sources:
        diagnostics.append(
            _diagnostic(
                "provenance.sources",
                "missing_field",
                "provenance.sources must contain at least one source record.",
            )
        )
    else:
        for index, raw_source in enumerate(provenance.sources):
            path = f"provenance.sources[{index}]"
            if not isinstance(raw_source, dict):
                diagnostics.append(
                    _diagnostic(path, "invalid_type", "Source record must be an object.")
                )
                continue
            diagnostics.extend(_check_unknown_fields(raw_source, path, _SOURCE_FIELDS))
            source_id = raw_source.get("id")
            if not _non_empty_string(source_id) or not is_valid_geotask_id(str(source_id)):
                diagnostics.append(
                    _diagnostic(
                        f"{path}.id",
                        "invalid_type",
                        "Source id must be a valid GeoTask identifier.",
                    )
                )
            elif str(source_id) in source_ids:
                diagnostics.append(
                    _diagnostic(
                        f"{path}.id",
                        "duplicate_id",
                        f"Duplicate provenance source id '{source_id}'.",
                    )
                )
            else:
                source_ids.add(str(source_id))

            kind = raw_source.get("kind")
            if kind not in _SOURCE_KINDS:
                diagnostics.append(
                    _diagnostic(
                        f"{path}.kind",
                        "invalid_type",
                        f"Unsupported source kind '{kind}'.",
                        f"Use one of: {', '.join(sorted(_SOURCE_KINDS))}.",
                    )
                )
            if not _non_empty_string(raw_source.get("title")):
                diagnostics.append(
                    _diagnostic(f"{path}.title", "missing_field", "Source title is required.")
                )
            if not (
                _non_empty_string(raw_source.get("artifact_id"))
                or _non_empty_string(raw_source.get("uri"))
            ):
                diagnostics.append(
                    _diagnostic(
                        path,
                        "missing_field",
                        "Source record requires artifact_id or uri.",
                    )
                )
            sha256 = raw_source.get("sha256")
            if sha256 is not None and (
                not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256)
            ):
                diagnostics.append(
                    _diagnostic(
                        f"{path}.sha256",
                        "invalid_type",
                        "Source sha256 must be 64 lowercase hexadecimal characters.",
                    )
                )
            parsed_times: dict[str, datetime] = {}
            for field in ("issued_at", "retrieved_at", "verified_at"):
                timestamp = raw_source.get(field)
                if timestamp is None:
                    continue
                parsed = _parse_timestamp(timestamp)
                if parsed is None:
                    diagnostics.append(
                        _diagnostic(
                            f"{path}.{field}",
                            "invalid_type",
                            f"{field} must be an ISO 8601 timestamp with timezone.",
                        )
                    )
                else:
                    parsed_times[field] = parsed
            for earlier, later in (
                ("issued_at", "retrieved_at"),
                ("retrieved_at", "verified_at"),
                ("issued_at", "verified_at"),
            ):
                if (
                    earlier in parsed_times
                    and later in parsed_times
                    and parsed_times[earlier] > parsed_times[later]
                ):
                    diagnostics.append(
                        _diagnostic(
                            f"{path}.{later}",
                            "invalid_interval",
                            f"{later} cannot be earlier than {earlier}.",
                        )
                    )
            if (
                _non_empty_string(source_id)
                and "verified_at" in parsed_times
            ):
                source_verified_at[str(source_id)] = parsed_times["verified_at"]

    assertion_ids = {
        assertion.id
        for task in tasks
        for assertion in task.assertions
        if assertion.id
    }
    bound_assertions: set[str] = set()
    if not isinstance(provenance.evidence_bindings, list):
        diagnostics.append(
            _diagnostic(
                "provenance.evidence_bindings",
                "invalid_type",
                "evidence_bindings must be an array.",
            )
        )
    else:
        for index, raw_binding in enumerate(provenance.evidence_bindings):
            path = f"provenance.evidence_bindings[{index}]"
            if not isinstance(raw_binding, dict):
                diagnostics.append(
                    _diagnostic(path, "invalid_type", "Evidence binding must be an object.")
                )
                continue
            diagnostics.extend(_check_unknown_fields(raw_binding, path, _BINDING_FIELDS))
            assertion_id = raw_binding.get("assertion_id")
            if not _non_empty_string(assertion_id):
                diagnostics.append(
                    _diagnostic(
                        f"{path}.assertion_id",
                        "missing_field",
                        "Evidence binding requires assertion_id.",
                    )
                )
            else:
                assertion_id = str(assertion_id)
                if assertion_id not in assertion_ids:
                    diagnostics.append(
                        _diagnostic(
                            f"{path}.assertion_id",
                            "invalid_reference",
                            f"Unknown assertion '{assertion_id}'.",
                        )
                    )
                if assertion_id in bound_assertions:
                    diagnostics.append(
                        _diagnostic(
                            f"{path}.assertion_id",
                            "duplicate_id",
                            f"Assertion '{assertion_id}' has multiple evidence bindings.",
                        )
                    )
                bound_assertions.add(assertion_id)
            _, ref_diagnostics = _validate_string_refs(
                raw_binding.get("source_refs"),
                f"{path}.source_refs",
                source_ids=source_ids,
            )
            diagnostics.extend(ref_diagnostics)

    audit = provenance.audit
    if not isinstance(audit, dict):
        diagnostics.append(
            _diagnostic("provenance.audit", "invalid_type", "Audit metadata must be an object.")
        )
        return diagnostics
    diagnostics.extend(_check_unknown_fields(audit, "provenance.audit", _AUDIT_FIELDS))
    if not _non_empty_string(audit.get("generated_by")):
        diagnostics.append(
            _diagnostic(
                "provenance.audit.generated_by",
                "missing_field",
                "generated_by is required.",
            )
        )
    generated_at = _parse_timestamp(audit.get("generated_at"))
    if generated_at is None:
        diagnostics.append(
            _diagnostic(
                "provenance.audit.generated_at",
                "invalid_type",
                "generated_at must be an ISO 8601 timestamp with timezone.",
            )
        )
    audit_source_refs, audit_ref_diagnostics = _validate_string_refs(
        audit.get("source_refs"),
        "provenance.audit.source_refs",
        source_ids=source_ids,
    )
    diagnostics.extend(audit_ref_diagnostics)
    if generated_at is not None:
        for source_ref in audit_source_refs:
            verified_at = source_verified_at.get(source_ref)
            if verified_at is not None and generated_at < verified_at:
                diagnostics.append(
                    _diagnostic(
                        "provenance.audit.generated_at",
                        "invalid_interval",
                        f"Audit generation cannot predate verification of source '{source_ref}'.",
                    )
                )
    for optional_field in ("generator_version", "audit_ref"):
        value = audit.get(optional_field)
        if value is not None and not _non_empty_string(value):
            diagnostics.append(
                _diagnostic(
                    f"provenance.audit.{optional_field}",
                    "invalid_type",
                    f"{optional_field} must be a non-empty string when provided.",
                )
            )
    return diagnostics


def evidence_refs_by_assertion(
    provenance: ProvenanceDefinition | None,
) -> dict[str, list[str]]:
    """Return validated-style evidence bindings without mutating the document."""
    if provenance is None or not isinstance(provenance.evidence_bindings, list):
        return {}
    result: dict[str, list[str]] = {}
    for binding in provenance.evidence_bindings:
        if not isinstance(binding, dict):
            continue
        assertion_id = binding.get("assertion_id")
        source_refs = binding.get("source_refs")
        if isinstance(assertion_id, str) and isinstance(source_refs, list):
            result[assertion_id] = [
                item for item in source_refs if isinstance(item, str)
            ]
    return result


__all__ = ["evidence_refs_by_assertion", "validate_provenance"]
