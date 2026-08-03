from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import geotask_core
import geotask_core.v1 as geotask_v1
from geotask_core.v1.observation_merge import (
    OBSERVATION_MERGE_RESULT_ARTIFACT_ID,
    OBSERVATION_MERGE_RESULT_SCHEMA_ID,
    ObservationMergeError,
    ObservationMergeInstruction,
    ObservationMergeConflictPolicy,
    load_observation_merge_result,
    merge_observations_into_world_state,
    validate_observation_merge_result_bindings,
)
from geotask_core.v1.world_state import load_world_state


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "examples" / "core"
BASE_STATE = CORE / "world_state_uav_separation.json"
OBSERVATION = CORE / "observation_uav_b_delay_recheck.json"
SUCCESSOR_STATE = CORE / "world_state_uav_separation_observation_merged.json"
RESULT = CORE / "observation_merge_result_uav_recheck.json"
SCHEMA = ROOT / "schemas" / "geotask-observation-merge-result-v0.1.schema.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical(payload: dict) -> bytes:
    return (json.dumps(payload, indent=2) + "\n").encode("utf-8")


def _payload() -> dict:
    return copy.deepcopy(_json(RESULT))


def _result(payload: dict | None = None):
    return load_observation_merge_result(payload or _payload())


def _instruction(
    *,
    observation_id: str = "obs-uav-b-delay-002",
    claim_id: str = "uav-b-delay-seconds",
    target_path: str = "/objects/uav-b/attributes/delay_seconds",
) -> ObservationMergeInstruction:
    return ObservationMergeInstruction(
        observation_id=observation_id,
        claim_id=claim_id,
        target_path=target_path,
    )


def _merge(
    *,
    base_bytes: bytes | None = None,
    observation_bytes: list[bytes] | None = None,
    instructions: list[ObservationMergeInstruction] | None = None,
    conflict_policies: list[ObservationMergeConflictPolicy] | None = None,
    successor_as_of: str = "2026-07-16T10:01:00+08:00",
    successor_materialized_at: str = "2026-07-16T10:01:03+08:00",
):
    return merge_observations_into_world_state(
        merge_id="fictional-uav-observation-merge",
        created_at="2026-07-16T10:01:04+08:00",
        reason="Apply the latest telemetry claim without recomputing dependent relations.",
        base_world_state_bytes=base_bytes or BASE_STATE.read_bytes(),
        observation_bytes=observation_bytes or [OBSERVATION.read_bytes()],
        instructions=instructions or [_instruction()],
        successor_as_of=successor_as_of,
        successor_materialized_at=successor_materialized_at,
        conflict_policies=conflict_policies or [],
    )


def _observation_variant(
    observation_id: str,
    *,
    value: int = 60,
    claim_id: str = "uav-b-delay-seconds",
) -> bytes:
    payload = _json(OBSERVATION)
    body = payload["observation"]
    body["observation_id"] = observation_id
    body["source"]["reference"] = f"telemetry:fictional/uav-b/{observation_id}"
    body["source"]["sha256"] = "c" * 64
    body["claims"][0]["id"] = claim_id
    body["claims"][0]["value"] = value
    body["claims"][0]["evidence_refs"] = [body["source"]["reference"]]
    return _canonical(payload)


def test_conflict_policy_types_are_public_api() -> None:
    assert geotask_core.ObservationMergeConflictPolicy is ObservationMergeConflictPolicy
    assert geotask_v1.ObservationMergeConflictPolicy is ObservationMergeConflictPolicy
    assert geotask_core.OBSERVATION_MERGE_CONFLICT_STRATEGIES == frozenset(
        {"require_equal", "explicit_precedence"}
    )


def test_merge_rejects_ambiguous_composite_application_ids() -> None:
    with pytest.raises(ObservationMergeError, match="duplicate application IDs"):
        _merge(
            observation_bytes=[
                _observation_variant("obs#a", claim_id="b"),
                _observation_variant("obs", claim_id="a#b"),
            ],
            instructions=[
                _instruction(observation_id="obs#a", claim_id="b"),
                _instruction(observation_id="obs", claim_id="a#b"),
            ],
        )


def test_public_identity_schema_and_fingerprint_are_stable() -> None:
    result = _result()
    assert OBSERVATION_MERGE_RESULT_ARTIFACT_ID == "geotask.observation-merge-result"
    assert OBSERVATION_MERGE_RESULT_SCHEMA_ID.endswith(
        "geotask-observation-merge-result-v0.1.schema.json"
    )
    assert result.state == "completed"
    assert result.semantic_fingerprint() == (
        "c02a8b58c1d6cae1c76774b505541337a9a632ad86790bdfcb8e1da6e4d6bd61"
    )
    assert load_observation_merge_result(result.to_dict()) == result


