#!/usr/bin/env python3
"""Build the fictional GT23 five-minute UAV state change.

This case-specific example applies two explicit Observations to the GT22 snapshot,
refreshes the object's coherent validity window, and authors one State Transition.
Every declared before/after value is checked against the two bound World States.
It is not a generic diff engine and does not assess impact, verify external truth,
or authorize an action.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Mapping, Sequence

from geotask_core.v1.observation import Observation, WorldClaim, load_observation
from geotask_core.v1.state_transition import (
    StateTransition,
    load_state_transition,
    validate_state_transition_bindings,
)
from geotask_core.v1.world_state import WorldState, WorldStateAttribute, load_world_state


class GT23BuildError(ValueError):
    """Raised when the explicit GT23 change plan is incomplete or inconsistent."""


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GT23BuildError(f"{path}: must be an object")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise GT23BuildError(f"{path}: must be an array")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GT23BuildError(f"{path}: must be a non-empty string")
    return value


def _case_file(scenario_path: Path, filename: object, path: str) -> Path:
    name = _string(filename, path)
    base = scenario_path.parent.resolve()
    candidate = (base / name).resolve()
    if candidate.parent != base:
        raise GT23BuildError(f"{path}: must stay in {base}")
    return candidate


def _claim(observation: Observation, claim_id: str) -> WorldClaim:
    matches = [item for item in observation.claims if item.id == claim_id]
    if len(matches) != 1:
        raise GT23BuildError(
            f"{observation.observation_id}#{claim_id}: claim must exist exactly once"
        )
    return matches[0]


def _attribute(state: WorldState, target_path: str) -> WorldStateAttribute:
    parts = target_path.split("/")
    if len(parts) != 5 or parts[:2] != ["", "objects"] or parts[3] != "attributes":
        raise GT23BuildError(
            f"target_path: expected /objects/<id>/attributes/<name>, got {target_path!r}"
        )
    object_id, attribute_name = parts[2], parts[4]
    objects = [item for item in state.objects if item.id == object_id]
    if len(objects) != 1:
        raise GT23BuildError(f"target_path: object {object_id!r} must exist exactly once")
    attributes = [item for item in objects[0].attributes if item.name == attribute_name]
    if len(attributes) != 1:
        raise GT23BuildError(
            f"target_path: attribute {object_id}.{attribute_name} must exist exactly once"
        )
    return attributes[0]


def _object_payload(body: dict[str, object], object_id: str) -> dict[str, object]:
    objects = body.get("objects")
    if not isinstance(objects, list):
        raise GT23BuildError("world_state.objects: must be an array")
    matches = [item for item in objects if isinstance(item, dict) and item.get("id") == object_id]
    if len(matches) != 1:
        raise GT23BuildError(f"world_state.objects: {object_id!r} must exist exactly once")
    return matches[0]


def _attribute_payload(item: dict[str, object], name: str) -> dict[str, object]:
    attributes = item.get("attributes")
    if not isinstance(attributes, list):
        raise GT23BuildError("world_state object attributes: must be an array")
    matches = [
        attribute
        for attribute in attributes
        if isinstance(attribute, dict) and attribute.get("name") == name
    ]
    if len(matches) != 1:
        raise GT23BuildError(f"attribute {name!r} must exist exactly once")
    return matches[0]


def build_gt23_state_change(
    scenario_path: str | Path,
    *,
    observation_filenames: Sequence[str] | None = None,
) -> tuple[WorldState, StateTransition]:
    """Build the successor snapshot and its explicitly declared State Transition."""

    path = Path(scenario_path).resolve()
    root = _mapping(json.loads(path.read_text(encoding="utf-8")), "root")
    scenario = _mapping(root.get("scenario"), "scenario")

    base_path = _case_file(path, scenario.get("base_world_state"), "scenario.base_world_state")
    base_payload = json.loads(base_path.read_text(encoding="utf-8"))
    base_state = load_world_state(base_payload)

    declared_files = tuple(
        _string(item, f"scenario.observations[{index}]")
        for index, item in enumerate(
            _sequence(scenario.get("observations"), "scenario.observations")
        )
    )
    selected_files = tuple(observation_filenames or declared_files)
    if len(selected_files) != len(declared_files) or set(selected_files) != set(declared_files):
        raise GT23BuildError(
            "observation_filenames: must contain every declared Observation file exactly once"
        )

    observations: dict[str, Observation] = {}
    for index, filename in enumerate(selected_files):
        observation_path = _case_file(path, filename, f"observation_filenames[{index}]")
        observation = load_observation(json.loads(observation_path.read_text(encoding="utf-8")))
        if observation.observation_id in observations:
            raise GT23BuildError(
                f"observation_filenames[{index}]: duplicates {observation.observation_id!r}"
            )
        observations[observation.observation_id] = observation

    mappings = _sequence(scenario.get("mappings"), "scenario.mappings")
    available_claims = {
        (observation.observation_id, claim.id)
        for observation in observations.values()
        for claim in observation.claims
    }
    declared_claims: set[tuple[str, str]] = set()
    normalized_mappings: list[Mapping[str, object]] = []
    for index, raw_mapping in enumerate(mappings):
        mapping = _mapping(raw_mapping, f"scenario.mappings[{index}]")
        observation_id = _string(
            mapping.get("observation_id"), f"scenario.mappings[{index}].observation_id"
        )
        claim_id = _string(mapping.get("claim_id"), f"scenario.mappings[{index}].claim_id")
        target_path = _string(
            mapping.get("target_path"), f"scenario.mappings[{index}].target_path"
        )
        key = (observation_id, claim_id)
        if key in declared_claims:
            raise GT23BuildError(f"scenario.mappings[{index}]: duplicates claim mapping {key}")
        if observation_id not in observations:
            raise GT23BuildError(
                f"scenario.mappings[{index}]: unknown Observation {observation_id!r}"
            )
        claim = _claim(observations[observation_id], claim_id)
        if claim.subject_ref != "uav-alpha":
            raise GT23BuildError(
                f"scenario.mappings[{index}]: subject_ref must remain 'uav-alpha'"
            )
        _attribute(base_state, target_path)
        declared_claims.add(key)
        normalized_mappings.append(mapping)
    if declared_claims != available_claims:
        raise GT23BuildError(
            "explicit claim coverage mismatch: "
            f"missing={sorted(available_claims - declared_claims)}, "
            f"extra={sorted(declared_claims - available_claims)}"
        )

    merge = _mapping(scenario.get("merge"), "scenario.merge")
    successor_payload = copy.deepcopy(base_payload)
    body = successor_payload["world_state"]
    body["revision"] = base_state.revision + 1
    body["as_of"] = _string(merge.get("successor_as_of"), "scenario.merge.successor_as_of")
    body["materialized_at"] = _string(
        merge.get("successor_materialized_at"),
        "scenario.merge.successor_materialized_at",
    )

    object_payload = _object_payload(body, "uav-alpha")
    new_observation_refs = set(body.get("observation_refs", []))
    new_evidence_refs = set(body.get("evidence_refs", []))
    object_observation_refs = set(object_payload.get("observation_refs", []))
    object_evidence_refs = set(object_payload.get("evidence_refs", []))
    valid_until_values: list[str] = []

    for mapping in normalized_mappings:
        observation_id = _string(mapping.get("observation_id"), "mapping.observation_id")
        claim_id = _string(mapping.get("claim_id"), "mapping.claim_id")
        target_path = _string(mapping.get("target_path"), "mapping.target_path")
        claim = _claim(observations[observation_id], claim_id)
        attribute_name = target_path.split("/")[-1]
        attribute_payload = _attribute_payload(object_payload, attribute_name)
        attribute_payload["value"] = copy.deepcopy(claim.value)
        attribute_payload["basis"] = claim.basis
        attribute_payload["verification_status"] = "asserted"
        attribute_payload["valid_from"] = claim.observed_at or observations[observation_id].observed_at
        if claim.valid_until is None:
            raise GT23BuildError(f"{observation_id}#{claim_id}: valid_until is required")
        attribute_payload["valid_until"] = claim.valid_until
        valid_until_values.append(claim.valid_until)
        if claim.uncertainty is None:
            attribute_payload.pop("uncertainty", None)
        else:
            attribute_payload["uncertainty"] = claim.uncertainty.to_dict()
        attribute_payload["observation_refs"] = [observation_id]
        attribute_payload["evidence_refs"] = sorted(claim.evidence_refs)
        new_observation_refs.add(observation_id)
        new_evidence_refs.update(claim.evidence_refs)
        object_observation_refs.add(observation_id)
        object_evidence_refs.update(claim.evidence_refs)

    before_object_valid_until = object_payload.get("valid_until")
    object_payload["valid_until"] = min(valid_until_values)
    object_payload["observation_refs"] = sorted(object_observation_refs)
    object_payload["evidence_refs"] = sorted(object_evidence_refs)
    body["observation_refs"] = sorted(new_observation_refs)
    body["evidence_refs"] = sorted(new_evidence_refs)
    successor = load_world_state(successor_payload)

    transition_config = _mapping(scenario.get("transition"), "scenario.transition")
    declared_changes: list[dict[str, object]] = []
    all_evidence_refs: set[str] = set()
    for index, mapping in enumerate(normalized_mappings):
        observation_id = _string(mapping.get("observation_id"), "mapping.observation_id")
        claim_id = _string(mapping.get("claim_id"), "mapping.claim_id")
        target_path = _string(mapping.get("target_path"), "mapping.target_path")
        claim = _claim(observations[observation_id], claim_id)
        before = _attribute(base_state, target_path).value
        after = _attribute(successor, target_path).value
        if before == after:
            raise GT23BuildError(
                f"scenario.mappings[{index}]: declared replace did not change {target_path}"
            )
        all_evidence_refs.update(claim.evidence_refs)
        declared_changes.append(
            {
                "id": _string(mapping.get("change_id"), "mapping.change_id"),
                "kind": "attribute",
                "operation": "replace",
                "path": f"{target_path}/value",
                "before": before,
                "after": after,
                "basis": claim.basis,
                "verification_status": "asserted",
                "reason": _string(mapping.get("reason"), "mapping.reason"),
                "observation_refs": [observation_id],
                "evidence_refs": sorted(claim.evidence_refs),
            }
        )

    if before_object_valid_until == object_payload["valid_until"]:
        raise GT23BuildError("object validity refresh must change valid_until")
    declared_changes.append(
        {
            "id": "uav-alpha-validity-refresh",
            "kind": "object",
            "operation": "replace",
            "path": "/objects/uav-alpha/valid_until",
            "before": before_object_valid_until,
            "after": object_payload["valid_until"],
            "basis": "direct_observation",
            "verification_status": "asserted",
            "reason": "The coherent object window is refreshed to the earliest expiry of the new telemetry claims.",
            "observation_refs": sorted(observations),
            "evidence_refs": sorted(all_evidence_refs),
        }
    )

    transition_payload = {
        "state_transition": {
            "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-state-transition-v0.1.schema.json",
            "schema_version": "0.1",
            "transition_id": _string(
                transition_config.get("transition_id"),
                "scenario.transition.transition_id",
            ),
            "occurred_at": _string(
                transition_config.get("occurred_at"), "scenario.transition.occurred_at"
            ),
            "recorded_at": _string(
                transition_config.get("recorded_at"), "scenario.transition.recorded_at"
            ),
            "from_state": {
                "world_state_id": base_state.world_state_id,
                "revision": base_state.revision,
                "as_of": base_state.as_of,
                "semantic_fingerprint": base_state.semantic_fingerprint(),
            },
            "to_state": {
                "world_state_id": successor.world_state_id,
                "revision": successor.revision,
                "as_of": successor.as_of,
                "semantic_fingerprint": successor.semantic_fingerprint(),
            },
            "observation_refs": sorted(observations),
            "evidence_refs": sorted(all_evidence_refs),
            "changes": declared_changes,
            "action_eligibility_changes": [],
        }
    }
    transition = load_state_transition(transition_payload)
    validate_state_transition_bindings(transition, base_state, successor)

    actual_changes = {item.path: item for item in transition.changes}
    expected_paths = {
        f"{_string(mapping.get('target_path'), 'mapping.target_path')}/value"
        for mapping in normalized_mappings
    } | {"/objects/uav-alpha/valid_until"}
    if set(actual_changes) != expected_paths:
        raise GT23BuildError(
            f"transition change coverage mismatch: expected={sorted(expected_paths)}, "
            f"actual={sorted(actual_changes)}"
        )
    for mapping in normalized_mappings:
        target_path = _string(mapping.get("target_path"), "mapping.target_path")
        change = actual_changes[f"{target_path}/value"]
        if change.before != _attribute(base_state, target_path).value:
            raise GT23BuildError(f"transition before value does not match {target_path}")
        if change.after != _attribute(successor, target_path).value:
            raise GT23BuildError(f"transition after value does not match {target_path}")

    return successor, transition


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        nargs="?",
        default=str(Path(__file__).with_name("gt23_uav_state_change.json")),
    )
    parser.add_argument("--successor-output")
    parser.add_argument("--transition-output")
    args = parser.parse_args()

    successor, transition = build_gt23_state_change(args.scenario)
    outputs = (
        (args.successor_output, successor.to_dict()),
        (args.transition_output, transition.to_dict()),
    )
    wrote = False
    for destination, payload in outputs:
        if destination:
            Path(destination).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            wrote = True
    if not wrote:
        print(json.dumps(transition.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
