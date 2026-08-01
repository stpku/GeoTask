"""Public Observation v0.1 contract for the GeoTask world-model foundation.

An Observation records what one producer claims to have observed or inferred at
one point in time. Loading an Observation validates structure, references,
timestamps, uncertainty metadata, and JSON safety. It does not verify that the
claims are true, fetch source content, mutate a WorldState, or authorize action.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Mapping, Sequence


OBSERVATION_ARTIFACT_ID = "geotask.observation"
OBSERVATION_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/geotask-observation-v0.1.schema.json"
)
OBSERVATION_SCHEMA_VERSION = "0.1"
OBSERVATION_FORMAT_VERSION = "0.1"

SOURCE_KINDS = frozenset(
    {
        "multimodal_model",
        "sensor",
        "map",
        "authoritative_data",
        "human",
        "external_system",
        "simulation",
    }
)
PRODUCER_KINDS = frozenset(
    {"ai_model", "sensor", "human", "software", "organization"}
)
CLAIM_BASES = frozenset(
    {
        "direct_observation",
        "model_inference",
        "derived",
        "external_assertion",
        "human_judgment",
    }
)
UNCERTAINTY_KINDS = frozenset(
    {
        "probability_of_error",
        "confidence",
        "standard_deviation",
        "interval_width",
        "qualitative",
    }
)
QUALITATIVE_UNCERTAINTY_VALUES = frozenset({"low", "medium", "high", "unknown"})


class ObservationFormatError(ValueError):
    """Raised when an Observation payload violates the public v0.1 contract."""


def _fail(path: str, message: str) -> None:
    raise ObservationFormatError(f"{path}: {message}")


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


def _optional_string(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _enum(value: object, path: str, allowed: frozenset[str]) -> str:
    normalized = _string(value, path)
    if normalized not in allowed:
        _fail(path, "must be one of: " + ", ".join(sorted(allowed)))
    return normalized


def _timestamp(value: object, path: str) -> tuple[str, datetime]:
    text = _string(value, path)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ObservationFormatError(f"{path}: must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must include a timezone offset")
    return text, parsed


def _sha256(value: object, path: str) -> str:
    text = _string(value, path)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        _fail(path, "must be a 64-character lowercase SHA-256 digest")
    return text


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


@dataclass(frozen=True)
class ObservationSource:
    kind: str
    reference: str
    artifact_id: str | None = None
    sha256: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"kind": self.kind, "reference": self.reference}
        if self.artifact_id is not None:
            payload["artifact_id"] = self.artifact_id
        if self.sha256 is not None:
            payload["sha256"] = self.sha256
        return payload


@dataclass(frozen=True)
class ObservationProducer:
    id: str
    kind: str
    version: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"id": self.id, "kind": self.kind}
        if self.version is not None:
            payload["version"] = self.version
        return payload


@dataclass(frozen=True)
class ObservationUncertainty:
    kind: str
    value: float | str
    unit: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"kind": self.kind, "value": self.value}
        if self.unit is not None:
            payload["unit"] = self.unit
        return payload


@dataclass(frozen=True)
class WorldClaim:
    id: str
    subject_ref: str
    predicate: str
    basis: str
    value: object
    object_ref: str | None = None
    observed_at: str | None = None
    valid_until: str | None = None
    uncertainty: ObservationUncertainty | None = None
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "subject_ref": self.subject_ref,
            "predicate": self.predicate,
            "basis": self.basis,
            "value": copy.deepcopy(self.value),
        }
        if self.object_ref is not None:
            payload["object_ref"] = self.object_ref
        if self.observed_at is not None:
            payload["observed_at"] = self.observed_at
        if self.valid_until is not None:
            payload["valid_until"] = self.valid_until
        if self.uncertainty is not None:
            payload["uncertainty"] = self.uncertainty.to_dict()
        if self.evidence_refs:
            payload["evidence_refs"] = list(self.evidence_refs)
        return payload


@dataclass(frozen=True)
class Observation:
    observation_id: str
    observed_at: str
    received_at: str
    source: ObservationSource
    producer: ObservationProducer
    claims: tuple[WorldClaim, ...]
    supersedes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_id": OBSERVATION_SCHEMA_ID,
            "schema_version": OBSERVATION_SCHEMA_VERSION,
            "observation_id": self.observation_id,
            "observed_at": self.observed_at,
            "received_at": self.received_at,
            "source": self.source.to_dict(),
            "producer": self.producer.to_dict(),
            "claims": [claim.to_dict() for claim in self.claims],
        }
        if self.supersedes:
            body["supersedes"] = list(self.supersedes)
        return {"observation": body}


def _load_source(value: object) -> ObservationSource:
    path = "observation.source"
    source = _mapping(value, path)
    _exact_fields(
        source,
        path,
        required={"kind", "reference"},
        optional={"artifact_id", "sha256"},
    )
    return ObservationSource(
        kind=_enum(source["kind"], f"{path}.kind", SOURCE_KINDS),
        reference=_string(source["reference"], f"{path}.reference"),
        artifact_id=_optional_string(source.get("artifact_id"), f"{path}.artifact_id"),
        sha256=_sha256(source["sha256"], f"{path}.sha256")
        if "sha256" in source
        else None,
    )


def _load_producer(value: object) -> ObservationProducer:
    path = "observation.producer"
    producer = _mapping(value, path)
    _exact_fields(
        producer,
        path,
        required={"id", "kind"},
        optional={"version"},
    )
    return ObservationProducer(
        id=_string(producer["id"], f"{path}.id"),
        kind=_enum(producer["kind"], f"{path}.kind", PRODUCER_KINDS),
        version=_optional_string(producer.get("version"), f"{path}.version"),
    )


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
    unit = _optional_string(uncertainty.get("unit"), f"{path}.unit")

    if kind == "qualitative":
        value_text = _enum(
            raw_value,
            f"{path}.value",
            QUALITATIVE_UNCERTAINTY_VALUES,
        )
        if unit is not None:
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
        if unit is not None:
            _fail(f"{path}.unit", f"is not allowed for {kind}")
    elif numeric < 0.0:
        _fail(f"{path}.value", "must be greater than or equal to 0")
    return ObservationUncertainty(kind=kind, value=numeric, unit=unit)


def _load_claim(
    value: object,
    *,
    index: int,
    parent_observed_at: datetime,
    received_at: datetime,
) -> WorldClaim:
    path = f"observation.claims[{index}]"
    claim = _mapping(value, path)
    _exact_fields(
        claim,
        path,
        required={"id", "subject_ref", "predicate", "basis", "value"},
        optional={
            "object_ref",
            "observed_at",
            "valid_until",
            "uncertainty",
            "evidence_refs",
        },
    )

    claim_observed_text: str | None = None
    claim_observed = parent_observed_at
    if "observed_at" in claim:
        claim_observed_text, claim_observed = _timestamp(
            claim["observed_at"], f"{path}.observed_at"
        )
    if claim_observed > received_at:
        _fail(f"{path}.observed_at", "must not be later than observation.received_at")

    valid_until_text: str | None = None
    if "valid_until" in claim:
        valid_until_text, valid_until = _timestamp(
            claim["valid_until"], f"{path}.valid_until"
        )
        if valid_until < claim_observed:
            _fail(f"{path}.valid_until", "must not be earlier than the claim observation time")

    return WorldClaim(
        id=_string(claim["id"], f"{path}.id"),
        subject_ref=_string(claim["subject_ref"], f"{path}.subject_ref"),
        predicate=_string(claim["predicate"], f"{path}.predicate"),
        basis=_enum(claim["basis"], f"{path}.basis", CLAIM_BASES),
        value=_json_value(claim["value"], f"{path}.value"),
        object_ref=_optional_string(claim.get("object_ref"), f"{path}.object_ref"),
        observed_at=claim_observed_text,
        valid_until=valid_until_text,
        uncertainty=_load_uncertainty(claim["uncertainty"], f"{path}.uncertainty")
        if "uncertainty" in claim
        else None,
        evidence_refs=_string_list(
            claim.get("evidence_refs", ()), f"{path}.evidence_refs"
        ),
    )


def load_observation(payload: Mapping[str, object]) -> Observation:
    """Load and strictly validate one Observation v0.1 payload.

    The function validates only the declared contract. It does not resolve the
    source reference, authenticate the producer, verify claim truth, or update a
    world state.
    """

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"observation"})
    body = _mapping(root["observation"], "observation")
    _exact_fields(
        body,
        "observation",
        required={
            "schema_id",
            "schema_version",
            "observation_id",
            "observed_at",
            "received_at",
            "source",
            "producer",
            "claims",
        },
        optional={"supersedes"},
    )
    if body["schema_id"] != OBSERVATION_SCHEMA_ID:
        _fail("observation.schema_id", f"must equal {OBSERVATION_SCHEMA_ID!r}")
    if body["schema_version"] != OBSERVATION_SCHEMA_VERSION:
        _fail(
            "observation.schema_version",
            f"must equal {OBSERVATION_SCHEMA_VERSION!r}",
        )

    observation_id = _string(body["observation_id"], "observation.observation_id")
    observed_at_text, observed_at = _timestamp(
        body["observed_at"], "observation.observed_at"
    )
    received_at_text, received_at = _timestamp(
        body["received_at"], "observation.received_at"
    )
    if received_at < observed_at:
        _fail("observation.received_at", "must not be earlier than observation.observed_at")

    raw_claims = body["claims"]
    if not isinstance(raw_claims, Sequence) or isinstance(
        raw_claims, (str, bytes, bytearray)
    ):
        _fail("observation.claims", "must be a non-empty array")
    if not raw_claims:
        _fail("observation.claims", "must contain at least one world claim")

    claims: list[WorldClaim] = []
    claim_ids: set[str] = set()
    for index, raw_claim in enumerate(raw_claims):
        claim = _load_claim(
            raw_claim,
            index=index,
            parent_observed_at=observed_at,
            received_at=received_at,
        )
        if claim.id in claim_ids:
            _fail(f"observation.claims[{index}].id", f"duplicates claim id {claim.id!r}")
        claim_ids.add(claim.id)
        claims.append(claim)

    supersedes = _string_list(
        body.get("supersedes", ()), "observation.supersedes"
    )
    if observation_id in supersedes:
        _fail("observation.supersedes", "must not contain the current observation_id")

    return Observation(
        observation_id=observation_id,
        observed_at=observed_at_text,
        received_at=received_at_text,
        source=_load_source(body["source"]),
        producer=_load_producer(body["producer"]),
        claims=tuple(claims),
        supersedes=supersedes,
    )


__all__ = [
    "OBSERVATION_ARTIFACT_ID",
    "OBSERVATION_SCHEMA_ID",
    "OBSERVATION_SCHEMA_VERSION",
    "OBSERVATION_FORMAT_VERSION",
    "SOURCE_KINDS",
    "PRODUCER_KINDS",
    "CLAIM_BASES",
    "UNCERTAINTY_KINDS",
    "QUALITATIVE_UNCERTAINTY_VALUES",
    "ObservationFormatError",
    "ObservationSource",
    "ObservationProducer",
    "ObservationUncertainty",
    "WorldClaim",
    "Observation",
    "load_observation",
]