def test_schema_and_exact_binding_accept_reference_example() -> None:
    schema = _json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_payload())
    validate_observation_merge_result_bindings(
        _result(),
        base_world_state_bytes=BASE_STATE.read_bytes(),
        observation_bytes=[OBSERVATION.read_bytes()],
        successor_world_state_bytes=SUCCESSOR_STATE.read_bytes(),
    )


def test_merge_matches_successor_fixture_without_recomputing_dependents() -> None:
    output = _merge()
    assert output.world_state == load_world_state(_json(SUCCESSOR_STATE))
    assert output.world_state_bytes == SUCCESSOR_STATE.read_bytes()
    delay = next(
        attribute
        for item in output.world_state.objects
        if item.id == "uav-b"
        for attribute in item.attributes
        if attribute.name == "delay_seconds"
    )
    relation = next(
        item
        for item in output.world_state.relations
        if item.id == "uav-temporal-separation"
    )
    assert delay.value == 60
    assert delay.verification_status == "asserted"
    assert relation.value == 80
    assert output.result.state_transition_computed is False
    assert output.result.next_action == "compute_state_transition"


def test_merge_requires_complete_claim_mapping() -> None:
    payload = _json(OBSERVATION)
    extra = copy.deepcopy(payload["observation"]["claims"][0])
    extra["id"] = "uav-b-route-id"
    extra["predicate"] = "route_id"
    extra["value"] = "route-bravo"
    payload["observation"]["claims"].append(extra)

    with pytest.raises(ObservationMergeError, match="cover every supplied claim"):
        _merge(observation_bytes=[_canonical(payload)])


def test_merge_rejects_subject_or_predicate_target_drift() -> None:
    with pytest.raises(ObservationMergeError, match="object identity"):
        _merge(
            instructions=[
                _instruction(target_path="/objects/uav-a/attributes/route_id")
            ]
        )

    with pytest.raises(ObservationMergeError, match="attribute name"):
        _merge(
            instructions=[
                _instruction(target_path="/objects/uav-b/attributes/route_id")
            ]
        )


def test_merge_does_not_create_missing_attribute() -> None:
    payload = _json(OBSERVATION)
    payload["observation"]["claims"][0]["predicate"] = "new_attribute"
    with pytest.raises(ObservationMergeError, match="unknown attribute"):
        _merge(
            observation_bytes=[_canonical(payload)],
            instructions=[
                _instruction(target_path="/objects/uav-b/attributes/new_attribute")
            ],
        )


def test_merge_rejects_duplicate_target_paths() -> None:
    payload = _json(OBSERVATION)
    duplicate = copy.deepcopy(payload["observation"]["claims"][0])
    duplicate["id"] = "uav-b-delay-seconds-duplicate"
    payload["observation"]["claims"].append(duplicate)
    with pytest.raises(ObservationMergeError, match="duplicates target path"):
        _merge(
            observation_bytes=[_canonical(payload)],
            instructions=[
                _instruction(),
                _instruction(claim_id="uav-b-delay-seconds-duplicate"),
            ],
        )


def test_require_equal_conflict_consolidates_provenance() -> None:
    second_id = "obs-uav-b-delay-corroborating"
    second_bytes = _observation_variant(second_id)
    target_path = "/objects/uav-b/attributes/delay_seconds"
    output = _merge(
        observation_bytes=[OBSERVATION.read_bytes(), second_bytes],
        instructions=[
            _instruction(),
            _instruction(observation_id=second_id),
        ],
        conflict_policies=[
            ObservationMergeConflictPolicy(
                target_path=target_path,
                strategy="require_equal",
            )
        ],
    )

    delay = next(
        attribute
        for item in output.world_state.objects
        if item.id == "uav-b"
        for attribute in item.attributes
        if attribute.name == "delay_seconds"
    )
    assert delay.value == 60
    assert delay.observation_refs == (
        "obs-uav-b-delay-002",
        second_id,
    )
    states = {item.application_id: item.state for item in output.result.applied_claims}
    assert sorted(states.values()) == ["applied", "consolidated"]
    resolution = output.result.conflict_resolutions[0]
    assert resolution.strategy == "require_equal"
    assert resolution.selected_application_id is None
    assert set(resolution.contributing_application_ids) == set(states)

    schema = _json(SCHEMA)
    Draft202012Validator(schema).validate(output.result.to_dict())
    validate_observation_merge_result_bindings(
        output.result,
        base_world_state_bytes=BASE_STATE.read_bytes(),
        observation_bytes=[OBSERVATION.read_bytes(), second_bytes],
        successor_world_state_bytes=output.world_state_bytes,
    )


