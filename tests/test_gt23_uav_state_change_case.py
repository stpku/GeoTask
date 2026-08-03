from __future__ import annotations

import copy
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.v1.observation import load_observation
from geotask_core.v1.state_transition import (
    StateTransitionFormatError,
    load_state_transition,
    validate_state_transition_bindings,
)
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
SCENARIO = CORE / "gt23_uav_state_change.json"
BASE_STATE = CORE / "world_state_uav_alpha_initial_gt22.json"
SUCCESSOR_STATE = CORE / "world_state_uav_alpha_after_five_minutes_gt23.json"
TRANSITION = CORE / "state_transition_uav_alpha_gt23.json"
BUILDER_PATH = CORE / "gt23_build_state_change.py"
WORLD_STATE_SCHEMA = ROOT / "schemas" / "geotask-world-state-v0.1.schema.json"
TRANSITION_SCHEMA = ROOT / "schemas" / "geotask-state-transition-v0.1.schema.json"


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt23_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


def _payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_case(tmp_path: Path) -> Path:
    for filename in (
        "gt23_uav_state_change.json",
        "world_state_uav_alpha_initial_gt22.json",
        "observation_uav_alpha_position_gt23.json",
        "observation_uav_alpha_battery_gt23.json",
    ):
        shutil.copy2(CORE / filename, tmp_path / filename)
    return tmp_path / "gt23_uav_state_change.json"


def _attribute_value(state, name: str):
    item = next(obj for obj in state.objects if obj.id == "uav-alpha")
    return next(attribute.value for attribute in item.attributes if attribute.name == name)


def test_gt23_sources_successor_and_transition_are_strictly_valid() -> None:
    scenario = _payload(SCENARIO)["scenario"]
    observations = [
        load_observation(_payload(CORE / filename)) for filename in scenario["observations"]
    ]
    base = load_world_state(_payload(BASE_STATE))
    successor = load_world_state(_payload(SUCCESSOR_STATE))
    transition = load_state_transition(_payload(TRANSITION))

    Draft202012Validator(_payload(WORLD_STATE_SCHEMA)).validate(successor.to_dict())
    Draft202012Validator(_payload(TRANSITION_SCHEMA)).validate(transition.to_dict())
    validate_state_transition_bindings(transition, base, successor)

    assert [item.observation_id for item in observations] == [
        "obs-uav-alpha-position-gt23",
        "obs-uav-alpha-battery-gt23",
    ]
    assert successor.revision == 2
    assert transition.from_state.revision == 1
    assert transition.to_state.revision == 2
    assert len(transition.changes) == 3


def test_gt23_builder_reproduces_fixed_snapshots_and_declared_changes() -> None:
    scenario = _payload(SCENARIO)["scenario"]
    expected = scenario["expected"]
    successor, transition = BUILDER.build_gt23_state_change(SCENARIO)

    assert successor.to_dict() == _payload(SUCCESSOR_STATE)
    assert transition.to_dict() == _payload(TRANSITION)
    assert successor.semantic_fingerprint() == expected["successor_semantic_fingerprint"]
    assert transition.semantic_fingerprint() == expected["transition_semantic_fingerprint"]
    assert len(transition.changes) == expected["transition_change_count"]
    assert _attribute_value(successor, "position_local_enu") == expected["after_position"]
    assert _attribute_value(successor, "battery_percent") == expected[
        "after_battery_percent"
    ]

    from_time = datetime.fromisoformat(transition.from_state.as_of)
    to_time = datetime.fromisoformat(transition.to_state.as_of)
    assert int((to_time - from_time).total_seconds()) == expected["elapsed_seconds"]


def test_gt23_build_is_independent_of_observation_file_order() -> None:
    scenario = _payload(SCENARIO)["scenario"]
    normal_state, normal_transition = BUILDER.build_gt23_state_change(SCENARIO)
    reversed_state, reversed_transition = BUILDER.build_gt23_state_change(
        SCENARIO,
        observation_filenames=tuple(reversed(scenario["observations"])),
    )

    assert reversed_state.to_dict() == normal_state.to_dict()
    assert reversed_transition.to_dict() == normal_transition.to_dict()


def test_gt23_fails_closed_when_one_claim_is_not_mapped(tmp_path: Path) -> None:
    scenario_path = _copy_case(tmp_path)
    payload = _payload(scenario_path)
    payload["scenario"]["mappings"].pop()
    scenario_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    with pytest.raises(BUILDER.GT23BuildError, match="explicit claim coverage mismatch"):
        BUILDER.build_gt23_state_change(scenario_path)


def test_gt23_fails_closed_on_unknown_target_attribute(tmp_path: Path) -> None:
    scenario_path = _copy_case(tmp_path)
    payload = _payload(scenario_path)
    payload["scenario"]["mappings"][0]["target_path"] = (
        "/objects/uav-alpha/attributes/imaginary_position"
    )
    scenario_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    with pytest.raises(BUILDER.GT23BuildError, match="must exist exactly once"):
        BUILDER.build_gt23_state_change(scenario_path)


def test_gt23_transition_binding_rejects_a_tampered_successor() -> None:
    transition = load_state_transition(_payload(TRANSITION))
    base = load_world_state(_payload(BASE_STATE))
    tampered = copy.deepcopy(_payload(SUCCESSOR_STATE))
    for attribute in tampered["world_state"]["objects"][0]["attributes"]:
        if attribute["name"] == "battery_percent":
            attribute["value"] = 51
    tampered_successor = load_world_state(tampered)

    with pytest.raises(StateTransitionFormatError, match="semantic_fingerprint"):
        validate_state_transition_bindings(transition, base, tampered_successor)
