"""Public Discrepancy Report v0.1 contract.

A Discrepancy Report binds one World State snapshot to exact serialized source
artifacts and records explicit discrepancies, downstream impact, and bounded
correction scope. Loading validates structure, reference closure, value-shape
rules, path safety, aggregate state/severity, and deterministic fingerprinting.
Binding validation checks the World State identity/fingerprint and raw SHA-256
digests of supplied artifact bytes. It does not compare source contents, discover
discrepancies, create a Correction Request, apply a correction, materialize state,
run rechecks, verify external truth, or authorize action.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Mapping, Sequence

from geotask_core.v1.world_state import WorldState


DISCREPANCY_REPORT_ARTIFACT_ID = "geotask.discrepancy-report"
DISCREPANCY_REPORT_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/"
    "geotask-discrepancy-report-v0.1.schema.json"
)
DISCREPANCY_REPORT_SCHEMA_VERSION = "0.1"
DISCREPANCY_REPORT_FORMAT_VERSION = "0.1"

DISCREPANCY_STATES = frozenset({"detected", "confirmed", "need_review", "unknown"})
DISCREPANCY_KINDS = frozenset(
    {
        "value_mismatch",
        "missing_claim",
        "unexpected_claim",
        "stale_claim",
        "source_conflict",
        "validity_conflict",
        "uncertainty_conflict",
        "unsupported_claim",
    }
)
DISCREPANCY_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
DISCREPANCY_SUBJECT_KINDS = frozenset(
    {"object", "attribute", "relation", "action_eligibility", "claim", "artifact"}
)
DISCREPANCY_IMPACT_STATES = frozenset({"none", "potential", "confirmed", "unknown"})
DISCREPANCY_CORRECTION_STATES = frozenset(
    {"allowed", "blocked", "need_review", "not_applicable"}
)

_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class DiscrepancyReportFormatError(ValueError):
    """Raised when a Discrepancy Report payload violates the v0.1 contract."""


def _fail(path: str, message: str) -> None:
    raise DiscrepancyReportFormatError(f"{path}: {message}")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _exact_fields(
    value: Mapping[str, object],
    path: str,
    *,
    required: AbstractSet[str],
    optional: AbstractSet[str] = frozenset(),
) -> None:
    missing = sorted(required - set(value))
    if missing:
        _fail(path, "missing required fields: " + ", ".join(missing))
    unknown = sorted(set(value) - required - optional)
    if unknown:
        _fail(path, "contains unknown fields: " + ", ".join(unknown))


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")
    return value


def _enum(value: object, path: str, allowed: frozenset[str]) -> str:
    normalized = _string(value, path)
    if normalized not in allowed:
        _fail(path, "must be one of: " + ", ".join(sorted(allowed)))
    return normalized


def _positive_integer(value: object, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        _fail(path, "must be an integer greater than or equal to 1")
    return value


def _timestamp(value: object, path: str) -> tuple[str, datetime]:
    text = _string(value, path)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DiscrepancyReportFormatError(
            f"{path}: must be an ISO 8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must include a timezone offset")
    return text, parsed


def _sha256(value: object, path: str) -> str:
    text = _string(value, path)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        _fail(path, "must be a lowercase 64-character SHA-256 hexadecimal digest")
    return text


def _string_list(
    value: object,
    path: str,
    *,
    non_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array of non-empty strings")
    if non_empty and not value:
        _fail(path, "must contain at least one item")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _string(item, f"{path}[{index}]")
        if text in seen:
            _fail(f"{path}[{index}]", f"duplicates {text!r}")
        seen.add(text)
        items.append(text)
    return tuple(items)


def _json_value(value: object, path: str) -> object:
    if value is None or isinstance(value, (str, bool)):
        return copy.deepcopy(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            _fail(path, "must not contain a non-finite number")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(path, "object keys must be strings")
            normalized[key] = _json_value(item, f"{path}.{key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            _json_value(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    _fail(path, "must be a JSON-compatible value")


def _json_pointer(value: object, path: str, *, subject_kind: str | None = None) -> str:
    pointer = _string(value, path)
    if not pointer.startswith("/") or pointer.endswith("/"):
        _fail(path, "must be a non-root JSON Pointer without a trailing slash")
    segments = pointer.split("/")[1:]
    if not segments or any(not segment for segment in segments):
        _fail(path, "must not contain an empty path segment")
    for segment in segments:
        index = 0
        while index < len(segment):
            if segment[index] == "~":
                if index + 1 >= len(segment) or segment[index + 1] not in {"0", "1"}:
                    _fail(path, "contains an invalid JSON Pointer escape")
                index += 2
            else:
                index += 1

    if subject_kind == "object":
        if len(segments) < 2 or segments[0] != "objects" or "attributes" in segments:
            _fail(path, "object subjects must target /objects/<object-id>/...")
    elif subject_kind == "attribute":
        if len(segments) < 4 or segments[0] != "objects" or segments[2] != "attributes":
            _fail(
                path,
                "attribute subjects must target /objects/<object-id>/attributes/<name>/...",
            )
    elif subject_kind == "relation":
        if len(segments) < 2 or segments[0] != "relations":
            _fail(path, "relation subjects must target /relations/<relation-id>/...")
    elif subject_kind == "action_eligibility":
        if len(segments) < 2 or segments[0] != "action_eligibility":
            _fail(
                path,
                "action eligibility subjects must target /action_eligibility/<output-ref>/...",
            )
    elif subject_kind == "claim":
        if len(segments) < 2 or segments[0] != "claims":
            _fail(path, "claim subjects must target /claims/<claim-id>/...")
    elif subject_kind == "artifact":
        if len(segments) < 2 or segments[0] != "artifacts":
            _fail(path, "artifact subjects must target /artifacts/<artifact-ref>/...")
    return pointer


def _closed_refs(
    refs: tuple[str, ...],
    path: str,
    declared: frozenset[str],
    declaration_path: str,
) -> None:
    for index, ref in enumerate(refs):
        if ref not in declared:
            _fail(f"{path}[{index}]", f"must be declared in {declaration_path}: {ref!r}")


def _paths_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


@dataclass(frozen=True)
class DiscrepancyWorldStateRef:
    world_state_id: str
    revision: int
    as_of: str
    semantic_fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "world_state_id": self.world_state_id,
            "revision": self.revision,
            "as_of": self.as_of,
            "semantic_fingerprint": self.semantic_fingerprint,
        }


@dataclass(frozen=True)
class DiscrepancyArtifactRef:
    ref_id: str
    artifact_id: str
    schema_version: str
    instance_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ref_id": self.ref_id,
            "artifact_id": self.artifact_id,
            "schema_version": self.schema_version,
            "instance_id": self.instance_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class DiscrepancyImpact:
    state: str
    reason: str
    affected_paths: tuple[str, ...]
    affected_assertion_refs: tuple[str, ...]
    affected_output_refs: tuple[str, ...]
    affected_action_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "reason": self.reason,
            "affected_paths": sorted(self.affected_paths),
            "affected_assertion_refs": sorted(self.affected_assertion_refs),
            "affected_output_refs": sorted(self.affected_output_refs),
            "affected_action_refs": sorted(self.affected_action_refs),
        }


@dataclass(frozen=True)
class DiscrepancyCorrectionScope:
    state: str
    reason: str
    mutable_paths: tuple[str, ...]
    immutable_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "reason": self.reason,
            "mutable_paths": sorted(self.mutable_paths),
            "immutable_paths": sorted(self.immutable_paths),
        }


@dataclass(frozen=True)
class DiscrepancyFinding:
    id: str
    kind: str
    state: str
    severity: str
    subject_kind: str
    subject_path: str
    summary: str
    reason: str
    basis_refs: tuple[str, ...]
    observation_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    has_expected: bool
    expected: object
    has_observed: bool
    observed: object
    impact: DiscrepancyImpact
    correction_scope: DiscrepancyCorrectionScope

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "kind": self.kind,
            "state": self.state,
            "severity": self.severity,
            "subject_kind": self.subject_kind,
            "subject_path": self.subject_path,
            "summary": self.summary,
            "reason": self.reason,
            "basis_refs": sorted(self.basis_refs),
            "observation_refs": sorted(self.observation_refs),
            "evidence_refs": sorted(self.evidence_refs),
            "impact": self.impact.to_dict(),
            "correction_scope": self.correction_scope.to_dict(),
        }
        if self.has_expected:
            payload["expected"] = copy.deepcopy(self.expected)
        if self.has_observed:
            payload["observed"] = copy.deepcopy(self.observed)
        return payload


@dataclass(frozen=True)
class DiscrepancyReport:
    report_id: str
    recorded_at: str
    state: str
    severity: str
    reason: str
    world_state: DiscrepancyWorldStateRef
    observation_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    artifact_refs: tuple[DiscrepancyArtifactRef, ...]
    discrepancies: tuple[DiscrepancyFinding, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "discrepancy_report": {
                "schema_id": DISCREPANCY_REPORT_SCHEMA_ID,
                "schema_version": DISCREPANCY_REPORT_SCHEMA_VERSION,
                "report_id": self.report_id,
                "recorded_at": self.recorded_at,
                "state": self.state,
                "severity": self.severity,
                "reason": self.reason,
                "world_state": self.world_state.to_dict(),
                "observation_refs": sorted(self.observation_refs),
                "evidence_refs": sorted(self.evidence_refs),
                "artifact_refs": [
                    item.to_dict()
                    for item in sorted(self.artifact_refs, key=lambda item: item.ref_id)
                ],
                "discrepancies": [
                    item.to_dict()
                    for item in sorted(self.discrepancies, key=lambda item: item.id)
                ],
            }
        }

    def semantic_fingerprint(self) -> str:
        raw = json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _load_world_state_ref(
    value: object, path: str
) -> tuple[DiscrepancyWorldStateRef, datetime]:
    ref = _mapping(value, path)
    _exact_fields(
        ref,
        path,
        required={"world_state_id", "revision", "as_of", "semantic_fingerprint"},
    )
    as_of_text, as_of = _timestamp(ref["as_of"], f"{path}.as_of")
    return (
        DiscrepancyWorldStateRef(
            world_state_id=_string(ref["world_state_id"], f"{path}.world_state_id"),
            revision=_positive_integer(ref["revision"], f"{path}.revision"),
            as_of=as_of_text,
            semantic_fingerprint=_sha256(
                ref["semantic_fingerprint"], f"{path}.semantic_fingerprint"
            ),
        ),
        as_of,
    )


def _load_artifact_refs(value: object) -> tuple[DiscrepancyArtifactRef, ...]:
    path = "discrepancy_report.artifact_refs"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if not value:
        _fail(path, "must contain at least one item")
    items: list[DiscrepancyArtifactRef] = []
    ref_ids: set[str] = set()
    instance_ids: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        ref = _mapping(raw, item_path)
        _exact_fields(
            ref,
            item_path,
            required={
                "ref_id",
                "artifact_id",
                "schema_version",
                "instance_id",
                "content_sha256",
            },
        )
        ref_id = _string(ref["ref_id"], f"{item_path}.ref_id")
        instance_id = _string(ref["instance_id"], f"{item_path}.instance_id")
        if ref_id in ref_ids:
            _fail(f"{item_path}.ref_id", f"duplicates ref_id {ref_id!r}")
        if instance_id in instance_ids:
            _fail(f"{item_path}.instance_id", f"duplicates instance_id {instance_id!r}")
        ref_ids.add(ref_id)
        instance_ids.add(instance_id)
        items.append(
            DiscrepancyArtifactRef(
                ref_id=ref_id,
                artifact_id=_string(ref["artifact_id"], f"{item_path}.artifact_id"),
                schema_version=_string(
                    ref["schema_version"], f"{item_path}.schema_version"
                ),
                instance_id=instance_id,
                content_sha256=_sha256(
                    ref["content_sha256"], f"{item_path}.content_sha256"
                ),
            )
        )
    return tuple(sorted(items, key=lambda item: item.ref_id))


def _load_impact(value: object, path: str) -> DiscrepancyImpact:
    impact = _mapping(value, path)
    _exact_fields(
        impact,
        path,
        required={
            "state",
            "reason",
            "affected_paths",
            "affected_assertion_refs",
            "affected_output_refs",
            "affected_action_refs",
        },
    )
    state = _enum(impact["state"], f"{path}.state", DISCREPANCY_IMPACT_STATES)
    affected_paths = tuple(
        sorted(
            _json_pointer(item, f"{path}.affected_paths[{index}]")
            for index, item in enumerate(
                _string_list(impact["affected_paths"], f"{path}.affected_paths")
            )
        )
    )
    assertion_refs = _string_list(
        impact["affected_assertion_refs"], f"{path}.affected_assertion_refs"
    )
    output_refs = _string_list(
        impact["affected_output_refs"], f"{path}.affected_output_refs"
    )
    action_refs = _string_list(
        impact["affected_action_refs"], f"{path}.affected_action_refs"
    )
    affected_count = (
        len(affected_paths) + len(assertion_refs) + len(output_refs) + len(action_refs)
    )
    if state == "none" and affected_count:
        _fail(path, "state 'none' requires all affected reference arrays to be empty")
    if state in {"potential", "confirmed"} and not affected_count:
        _fail(path, f"state {state!r} requires at least one affected reference")
    return DiscrepancyImpact(
        state=state,
        reason=_string(impact["reason"], f"{path}.reason"),
        affected_paths=affected_paths,
        affected_assertion_refs=tuple(sorted(assertion_refs)),
        affected_output_refs=tuple(sorted(output_refs)),
        affected_action_refs=tuple(sorted(action_refs)),
    )


def _load_correction_scope(value: object, path: str) -> DiscrepancyCorrectionScope:
    scope = _mapping(value, path)
    _exact_fields(
        scope,
        path,
        required={"state", "reason", "mutable_paths", "immutable_paths"},
    )
    state = _enum(
        scope["state"], f"{path}.state", DISCREPANCY_CORRECTION_STATES
    )
    mutable_paths = tuple(
        sorted(
            _json_pointer(item, f"{path}.mutable_paths[{index}]")
            for index, item in enumerate(
                _string_list(scope["mutable_paths"], f"{path}.mutable_paths")
            )
        )
    )
    immutable_paths = tuple(
        sorted(
            _json_pointer(item, f"{path}.immutable_paths[{index}]")
            for index, item in enumerate(
                _string_list(scope["immutable_paths"], f"{path}.immutable_paths")
            )
        )
    )
    for mutable in mutable_paths:
        for immutable in immutable_paths:
            if _paths_overlap(mutable, immutable):
                _fail(
                    path,
                    "mutable and immutable paths must not overlap: "
                    f"{mutable!r} versus {immutable!r}",
                )
    if state == "allowed" and not mutable_paths:
        _fail(path, "state 'allowed' requires at least one mutable path")
    if state == "blocked" and (mutable_paths or not immutable_paths):
        _fail(
            path,
            "state 'blocked' requires no mutable paths and at least one immutable path",
        )
    if state == "need_review" and not (mutable_paths or immutable_paths):
        _fail(path, "state 'need_review' requires at least one scoped path")
    if state == "not_applicable" and (mutable_paths or immutable_paths):
        _fail(path, "state 'not_applicable' requires both path arrays to be empty")
    return DiscrepancyCorrectionScope(
        state=state,
        reason=_string(scope["reason"], f"{path}.reason"),
        mutable_paths=mutable_paths,
        immutable_paths=immutable_paths,
    )


def _load_discrepancy(
    value: object,
    *,
    index: int,
    declared_artifact_refs: frozenset[str],
    declared_observation_refs: frozenset[str],
    declared_evidence_refs: frozenset[str],
) -> DiscrepancyFinding:
    path = f"discrepancy_report.discrepancies[{index}]"
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={
            "id",
            "kind",
            "state",
            "severity",
            "subject_kind",
            "subject_path",
            "summary",
            "reason",
            "basis_refs",
            "observation_refs",
            "evidence_refs",
            "impact",
            "correction_scope",
        },
        optional={"expected", "observed"},
    )
    kind = _enum(item["kind"], f"{path}.kind", DISCREPANCY_KINDS)
    state = _enum(item["state"], f"{path}.state", DISCREPANCY_STATES)
    severity = _enum(
        item["severity"], f"{path}.severity", DISCREPANCY_SEVERITIES
    )
    subject_kind = _enum(
        item["subject_kind"],
        f"{path}.subject_kind",
        DISCREPANCY_SUBJECT_KINDS,
    )
    subject_path = _json_pointer(
        item["subject_path"], f"{path}.subject_path", subject_kind=subject_kind
    )

    has_expected = "expected" in item
    has_observed = "observed" in item
    expected = _json_value(item["expected"], f"{path}.expected") if has_expected else None
    observed = _json_value(item["observed"], f"{path}.observed") if has_observed else None

    paired_kinds = {
        "value_mismatch",
        "source_conflict",
        "validity_conflict",
        "uncertainty_conflict",
    }
    if kind in paired_kinds and (not has_expected or not has_observed):
        _fail(path, f"kind {kind!r} requires both expected and observed")
    if kind in paired_kinds and expected == observed:
        _fail(path, f"kind {kind!r} requires expected and observed to differ")
    if kind == "missing_claim" and (not has_expected or has_observed):
        _fail(path, "kind 'missing_claim' requires expected and forbids observed")
    if kind == "unexpected_claim" and (has_expected or not has_observed):
        _fail(path, "kind 'unexpected_claim' requires observed and forbids expected")
    if kind in {"stale_claim", "unsupported_claim"} and not has_observed:
        _fail(path, f"kind {kind!r} requires observed")

    basis_refs = _string_list(
        item["basis_refs"], f"{path}.basis_refs", non_empty=True
    )
    observation_refs = _string_list(
        item["observation_refs"], f"{path}.observation_refs"
    )
    evidence_refs = _string_list(item["evidence_refs"], f"{path}.evidence_refs")
    _closed_refs(
        basis_refs,
        f"{path}.basis_refs",
        declared_artifact_refs,
        "discrepancy_report.artifact_refs",
    )
    _closed_refs(
        observation_refs,
        f"{path}.observation_refs",
        declared_observation_refs,
        "discrepancy_report.observation_refs",
    )
    _closed_refs(
        evidence_refs,
        f"{path}.evidence_refs",
        declared_evidence_refs,
        "discrepancy_report.evidence_refs",
    )

    return DiscrepancyFinding(
        id=_string(item["id"], f"{path}.id"),
        kind=kind,
        state=state,
        severity=severity,
        subject_kind=subject_kind,
        subject_path=subject_path,
        summary=_string(item["summary"], f"{path}.summary"),
        reason=_string(item["reason"], f"{path}.reason"),
        basis_refs=tuple(sorted(basis_refs)),
        observation_refs=tuple(sorted(observation_refs)),
        evidence_refs=tuple(sorted(evidence_refs)),
        has_expected=has_expected,
        expected=expected,
        has_observed=has_observed,
        observed=observed,
        impact=_load_impact(item["impact"], f"{path}.impact"),
        correction_scope=_load_correction_scope(
            item["correction_scope"], f"{path}.correction_scope"
        ),
    )


def _aggregate_state(discrepancies: Sequence[DiscrepancyFinding]) -> str:
    states = {item.state for item in discrepancies}
    if "confirmed" in states:
        return "confirmed"
    if "need_review" in states:
        return "need_review"
    if "detected" in states:
        return "detected"
    return "unknown"


def _aggregate_severity(discrepancies: Sequence[DiscrepancyFinding]) -> str:
    return max(discrepancies, key=lambda item: _SEVERITY_RANK[item.severity]).severity


def load_discrepancy_report(payload: Mapping[str, object]) -> DiscrepancyReport:
    """Load and strictly validate one Discrepancy Report v0.1 payload."""

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"discrepancy_report"})
    body = _mapping(root["discrepancy_report"], "discrepancy_report")
    _exact_fields(
        body,
        "discrepancy_report",
        required={
            "schema_id",
            "schema_version",
            "report_id",
            "recorded_at",
            "state",
            "severity",
            "reason",
            "world_state",
            "observation_refs",
            "evidence_refs",
            "artifact_refs",
            "discrepancies",
        },
    )
    if body["schema_id"] != DISCREPANCY_REPORT_SCHEMA_ID:
        _fail(
            "discrepancy_report.schema_id",
            f"must equal {DISCREPANCY_REPORT_SCHEMA_ID!r}",
        )
    if body["schema_version"] != DISCREPANCY_REPORT_SCHEMA_VERSION:
        _fail(
            "discrepancy_report.schema_version",
            f"must equal {DISCREPANCY_REPORT_SCHEMA_VERSION!r}",
        )

    recorded_at_text, recorded_at = _timestamp(
        body["recorded_at"], "discrepancy_report.recorded_at"
    )
    world_state, world_as_of = _load_world_state_ref(
        body["world_state"], "discrepancy_report.world_state"
    )
    if recorded_at < world_as_of:
        _fail(
            "discrepancy_report.recorded_at",
            "must not be earlier than world_state.as_of",
        )

    observation_refs = _string_list(
        body["observation_refs"], "discrepancy_report.observation_refs"
    )
    evidence_refs = _string_list(
        body["evidence_refs"], "discrepancy_report.evidence_refs"
    )
    artifact_refs = _load_artifact_refs(body["artifact_refs"])
    declared_artifact_refs = frozenset(item.ref_id for item in artifact_refs)
    declared_observation_refs = frozenset(observation_refs)
    declared_evidence_refs = frozenset(evidence_refs)

    raw_discrepancies = body["discrepancies"]
    if not isinstance(raw_discrepancies, Sequence) or isinstance(
        raw_discrepancies, (str, bytes, bytearray)
    ):
        _fail("discrepancy_report.discrepancies", "must be an array")
    if not raw_discrepancies:
        _fail("discrepancy_report.discrepancies", "must contain at least one item")
    discrepancies: list[DiscrepancyFinding] = []
    ids: set[str] = set()
    for index, raw in enumerate(raw_discrepancies):
        item = _load_discrepancy(
            raw,
            index=index,
            declared_artifact_refs=declared_artifact_refs,
            declared_observation_refs=declared_observation_refs,
            declared_evidence_refs=declared_evidence_refs,
        )
        if item.id in ids:
            _fail(
                f"discrepancy_report.discrepancies[{index}].id",
                f"duplicates id {item.id!r}",
            )
        ids.add(item.id)
        discrepancies.append(item)

    normalized_discrepancies = tuple(sorted(discrepancies, key=lambda item: item.id))
    state = _enum(body["state"], "discrepancy_report.state", DISCREPANCY_STATES)
    expected_state = _aggregate_state(normalized_discrepancies)
    if state != expected_state:
        _fail(
            "discrepancy_report.state",
            f"must equal aggregate discrepancy state {expected_state!r}",
        )
    severity = _enum(
        body["severity"],
        "discrepancy_report.severity",
        DISCREPANCY_SEVERITIES,
    )
    expected_severity = _aggregate_severity(normalized_discrepancies)
    if severity != expected_severity:
        _fail(
            "discrepancy_report.severity",
            f"must equal maximum discrepancy severity {expected_severity!r}",
        )

    return DiscrepancyReport(
        report_id=_string(body["report_id"], "discrepancy_report.report_id"),
        recorded_at=recorded_at_text,
        state=state,
        severity=severity,
        reason=_string(body["reason"], "discrepancy_report.reason"),
        world_state=world_state,
        observation_refs=tuple(sorted(observation_refs)),
        evidence_refs=tuple(sorted(evidence_refs)),
        artifact_refs=artifact_refs,
        discrepancies=normalized_discrepancies,
    )


def validate_discrepancy_report_bindings(
    report: DiscrepancyReport,
    world_state: WorldState,
    artifact_contents: Mapping[str, bytes],
) -> None:
    """Validate snapshot identity and exact byte bindings for report sources.

    This does not parse source artifacts, compare their values, or prove that any
    declared discrepancy, impact, or correction scope is operationally correct.
    """

    checks = (
        (
            "discrepancy_report.world_state.world_state_id",
            report.world_state.world_state_id,
            world_state.world_state_id,
        ),
        (
            "discrepancy_report.world_state.revision",
            report.world_state.revision,
            world_state.revision,
        ),
        (
            "discrepancy_report.world_state.as_of",
            report.world_state.as_of,
            world_state.as_of,
        ),
        (
            "discrepancy_report.world_state.semantic_fingerprint",
            report.world_state.semantic_fingerprint,
            world_state.semantic_fingerprint(),
        ),
    )
    for path, declared, actual in checks:
        if declared != actual:
            _fail(path, f"does not match bound World State: expected {actual!r}")

    missing_observations = sorted(
        set(report.observation_refs) - set(world_state.observation_refs)
    )
    if missing_observations:
        _fail(
            "discrepancy_report.observation_refs",
            "not declared by bound World State: " + ", ".join(missing_observations),
        )
    missing_evidence = sorted(set(report.evidence_refs) - set(world_state.evidence_refs))
    if missing_evidence:
        _fail(
            "discrepancy_report.evidence_refs",
            "not declared by bound World State: " + ", ".join(missing_evidence),
        )

    expected_refs = {item.ref_id: item for item in report.artifact_refs}
    supplied_refs = set(artifact_contents)
    missing = sorted(set(expected_refs) - supplied_refs)
    unknown = sorted(supplied_refs - set(expected_refs))
    if missing:
        _fail("artifact_contents", "missing ref_id values: " + ", ".join(missing))
    if unknown:
        _fail("artifact_contents", "contains unknown ref_id values: " + ", ".join(unknown))

    for ref_id, ref in expected_refs.items():
        content = artifact_contents[ref_id]
        if not isinstance(content, bytes):
            _fail(f"artifact_contents[{ref_id!r}]", "must be bytes")
        actual = hashlib.sha256(content).hexdigest()
        if actual != ref.content_sha256:
            _fail(
                f"artifact_contents[{ref_id!r}]",
                f"SHA-256 mismatch: expected {ref.content_sha256!r}, got {actual!r}",
            )


__all__ = [
    "DISCREPANCY_REPORT_ARTIFACT_ID",
    "DISCREPANCY_REPORT_SCHEMA_ID",
    "DISCREPANCY_REPORT_SCHEMA_VERSION",
    "DISCREPANCY_REPORT_FORMAT_VERSION",
    "DISCREPANCY_STATES",
    "DISCREPANCY_KINDS",
    "DISCREPANCY_SEVERITIES",
    "DISCREPANCY_SUBJECT_KINDS",
    "DISCREPANCY_IMPACT_STATES",
    "DISCREPANCY_CORRECTION_STATES",
    "DiscrepancyReportFormatError",
    "DiscrepancyWorldStateRef",
    "DiscrepancyArtifactRef",
    "DiscrepancyImpact",
    "DiscrepancyCorrectionScope",
    "DiscrepancyFinding",
    "DiscrepancyReport",
    "load_discrepancy_report",
    "validate_discrepancy_report_bindings",
]
