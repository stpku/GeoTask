"""Offline proof that provider completeness is not enough when representation is wrong.

This benchmark helper uses already-recorded TC1-Real Phoenix evidence. It does
not access the live provider and it does not treat cross-representation byte
ratios as compression savings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ProviderRepresentationProof:
    joined_feature_count: int
    unique_planning_unit_count: int
    base_feature_count: int
    joined_records_per_unit: float
    base_is_one_feature_per_unit: bool
    byte_ratio_scoreable: bool


def analyze_provider_representation(
    evidence: Mapping[str, object],
) -> ProviderRepresentationProof:
    joined = evidence["joined_representation"]
    base = evidence["base_representation"]
    if not isinstance(joined, Mapping) or not isinstance(base, Mapping):
        raise ValueError("representation evidence must contain mapping records")

    if joined.get("complete") is not True or base.get("complete") is not True:
        raise ValueError("both representations must have complete acquisition evidence")

    joined_count = int(joined["complete_feature_count"])
    unique_count = int(joined["unique_planning_unit_count"])
    base_count = int(base["complete_feature_count"])
    base_unique_count = int(base["unique_planning_unit_count"])
    if min(joined_count, unique_count, base_count, base_unique_count) <= 0:
        raise ValueError("representation counts must be > 0")
    if unique_count != base_unique_count:
        raise ValueError("joined and base evidence must refer to the same unique unit set")

    note = str(evidence.get("provenance_note", ""))
    byte_ratio_scoreable = not (
        "do not carry identical semantics" in note
        or "must not be reported as compression savings" in note
    )

    return ProviderRepresentationProof(
        joined_feature_count=joined_count,
        unique_planning_unit_count=unique_count,
        base_feature_count=base_count,
        joined_records_per_unit=joined_count / unique_count,
        base_is_one_feature_per_unit=base_count == base_unique_count,
        byte_ratio_scoreable=byte_ratio_scoreable,
    )
