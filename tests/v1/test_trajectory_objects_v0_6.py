"""v0.6 moving-object and discrete trajectory contracts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]


def _document() -> dict:
    return {
        "geotask": {
            "id": "gt33-moving-object-trajectory",
            "name": "GT33 Moving Object Trajectory",
            "description": "Validate one fictional discrete moving-object trajectory.",
            "schema_version": "1.0",
            "language": "en",
            "domain": "general_spatial",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "fictional_local_xy_m"},
            "axes": {"x": "east", "y": "north"},
            "horizontal_unit": "meter",
            "coordinate_order": ["x", "y"],
        },
        "objects": {
            "uav_alpha": {
                "type": "moving_object",
                "object_class": "uav",
                "identity": "fictional-uav-alpha",
            },
            "uav_alpha_track": {
                "type": "trajectory",
                "subject_ref": "uav_alpha",
                "interpolation": "none",
                "samples": [
                    {
                        "observed_at": "2026-08-05T08:00:00+08:00",
                        "coordinates": [0, 0],
                    },
                    {
                        "observed_at": "2026-08-05T08:02:00+08:00",
                        "coordinates": [12, 5],
                    },
                    {
                        "observed_at": "2026-08-05T08:05:00+08:00",
                        "coordinates": [30, 40],
                    },
                ],
            },
        },
        "operator_set": ["trajectory_duration_seconds"],
        "tasks": [
            {
                "id": "measure_track_duration",
                "family": "trajectory_measurement",
                "goal": "Measure elapsed time between explicit endpoint observations.",
                "assertions": [
                    {
                        "id": "track_duration_seconds",
                        "operator": "trajectory_duration_seconds",
                        "object_refs": ["uav_alpha_track"],
                        "expected_type": "number",
                        "unit": "second",
                    }
                ],
                "outputs": ["track_duration_seconds"],
            }
        ],
        "execution": {
            "mode": "local_only",
            "steps": [
                {
                    "id": "measure_duration",
                    "executor": "local",
                    "assertion_refs": ["track_duration_seconds"],
                    "depends_on": [],
                }
            ],
        },
        "verification": {
            "mode": "local_deterministic",
            "required_assurance": "local_deterministic",
        },
        "output_contract": {
            "format": "structured",
            "required_fields": ["track_duration_seconds"],
            "allow_additional_fields": False,
            "allow_model_inference": False,
        },
    }


def _diagnostics(payload: dict) -> list[dict]:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    return validate_canonical(canonicalize(payload))


def test_trajectory_executes_as_discrete_endpoint_duration() -> None:
    from geotask_core.parser import validate_document
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical
    from geotask_core.v1.validator import validate_canonical

    payload = _document()
    assert validate_document(copy.deepcopy(payload)) == []
    canonical = canonicalize(payload)
    assert canonical.objects["uav_alpha"].type == "moving_object"
    assert canonical.objects["uav_alpha_track"].type == "trajectory"
    assert validate_canonical(canonical) == []

    result = execute_canonical(canonical)
    check = result.checks[0]
    assert check.operator == "trajectory_duration_seconds"
    assert check.value == 300.0
    assert check.unit == "second"
    assert check.status == "verified"
    assert result.outputs == {"track_duration_seconds": 300.0}
    assert result.overall.status == "verified"


def test_trajectory_operator_rejects_static_polyline_substitution() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    canonical = canonicalize(_document())
    canonical.objects["uav_alpha_track"].type = "polyline"
    canonical.objects["uav_alpha_track"].data = {
        "coordinates": [[0, 0], [12, 5], [30, 40]]
    }
    diagnostics = validate_canonical(canonical)
    assert any(
        item["code"] == "object_type_mismatch"
        and "expects type 'trajectory'" in item["message"]
        for item in diagnostics
    )


def test_trajectory_subject_must_resolve_to_moving_object() -> None:
    missing = _document()
    missing["objects"]["uav_alpha_track"]["subject_ref"] = "missing_uav"
    diagnostics = _diagnostics(missing)
    assert any(
        item["code"] == "invalid_reference" and "does not resolve" in item["message"]
        for item in diagnostics
    )

    static_subject = _document()
    static_subject["objects"]["uav_alpha"] = {
        "type": "point",
        "coordinates": [0, 0],
    }
    diagnostics = _diagnostics(static_subject)
    assert any(
        item["code"] == "object_type_mismatch"
        and "expected 'moving_object'" in item["message"]
        for item in diagnostics
    )


def test_trajectory_time_is_timezone_aware_and_strictly_increasing() -> None:
    naive = _document()
    naive["objects"]["uav_alpha_track"]["samples"][1]["observed_at"] = (
        "2026-08-05T08:02:00"
    )
    diagnostics = _diagnostics(naive)
    assert any(
        item["code"] == "invalid_interval"
        and "timezone-aware" in item["message"]
        for item in diagnostics
    )

    duplicate = _document()
    duplicate["objects"]["uav_alpha_track"]["samples"][1]["observed_at"] = (
        "2026-08-05T08:00:00+08:00"
    )
    diagnostics = _diagnostics(duplicate)
    assert any(
        item["code"] == "invalid_interval"
        and "strictly increasing" in item["message"]
        for item in diagnostics
    )

    reversed_order = _document()
    reversed_order["objects"]["uav_alpha_track"]["samples"][2]["observed_at"] = (
        "2026-08-05T08:01:00+08:00"
    )
    diagnostics = _diagnostics(reversed_order)
    assert any("strictly increasing" in item["message"] for item in diagnostics)


def test_trajectory_forbids_interpolation_and_undeclared_fields() -> None:
    interpolated = _document()
    interpolated["objects"]["uav_alpha_track"]["interpolation"] = "linear"
    diagnostics = _diagnostics(interpolated)
    assert any(
        item["code"] == "invalid_type"
        and "interpolation must be exactly 'none'" in item["message"]
        for item in diagnostics
    )

    extra_sample_field = _document()
    extra_sample_field["objects"]["uav_alpha_track"]["samples"][0][
        "predicted"
    ] = True
    diagnostics = _diagnostics(extra_sample_field)
    assert any(
        item["code"] == "unknown_field" and "predicted" in item["message"]
        for item in diagnostics
    )

    embedded_position = _document()
    embedded_position["objects"]["uav_alpha"]["coordinates"] = [0, 0]
    diagnostics = _diagnostics(embedded_position)
    assert any(
        item["code"] == "unknown_field" and "coordinates" in item["message"]
        for item in diagnostics
    )


def test_trajectory_schema_declares_strict_public_shapes() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "geotask-v1.0.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    object_types = schema["$defs"]["geoObject"]["properties"]["type"]["enum"]
    assert "moving_object" in object_types
    assert "trajectory" in object_types
    assert schema["$defs"]["trajectorySampleList"]["minItems"] == 2
    assert schema["$defs"]["trajectoryData"]["additionalProperties"] is False

    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(_document())) == []

    invalid = _document()
    invalid["objects"]["uav_alpha_track"]["interpolation"] = "linear"
    assert list(validator.iter_errors(invalid))

    invalid = _document()
    invalid["objects"]["uav_alpha_track"]["samples"][0]["predicted"] = True
    assert list(validator.iter_errors(invalid))


def test_public_api_exposes_trajectory_contract() -> None:
    import geotask_core
    from geotask_core.operator_registry import get_operator_metadata, operator_names

    assert geotask_core.MovingObject.__name__ == "MovingObject"
    assert geotask_core.TrajectorySample.__name__ == "TrajectorySample"
    assert geotask_core.TrajectoryObject.__name__ == "TrajectoryObject"
    assert callable(geotask_core.trajectory_duration_seconds)
    assert "trajectory_duration_seconds" in operator_names()
    metadata = get_operator_metadata("trajectory_duration_seconds")
    assert metadata["supported_geometry"] == ["trajectory"]
    assert metadata["output_type"] == "float"
    assert metadata["semantics"]["interpolation"] == "none"
