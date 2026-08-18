"""Measurement and provenance records for TC1-Real.

Real acquisition burden is intentionally multi-dimensional. Missing values are
``None`` (unknown), never silently coerced to zero.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Mapping


@dataclass(frozen=True)
class AcquisitionMeasurement:
    monetary_cost: float | None = None
    request_count: int | None = None
    bytes_transferred: int | None = None
    wall_clock_seconds: float | None = None
    processing_cpu_seconds: float | None = None
    storage_bytes: int | None = None
    human_preparation_seconds: float | None = None

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value is not None and value < 0:
                raise ValueError(f"{name} must be >= 0 when known")

    @property
    def known_dimensions(self) -> tuple[str, ...]:
        return tuple(
            name for name, value in asdict(self).items() if value is not None
        )


@dataclass(frozen=True)
class SourceProvenance:
    source_id: str
    source_family: str
    retrieval_timestamp: str
    source_url: str
    request_parameters: Mapping[str, object] = field(default_factory=dict)
    source_effective_at: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    source_crs: str | None = None
    source_units: Mapping[str, str] = field(default_factory=dict)
    source_resolution: str | None = None
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "source_id",
            "source_family",
            "retrieval_timestamp",
            "source_url",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if self.content_sha256 is not None:
            if len(self.content_sha256) != 64:
                raise ValueError("content_sha256 must be a 64-character hex digest")
            try:
                int(self.content_sha256, 16)
            except ValueError as exc:
                raise ValueError("content_sha256 must be hexadecimal") from exc


@dataclass(frozen=True)
class AcquisitionRecord:
    provenance: SourceProvenance
    measurement: AcquisitionMeasurement
    fixture_path: str | None = None
    notes: str = ""

    def to_json_dict(self) -> dict[str, object]:
        return {
            "provenance": {
                **asdict(self.provenance),
                "request_parameters": dict(self.provenance.request_parameters),
                "source_units": dict(self.provenance.source_units),
            },
            "measurement": asdict(self.measurement),
            "fixture_path": self.fixture_path,
            "notes": self.notes,
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_json_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_offline_record(
    *,
    source_id: str,
    source_family: str,
    retrieval_timestamp: str,
    source_url: str,
    payload: bytes,
    measurement: AcquisitionMeasurement,
    fixture_path: str | None = None,
    request_parameters: Mapping[str, object] | None = None,
    source_effective_at: str | None = None,
    valid_from: str | None = None,
    valid_until: str | None = None,
    source_crs: str | None = None,
    source_units: Mapping[str, str] | None = None,
    source_resolution: str | None = None,
    notes: str = "",
) -> AcquisitionRecord:
    """Build one replayable record from exact acquired bytes.

    The caller supplies measured burden explicitly. This helper hashes payload
    bytes but does not fetch a network resource or infer source semantics.
    """

    provenance = SourceProvenance(
        source_id=source_id,
        source_family=source_family,
        retrieval_timestamp=retrieval_timestamp,
        source_url=source_url,
        request_parameters=request_parameters or {},
        source_effective_at=source_effective_at,
        valid_from=valid_from,
        valid_until=valid_until,
        source_crs=source_crs,
        source_units=source_units or {},
        source_resolution=source_resolution,
        content_sha256=sha256_bytes(payload),
    )
    return AcquisitionRecord(
        provenance=provenance,
        measurement=measurement,
        fixture_path=fixture_path,
        notes=notes,
    )
