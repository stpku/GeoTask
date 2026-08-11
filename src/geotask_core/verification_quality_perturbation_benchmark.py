"""Deterministic synthetic perturbation benchmark for the Reference Agent.

This Product-Track benchmark expands the fixed five-scenario verification-quality
gate without claiming real-world statistical accuracy. Every case is fictional,
locally generated, replayed through the installed Reference Agent bundle, and
checked against an explicit deterministic oracle.
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping

from geotask_core.reference_agent_activation import (
    locate_reference_agent_bundle,
    replay_materialized_reference_agent,
)
from geotask_core.verification_quality_benchmark import (
    BENCHMARK_ID,
    EXPECTED_AFFECTED_SCOPE,
    EXPECTED_REUSED_SCOPE,
    _attribute_value,
    _mapping,
    _percent,
)


BENCHMARK_VERSION = "0.2"
EVALUATION_TIME = "2026-08-07T09:00:00+08:00"
MATERIALIZED_AT = "2026-08-07T09:00:05+08:00"
FRESH_UNTIL = "2026-08-07T10:00:00+08:00"
STALE_UNTIL = "2026-08-07T08:59:59+08:00"
LONG_STALE_UNTIL = "2026-08-07T08:56:00+08:00"
ERROR_STATES = {"unverifiable", "conflicted", "contradicted"}
EXPECTED_METRICS = {
    "outcome_match_rate_pct": 100.0,
    "error_detection_rate_pct": 100.0,
    "missed_error_rate_pct": 0.0,
    "false_blocking_rate_pct": 0.0,
    "control_gate_block_rate_pct": 100.0,
    "threshold_boundary_accuracy_pct": 100.0,
    "correction_success_rate_pct": 100.0,
    "impact_scope_precision_pct": 100.0,
    "impact_scope_recall_pct": 100.0,
    "deterministic_replay_pass_rate_pct": 100.0,
    "side_effect_boundary_pass_rate_pct": 100.0,
}


def _evidence(
    case_id: str,
    distance_m: float,
    *,
    suffix: str = "a",
    valid_until: str = FRESH_UNTIL,
) -> dict[str, Any]:
    return {
        "observation_id": f"obs-{case_id}-{suffix}",
        "source_reference": f"map:fictional/perturbation/{case_id}-{suffix}",
        "source_version": "1.0",
        "producer_id": f"fictional-perturbation-provider-{suffix}",
        "observed_at": "2026-08-07T08:55:00+08:00",
        "received_at": "2026-08-07T08:55:05+08:00",
        "valid_until": valid_until,
        "coordinates": [distance_m, 0],
    }


def _case(
    case_id: str,
    kind: str,
    *,
    threshold_m: float = 50.0,
    evidence: list[dict[str, Any]],
    expected_verification_state: str,
    expected_report_update_eligible: bool,
    human_review: bool | str = True,
    expected_distance_m: float | None = None,
) -> dict[str, Any]:
    scenario: dict[str, Any] = {
        "id": case_id,
        "evaluation_time": EVALUATION_TIME,
        "materialized_at": MATERIALIZED_AT,
        "min_obstacle_distance_m": threshold_m,
        "evidence": evidence,
    }
    if human_review != "missing":
        scenario["human_review_approved"] = human_review
    return {
        "case_id": case_id,
        "kind": kind,
        "scenario": scenario,
        "expected": {
            "verification_state": expected_verification_state,
            "report_update_eligible": expected_report_update_eligible,
            "distance_m": expected_distance_m,
            "threshold_m": threshold_m,
        },
    }


def build_perturbation_cases() -> list[dict[str, Any]]:
    """Build a fixed 34-case matrix without random sampling."""

    cases: list[dict[str, Any]] = []

    for threshold_m in (10.0, 25.0, 50.0, 100.0):
        for offset_m in (-0.01, 0.0, 0.01, 20.0):
            distance_m = round(threshold_m + offset_m, 2)
            offset_label = (
                f"{offset_m:+.2f}"
                .replace("+", "plus")
                .replace("-", "minus")
                .replace(".", "p")
            )
            case_id = f"threshold-{int(threshold_m)}-{offset_label}"
            satisfied = distance_m >= threshold_m
            cases.append(
                _case(
                    case_id,
                    "threshold_boundary",
                    threshold_m=threshold_m,
                    evidence=[_evidence(case_id, distance_m)],
                    expected_verification_state=(
                        "satisfied" if satisfied else "contradicted"
                    ),
                    expected_report_update_eligible=satisfied,
                    expected_distance_m=distance_m,
                )
            )

    for threshold_m in (10.0, 25.0, 50.0, 100.0):
        distance_m = threshold_m + 10.0
        for review_mode in (False, "missing"):
            label = "false" if review_mode is False else "missing"
            case_id = f"review-gate-{int(threshold_m)}-{label}"
            cases.append(
                _case(
                    case_id,
                    "control_gate",
                    threshold_m=threshold_m,
                    evidence=[_evidence(case_id, distance_m)],
                    expected_verification_state="satisfied",
                    expected_report_update_eligible=False,
                    human_review=review_mode,
                    expected_distance_m=distance_m,
                )
            )

    for distance_m in (30.0, 70.0):
        relation = "unsafe" if distance_m < 50.0 else "safe"
        stale_id = f"freshness-stale-{relation}"
        cases.append(
            _case(
                stale_id,
                "freshness",
                evidence=[_evidence(stale_id, distance_m, valid_until=STALE_UNTIL)],
                expected_verification_state="unverifiable",
                expected_report_update_eligible=False,
            )
        )
        long_stale_id = f"freshness-long-stale-{relation}"
        cases.append(
            _case(
                long_stale_id,
                "freshness",
                evidence=[
                    _evidence(
                        long_stale_id,
                        distance_m,
                        valid_until=LONG_STALE_UNTIL,
                    )
                ],
                expected_verification_state="unverifiable",
                expected_report_update_eligible=False,
            )
        )
        exact_id = f"freshness-exact-evaluation-{relation}"
        satisfied = distance_m >= 50.0
        cases.append(
            _case(
                exact_id,
                "freshness_boundary",
                evidence=[
                    _evidence(exact_id, distance_m, valid_until=EVALUATION_TIME)
                ],
                expected_verification_state=(
                    "satisfied" if satisfied else "contradicted"
                ),
                expected_report_update_eligible=satisfied,
                expected_distance_m=distance_m,
            )
        )

    for index, (distance_a, distance_b) in enumerate(
        ((70.0, 30.0), (51.0, 49.0)),
        start=1,
    ):
        case_id = f"conflict-pair-{index}"
        cases.append(
            _case(
                case_id,
                "conflict",
                evidence=[
                    _evidence(case_id, distance_a, suffix="a"),
                    _evidence(case_id, distance_b, suffix="b"),
                ],
                expected_verification_state="conflicted",
                expected_report_update_eligible=False,
            )
        )

    for distance_m in (30.0, 70.0):
        relation = "unsafe" if distance_m < 50.0 else "safe"
        case_id = f"consistent-multisource-{relation}"
        satisfied = distance_m >= 50.0
        cases.append(
            _case(
                case_id,
                "consistent_multisource",
                evidence=[
                    _evidence(case_id, distance_m, suffix="a"),
                    _evidence(case_id, distance_m, suffix="b"),
                ],
                expected_verification_state=(
                    "satisfied" if satisfied else "contradicted"
                ),
                expected_report_update_eligible=satisfied,
                expected_distance_m=distance_m,
            )
        )

    if len(cases) != 34:
        raise RuntimeError(f"unexpected perturbation case count: {len(cases)}")
    return cases


def _scope_sets(
    body: Mapping[str, Any],
    case_id: str,
) -> tuple[set[str], set[str]]:
    impact = _mapping(body.get("impact_scope"), f"{case_id}.impact_scope")
    affected_nodes = impact.get("affected_nodes")
    if not isinstance(affected_nodes, list):
        raise ValueError(f"{case_id}.impact_scope.affected_nodes must be an array")
    predicted = {
        str(_mapping(node, f"{case_id}.impact_scope.affected_nodes[]").get("identity"))
        for node in affected_nodes
    }
    reused_raw = impact.get("reused_nodes")
    if not isinstance(reused_raw, list):
        raise ValueError(f"{case_id}.impact_scope.reused_nodes must be an array")
    return predicted, {str(item) for item in reused_raw}


def run_verification_quality_perturbation_benchmark() -> dict[str, Any]:
    """Run the deterministic 34-case perturbation matrix from the installed bundle."""

    bundle = locate_reference_agent_bundle()
    cases = build_perturbation_cases()
    rows: list[dict[str, Any]] = []

    outcome_matches = 0
    detected_errors = 0
    expected_error_cases = 0
    false_blocks = 0
    clean_cases = 0
    control_gate_passes = 0
    control_gate_cases = 0
    successful_corrections = 0
    correction_cases = 0
    threshold_matches = 0
    threshold_cases = 0
    deterministic_replays = 0
    side_effect_passes = 0
    scope_true_positive = 0
    scope_predicted = 0
    scope_gold = 0

    with tempfile.TemporaryDirectory(prefix="geotask-quality-v0-2-") as temporary:
        temp_dir = Path(temporary)
        for case in cases:
            case_id = str(case["case_id"])
            expected = _mapping(case["expected"], f"{case_id}.expected")
            scenario_path = temp_dir / f"{case_id}.json"
            scenario_path.write_text(
                json.dumps(
                    {"scenario": case["scenario"]},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            first = _mapping(
                replay_materialized_reference_agent(
                    bundle,
                    scenario_path=scenario_path,
                ).get("reference_agent"),
                case_id,
            )
            second = _mapping(
                replay_materialized_reference_agent(
                    bundle,
                    scenario_path=scenario_path,
                ).get("reference_agent"),
                case_id,
            )
            verification = _mapping(
                first.get("verification"),
                f"{case_id}.verification",
            )
            decision = _mapping(
                first.get("decision_assurance"),
                f"{case_id}.decision_assurance",
            )
            update = _mapping(
                first.get("world_state_update"),
                f"{case_id}.world_state_update",
            )

            actual_state = str(verification.get("state"))
            actual_eligible = decision.get("report_update_eligible") is True
            expected_state = str(expected.get("verification_state"))
            expected_eligible = expected.get("report_update_eligible") is True
            outcome_match = (
                actual_state == expected_state
                and actual_eligible == expected_eligible
            )
            outcome_matches += int(outcome_match)

            expects_error = expected_state in ERROR_STATES
            if expects_error:
                expected_error_cases += 1
                detected_errors += int(
                    actual_state in ERROR_STATES and not actual_eligible
                )

            is_clean = expected_state == "satisfied" and expected_eligible
            if is_clean:
                clean_cases += 1
                false_blocks += int(
                    not (actual_state == "satisfied" and actual_eligible)
                )

            if case["kind"] == "control_gate":
                control_gate_cases += 1
                control_gate_passes += int(
                    actual_state == "satisfied"
                    and not actual_eligible
                    and decision.get("action_authorized") is False
                    and decision.get("action_executed") is False
                )

            if case["kind"] == "threshold_boundary":
                threshold_cases += 1
                threshold_matches += int(outcome_match)

            expected_distance = expected.get("distance_m")
            correction_success: bool | None = None
            scope_exact_match: bool | None = None
            reused_scope_exact_match: bool | None = None
            if expected_distance is not None:
                correction_cases += 1
                successor = update.get("successor")
                successor_distance = _attribute_value(
                    successor,
                    "assessment-FAC-001",
                    "obstacle_distance_m",
                )
                successor_clearance = _attribute_value(
                    successor,
                    "assessment-FAC-001",
                    "obstacle_clearance_pass",
                )
                threshold_m = float(expected["threshold_m"])
                distance_m = float(expected_distance)
                expected_clearance = distance_m >= threshold_m
                correction_success = all(
                    (
                        update.get("baseline_immutable") is True,
                        update.get("successor_materialized") is True,
                        update.get("successor_revision") == 3,
                        isinstance(successor_distance, (int, float)),
                        math.isclose(
                            float(successor_distance),
                            distance_m,
                            rel_tol=0.0,
                            abs_tol=1e-9,
                        ),
                        successor_clearance is expected_clearance,
                        decision.get("production_write_performed") is False,
                        decision.get("production_report_refreshed") is False,
                        decision.get("action_authorized") is False,
                        decision.get("action_executed") is False,
                    )
                )
                successful_corrections += int(correction_success)

                predicted_scope, reused_scope = _scope_sets(first, case_id)
                intersection = predicted_scope & EXPECTED_AFFECTED_SCOPE
                scope_true_positive += len(intersection)
                scope_predicted += len(predicted_scope)
                scope_gold += len(EXPECTED_AFFECTED_SCOPE)
                scope_exact_match = predicted_scope == EXPECTED_AFFECTED_SCOPE
                reused_scope_exact_match = reused_scope == EXPECTED_REUSED_SCOPE

            replay_stable = (
                first.get("replay_fingerprint")
                == second.get("replay_fingerprint")
            )
            deterministic_replays += int(replay_stable)
            side_effect_pass = all(
                (
                    decision.get("production_write_performed") is False,
                    decision.get("production_report_refreshed") is False,
                    decision.get("action_authorized") is False,
                    decision.get("action_executed") is False,
                )
            )
            side_effect_passes += int(side_effect_pass)

            rows.append(
                {
                    "case_id": case_id,
                    "kind": case["kind"],
                    "expected_verification_state": expected_state,
                    "actual_verification_state": actual_state,
                    "expected_report_update_eligible": expected_eligible,
                    "actual_report_update_eligible": actual_eligible,
                    "outcome_match": outcome_match,
                    "correction_success": correction_success,
                    "scope_exact_match": scope_exact_match,
                    "reused_scope_exact_match": reused_scope_exact_match,
                    "deterministic_replay": replay_stable,
                    "side_effect_boundary_pass": side_effect_pass,
                }
            )

    total_cases = len(cases)
    missed_errors = expected_error_cases - detected_errors
    metrics = {
        "outcome_match_rate_pct": _percent(outcome_matches, total_cases),
        "error_detection_rate_pct": _percent(
            detected_errors,
            expected_error_cases,
        ),
        "missed_error_rate_pct": _percent(
            missed_errors,
            expected_error_cases,
        ),
        "false_blocking_rate_pct": _percent(false_blocks, clean_cases),
        "control_gate_block_rate_pct": _percent(
            control_gate_passes,
            control_gate_cases,
        ),
        "threshold_boundary_accuracy_pct": _percent(
            threshold_matches,
            threshold_cases,
        ),
        "correction_success_rate_pct": _percent(
            successful_corrections,
            correction_cases,
        ),
        "impact_scope_precision_pct": _percent(
            scope_true_positive,
            scope_predicted,
        ),
        "impact_scope_recall_pct": _percent(
            scope_true_positive,
            scope_gold,
        ),
        "deterministic_replay_pass_rate_pct": _percent(
            deterministic_replays,
            total_cases,
        ),
        "side_effect_boundary_pass_rate_pct": _percent(
            side_effect_passes,
            total_cases,
        ),
    }
    valid = metrics == EXPECTED_METRICS

    return {
        "verification_quality_benchmark": {
            "schema_version": "0.1",
            "benchmark_id": BENCHMARK_ID,
            "benchmark_version": BENCHMARK_VERSION,
            "state": "passed" if valid else "failed",
            "valid": valid,
            "metrics": metrics,
            "counts": {
                "total_cases": total_cases,
                "known_error_cases": expected_error_cases,
                "clean_cases": clean_cases,
                "control_gate_cases": control_gate_cases,
                "threshold_boundary_cases": threshold_cases,
                "correction_cases": correction_cases,
                "deterministic_replay_cases": total_cases,
                "side_effect_boundary_cases": total_cases,
            },
            "cases": rows,
            "boundaries": {
                "fictional_data_only": True,
                "generated_synthetic_perturbations": True,
                "network_used": False,
                "model_called": False,
                "production_system_accessed": False,
                "production_write_performed": False,
                "automatic_dependency_discovery": False,
                "automatic_global_recompute": False,
                "metric_scope": (
                    "reference_agent_v0.1_deterministic_synthetic_perturbation_matrix"
                ),
                "real_world_accuracy_claimed": False,
                "cross_domain_generalization_claimed": False,
            },
        }
    }


def render_verification_quality_perturbation_text(
    report: Mapping[str, Any],
) -> str:
    body = _mapping(
        report.get("verification_quality_benchmark"),
        "verification_quality_benchmark",
    )
    metrics = _mapping(
        body.get("metrics"),
        "verification_quality_benchmark.metrics",
    )
    counts = _mapping(
        body.get("counts"),
        "verification_quality_benchmark.counts",
    )
    lines = [
        "GeoTask Verification Quality Benchmark v0.2",
        f"state: {body['state']}",
        f"synthetic perturbation cases: {counts['total_cases']}",
        f"outcome match rate: {metrics['outcome_match_rate_pct']:.2f}%",
        f"error detection rate: {metrics['error_detection_rate_pct']:.2f}%",
        f"missed error rate: {metrics['missed_error_rate_pct']:.2f}%",
        f"false blocking rate: {metrics['false_blocking_rate_pct']:.2f}%",
        f"control gate block rate: {metrics['control_gate_block_rate_pct']:.2f}%",
        f"threshold boundary accuracy: {metrics['threshold_boundary_accuracy_pct']:.2f}%",
        f"correction success rate: {metrics['correction_success_rate_pct']:.2f}%",
        f"impact scope precision: {metrics['impact_scope_precision_pct']:.2f}%",
        f"impact scope recall: {metrics['impact_scope_recall_pct']:.2f}%",
        (
            "deterministic replay pass rate: "
            f"{metrics['deterministic_replay_pass_rate_pct']:.2f}%"
        ),
        (
            "side-effect boundary pass rate: "
            f"{metrics['side_effect_boundary_pass_rate_pct']:.2f}%"
        ),
        (
            "boundary: deterministic fictional perturbations only; "
            "no real-world accuracy or cross-domain claim"
        ),
    ]
    return "\n".join(lines) + "\n"


__all__ = [
    "BENCHMARK_VERSION",
    "EXPECTED_METRICS",
    "build_perturbation_cases",
    "render_verification_quality_perturbation_text",
    "run_verification_quality_perturbation_benchmark",
]