def test_require_equal_conflict_rejects_semantic_disagreement() -> None:
    second_id = "obs-uav-b-delay-disagreeing"
    with pytest.raises(ObservationMergeError, match="not semantically equal"):
        _merge(
            observation_bytes=[
                OBSERVATION.read_bytes(),
                _observation_variant(second_id, value=45),
            ],
            instructions=[
                _instruction(),
                _instruction(observation_id=second_id),
            ],
            conflict_policies=[
                ObservationMergeConflictPolicy(
                    target_path="/objects/uav-b/attributes/delay_seconds",
                    strategy="require_equal",
                )
            ],
        )


def test_explicit_precedence_selects_declared_claim_and_audits_loser() -> None:
    second_id = "obs-uav-b-delay-priority"
    second_bytes = _observation_variant(second_id, value=45)
    target_path = "/objects/uav-b/attributes/delay_seconds"
    selected_id = f"{second_id}#uav-b-delay-seconds"
    original_id = "obs-uav-b-delay-002#uav-b-delay-seconds"
    output = _merge(
        observation_bytes=[OBSERVATION.read_bytes(), second_bytes],
        instructions=[
            _instruction(),
            _instruction(observation_id=second_id),
        ],
        conflict_policies=[
            ObservationMergeConflictPolicy(
                target_path=target_path,
                strategy="explicit_precedence",
                precedence=(selected_id, original_id),
            )
        ],
    )

    delay = next(
        attribute
        for item in output.world_state.objects
        if item.id == "uav-b"
        for attribute in item.attributes
        if attribute.name == "delay_seconds"
    )
    assert delay.value == 45
    assert delay.observation_refs == (second_id,)
    states = {item.application_id: item.state for item in output.result.applied_claims}
    assert states[selected_id] == "applied"
    assert states[original_id] == "superseded"
    resolution = output.result.conflict_resolutions[0]
    assert resolution.selected_application_id == selected_id
    assert resolution.precedence == (selected_id, original_id)
    assert resolution.contributing_application_ids == (selected_id,)

    validate_observation_merge_result_bindings(
        output.result,
        base_world_state_bytes=BASE_STATE.read_bytes(),
        observation_bytes=[OBSERVATION.read_bytes(), second_bytes],
        successor_world_state_bytes=output.world_state_bytes,
    )


def test_explicit_precedence_requires_complete_participant_order() -> None:
    second_id = "obs-uav-b-delay-priority"
    with pytest.raises(ObservationMergeError, match="every conflicting application"):
        _merge(
            observation_bytes=[
                OBSERVATION.read_bytes(),
                _observation_variant(second_id, value=45),
            ],
            instructions=[
                _instruction(),
                _instruction(observation_id=second_id),
            ],
            conflict_policies=[
                ObservationMergeConflictPolicy(
                    target_path="/objects/uav-b/attributes/delay_seconds",
                    strategy="explicit_precedence",
                    precedence=(
                        f"{second_id}#uav-b-delay-seconds",
                    ),
                )
            ],
        )


def test_loader_rejects_tampered_conflict_resolution() -> None:
    second_id = "obs-uav-b-delay-priority"
    output = _merge(
        observation_bytes=[
            OBSERVATION.read_bytes(),
            _observation_variant(second_id, value=45),
        ],
        instructions=[
            _instruction(),
            _instruction(observation_id=second_id),
        ],
        conflict_policies=[
            ObservationMergeConflictPolicy(
                target_path="/objects/uav-b/attributes/delay_seconds",
                strategy="explicit_precedence",
                precedence=(
                    f"{second_id}#uav-b-delay-seconds",
                    "obs-uav-b-delay-002#uav-b-delay-seconds",
                ),
            )
        ],
    )
    payload = output.result.to_dict()
    payload["observation_merge_result"]["conflict_resolutions"][0][
        "selected_application_id"
    ] = "obs-uav-b-delay-002#uav-b-delay-seconds"
    with pytest.raises(ObservationMergeError, match="first explicit precedence"):
        load_observation_merge_result(payload)


def test_loader_requires_complete_conflict_participant_coverage() -> None:
    first_id = "obs-uav-b-delay-priority-a"
    second_id = "obs-uav-b-delay-priority-b"
    first_application = f"{first_id}#uav-b-delay-seconds"
    second_application = f"{second_id}#uav-b-delay-seconds"
    original_application = "obs-uav-b-delay-002#uav-b-delay-seconds"
    output = _merge(
        observation_bytes=[
            OBSERVATION.read_bytes(),
            _observation_variant(first_id, value=45),
            _observation_variant(second_id, value=30),
        ],
        instructions=[
            _instruction(),
            _instruction(observation_id=first_id),
            _instruction(observation_id=second_id),
        ],
        conflict_policies=[
            ObservationMergeConflictPolicy(
                target_path="/objects/uav-b/attributes/delay_seconds",
                strategy="explicit_precedence",
                precedence=(
                    first_application,
                    second_application,
                    original_application,
                ),
            )
        ],
    )
    payload = output.result.to_dict()
    resolution = payload["observation_merge_result"]["conflict_resolutions"][0]
    resolution["participant_application_ids"] = [
        first_application,
        second_application,
    ]
    resolution["precedence"] = [first_application, second_application]
    resolution["contributing_application_ids"] = [first_application]
    with pytest.raises(ObservationMergeError, match="exactly match every application"):
        load_observation_merge_result(payload)


