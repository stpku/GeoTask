"""Public World State v0.1 contract for explicit GeoTask snapshots.

A World State records one versioned, point-in-time snapshot of world objects,
attributes, and relations. Loading validates structure, timestamps, reference
closure, traceability, uncertainty metadata, JSON safety, and a deterministic
semantic fingerprint. It does not ingest observations, verify external evidence,
compute a State Transition, rerun tasks, or authorize action.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Mapping, Sequence

from geotask_core.v1.observation import (
    CLAIM_BASES,
    QUALITATIVE_UNCERTAINTY_VALUES,
    UNCERTAINTY_KINDS,
    ObservationUncertainty,
)


WORLD_STATE_ARTIFACT_ID = "geotask.world-state"
WORLD_STATE_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/geotask-world-state-v0.1.schema.json"
)
WORLD_STATE_SCHEMA_VERSION = "0.1"
WORLD_STATE_FORMAT_VERSION = "0.1"

VERIFICATION_STATUSES = frozenset(
    {
        "asserted",
        "verified",
        "contradicted",
        "unverifiable",
        "need_data",
        "unknown",
    }
)
_TRACEABILITY_REQUIRED_STATUSES = frozenset(
    {"asserted", "verified", "contradicted"}
)


class WorldStateFormatError(ValueError):
    """Raised when a World State payload violates the public v0.1 contract."""


def _fail(path: str, message: str) -> None:
    raise WorldStateFormatError(f"{path}: {message}")


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
        raise WorldStateFormatError(f"{path}: must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must include a timezone offset")
    return text, parsed


def _string_list(value: object, path: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array of non-empty strings")
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
        return [_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    _fail(path, "must be a JSON-compatible value")


def _load_uncertainty(value: object, path: str) -> ObservationUncertainty:
    uncertainty = _mapping(value, path)
    _exact_fields(
        uncertainty,
        path,
        required={"kind", "value"},
        optional={"unit"},
    )
    kind = _enum(uncertainty["kind"], f"{path}.kind", UNCERTAINTY_KINDS)
    raw_value = uncertainty["value"]
    unit = uncertainty.get("unit")
    unit_text = _string(unit, f"{path}.unit") if unit is not None else None

    if kind == "qualitative":
        value_text = _enum(
            raw_value,
            f"{path}.value",
            QUALITATIVE_UNCERTAINTY_VALUES,
        )
        if unit_text is not None:
            _fail(f"{path}.unit", "is not allowed for qualitative uncertainty")
        return ObservationUncertainty(kind=kind, value=value_text)

    if not isinstance(raw_value, (int, float)) or isinstance(raw_value, bool):
        _fail(f"{path}.value", "must be a finite number")
    numeric = float(raw_value)
    if not math.isfinite(numeric):
        _fail(f"{path}.value", "must be a finite number")
    if kind in {"probability_of_error", "confidence"}:
        if not 0.0 <= numeric <= 1.0:
            _fail(f"{path}.value", "must be between 0 and 1 inclusive")
        if unit_text is not None:
            _fail(f"{path}.unit", f"is not allowed for {kind}")
    elif numeric < 0.0:
        _fail(f"{path}.value", "must be greater than or equal to 0")
    return ObservationUncertainty(kind=kind, value=numeric, unit=unit_text)


def _load_validity(
    value: Mapping[str, object],
    path: str,
    *,
    as_of: datetime,
) -> tuple[str | None, str | None]:
    valid_from_text: str | None = None
    valid_from: datetime | None = None
    if "valid_from" in value:
        valid_from_text, valid_from = _timestamp(
            value["valid_from"], f"{path}.valid_from"
        )
        if valid_from > as_of:
            _fail(f"{path}.valid_from", "must not be later than world_state.as_of")

    valid_until_text: str | None = None
    valid_until: datetime | None = None
    if "valid_until" in value:
        valid_until_text, valid_until = _timestamp(
            value["valid_until"], f"{path}.valid_until"
        )
        if valid_until < as_of:
            _fail(f"{path}.valid_until", "must not be earlier than world_state.as_of")

    if valid_from is not None and valid_until is not None and valid_until < valid_from:
        _fail(f"{path}.valid_until", "must not be earlier than valid_from")
    return valid_from_text, valid_until_text


def _load_traceability(
    value: Mapping[str, object],
    path: str,
    *,
    declared_observation_refs: frozenset[str],
    declared_evidence_refs: frozenset[str],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    verification_status = _enum(
        value["verification_status"],
        f"{path}.verification_status",
        VERIFICATION_STATUSES,
    )
    observation_refs = _string_list(
        value.get("observation_refs", ()),
        f"{path}.observation_refs",
    )
    evidence_refs = _string_list(
        value.get("evidence_refs", ()),
        f"{path}.evidence_refs",
    )

    for index, ref in enumerate(observation_refs):
        if ref not in declared_observation_refs:
            _fail(
                f"{path}.observation_refs[{index}]",
                f"must be declared in world_state.observation_refs: {ref!r}",
            )
    for index, ref in enumerate(evidence_refs):
        if ref not in declared_evidence_refs:
            _fail(
                f"{path}.evidence_refs[{index}]",
                f"must be declared in world_state.evidence_refs: {ref!r}",
            )

    if (
        verification_status in _TRACEABILITY_REQUIRED_STATUSES
        and not observation_refs
        and not evidence_refs
    ):
        _fail(
            path,
            f"verification_status {verification_status!r} requires at least one "
            "observation_ref or evidence_ref",
        )
    return (
        verification_status,
        tuple(sorted(observation_refs)),
        tuple(sorted(evidence_refs)),
    )


@dataclass(frozen=True)
class WorldStateAttribute:
    name: str
    value: object
    basis: str
    verification_status: str
    valid_from: str | None = None
    valid_until: str | None = None
    uncertainty: ObservationUncertainty | None = None
    observation_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "value": copy.deepcopy(self.value),
            "basis": self.basis,
            "verification_status": self.verification_status,
            "observation_refs": sorted(self.observation_refs),
            "evidence_refs": sorted(self.evidence_refs),
        }
        if self.valid_from is not None:
            payload["valid_from"] = self.valid_from
        if self.valid_until is not None:
            payload["valid_until"] = self.valid_until
        if self.uncertainty is not None:
            payload["uncertainty"] = self.uncertainty.to_dict()
        return payload


@dataclass(frozen=True)
class WorldStateObject:
    id: str
    type: str
    verification_status: str
    attributes: tuple[WorldStateAttribute, ...]
    valid_from: str | None = None
    valid_until: str | None = None
    uncertainty: ObservationUncertainty | None = None
    observation_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "type": self.type,
            "verification_status": self.verification_status,
            "observation_refs": sorted(self.observation_refs),
            "evidence_refs": sorted(self.evidence_refs),
            "attributes": [
                item.to_dict() for item in sorted(self.attributes, key=lambda item: item.name)
            ],
        }
        if self.valid_from is not None:
            payload["valid_from"] = self.valid_from
        if self.valid_until is not None:
            payload["valid_until"] = self.valid_until
        if self.uncertainty is not None:
            payload["uncertainty"] = self.uncertainty.to_dict()
        return payload


@dataclass(frozen=True)
class WorldStateRelation:
    id: str
    subject_ref: str
    predicate: str
    object_ref: str
    value: object
    basis: str
    verification_status: str
    valid_from: str | None = None
    valid_until: str | None = None
    uncertainty: ObservationUncertainty | None = None
    observation_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "subject_ref": self.subject_ref,
            "predicate": self.predicate,
            "object_ref": self.object_ref,
            "value": copy.deepcopy(self.value),
            "basis": self.basis,
            "verification_status": self.verification_status,
            "observation_refs": sorted(self.observation_refs),
            "evidence_refs": sorted(self.evidence_refs),
        }
        if self.valid_from is not None:
            payload["valid_from"] = self.valid_from
        if self.valid_until is not None:
            payload["valid_until"] = self.valid_until
        if self.uncertainty is not None:
            payload["uncertainty"] = self.uncertainty.to_dict()
        return payload


@dataclass(frozen=True)
class WorldState:
    world_state_id: str
    revision: int
    as_of: str
    materialized_at: str
    observation_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    objects: tuple[WorldStateObject, ...]
    relations: tuple[WorldStateRelation, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "world_state": {
                "schema_id": WORLD_STATE_SCHEMA_ID,
                "schema_version": WORLD_STATE_SCHEMA_VERSION,
                "world_state_id": self.world_state_id,
                "revision": self.revision,
                "as_of": self.as_of,
                "materialized_at": self.materialized_at,
                "observation_refs": sorted(self.observation_refs),
                "evidence_refs": sorted(self.evidence_refs),
                "objects": [
                    item.to_dict() for item in sorted(self.objects, key=lambda item: item.id)
                ],
                "relations": [
                    item.to_dict() for item in sorted(self.relations, key=lambda item: item.id)
                ],
            }
        }

    def semantic_fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint of the normalized snapshot."""

        raw = json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _load_attribute(
    value: object,
    *,
    object_index: int,
    attribute_index: int,
    as_of: datetime,
    declared_observation_refs: frozenset[str],
    declared_evidence_refs: frozenset[str],
) -> WorldStateAttribute:
    path = f"world_state.objects[{object_index}].attributes[{attribute_index}]"
    attribute = _mapping(value, path)
    _exact_fields(
        attribute,
        path,
        required={"name", "value", "basis", "verification_status"},
        optional={
            "valid_from",
            "valid_until",
            "uncertainty",
            "observation_refs",
            "evidence_refs",
        },
    )
    valid_from, valid_until = _load_validity(attribute, path, as_of=as_of)
    verification_status, observation_refs, evidence_refs = _load_traceability(
        attribute,
        path,
        declared_observation_refs=declared_observation_refs,
        declared_evidence_refs=declared_evidence_refs,
    )
    return WorldStateAttribute(
        name=_string(attribute["name"], f"{path}.name"),
        value=_json_value(attribute["value"], f"{path}.value"),
        basis=_enum(attribute["basis"], f"{path}.basis", CLAIM_BASES),
        verification_status=verification_status,
        valid_from=valid_from,
        valid_until=valid_until,
        uncertainty=_load_uncertainty(attribute["uncertainty"], f"{path}.uncertainty")
        if "uncertainty" in attribute
        else None,
        observation_refs=observation_refs,
        evidence_refs=evidence_refs,
    )


