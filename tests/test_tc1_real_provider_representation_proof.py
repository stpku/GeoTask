from __future__ import annotations

import json
from pathlib import Path


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
    evidence = _evidence()
    joined = evidence["joined_representation"]
    base = evidence["base_representation"]

    assert joined["complete"] is True
    assert base["complete"] is True
    assert joined["unique_planning_unit_count"] == 471
    assert base["unique_planning_unit_count"] == 471
    assert base["complete_feature_count"] == 471
    assert joined["complete_feature_count"] == 118190

    duplication_factor = joined["complete_feature_count"] / joined["unique_planning_unit_count"]
    assert 250.0 < duplication_factor < 252.0


def test_cross_representation_network_bytes_are_not_a_compression_claim() -> None:
    evidence = _evidence()
    note = str(evidence["provenance_note"])
    assert "do not carry identical semantics" in note
    assert "must not be reported as compression savings" in note


def test_population_semantics_remain_related_separately() -> None:
    evidence = _evidence()
    relation = evidence["relationship"]
    assert relation == {"population_table_id": 13, "key": "newluau"}
