from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "reference_agent" / "facility_assessment_update"
REPLAY_PATH = EXAMPLE / "replay.py"
TASK = EXAMPLE / "task.yaml"
WORLD_STATE = EXAMPLE / "world_state_before.json"
SCENARIOS = (
    "success",
    "missing_evidence",
    "conflicting_evidence",
    "stale_evidence",
    "contradicted",
)


def _load_replay_module():
    spec = importlib.util.spec_from_file_location("reference_agent_replay", REPLAY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPLAY = _load_replay_module()


def _body(name: str) -> dict:
    return REPLAY.replay_scenario(name)["reference_agent"]


def test_reference_agent_fixed_inputs_are_strict_and_public_core_valid() -> None:
    document = load_geotask(TASK)
    errors = [
        item
        for item in validate_document(document)
        if item.get("severity", "error") == "error"
    ]
    assert errors == []
    state = load_world_state(json.loads(WORLD_STATE.read_text(encoding="utf-8")))
    assert state.world_state_id == "reference-agent-facility-assessment-state"
    assert state.revision == 1

    for name in SCENARIOS:
        payload = json.loads((EXAMPLE / "scenarios" / f"{name}.json").read_text(encoding="utf-8"))
        assert payload["scenario"]["id"] == name


def test_reference_agent_all_five_fixed_scenarios_match_acceptance_fields() -> None:
    for name in SCENARIOS:
        result = REPLAY.replay_scenario(name)
        REPLAY._assert_expected(name, result)


def test_reference_agent_success_is_eligible_but_never_executes() -> None:
    body = _body("success")
    assert body["evidence"]["state"] == "verified"
    assert body["verification"]["state"] == "satisfied"
    assert body["verification"]["distance_m"] == 70.0
    assert body["world_state_update"]["observation_state_materialized"] is True
    assert body["world_state_update"]["observation_state_revision"] == 2
    assert body["world_state_update"]["successor_materialized"] is True
    assert body["world_state_update"]["successor_revision"] == 3
    assert body["world_state_update"]["baseline_immutable"] is True
    assert body["registered_impact_bundle"]["registered_artifacts_validated"] is True
    assert body["control_evaluation"]["state"] == "satisfied"
    assert body["decision_assurance"]["report_update_eligible"] is True
    assert body["decision_assurance"]["production_write_performed"] is False
    assert body["decision_assurance"]["production_report_refreshed"] is False
    assert body["decision_assurance"]["action_authorized"] is False
    assert body["decision_assurance"]["action_executed"] is False


def test_reference_agent_missing_stale_and_conflict_fail_closed() -> None:
    for name, evidence_state, verification_state in (
        ("missing_evidence", "missing", "unverifiable"),
        ("stale_evidence", "stale", "unverifiable"),
        ("conflicting_evidence", "conflicted", "conflicted"),
    ):
        body = _body(name)
        assert body["evidence"]["state"] == evidence_state
        assert body["verification"]["state"] == verification_state
        assert body["world_state_update"]["successor_materialized"] is False
        assert body["control_evaluation"]["state"] == "unknown"
        assert body["evidence_request"]["state"] == "required"
        assert body["decision_assurance"]["report_update_eligible"] is False
        assert body["decision_assurance"]["production_report_refreshed"] is False
        assert body["decision_assurance"]["action_executed"] is False


def test_reference_agent_contradiction_materializes_fact_but_keeps_report_blocked() -> None:
    body = _body("contradicted")
    assert body["evidence"]["state"] == "verified"
    assert body["verification"]["state"] == "contradicted"
    assert body["verification"]["distance_m"] == 30.0
    assert body["world_state_update"]["successor_materialized"] is True
    successor = body["world_state_update"]["successor"]["world_state"]
    assessment = next(item for item in successor["objects"] if item["id"] == "assessment-FAC-001")
    clearance = next(
        item for item in assessment["attributes"] if item["name"] == "obstacle_clearance_pass"
    )
    assert clearance["value"] is False
    assert body["control_evaluation"]["state"] == "blocked"
    assert body["decision_assurance"]["report_update_eligible"] is False
    assert body["decision_assurance"]["action_executed"] is False


def test_reference_agent_impact_scope_is_bounded_and_preserves_unrelated_sections() -> None:
    body = _body("success")
    impact = body["impact_scope"]
    affected = {item["identity"] for item in impact["affected_nodes"]}
    assert affected == {
        "/objects/mapped-obstacle-01/attributes/position_xy/value",
        "obstacle_distance_m",
        "assessment-FAC-001.obstacle_clearance_pass",
        "report-v4.safety.obstacle_clearance",
        "review:FAC-001:obstacle-clearance",
    }
    assert set(impact["reused_nodes"]) == {
        "assessment-FAC-001.accessibility_score",
        "assessment-FAC-001.service_capability_score",
        "report-v4.operator_summary",
    }
    assert impact["automatic_dependency_discovery"] is False
    assert impact["automatic_global_recompute"] is False


def test_reference_agent_uses_registered_discrepancy_correction_and_impact_artifacts() -> None:
    body = _body("success")
    bundle = body["registered_impact_bundle"]
    assert bundle["registered_artifacts_validated"] is True
    assert bundle["discrepancy_report"]["discrepancy_report"]["state"] == "confirmed"
    assert bundle["correction_request"]["correction_request"]["state"] == "required"
    graph = bundle["impact_graph"]["impact_graph"]
    assert graph["state"] == "blocked"
    assert graph["blocked_outputs"] == ["assessment_refresh", "report_refresh"]
    assert {item["identity"] for item in graph["nodes"] if item["kind"] == "world_state_path"} == {
        "/objects/assessment-FAC-001/attributes/obstacle_distance_m/value",
        "/objects/assessment-FAC-001/attributes/obstacle_clearance_pass/value",
    }
    assert len(bundle["discrepancy_report_sha256"]) == 64
    assert len(bundle["correction_request_sha256"]) == 64
    assert len(bundle["impact_graph_sha256"]) == 64


def test_reference_agent_accepts_a_developer_supplied_scenario_file(tmp_path: Path) -> None:
    payload = json.loads((EXAMPLE / "scenarios" / "success.json").read_text(encoding="utf-8"))
    payload["scenario"]["id"] = "developer-60m"
    payload["scenario"]["evidence"][0]["coordinates"] = [60, 0]
    payload["scenario"].pop("expected", None)
    scenario_path = tmp_path / "developer-60m.json"
    scenario_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = REPLAY.replay_scenario(scenario_path=scenario_path)
    body = result["reference_agent"]
    assert body["scenario"] == "developer-60m"
    assert body["verification"]["distance_m"] == 60.0
    assert body["world_state_update"]["observation_state_revision"] == 2
    assert body["world_state_update"]["successor_revision"] == 3
    assert body["registered_impact_bundle"]["registered_artifacts_validated"] is True
    assert body["decision_assurance"]["report_update_eligible"] is True
    assert body["decision_assurance"]["production_report_refreshed"] is False


def test_reference_agent_replay_is_deterministic() -> None:
    for name in SCENARIOS:
        first = REPLAY.replay_scenario(name)
        second = REPLAY.replay_scenario(name)
        assert first == second
        assert first["reference_agent"]["replay_fingerprint"] == second["reference_agent"][
            "replay_fingerprint"
        ]


def test_reference_agent_evidence_traceability_preserves_source_and_version() -> None:
    body = _body("success")
    observation = body["evidence"]["observations"][0]
    assert observation["source_reference"] == "map:fictional/obstacle/update-success-v5"
    assert observation["producer_version"] == "5.0"
    assert len(observation["content_sha256"]) == 64
    successor = body["world_state_update"]["successor"]["world_state"]
    assert "map:fictional/obstacle/update-success-v5" in successor["evidence_refs"]
    assert "obs-map-obstacle-success" in successor["observation_refs"]
