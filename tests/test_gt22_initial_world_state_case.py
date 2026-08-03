from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.v1.observation import load_observation
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
SCENARIO = CORE / "gt22_initial_world_state_snapshot.json"
EXPECTED_STATE = CORE / "world_state_uav_alpha_initial_gt22.json"
WORLD_STATE_SCHEMA = ROOT / "schemas" / "geotask-world-state-v0.1.schema.json"
BUILDER_PATH = CORE / "gt22_build_initial_world_state.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("gt22_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


def _payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_case(tmp_path: Path) -> Path:
    for filename in (
        "gt22_initial_world_state_snapshot.json",
        "observation_uav_alpha_position_gt22.json",
        "observation_uav_alpha_battery_gt22.json",
    ):
        shutil.copy2(CORE / filename, tmp_path / filename)
    return tmp_path / "gt22_initial_world_state_snapshot.json"


def test_gt22_observations_and_expected_world_state_are_strictly_valid() -> None:
    scenario = _payload(SCENARIO)["scenario"]
    observations = [
        load_observation(_payload(CORE / filename))
        for filename in scenario["observations"]
    ]
    expected = load_world_state(_payload(EXPECTED_STATE))

    assert [item.observation_id for item in observations] == [
        "obs-uav-alpha-position-gt22",
        "obs-uav-alpha-battery-gt22",
    ]
    assert expected.revision == 1
    assert expected.world_state_id == "fictional-uav-alpha-initial-state"
    assert expected.observation_refs == (
        "obs-uav-alpha-battery-gt22",
        "obs-uav-alpha-position-gt22",
    )
    Draft202012Validator(_payload(WORLD_STATE_SCHEMA)).validate(expected.to_dict())


def test_gt22_builder_produces_the_fixed_referenceable_snapshot() -> None:
    scenario = _payload(SCENARIO)["scenario"]
    expected_payload = _payload(EXPECTED_STATE)
    state = BUILDER.build_initial_world_state(SCENARIO)

    assert state.to_dict() == expected_payload
    assert len(state.objects) == scenario["expected"]["object_count"]
    assert len(state.relations) == scenario["expected"]["relation_count"]
    assert [attribute.name for attribute in state.objects[0].attributes] == scenario[
        "expected"
    ]["attribute_names"]
    assert len(state.observation_refs) == scenario["expected"]["observation_ref_count"]
    assert len(state.evidence_refs) == scenario["expected"]["evidence_ref_count"]
    assert state.semantic_fingerprint() == scenario["expected"]["semantic_fingerprint"]
    assert load_world_state(state.to_dict()) == state


def test_gt22_construction_is_independent_of_observation_file_order() -> None:
    scenario = _payload(SCENARIO)["scenario"]
    normal = BUILDER.build_initial_world_state(SCENARIO)
    reversed_state = BUILDER.build_initial_world_state(
        SCENARIO,
        observation_filenames=tuple(reversed(scenario["observations"])),
    )

    assert reversed_state.to_dict() == normal.to_dict()
    assert reversed_state.semantic_fingerprint() == normal.semantic_fingerprint()


def test_gt22_fails_closed_when_one_claim_is_not_explicitly_mapped(tmp_path: Path) -> None:
    scenario_path = _copy_case(tmp_path)
    payload = _payload(scenario_path)
    payload["scenario"]["object_plan"][0]["claims"].pop()
    scenario_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    with pytest.raises(
        BUILDER.InitialSnapshotBuildError,
        match="explicit claim coverage mismatch",
    ):
        BUILDER.build_initial_world_state(scenario_path)


def test_gt22_fails_closed_instead_of_inferring_object_identity(tmp_path: Path) -> None:
    scenario_path = _copy_case(tmp_path)
    payload = _payload(scenario_path)
    payload["scenario"]["object_plan"][0]["id"] = "uav-inferred"
    scenario_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    with pytest.raises(
        BUILDER.InitialSnapshotBuildError,
        match="does not equal explicit object id",
    ):
        BUILDER.build_initial_world_state(scenario_path)


def test_gt22_world_state_references_do_not_bind_observation_file_bytes(
    tmp_path: Path,
) -> None:
    scenario_path = _copy_case(tmp_path)
    position_path = tmp_path / "observation_uav_alpha_position_gt22.json"
    before_bytes = position_path.read_bytes()
    before_state = BUILDER.build_initial_world_state(scenario_path)

    position_path.write_bytes(before_bytes + b"\n")
    after_bytes = position_path.read_bytes()
    after_state = BUILDER.build_initial_world_state(scenario_path)

    assert hashlib.sha256(before_bytes).hexdigest() != hashlib.sha256(after_bytes).hexdigest()
    assert before_state.to_dict() == after_state.to_dict()
    assert before_state.semantic_fingerprint() == after_state.semantic_fingerprint()
    assert _payload(SCENARIO)["scenario"]["safety_boundary"][
        "observation_bytes_bound_by_world_state"
    ] is False
