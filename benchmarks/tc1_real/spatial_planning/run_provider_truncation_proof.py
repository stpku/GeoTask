"""Replay the recorded Phoenix provider-truncation proof.

Usage:
    python -m benchmarks.tc1_real.spatial_planning.run_provider_truncation_proof
"""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.tc1_real.spatial_planning.provider_truncation_proof import (
    analyze_provider_truncation_evidence,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "planning_phx_20260818"
    / "provider-truncation-evidence.json"
)


def main() -> int:
    evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = analyze_provider_truncation_evidence(evidence)

    print("GeoTask TC1 Provider Truncation Proof")
    print("recorded_real_evidence=true")
    print("live_network=false")
    print(
        "naive_task_vs_broad_byte_reduction_percent="
        f"{result.naive_task_vs_broad_byte_reduction_ratio * 100:.5f}"
    )
    print(
        "ordinary_broad_return_fraction_of_complete_percent="
        f"{result.naive_broad_return_fraction_of_complete * 100:.5f}"
    )
    print(
        "ordinary_broad_undercount_percent="
        f"{result.naive_broad_undercount_ratio * 100:.5f}"
    )
    print(
        "both_single_queries_hit_observed_ceiling="
        f"{str(result.both_single_queries_hit_observed_ceiling).lower()}"
    )
    print(
        "complete_broad_exceeds_single_query="
        f"{str(result.complete_broad_exceeds_single_query).lower()}"
    )
    print(f"reduction_scoreable={str(result.reduction_scoreable).lower()}")
    print(f"verdict={result.verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
