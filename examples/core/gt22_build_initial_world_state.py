#!/usr/bin/env python3
"""Build the fictional GT22 revision-1 World State from explicit mappings.

This is a case-specific example, not a generic ingestion engine. It strictly
loads every Observation, requires every claim to be mapped exactly once by the
caller, constructs only declared objects and attributes, and validates the
result with the public World State v0.1 loader. It does not infer identity,
verify external truth, bind the original Observation file bytes inside the
World State, compute a State Transition, or authorize action.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

from geotask_core.v1.observation import Observation, WorldClaim, load_observation
from geotask_core.v1.world_state import (
    WorldState,
    WorldStateAttribute,
    WorldStateObject,
    load_world_state,
)


class InitialSnapshotBuildError(ValueError):
    """Raised when the GT22 explicit construction plan is incomplete."""


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise InitialSnapshotBuildError(f"{path}: must be an object")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise InitialSnapshotBuildError(f"{path}: must be an array")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InitialSnapshotBuildError(f"{path}: must be a non-empty string")
    return value


def _timestamp(value: object, path: str) -> tuple[str, datetime]:
    text = _string(value, path)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InitialSnapshotBuildError(f"{path}: must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InitialSnapshotBuildError(f"{path}: must include a timezone offset")
    return text, parsed


def _load_observations(
    scenario_path: Path,
    filenames: Sequence[str],
) -> dict[str, Observation]:
    loaded: dict[str, Observation] = {}
    base = scenario_path.parent.resolve()
    for index, filename in enumerate(filenames):
        name = _string(filename, f"scenario.observations[{index}]")
        candidate = (base / name).resolve()
        if candidate.parent != base:
            raise InitialSnapshotBuildError(
                f"scenario.observations[{index}]: must stay in {base}"
            )
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        observation = load_observation(payload)
        if observation.observation_id in loaded:
            raise InitialSnapshotBuildError(
                f"scenario.observations[{index}]: duplicates observation id "
                f"{observation.observation_id!r}"
            )
        loaded[observation.observation_id] = observation
    return loaded


def _claim_by_id(observation: Observation, claim_id: str) -> WorldClaim:
    matches = [claim for claim in observation.claims if claim.id == claim_id]
    if len(matches) != 1:
        raise InitialSnapshotBuildError(
            f"mapping {observation.observation_id}#{claim_id}: claim must exist exactly once"
        )
    return matches[0]


def build_initial_world_state(
    scenario_path: str | Path,
    *,
    observation_filenames: Sequence[str] | None = None,
) -> WorldState:
    """Construct and strictly validate the GT22 revision-1 snapshot."""

    path = Path(scenario_path).resolve()
    root = _mapping(json.loads(path.read_text(encoding="utf-8")), "root")
    scenario = _mapping(root.get("scenario"), "scenario")
    declared_filenames = tuple(
        _string(item, f"scenario.observations[{index}]")
        for index, item in enumerate(_sequence(scenario.get("observations"), "scenario.observations"))
    )
    filenames = tuple(observation_filenames or declared_filenames)
    if set(filenames) != set(declared_filenames) or len(filenames) != len(declared_filenames):
        raise InitialSnapshotBuildError(
            "observation_filenames: must contain every declared Observation file exactly once"
        )
    observations = _load_observations(path, filenames)

    snapshot = _mapping(scenario.get("snapshot"), "scenario.snapshot")
    world_state_id = _string(snapshot.get("world_state_id"), "scenario.snapshot.world_state_id")
    revision = snapshot.get("revision")
    if revision != 1:
        raise InitialSnapshotBuildError("scenario.snapshot.revision: initial snapshot must be 1")
    as_of_text, as_of = _timestamp(snapshot.get("as_of"), "scenario.snapshot.as_of")
    materialized_at_text, _ = _timestamp(
        snapshot.get("materialized_at"), "scenario.snapshot.materialized_at"
    )
    latest_observation = max(
        _timestamp(observation.observed_at, "observation.observed_at")[1]
        for observation in observations.values()
    )
    if as_of != latest_observation:
        raise InitialSnapshotBuildError(
            "scenario.snapshot.as_of: must equal the latest declared Observation time"
        )

    available_claims = {
        (observation.observation_id, claim.id)
        for observation in observations.values()
        for claim in observation.claims
    }
    mapped_claims: set[tuple[str, str]] = set()
    objects: list[WorldStateObject] = []
    object_ids: set[str] = set()

    for object_index, raw_object in enumerate(
        _sequence(scenario.get("object_plan"), "scenario.object_plan")
    ):
        plan = _mapping(raw_object, f"scenario.object_plan[{object_index}]")
        object_id = _string(plan.get("id"), f"scenario.object_plan[{object_index}].id")
        object_type = _string(
            plan.get("type"), f"scenario.object_plan[{object_index}].type"
        )
        if object_id in object_ids:
            raise InitialSnapshotBuildError(
                f"scenario.object_plan[{object_index}].id: duplicates {object_id!r}"
            )
        object_ids.add(object_id)
        status = _string(
            plan.get("verification_status"),
            f"scenario.object_plan[{object_index}].verification_status",
        )
        valid_from = _string(
            plan.get("valid_from"), f"scenario.object_plan[{object_index}].valid_from"
        )
        valid_until = _string(
            plan.get("valid_until"), f"scenario.object_plan[{object_index}].valid_until"
        )

        attributes: list[WorldStateAttribute] = []
        attribute_names: set[str] = set()
        object_observation_refs: set[str] = set()
        object_evidence_refs: set[str] = set()
        for claim_index, raw_binding in enumerate(
            _sequence(plan.get("claims"), f"scenario.object_plan[{object_index}].claims")
        ):
            binding = _mapping(
                raw_binding,
                f"scenario.object_plan[{object_index}].claims[{claim_index}]",
            )
            observation_id = _string(binding.get("observation_id"), "mapping.observation_id")
            claim_id = _string(binding.get("claim_id"), "mapping.claim_id")
            attribute_name = _string(
                binding.get("attribute_name"), "mapping.attribute_name"
            )
            key = (observation_id, claim_id)
            if key in mapped_claims:
                raise InitialSnapshotBuildError(
                    f"mapping {observation_id}#{claim_id}: mapped more than once"
                )
            observation = observations.get(observation_id)
            if observation is None:
                raise InitialSnapshotBuildError(
                    f"mapping {observation_id}#{claim_id}: Observation is not declared"
                )
            claim = _claim_by_id(observation, claim_id)
            if claim.subject_ref != object_id:
                raise InitialSnapshotBuildError(
                    f"mapping {observation_id}#{claim_id}: subject_ref {claim.subject_ref!r} "
                    f"does not equal explicit object id {object_id!r}"
                )
            if claim.object_ref is not None:
                raise InitialSnapshotBuildError(
                    f"mapping {observation_id}#{claim_id}: relation claims are not supported in GT22"
                )
            if attribute_name in attribute_names:
                raise InitialSnapshotBuildError(
                    f"object {object_id!r}: duplicates attribute name {attribute_name!r}"
                )
            attribute_names.add(attribute_name)
            mapped_claims.add(key)
            object_observation_refs.add(observation_id)
            object_evidence_refs.update(claim.evidence_refs)
            attributes.append(
                WorldStateAttribute(
                    name=attribute_name,
                    value=claim.value,
                    basis=claim.basis,
                    verification_status="asserted",
                    valid_from=claim.observed_at or observation.observed_at,
                    valid_until=claim.valid_until,
                    uncertainty=claim.uncertainty,
                    observation_refs=(observation_id,),
                    evidence_refs=tuple(sorted(claim.evidence_refs)),
                )
            )

        objects.append(
            WorldStateObject(
                id=object_id,
                type=object_type,
                verification_status=status,
                valid_from=valid_from,
                valid_until=valid_until,
                observation_refs=tuple(sorted(object_observation_refs)),
                evidence_refs=tuple(sorted(object_evidence_refs)),
                attributes=tuple(sorted(attributes, key=lambda item: item.name)),
            )
        )

    if mapped_claims != available_claims:
        missing = sorted(available_claims - mapped_claims)
        extra = sorted(mapped_claims - available_claims)
        raise InitialSnapshotBuildError(
            f"explicit claim coverage mismatch: missing={missing}, extra={extra}"
        )

    world_observation_refs = tuple(sorted(observations))
    world_evidence_refs = tuple(
        sorted(
            {
                evidence_ref
                for observation in observations.values()
                for claim in observation.claims
                for evidence_ref in claim.evidence_refs
            }
        )
    )
    candidate = WorldState(
        world_state_id=world_state_id,
        revision=1,
        as_of=as_of_text,
        materialized_at=materialized_at_text,
        observation_refs=world_observation_refs,
        evidence_refs=world_evidence_refs,
        objects=tuple(sorted(objects, key=lambda item: item.id)),
        relations=(),
    )
    return load_world_state(candidate.to_dict())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        nargs="?",
        default=str(Path(__file__).with_name("gt22_initial_world_state_snapshot.json")),
    )
    parser.add_argument("--output", help="write the normalized World State JSON")
    args = parser.parse_args()

    state = build_initial_world_state(args.scenario)
    text = json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