def _load_object(
    value: object,
    *,
    index: int,
    as_of: datetime,
    declared_observation_refs: frozenset[str],
    declared_evidence_refs: frozenset[str],
) -> WorldStateObject:
    path = f"world_state.objects[{index}]"
    item = _mapping(value, path)
    _exact_fields(
        item,
        path,
        required={"id", "type", "verification_status", "attributes"},
        optional={
            "valid_from",
            "valid_until",
            "uncertainty",
            "observation_refs",
            "evidence_refs",
        },
    )
    raw_attributes = item["attributes"]
    if not isinstance(raw_attributes, Sequence) or isinstance(
        raw_attributes, (str, bytes, bytearray)
    ):
        _fail(f"{path}.attributes", "must be an array")

    attributes: list[WorldStateAttribute] = []
    attribute_names: set[str] = set()
    for attribute_index, raw_attribute in enumerate(raw_attributes):
        attribute = _load_attribute(
            raw_attribute,
            object_index=index,
            attribute_index=attribute_index,
            as_of=as_of,
            declared_observation_refs=declared_observation_refs,
            declared_evidence_refs=declared_evidence_refs,
        )
        if attribute.name in attribute_names:
            _fail(
                f"{path}.attributes[{attribute_index}].name",
                f"duplicates attribute name {attribute.name!r}",
            )
        attribute_names.add(attribute.name)
        attributes.append(attribute)

    valid_from, valid_until = _load_validity(item, path, as_of=as_of)
    verification_status, observation_refs, evidence_refs = _load_traceability(
        item,
        path,
        declared_observation_refs=declared_observation_refs,
        declared_evidence_refs=declared_evidence_refs,
    )
    return WorldStateObject(
        id=_string(item["id"], f"{path}.id"),
        type=_string(item["type"], f"{path}.type"),
        verification_status=verification_status,
        attributes=tuple(sorted(attributes, key=lambda item: item.name)),
        valid_from=valid_from,
        valid_until=valid_until,
        uncertainty=_load_uncertainty(item["uncertainty"], f"{path}.uncertainty")
        if "uncertainty" in item
        else None,
        observation_refs=observation_refs,
        evidence_refs=evidence_refs,
    )


