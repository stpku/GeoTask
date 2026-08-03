from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from geotask_core.v1.observation import load_observation
from geotask_core.v1.observation_merge import (
    ObservationMergeConflictPolicy,
    ObservationMergeError,
    ObservationMergeInstruction,
    load_observation_merge_result,
    merge_observations_into_world_state,
    validate_observation_merge_result_bindings,
)
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "examples" / "core"
SCENARIO = CORE / "gt21_observation_conflict_precedence.json"
SCHEMA = ROOT / "schemas" / "geotask-observation-merge-result-v0.1.schema.json"


def _payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _scenario() -> dict:
    return _payload(SCENARIO)["scenario"]


def _inputs() -> tuple[dict, bytes, list[bytes], list[ObservationMergeInstruction]]:
    scenario = _scenario()
    base_bytes = (CORE / scenario["base_world_state"]).read_bytes()
    observation_bytes = [
        (CORE / filename).read_bytes() for filename in scenario["observations"]
    ]
    observations = [
        load_observation(json.loads(raw.decode("utf-8"))) for raw in observation_bytes
    ]
    instructions = [
        ObservationMergeInstruction(
            observation_id=observation.observation_id,
            claim_id=scenario["claim_id"],
            target_path=scenario["target_path"],
        )
        for observation in observations
    ]
    return scenario, base_bytes, observation_bytes, instructions


def _merge(*, with_policy: bool = True, reverse_inputs: bool = False):
    scenario, base_bytes, observation_bytes, instructions = _inputs()
    if reverse_inputs:
        observation_bytes = list(reversed(observation_bytes))
        instructions = list(reversed(instructions))
    policy = scenario["conflict_policy"]
    conflict_policies = (
        [
            ObservationMergeConflictPolicy(
                target_path=scenario["target_path"],
                strategy=policy["strategy"],
                precedence=tuple(policy["precedence"]),
            )
        ]
        if with_policy
        else []
    )
    merge = scenario["merge"]
    return merge_observations_into_world_state(
        merge_id=merge["merge_id"],
        created_at=merge["created_at"],
        reason=merge["reason"],
        base_world_state_bytes=base_bytes,
        observation_bytes=observation_bytes,
        instructions=instructions,
        successor_as_of=merge["successor_as_of"],
        successor_materialized_at=merge["successor_materialized_at"],
        conflict_policies=conflict_policies,
    )


def test_gt21_source_artifacts_are_strictly_loadable() -> None:
    scenario, base_bytes, observation_bytes, _ = _inputs()

    state = load_world_state(json.loads(base_bytes.decode("utf-8")))
    observations = [
        load_observation(json.loads(raw.decode("utf-8"))) for raw in observation_bytes
    ]

    assert state.revision == 1
    assert [item.observation_id for item in observations] == [
        "obs-uav-b-delay-002",
        "obs-uav-b-delay-ops-review",
    ]
    assert [item.claims[0].value for item in observations] == [60, 55]
    assert scenario["safety_boundary"] == {
        "core_infers_authority": False,
        "core_ranks_sources": False,
        "core_invents_precedence": False,
        "policy_declared_by_caller": True,
    }


def test_gt21_duplicate_target_fails_closed_without_policy() -> None:
    expected = _scenario()["without_policy"]

    with pytest.raises(ObservationMergeError, match=expected["reason"]):
        _merge(with_policy=False)

    assert expected["expected_state"] == "blocked"


def test_gt21_explicit_precedence_is_order_independent_and_auditable() -> None:
    scenario, base_bytes, observation_bytes, _ = _inputs()
    expected = scenario["expected"]
    output = _merge()
    reversed_output = _merge(reverse_inputs=True)

    assert output.world_state_bytes == reversed_output.world_state_bytes
    assert output.result_bytes == reversed_output.result_bytes
    assert output.world_state.revision == expected["successor_revision"]

    delay = next(
        attribute
        for item in output.world_state.objects
        if item.id == "uav-b"
        for attribute in item.attributes
        if attribute.name == "delay_seconds"
    )
    assert delay.value == expected["selected_value"]
    assert delay.observation_refs == ("obs-uav-b-delay-ops-review",)

    states = {
        application.application_id: application.state
        for application in output.result.applied_claims
    }
    assert states[expected["selected_application_id"]] == expected["selected_state"]
    assert (
        states[expected["superseded_application_id"]]
        == expected["superseded_state"]
    )

    resolution = output.result.conflict_resolutions[0]
    assert resolution.strategy == "explicit_precedence"
    assert resolution.precedence == tuple(scenario["conflict_policy"]["precedence"])
    assert resolution.selected_application_id == expected["selected_application_id"]
    assert resolution.contributing_application_ids == (
        expected["selected_application_id"],
    )
    assert output.result.next_action == expected["next_action"]
    assert output.result.state_transition_computed is expected["state_transition_computed"]
    assert output.result.external_truth_verified is expected["external_truth_verified"]
    assert output.result.action_authorized is expected["action_authorized"]

    schema = _payload(SCHEMA)
    Draft202012Validator(schema).validate(output.result.to_dict())
    assert load_observation_merge_result(output.result.to_dict()) == output.result
    validate_observation_merge_result_bindings(
        output.result,
        base_world_state_bytes=base_bytes,
        observation_bytes=observation_bytes,
        successor_world_state_bytes=output.world_state_bytes,
    )


def test_gt21_require_equal_rejects_the_unequal_claims() -> None:
    scenario, base_bytes, observation_bytes, instructions = _inputs()
    merge = scenario["merge"]

    with pytest.raises(ObservationMergeError, match="not semantically equal"):
        merge_observations_into_world_state(
            merge_id=merge["merge_id"],
            created_at=merge["created_at"],
            reason=merge["reason"],
            base_world_state_bytes=base_bytes,
            observation_bytes=observation_bytes,
            instructions=instructions,
            successor_as_of=merge["successor_as_of"],
            successor_materialized_at=merge["successor_materialized_at"],
            conflict_policies=[
                ObservationMergeConflictPolicy(
                    target_path=scenario["target_path"],
                    strategy="require_equal",
                )
            ],
        )
