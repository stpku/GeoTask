"""GT32 progressive takeoff-authorization case tests."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from geotask_core.v1.control_evaluation import load_control_evaluation


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
BUILDER = CORE / "gt32_build_progressive_takeoff_authorization.py"
SCENARIO = CORE / "gt32_progressive_takeoff_authorization.json"
FINAL_CONTROL = CORE / "takeoff_authorization_control_evaluation_gt32.json"
EVIDENCE = (
    CORE / "authorization_evidence_airspace_gt32.json",
    CORE / "authorization_evidence_operator_gt32.json",
    CORE / "authorization_evidence_departure_site_gt32.json",
    CORE / "authorization_evidence_weather_release_gt32.json",
    CORE / "authorization_evidence_mission_gt32.json",
)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt32_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gt32_progressively_removes_exactly_one_unknown_authorization() -> None:
    scenario = _json(SCENARIO)["scenario"]
    steps = scenario["steps"]
    assert [len(item["unknown_identifiers"]) for item in steps] == [4, 3, 2, 1, 0]
    assert [item["control_state"] for item in steps] == [
        "unknown",
        "unknown",
        "unknown",
        "unknown",
        "satisfied",
    ]
    assert [item["authorization_field"] for item in steps] == scenario[
        "authorization_order"
    ]
    for before, after in zip(steps, steps[1:]):
        assert len(before["remaining_authorizations"]) - 1 == len(
            after["remaining_authorizations"]
        )


def test_gt32_keeps_takeoff_outputs_blocked_until_the_fifth_record() -> None:
    steps = _json(SCENARIO)["scenario"]["steps"]
    for step in steps[:-1]:
        assert step["blocked_outputs"] == [
            "automatic_takeoff_authorization",
            "takeoff_command",
        ]
        assert step["eligible_outputs"] == []
        assert step["gate_satisfied"] is None
        assert step["action_executed"] is False
    assert steps[-1]["blocked_outputs"] == []
    assert steps[-1]["eligible_outputs"] == [
        "automatic_takeoff_authorization",
        "takeoff_command",
    ]
    assert steps[-1]["gate_satisfied"] is True
    assert steps[-1]["action_executed"] is False


def test_gt32_final_control_is_registered_and_non_executing() -> None:
    control = load_control_evaluation(_json(FINAL_CONTROL))
    assert control.state == "satisfied"
    assert control.gate_satisfied is True
    assert control.unknown_identifiers == ()
    assert control.blocked_outputs == ()
    assert control.eligible_outputs == (
        "automatic_takeoff_authorization",
        "takeoff_command",
    )
    assert control.action_executed is False


def test_gt32_final_eligibility_does_not_claim_release_or_execution() -> None:
    scenario = _json(SCENARIO)["scenario"]
    assert scenario["final_gate"] == {
        "control_state": "satisfied",
        "gate_satisfied": True,
        "automatic_takeoff_authorization": "eligible",
        "takeoff_command": "eligible",
        "production_output_released": False,
        "command_sent": False,
        "action_authorized_by_core": False,
        "action_executed": False,
    }
    assert scenario["boundaries"] == {
        "all_authorization_values_caller_asserted": True,
        "external_truth_verified_by_core": False,
        "real_authority_contacted": False,
        "authorization_inferred": False,
        "production_output_released": False,
        "command_sent": False,
        "action_authorized_by_core": False,
        "action_executed": False,
    }


def test_gt32_evidence_packets_are_fictional_scoped_and_side_effect_free() -> None:
    fields: list[str] = []
    for path in EVIDENCE:
        body = _json(path)["authorization_evidence"]
        fields.append(body["authorization_field"])
        assert body["authorization_value"] is True
        assert body["caller_asserted"] is True
        assert body["fictional_record"] is True
        assert body["external_truth_verified_by_core"] is False
        assert body["real_authority_contacted"] is False
        assert body["production_output_released"] is False
        assert body["command_sent"] is False
        assert body["action_authorized_by_core"] is False
        assert body["action_executed"] is False
    assert fields == _json(SCENARIO)["scenario"]["authorization_order"]
    assert len(set(fields)) == 5


def test_gt32_fixed_hashes_bind_gt28_gt31_evidence_and_final_control() -> None:
    expected = _json(SCENARIO)["scenario"]["sha256"]
    paths = {
        "task": CORE / "gt28_uav_takeoff_authorization_gate.yaml",
        "execution_result": CORE / "takeoff_preflight_execution_result_gt28.json",
        "initial_control_evaluation": CORE
        / "takeoff_authorization_control_evaluation_gt28.json",
        "gt31_assurance_evaluation": CORE
        / "assurance_evaluation_human_weather_adjudication_gt31.json",
        "gt31_scenario": CORE / "gt31_human_weather_adjudication.json",
        "authorization_evidence_airspace_authorized": EVIDENCE[0],
        "authorization_evidence_operator_authorized": EVIDENCE[1],
        "authorization_evidence_departure_site_authorized": EVIDENCE[2],
        "authorization_evidence_weather_release_authorized": EVIDENCE[3],
        "authorization_evidence_mission_authorized": EVIDENCE[4],
        "final_control_evaluation": FINAL_CONTROL,
    }
    assert {name: _sha(path) for name, path in paths.items()} == expected


def test_gt32_builder_reproduces_all_fixed_outputs() -> None:
    before = {path.name: path.read_bytes() for path in CORE.glob("*gt32.json")}
    _load_builder().build()
    after = {path.name: path.read_bytes() for path in CORE.glob("*gt32.json")}
    assert after == before


def test_gt32_missing_last_record_keeps_gate_unknown_and_blocked() -> None:
    module = _load_builder()
    payloads = [_json(path) for path in EVIDENCE[:-1]]
    evaluations = module.evaluate_authorization_sequence(payloads)
    final = evaluations[-1]
    assert final.state == "unknown"
    assert final.unknown_identifiers == ("mission_authorized",)
    assert final.blocked_outputs == (
        "automatic_takeoff_authorization",
        "takeoff_command",
    )
    assert final.eligible_outputs == ()
    assert final.action_executed is False


def test_gt32_explicit_false_authorization_blocks_without_becoming_unknown() -> None:
    module = _load_builder()
    payloads = [_json(path) for path in EVIDENCE]
    payloads[-1] = copy.deepcopy(payloads[-1])
    payloads[-1]["authorization_evidence"]["authorization_value"] = False
    final = module.evaluate_authorization_sequence(payloads)[-1]
    assert final.state == "blocked"
    assert final.gate_satisfied is False
    assert final.unknown_identifiers == ()
    assert final.blocked_outputs == (
        "automatic_takeoff_authorization",
        "takeoff_command",
    )
    assert final.eligible_outputs == ()
    assert final.action_executed is False


def test_gt32_duplicate_authorization_field_fails_closed() -> None:
    module = _load_builder()
    payloads = [_json(path) for path in EVIDENCE]
    payloads[1] = copy.deepcopy(payloads[1])
    payloads[1]["authorization_evidence"]["authorization_field"] = (
        "airspace_authorized"
    )
    with pytest.raises(module.GT32BuildError, match="duplicate authorization field"):
        module.evaluate_authorization_sequence(payloads)


def test_gt32_tampered_boundary_or_unknown_field_fails_closed() -> None:
    module = _load_builder()
    payload = _json(EVIDENCE[0])
    payload["authorization_evidence"]["command_sent"] = True
    with pytest.raises(module.GT32BuildError, match="command_sent"):
        module.validate_authorization_evidence(payload)

    payload = _json(EVIDENCE[0])
    payload["authorization_evidence"]["undeclared_priority"] = 1
    with pytest.raises(module.GT32BuildError, match="unknown field"):
        module.validate_authorization_evidence(payload)
