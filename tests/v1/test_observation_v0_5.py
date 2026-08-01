"""Observation v0.1 public world-model Artifact tests."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "core" / "observation_uav_delay.json"
SCHEMA = ROOT / "schemas" / "geotask-observation-v0.1.schema.json"


def _payload() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_observation_example_loads_and_round_trips() -> None:
    from geotask_core.v1.observation import load_observation

    observation = load_observation(_payload())
    assert observation.observation_id == "obs-fictional-uav-a-delay-4402"
    assert observation.source.kind == "sensor"
    assert observation.producer.kind == "software"
    assert len(observation.claims) == 2
    assert observation.claims[0].value == 40
    assert observation.claims[0].uncertainty is not None
    assert observation.claims[0].uncertainty.kind == "standard_deviation"
    assert observation.claims[1].uncertainty is not None
    assert observation.claims[1].uncertainty.value == "low"
    assert observation.to_dict() == _payload()


def test_observation_schema_is_valid_and_accepts_example() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    assert list(validator.iter_errors(_payload())) == []


def test_unified_artifact_validation_preserves_truth_boundary() -> None:
    from geotask_core.v1.artifact_validation import validate_artifact_payload

    report = validate_artifact_payload("geotask.observation", _payload())
    assert report.valid is True
    assert report.schema_verified is True
    assert report.summary == {
        "observation_id": "obs-fictional-uav-a-delay-4402",
        "source_kind": "sensor",
        "producer_kind": "software",
        "claim_count": 2,
        "uncertain_claim_count": 2,
        "supersedes_count": 1,
        "truth_verified": False,
        "world_state_updated": False,
    }


def test_duplicate_claim_evidence_and_supersession_fail_closed() -> None:
    from geotask_core.v1.observation import ObservationFormatError, load_observation

    duplicate_claim = _payload()
    duplicate_claim["observation"]["claims"][1]["id"] = (
        duplicate_claim["observation"]["claims"][0]["id"]
    )
    with pytest.raises(ObservationFormatError, match="duplicates claim id"):
        load_observation(duplicate_claim)

    duplicate_evidence = _payload()
    duplicate_evidence["observation"]["claims"][0]["evidence_refs"] = ["x", "x"]
    with pytest.raises(ObservationFormatError, match="duplicates 'x'"):
        load_observation(duplicate_evidence)

    self_supersession = _payload()
    self_supersession["observation"]["supersedes"] = [
        self_supersession["observation"]["observation_id"]
    ]
    with pytest.raises(ObservationFormatError, match="must not contain"):
        load_observation(self_supersession)


def test_observation_and_claim_time_order_fail_closed() -> None:
    from geotask_core.v1.observation import ObservationFormatError, load_observation

    received_before_observed = _payload()
    received_before_observed["observation"]["received_at"] = (
        "2026-08-01T08:30:04+08:00"
    )
    with pytest.raises(ObservationFormatError, match="received_at"):
        load_observation(received_before_observed)

    claim_after_received = _payload()
    claim_after_received["observation"]["claims"][0]["observed_at"] = (
        "2026-08-01T08:30:07+08:00"
    )
    with pytest.raises(ObservationFormatError, match="must not be later"):
        load_observation(claim_after_received)

    expired_before_observed = _payload()
    expired_before_observed["observation"]["claims"][0]["valid_until"] = (
        "2026-08-01T08:30:04+08:00"
    )
    with pytest.raises(ObservationFormatError, match="must not be earlier"):
        load_observation(expired_before_observed)


def test_uncertainty_contract_fails_closed() -> None:
    from geotask_core.v1.observation import ObservationFormatError, load_observation

    bad_probability = _payload()
    bad_probability["observation"]["claims"][0]["uncertainty"] = {
        "kind": "probability_of_error",
        "value": 1.2,
    }
    with pytest.raises(ObservationFormatError, match="between 0 and 1"):
        load_observation(bad_probability)

    qualitative_unit = _payload()
    qualitative_unit["observation"]["claims"][1]["uncertainty"]["unit"] = "level"
    with pytest.raises(ObservationFormatError, match="not allowed"):
        load_observation(qualitative_unit)

    negative_width = _payload()
    negative_width["observation"]["claims"][0]["uncertainty"] = {
        "kind": "interval_width",
        "value": -1,
        "unit": "second",
    }
    with pytest.raises(ObservationFormatError, match="greater than or equal to 0"):
        load_observation(negative_width)


def test_unknown_fields_and_nonfinite_claims_fail_closed() -> None:
    from geotask_core.v1.observation import ObservationFormatError, load_observation

    unknown = _payload()
    unknown["observation"]["verified"] = True
    with pytest.raises(ObservationFormatError, match="unknown fields"):
        load_observation(unknown)

    nonfinite = _payload()
    nonfinite["observation"]["claims"][0]["value"] = float("nan")
    with pytest.raises(ObservationFormatError, match="non-finite"):
        load_observation(nonfinite)


def test_registry_and_schema_bundle_publish_observation() -> None:
    from geotask_core.v1.artifact_registry import (
        artifact_registry_payload,
        get_artifact_descriptor,
    )
    from geotask_core.v1.observation import OBSERVATION_SCHEMA_ID
    from geotask_core.v1.schema_bundle import list_bundled_schema_ids, load_artifact_schema

    descriptor = get_artifact_descriptor("geotask.observation")
    assert descriptor.wrapper_key == "observation"
    assert descriptor.schema_path == "schemas/geotask-observation-v0.1.schema.json"
    assert descriptor.generation_command is None
    assert "WorldState" in descriptor.execution_boundary

    registry = artifact_registry_payload()["artifact_registry"]
    observation = next(
        item for item in registry["artifacts"] if item["artifact_id"] == "geotask.observation"
    )
    assert "*.geotask-observation.json" in observation["ide_file_patterns"]
    assert OBSERVATION_SCHEMA_ID in list_bundled_schema_ids()
    assert load_artifact_schema("geotask.observation")["$id"] == OBSERVATION_SCHEMA_ID


def test_cli_validates_observation_without_claiming_truth() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "geotask_core.cli",
            "artifact",
            "validate",
            "geotask.observation",
            str(EXAMPLE),
            "--format",
            "json",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)["artifact_validation"]
    assert payload["valid"] is True
    assert payload["summary"]["claim_count"] == 2
    assert payload["summary"]["truth_verified"] is False
    assert payload["summary"]["world_state_updated"] is False


def test_public_api_exports_observation_contract() -> None:
    import geotask_core
    import geotask_core.v1 as v1

    assert geotask_core.OBSERVATION_ARTIFACT_ID == "geotask.observation"
    assert v1.OBSERVATION_SCHEMA_VERSION == "0.1"
    assert callable(geotask_core.load_observation)


def test_loader_does_not_mutate_input() -> None:
    from geotask_core.v1.observation import load_observation

    payload = _payload()
    before = copy.deepcopy(payload)
    load_observation(payload)
    assert payload == before