def test_loader_rejects_explicit_empty_conflict_resolution_section() -> None:
    payload = _payload()
    payload["observation_merge_result"]["conflict_resolutions"] = []
    with pytest.raises(ObservationMergeError, match="at least one item when present"):
        load_observation_merge_result(payload)


def test_relation_merge_requires_and_binds_relation_identity() -> None:
    payload = _json(OBSERVATION)
    claim = payload["observation"]["claims"][0]
    claim.update(
        {
            "id": "uav-temporal-separation-observed",
            "subject_ref": "uav-a",
            "predicate": "temporal_separation_seconds",
            "object_ref": "uav-b",
            "value": 70,
        }
    )
    output = _merge(
        observation_bytes=[_canonical(payload)],
        instructions=[
            _instruction(
                claim_id="uav-temporal-separation-observed",
                target_path="/relations/uav-temporal-separation",
            )
        ],
    )
    relation = next(
        item
        for item in output.world_state.relations
        if item.id == "uav-temporal-separation"
    )
    assert relation.value == 70
    assert relation.verification_status == "asserted"

    payload = _json(OBSERVATION)
    with pytest.raises(ObservationMergeError, match="require claim.object_ref"):
        _merge(
            observation_bytes=[_canonical(payload)],
            instructions=[
                _instruction(target_path="/relations/uav-temporal-separation")
            ],
        )


def test_merge_rejects_future_observation() -> None:
    payload = _json(OBSERVATION)
    payload["observation"]["observed_at"] = "2026-07-16T10:02:00+08:00"
    payload["observation"]["received_at"] = "2026-07-16T10:02:01+08:00"
    payload["observation"]["claims"][0]["valid_until"] = (
        "2026-07-16T10:02:30+08:00"
    )
    with pytest.raises(ObservationMergeError, match="later than successor_as_of"):
        _merge(observation_bytes=[_canonical(payload)])


def test_merge_rejects_observation_already_declared_by_base() -> None:
    base = _json(BASE_STATE)
    base["world_state"]["observation_refs"].append("obs-uav-b-delay-002")
    with pytest.raises(ObservationMergeError, match="not already declared"):
        _merge(base_bytes=_canonical(base))


def test_loader_rejects_operational_claims_and_duplicate_observation_refs() -> None:
    payload = _payload()
    payload["observation_merge_result"]["state_transition_computed"] = True
    with pytest.raises(ObservationMergeError, match="must be false"):
        _result(payload)

    payload = _payload()
    payload["observation_merge_result"]["observation_refs"].append(
        copy.deepcopy(payload["observation_merge_result"]["observation_refs"][0])
    )
    with pytest.raises(ObservationMergeError, match="duplicates"):
        _result(payload)


def test_exact_binding_rejects_source_byte_drift() -> None:
    semantically_same = json.dumps(_json(OBSERVATION), separators=(",", ":")).encode(
        "utf-8"
    )
    with pytest.raises(ObservationMergeError, match="declared result differs"):
        validate_observation_merge_result_bindings(
            _result(),
            base_world_state_bytes=BASE_STATE.read_bytes(),
            observation_bytes=[semantically_same],
            successor_world_state_bytes=SUCCESSOR_STATE.read_bytes(),
        )


def test_exact_binding_rejects_successor_byte_drift() -> None:
    with pytest.raises(ObservationMergeError, match="canonical bytes"):
        validate_observation_merge_result_bindings(
            _result(),
            base_world_state_bytes=BASE_STATE.read_bytes(),
            observation_bytes=[OBSERVATION.read_bytes()],
            successor_world_state_bytes=SUCCESSOR_STATE.read_bytes() + b"\n",
        )


def test_exact_binding_rejects_tampered_application_record() -> None:
    payload = _payload()
    payload["observation_merge_result"]["applied_claims"][0]["before"]["value"] = 39
    result = _result(payload)
    with pytest.raises(ObservationMergeError, match="declared result differs"):
        validate_observation_merge_result_bindings(
            result,
            base_world_state_bytes=BASE_STATE.read_bytes(),
            observation_bytes=[OBSERVATION.read_bytes()],
            successor_world_state_bytes=SUCCESSOR_STATE.read_bytes(),
        )
