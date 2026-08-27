"""Offline proof that provider truncation must be resolved before scoring reduction.

This module replays recorded TC1-Real Phoenix planning evidence.  It does not
query the provider and does not promote a new GeoTask Core semantic.  Its only
purpose is to make one methodological failure reproducible:

    smaller response != smaller task context

when the response itself may have been truncated by the provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class TruncationProofResult:
    naive_task_vs_broad_byte_reduction_ratio: float
    naive_broad_return_fraction_of_complete: float
    naive_broad_undercount_ratio: float
    both_single_queries_hit_observed_ceiling: bool
    complete_broad_exceeds_single_query: bool
    reduction_scoreable: bool
    verdict: str


def _positive_int(value: object, name: str) -> int:
    result = int(value)
    if result <= 0:
        raise ValueError(f"{name} must be > 0")
    return result


def analyze_provider_truncation_evidence(
    evidence: Mapping[str, object],
) -> TruncationProofResult:
    """Compare ordinary bounded responses with the later complete broad retrieval.

    Reduction is deliberately fail-closed.  It is scoreable only if the evidence
    proves that ordinary responses did not hit the observed transfer ceiling and
    the complete broad cardinality does not exceed the ordinary broad response.
    The recorded real fixture should therefore reject the attractive naive byte
    reduction rather than turn it into a benchmark headline.
    """

    ordinary = evidence.get("ordinary_single_query")
    complete = evidence.get("ids_first_complete_broad")
    if not isinstance(ordinary, Mapping) or not isinstance(complete, Mapping):
        raise ValueError("evidence must contain ordinary and complete retrieval records")

    ceiling = _positive_int(
        ordinary.get("observed_transfer_ceiling_count"), "observed transfer ceiling"
    )
    broad = ordinary.get("broad")
    task = ordinary.get("task")
    if not isinstance(broad, Mapping) or not isinstance(task, Mapping):
        raise ValueError("ordinary evidence must contain broad and task records")

    broad_count = _positive_int(broad.get("feature_count"), "ordinary broad feature_count")
    task_count = _positive_int(task.get("feature_count"), "ordinary task feature_count")
    broad_bytes = _positive_int(broad.get("response_bytes"), "ordinary broad response_bytes")
    task_bytes = _positive_int(task.get("response_bytes"), "ordinary task response_bytes")
    complete_count = _positive_int(
        complete.get("feature_count"), "complete broad feature_count"
    )

    if complete.get("complete") is not True:
        raise ValueError("complete broad evidence must explicitly prove completeness")
    if task_bytes > broad_bytes:
        raise ValueError("recorded task response_bytes cannot exceed broad response_bytes")

    both_hit_ceiling = broad_count == ceiling and task_count == ceiling
    complete_exceeds_single = complete_count > broad_count

    naive_reduction = 1.0 - (task_bytes / broad_bytes)
    broad_return_fraction = broad_count / complete_count
    undercount_ratio = 1.0 - broad_return_fraction

    scoreable = not both_hit_ceiling and not complete_exceeds_single
    verdict = (
        "REJECT_NAIVE_REDUCTION_PROVIDER_TRUNCATED"
        if not scoreable
        else "ORDINARY_RESPONSE_COMPLETENESS_NOT_CONTRADICTED"
    )

    return TruncationProofResult(
        naive_task_vs_broad_byte_reduction_ratio=naive_reduction,
        naive_broad_return_fraction_of_complete=broad_return_fraction,
        naive_broad_undercount_ratio=undercount_ratio,
        both_single_queries_hit_observed_ceiling=both_hit_ceiling,
        complete_broad_exceeds_single_query=complete_exceeds_single,
        reduction_scoreable=scoreable,
        verdict=verdict,
    )