def _load_relation(
    value: object,
    *,
    index: int,
    as_of: datetime,
    object_ids: frozenset[str],
    declared_observation_refs: frozenset[str],
    declared_evidence_refs: frozenset[str],
) -> WorldStateRelation:
    path = f"world_state.relations[{index}]"
    relation = _mapping(value, path)
    _exact_fields(
        relation,
        path,
        required={
            "id",
            "subject_ref",
            "predicate",
            "object_ref",
            "value",
            "basis",
            "verification_status",
        },
        optional={
            "valid_from",
            "valid_until",
            "uncertainty",
            "observation_refs",
            "evidence_refs",
        },
    )
    subject_ref = _string(relation["subject_ref"], f"{path}.subject_ref")
    object_ref = _string(relation["object_ref"], f"{path}.object_ref")
    if subject_ref not in object_ids:
        _fail(f"{path}.subject_ref", f"references unknown world object {subject_ref!r}")
    if object_ref not in object_ids:
        _fail(f"{path}.object_ref", f"references unknown world object {object_ref!r}")

    valid_from, valid_until = _load_validity(relation, path, as_of=as_of)
    verification_status, observation_refs, evidence_refs = _load_traceability(
        relation,
        path,
        declared_observation_refs=declared_observation_refs,
        declared_evidence_refs=declared_evidence_refs,
    )
    return WorldStateRelation(
        id=_string(relation["id"], f"{path}.id"),
        subject_ref=subject_ref,
        predicate=_string(relation["predicate"], f"{path}.predicate"),
        object_ref=object_ref,
        value=_json_value(relation["value"], f"{path}.value"),
        basis=_enum(relation["basis"], f"{path}.basis", CLAIM_BASES),
        verification_status=verification_status,
        valid_from=valid_from,
        valid_until=valid_until,
        uncertainty=_load_uncertainty(relation["uncertainty"], f"{path}.uncertainty")
        if "uncertainty" in relation
        else None,
        observation_refs=observation_refs,
        evidence_refs=evidence_refs,
    )


