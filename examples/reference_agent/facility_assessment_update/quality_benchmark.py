#!/usr/bin/env python3
"""Product-level Verification Quality Benchmark for the GeoTask Reference Agent.

This benchmark measures the current public Reference Agent workflow, not generic
automatic dependency discovery. It uses only fixed fictional scenarios and the
public GeoTask Core path already exercised by ``replay.py``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from replay import replay_scenario


BENCHMARK_ID = "geotask.reference-agent-verification-quality"
BENCHMARK_VERSION = "0.1"
ERROR_SCENARIOS = (
    "missing_evidence",
    "conflicting_evidence",
    "stale_evidence",
    "contradicted",
)
CLEAN_SCENARIOS = ("success",)
CORRECTION_SCENARIOS = ("success", "contradicted")
EXPECTED_AFFECTED_SCOPE = {
    "/objects/mapped-obstacle-01/attributes/position_xy/value",
    "obstacle_distance_m",
    "assessment-FAC-001.obstacle_clearance_pass",
    "report-v4.safety.obstacle_clearance",
    "review:FAC-001:obstacle-clearance",
}
EXPECTED_REUSED_SCOPE = {
    "assessment-FAC-001.accessibility_score",
    "assessment-FAC-001.service_capability_score",
    "report-v4.operator_summary",
}


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    return value


def _attribute_value(world_state_wrapper: object, object_id: str, name: str) -> object:
    wrapper = _mapping(world_state_wrapper, "successor")
    state = _mapping(wrapper.get("world_state"), "successor.world_state")
    objects = state.get("objects")
    if not isinstance(objects, list):
        raise ValueError("successor.world_state.objects must be an array")
    for raw_object in objects:
        obj = _mapping(raw_object, "successor.world_state.objects[]")
        if obj.get("id") != object_id:
            continue
        attributes = obj.get("attributes")
        if not isinstance(attributes, list):
            raise ValueError(f"{object_id}.attributes must be an array")
        for raw_attribute in attributes:
            attribute = _mapping(raw_attribute, f"{object_id}.attributes[]")
            if attribute.get("name") == name:
                return attribute.get("value")
    raise ValueError(f"attribute not found: {object_id}.{name}")


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise ValueError("benchmark denominator must be positive")
    return round(100.0 * numerator / denominator, 2)


def run_quality_benchmark() -> dict[str, Any]:
    scenario_names = tuple(dict.fromkeys(ERROR_SCENARIOS + CLEAN_SCENARIOS + CORRECTION_SCENARIOS))
    results = {name: replay_scenario(name)["reference_agent"] for name in scenario_names}

    error_rows: list[dict[str, Any]] = []
    detected_errors = 0
    for name in ERROR_SCENARIOS:
        body = _mapping(results[name], name)
        verification = _mapping(body.get("verification"), f"{name}.verification")
        decision = _mapping(body.get("decision_assurance"), f"{name}.decision_assurance")
        state = str(verification.get("state"))
        detected = (
            state in {"unverifiable", "conflicted", "contradicted"}
            and decision.get("report_update_eligible") is False
        )
        detected_errors += int(detected)
        error_rows.append(
            {
                "scenario": name,
                "verification_state": state,
                "report_update_eligible": decision.get("report_update_eligible"),
                "error_detected": detected,
            }
        )

    clean_rows: list[dict[str, Any]] = []
    false_blocks = 0
    for name in CLEAN_SCENARIOS:
        body = _mapping(results[name], name)
        verification = _mapping(body.get("verification"), f"{name}.verification")
        decision = _mapping(body.get("decision_assurance"), f"{name}.decision_assurance")
        falsely_blocked = not (
            verification.get("state") == "satisfied"
            and decision.get("report_update_eligible") is True
        )
        false_blocks += int(falsely_blocked)
        clean_rows.append(
            {
                "scenario": name,
                "verification_state": verification.get("state"),
                "report_update_eligible": decision.get("report_update_eligible"),
                "false_block": falsely_blocked,
            }
        )

    correction_rows: list[dict[str, Any]] = []
    successful_corrections = 0
    scope_true_positive = 0
    scope_predicted = 0
    scope_gold = 0
    scope_recall_true_positive = 0

    for name in CORRECTION_SCENARIOS:
        body = _mapping(results[name], name)
        verification = _mapping(body.get("verification"), f"{name}.verification")
        update = _mapping(body.get("world_state_update"), f"{name}.world_state_update")
        impact = _mapping(body.get("impact_scope"), f"{name}.impact_scope")
        decision = _mapping(body.get("decision_assurance"), f"{name}.decision_assurance")

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
        expected_distance = verification.get("distance_m")
        expected_clearance = bool(
            isinstance(expected_distance, (int, float))
            and expected_distance >= float(verification.get("min_obstacle_distance_m", 0))
        )
        correction_success = all(
            (
                update.get("baseline_immutable") is True,
                update.get("successor_materialized") is True,
                update.get("successor_revision") == 3,
                successor_distance == expected_distance,
                successor_clearance is expected_clearance,
                decision.get("production_write_performed") is False,
                decision.get("production_report_refreshed") is False,
                decision.get("action_executed") is False,
            )
        )
        successful_corrections += int(correction_success)

        affected_nodes = impact.get("affected_nodes")
        if not isinstance(affected_nodes, list):
            raise ValueError(f"{name}.impact_scope.affected_nodes must be an array")
        predicted_scope = {
            str(_mapping(node, f"{name}.impact_scope.affected_nodes[]").get("identity"))
            for node in affected_nodes
        }
        reused_scope_raw = impact.get("reused_nodes")
        if not isinstance(reused_scope_raw, list):
            raise ValueError(f"{name}.impact_scope.reused_nodes must be an array")
        reused_scope = {str(item) for item in reused_scope_raw}
        intersection = predicted_scope & EXPECTED_AFFECTED_SCOPE
        scope_true_positive += len(intersection)
        scope_recall_true_positive += len(intersection)
        scope_predicted += len(predicted_scope)
        scope_gold += len(EXPECTED_AFFECTED_SCOPE)

        correction_rows.append(
            {
                "scenario": name,
                "correction_success": correction_success,
                "successor_distance_m": successor_distance,
                "successor_clearance_pass": successor_clearance,
                "predicted_affected_scope": sorted(predicted_scope),
                "expected_affected_scope": sorted(EXPECTED_AFFECTED_SCOPE),
                "reused_scope": sorted(reused_scope),
                "expected_reused_scope": sorted(EXPECTED_REUSED_SCOPE),
                "scope_exact_match": predicted_scope == EXPECTED_AFFECTED_SCOPE,
                "reused_scope_exact_match": reused_scope == EXPECTED_REUSED_SCOPE,
            }
        )

    safety_boundary_passes = 0
    safety_rows: list[dict[str, Any]] = []
    for name, raw in results.items():
        body = _mapping(raw, name)
        decision = _mapping(body.get("decision_assurance"), f"{name}.decision_assurance")
        boundary_pass = all(
            (
                decision.get("production_write_performed") is False,
                decision.get("production_report_refreshed") is False,
                decision.get("action_authorized") is False,
                decision.get("action_executed") is False,
            )
        )
        safety_boundary_passes += int(boundary_pass)
        safety_rows.append({"scenario": name, "boundary_pass": boundary_pass})

    error_count = len(ERROR_SCENARIOS)
    clean_count = len(CLEAN_SCENARIOS)
    correction_count = len(CORRECTION_SCENARIOS)
    total_safety_cases = len(results)
    missed_errors = error_count - detected_errors

    metrics = {
        "error_detection_rate_pct": _percent(detected_errors, error_count),
        "missed_error_rate_pct": _percent(missed_errors, error_count),
        "false_blocking_rate_pct": _percent(false_blocks, clean_count),
        "correction_success_rate_pct": _percent(successful_corrections, correction_count),
        "impact_scope_precision_pct": _percent(scope_true_positive, scope_predicted),
        "impact_scope_recall_pct": _percent(scope_recall_true_positive, scope_gold),
        "side_effect_boundary_pass_rate_pct": _percent(
            safety_boundary_passes,
            total_safety_cases,
        ),
    }
    valid = metrics == {
        "error_detection_rate_pct": 100.0,
        "missed_error_rate_pct": 0.0,
        "false_blocking_rate_pct": 0.0,
        "correction_success_rate_pct": 100.0,
        "impact_scope_precision_pct": 100.0,
        "impact_scope_recall_pct": 100.0,
        "side_effect_boundary_pass_rate_pct": 100.0,
    }

    return {
        "verification_quality_benchmark": {
            "schema_version": "0.1",
            "benchmark_id": BENCHMARK_ID,
            "benchmark_version": BENCHMARK_VERSION,
            "state": "passed" if valid else "failed",
            "valid": valid,
            "metrics": metrics,
            "counts": {
                "known_error_cases": error_count,
                "clean_cases": clean_count,
                "correction_cases": correction_count,
                "safety_boundary_cases": total_safety_cases,
            },
            "cases": {
                "error_detection": error_rows,
                "false_blocking": clean_rows,
                "correction_and_scope": correction_rows,
                "side_effect_boundary": safety_rows,
            },
            "boundaries": {
                "fictional_data_only": True,
                "network_used": False,
                "model_called": False,
                "production_system_accessed": False,
                "production_write_performed": False,
                "automatic_dependency_discovery": False,
                "automatic_global_recompute": False,
                "metric_scope": "reference_agent_v0.1_fixed_scenarios",
                "cross_domain_generalization_claimed": False,
            },
        }
    }


def _render_text(report: Mapping[str, Any]) -> str:
    body = _mapping(report.get("verification_quality_benchmark"), "verification_quality_benchmark")
    metrics = _mapping(body.get("metrics"), "verification_quality_benchmark.metrics")
    lines = [
        "GeoTask Verification Quality Benchmark v0.1",
        f"state: {body['state']}",
        f"error detection rate: {metrics['error_detection_rate_pct']:.2f}%",
        f"missed error rate: {metrics['missed_error_rate_pct']:.2f}%",
        f"false blocking rate: {metrics['false_blocking_rate_pct']:.2f}%",
        f"correction success rate: {metrics['correction_success_rate_pct']:.2f}%",
        f"impact scope precision: {metrics['impact_scope_precision_pct']:.2f}%",
        f"impact scope recall: {metrics['impact_scope_recall_pct']:.2f}%",
        f"side-effect boundary pass rate: {metrics['side_effect_boundary_pass_rate_pct']:.2f}%",
        "boundary: fixed fictional Reference Agent scenarios; no automatic dependency discovery claim",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run_quality_benchmark()
    rendered = (
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.format == "json"
        else _render_text(report)
    )
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["verification_quality_benchmark"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
