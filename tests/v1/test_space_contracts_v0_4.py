"""v0.4 cross-task CRS, unit, coordinate-order, and boundary contracts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]


def _base_document() -> dict:
    return {
        "geotask": {
            "id": "space-contract-test",
            "name": "Space Contract Test",
            "description": "Exercise document-wide space execution gates.",
            "schema_version": "1.0",
            "language": "en",
            "domain": "general_spatial",
        },
        "space": {
            "crs": {
                "type": "local_cartesian",
                "identifier": "fictional_local_xy_m",
            },
            "axes": {"x": "east", "y": "north"},
            "horizontal_unit": "meter",
            "vertical_unit": "meter",
            "coordinate_order": ["x", "y"],
            "boundary_semantics": "closed",
        },
        "objects": {
            "point_a": {"type": "point", "coordinates": [0, 0]},
            "point_b": {"type": "point", "coordinates": [3, 4]},
            "route": {
                "type": "polyline",
                "coordinates": [[-2, 5], [12, 5]],
            },
            "window": {"type": "rect", "bbox": [0, 0, 10, 10]},
            "altitude_a": {
                "type": "altitude_interval",
                "min": 100,
                "max": 150,
                "unit": "meter",
                "datum": "fictional_datum",
            },
            "altitude_b": {
                "type": "altitude_interval",
                "min": 120,
                "max": 180,
                "unit": "metre",
                "datum": "fictional_datum",
            },
        },
        "operator_set": [
            "distance_2d",
            "line_intersects_rect",
            "altitude_overlap",
        ],
        "tasks": [
            {
                "id": "measurement_task",
                "family": "measurement",
                "goal": "Measure under the shared horizontal unit.",
                "assertions": [
                    {
                        "id": "distance_check",
                        "operator": "distance_2d",
                        "object_refs": ["point_a", "point_b"],
                        "expected_type": "number",
                        "unit": "metre",
                    }
                ],
            },
            {
                "id": "topology_task",
                "family": "topology",
                "goal": "Evaluate under the shared boundary semantics.",
                "assertions": [
                    {
                        "id": "intersection_check",
                        "operator": "line_intersects_rect",
                        "object_refs": ["route", "window"],
                        "expected_type": "boolean",
                    }
                ],
            },
            {
                "id": "vertical_task",
                "family": "vertical",
                "goal": "Evaluate under the shared vertical unit and datum.",
                "assertions": [
                    {
                        "id": "altitude_check",
                        "operator": "altitude_overlap",
                        "object_refs": ["altitude_a", "altitude_b"],
                        "expected_type": "boolean",
                    }
                ],
            },
        ],
        "execution": {
            "mode": "local_only",
            "steps": [
                {
                    "id": "evaluate",
                    "executor": "local",
                    "assertion_refs": [
                        "distance_check",
                        "intersection_check",
                        "altitude_check",
                    ],
                    "depends_on": [],
                }
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [
                "distance_check",
                "intersection_check",
                "altitude_check",
            ],
            "allow_additional_fields": True,
        },
    }


def _diagnostics(payload: dict) -> list[dict]:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    return validate_canonical(canonicalize(payload))


def test_valid_cross_task_space_contract_executes() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical
    from geotask_core.v1.validator import validate_canonical

    canonical = canonicalize(_base_document())
    assert canonical.space.boundary_semantics == "closed"
    assert validate_canonical(canonical) == []

    result = execute_canonical(canonical)
    assert result.execution.status == "completed"
    assert result.outputs == {
        "distance_check": 5.0,
        "intersection_check": True,
        "altitude_check": True,
    }
    checks = {check.assertion_id: check for check in result.checks}
    assert checks["distance_check"].unit == "meter"
    assert result.overall.status == "verified"


def test_geographic_and_unknown_crs_block_planar_operators() -> None:
    geographic = _base_document()
    geographic["space"]["crs"] = {
        "type": "geographic",
        "identifier": "EPSG:4326",
    }
    diagnostics = _diagnostics(geographic)
    assert any(
        diagnostic["code"] == "invalid_crs"
        and diagnostic["path"] == "space.crs.type"
        and "does not project geographic coordinates" in diagnostic["message"]
        for diagnostic in diagnostics
    )

    unknown = _base_document()
    unknown["space"]["crs"] = {"type": "unknown", "identifier": ""}
    diagnostics = _diagnostics(unknown)
    assert any(
        diagnostic["code"] == "invalid_crs"
        and "unknown CRS" in diagnostic["message"]
        for diagnostic in diagnostics
    )


def test_geographic_crs_is_allowed_for_pure_time_task() -> None:
    payload = _base_document()
    payload["space"]["crs"] = {
        "type": "geographic",
        "identifier": "EPSG:4326",
    }
    payload["objects"] = {
        "window_a": {"type": "time_interval", "start": "08:00", "end": "09:00"},
        "window_b": {"type": "time_interval", "start": "08:30", "end": "10:00"},
    }
    payload["operator_set"] = ["time_overlap"]
    payload["tasks"] = [
        {
            "id": "time_task",
            "family": "temporal",
            "goal": "Evaluate time only.",
            "assertions": [
                {
                    "id": "time_check",
                    "operator": "time_overlap",
                    "object_refs": ["window_a", "window_b"],
                    "expected_type": "boolean",
                }
            ],
        }
    ]
    payload["execution"]["steps"][0]["assertion_refs"] = ["time_check"]
    payload["output_contract"]["required_fields"] = ["time_check"]

    assert _diagnostics(payload) == []


def test_projected_crs_requires_identifier_for_planar_execution() -> None:
    payload = _base_document()
    payload["space"]["crs"] = {"type": "projected", "identifier": ""}

    diagnostics = _diagnostics(payload)
    assert any(
        diagnostic["code"] == "invalid_crs"
        and diagnostic["path"] == "space.crs.identifier"
        for diagnostic in diagnostics
    )


def test_planar_coordinate_order_and_distance_unit_fail_closed() -> None:
    payload = _base_document()
    payload["space"]["coordinate_order"] = ["y", "x"]
    payload["tasks"][0]["assertions"][0]["unit"] = "kilometer"

    diagnostics = _diagnostics(payload)
    assert any(
        diagnostic["code"] == "invalid_coordinates"
        and diagnostic["path"] == "space.coordinate_order"
        and "require coordinate_order [x, y]" in diagnostic["message"]
        for diagnostic in diagnostics
    )
    assert any(
        diagnostic["code"] == "unit_mismatch"
        and diagnostic["path"] == "tasks.measurement_task.assertions[0].unit"
        for diagnostic in diagnostics
    )


def test_common_unit_aliases_are_equivalent_without_conversion() -> None:
    payload = _base_document()
    payload["space"]["horizontal_unit"] = "meters"
    payload["tasks"][0]["assertions"][0]["unit"] = "metre"
    payload["space"]["vertical_unit"] = "m"
    payload["objects"]["altitude_a"]["unit"] = "meters"
    payload["objects"]["altitude_b"]["unit"] = "metres"

    assert _diagnostics(payload) == []


def test_altitude_unit_and_datum_mismatches_fail_closed() -> None:
    payload = _base_document()
    payload["objects"]["altitude_b"]["unit"] = "foot"
    payload["objects"]["altitude_b"]["datum"] = "different_datum"

    diagnostics = _diagnostics(payload)
    assert any(
        diagnostic["code"] == "unit_mismatch"
        and diagnostic["path"] == "objects.altitude_b.data.unit"
        for diagnostic in diagnostics
    )
    assert any(
        diagnostic["code"] == "invalid_crs"
        and "incompatible vertical datums" in diagnostic["message"]
        for diagnostic in diagnostics
    )


def test_open_boundary_is_blocked_only_for_boundary_sensitive_operators() -> None:
    payload = _base_document()
    payload["space"]["boundary_semantics"] = "open"
    diagnostics = _diagnostics(payload)
    assert any(
        diagnostic["code"] == "boundary_semantics_mismatch"
        and diagnostic["path"] == "space.boundary_semantics"
        for diagnostic in diagnostics
    )

    distance_only = _base_document()
    distance_only["space"]["boundary_semantics"] = "open"
    distance_only["objects"] = {
        "point_a": {"type": "point", "coordinates": [0, 0]},
        "point_b": {"type": "point", "coordinates": [3, 4]},
    }
    distance_only["operator_set"] = ["distance_2d"]
    distance_only["tasks"] = [copy.deepcopy(distance_only["tasks"][0])]
    distance_only["execution"]["steps"][0]["assertion_refs"] = ["distance_check"]
    distance_only["output_contract"]["required_fields"] = ["distance_check"]
    assert _diagnostics(distance_only) == []


def test_invalid_space_contract_blocks_execution() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    payload = _base_document()
    payload["space"]["crs"] = {
        "type": "geographic",
        "identifier": "EPSG:4326",
    }
    result = execute_canonical(canonicalize(payload))
    assert result.execution.status == "failed"
    assert result.overall.status == "unverifiable"
    assert any(error["code"] == "invalid_crs" for error in result.errors)


def test_schema_and_round_trip_preserve_boundary_semantics() -> None:
    from geotask_core.v1.canonicalizer import document_to_dict, canonicalize

    schema = json.loads(
        (ROOT / "schemas" / "geotask-v1.0.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    payload = _base_document()
    assert list(validator.iter_errors(payload)) == []

    invalid_order = copy.deepcopy(payload)
    invalid_order["space"]["coordinate_order"] = ["x", "y", "z"]
    assert list(validator.iter_errors(invalid_order))

    invalid_boundary = copy.deepcopy(payload)
    invalid_boundary["space"]["boundary_semantics"] = "half_open"
    assert list(validator.iter_errors(invalid_boundary))

    canonical = canonicalize(payload)
    restored = document_to_dict(canonical)
    assert restored["space"]["boundary_semantics"] == "closed"


def test_public_space_contract_example_validates_and_executes() -> None:
    from geotask_core.parser import load_geotask
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical
    from geotask_core.v1.validator import validate_canonical

    payload = load_geotask(
        ROOT / "examples" / "core" / "v1_cross_task_space_contract.yaml"
    )
    canonical = canonicalize(payload)
    assert validate_canonical(canonical) == []
    result = execute_canonical(canonical)
    assert result.outputs == {
        "distance_check": 5.0,
        "intersection_check": True,
        "altitude_check": True,
    }
    assert result.overall.status == "verified"