def load_world_state(payload: Mapping[str, object]) -> WorldState:
    """Load and strictly validate one World State v0.1 payload.

    Validation proves only that the snapshot is structurally complete, internally
    consistent, reference-closed, time-consistent, JSON-safe, and traceable to its
    declared inputs. It does not verify external truth or materialize a transition.
    """

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"world_state"})
    body = _mapping(root["world_state"], "world_state")
    _exact_fields(
        body,
        "world_state",
        required={
            "schema_id",
            "schema_version",
            "world_state_id",
            "revision",
            "as_of",
            "materialized_at",
            "observation_refs",
            "evidence_refs",
            "objects",
            "relations",
        },
    )
    if body["schema_id"] != WORLD_STATE_SCHEMA_ID:
        _fail("world_state.schema_id", f"must equal {WORLD_STATE_SCHEMA_ID!r}")
    if body["schema_version"] != WORLD_STATE_SCHEMA_VERSION:
        _fail(
            "world_state.schema_version",
            f"must equal {WORLD_STATE_SCHEMA_VERSION!r}",
        )

    world_state_id = _string(body["world_state_id"], "world_state.world_state_id")
    revision = _positive_integer(body["revision"], "world_state.revision")
    as_of_text, as_of = _timestamp(body["as_of"], "world_state.as_of")
    materialized_at_text, materialized_at = _timestamp(
        body["materialized_at"], "world_state.materialized_at"
    )
    if materialized_at < as_of:
        _fail(
            "world_state.materialized_at",
            "must not be earlier than world_state.as_of",
        )

    observation_refs = _string_list(
        body["observation_refs"], "world_state.observation_refs"
    )
    evidence_refs = _string_list(body["evidence_refs"], "world_state.evidence_refs")
    declared_observation_refs = frozenset(observation_refs)
    declared_evidence_refs = frozenset(evidence_refs)

    raw_objects = body["objects"]
    if not isinstance(raw_objects, Sequence) or isinstance(
        raw_objects, (str, bytes, bytearray)
    ):
        _fail("world_state.objects", "must be a non-empty array")
    if not raw_objects:
        _fail("world_state.objects", "must contain at least one world object")

    objects: list[WorldStateObject] = []
    object_ids: set[str] = set()
    for index, raw_object in enumerate(raw_objects):
        item = _load_object(
            raw_object,
            index=index,
            as_of=as_of,
            declared_observation_refs=declared_observation_refs,
            declared_evidence_refs=declared_evidence_refs,
        )
        if item.id in object_ids:
            _fail(f"world_state.objects[{index}].id", f"duplicates object id {item.id!r}")
        object_ids.add(item.id)
        objects.append(item)

    raw_relations = body["relations"]
    if not isinstance(raw_relations, Sequence) or isinstance(
        raw_relations, (str, bytes, bytearray)
    ):
        _fail("world_state.relations", "must be an array")

    relations: list[WorldStateRelation] = []
    relation_ids: set[str] = set()
    frozen_object_ids = frozenset(object_ids)
    for index, raw_relation in enumerate(raw_relations):
        relation = _load_relation(
            raw_relation,
            index=index,
            as_of=as_of,
            object_ids=frozen_object_ids,
            declared_observation_refs=declared_observation_refs,
            declared_evidence_refs=declared_evidence_refs,
        )
        if relation.id in relation_ids:
            _fail(
                f"world_state.relations[{index}].id",
                f"duplicates relation id {relation.id!r}",
            )
        if relation.id in object_ids:
            _fail(
                f"world_state.relations[{index}].id",
                f"collides with world object id {relation.id!r}",
            )
        relation_ids.add(relation.id)
        relations.append(relation)

    return WorldState(
        world_state_id=world_state_id,
        revision=revision,
        as_of=as_of_text,
        materialized_at=materialized_at_text,
        observation_refs=tuple(sorted(observation_refs)),
        evidence_refs=tuple(sorted(evidence_refs)),
        objects=tuple(sorted(objects, key=lambda item: item.id)),
        relations=tuple(sorted(relations, key=lambda item: item.id)),
    )


__all__ = [
    "WORLD_STATE_ARTIFACT_ID",
    "WORLD_STATE_SCHEMA_ID",
    "WORLD_STATE_SCHEMA_VERSION",
    "WORLD_STATE_FORMAT_VERSION",
    "VERIFICATION_STATUSES",
    "WorldStateFormatError",
    "WorldStateAttribute",
    "WorldStateObject",
    "WorldStateRelation",
    "WorldState",
    "load_world_state",
]
