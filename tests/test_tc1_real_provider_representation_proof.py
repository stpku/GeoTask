from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.tc1_real.spatial_planning.provider_representation_proof import (
    analyze_provider_representation,
)


FIXTURE = (
    Path(__file__).parents[1]
    / "benchmarks"
    / "tc1_real"
    / "spatial_planning"
    / "fixtures"
    / "provider_representation_proof_v0_1.json"
)


def _evidence() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_joined_representation_repeats_base_planning_units() -> None:
    result = analyze_provider_representation(_evidence())

    assert result.joined_feature_count == 118190
    assert result.unique_planning_unit_count == 471
    assert result.base_feature_count == 471
    assert result.base_is_one_feature_per_unit is True
    assert result.joined_records_per_unit == pytest.approx(250.9342, rel=1e-4)


def test_cross_representation_network_bytes_are_not_a_compression_claim() -> None:
    result = analyze_provider_representation(_evidence())
    assert result.byte_ratio_scoreable is False


def test_population_semantics_remain_related_separately() -> None:
    evidence = _evidence()
    relation = evidence["relationship"]
    assert relation == {"population_table_id": 13, "key": "newluau"}


def test_incomplete_representation_evidence_fails_closed() -> None:
    evidence = _evidence()
    evidence["joined_representation"]["complete"] = False
    with pytest.raises(ValueError, match="complete acquisition evidence"):
        analyze_provider_representation(evidence)


def test_mismatched_unique_unit_sets_fail_closed() -> None:
    evidence = _evidence()
    evidence["base_representation"]["unique_planning_unit_count"] = 470
    with pytest.raises(ValueError, match="same unique unit set"):
        analyze_provider_representation(evidence)
