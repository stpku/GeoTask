"""v0.4 common spatial object and deterministic operator contracts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]


def _document() -> dict:
    return {
        "geotask": {
            "id": "object-extensions-v0-4",
            "name": "Object Extensions v0.4",
            "description": "Exercise polygon and multi-polyline contracts.",
            "schema_version": "1.0",
            "language": "en",
            "domain": "general_spatial",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "axes": {"x": "east", "y": "north"},
            "horizontal_unit": "meter",
            "coordinate_order": ["x", "y"],
        },
        "objects": {
            "query_point": {"type": "point", "coordinates": [5, 5]},
            "zone": {
                "type": "polygon",
                "coordinates": [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
            },
            "routes": {
                "type": "multi_polyline",
                "coordinates": [
                    [[-10, -10], [-5, -5]],
                    [[-2, 5], [12, 5]],
                ],
            },
            "window": {"type": "rect", "bbox": [0, 0, 10, 10]},
        },
        "operator_set": [
            "point_in_polygon",
            "multi_polyline_intersects_rect",
        ],
        "tasks": [
            {
                "id": "evaluate_extensions",
                "family": "topology",
                "goal": "Evaluate the two new deterministic object contracts.",
                "assertions": [
                    {
                        "id": "point_contained",
                        "operator": "point_in_polygon",
                        "object_refs": ["query_point", "zone"],
                        "expected_type": "boolean",
                    },
                    {
                        "id": "route_intersects",
                        "operator": "multi_polyline_intersects_rect",
                        "object_refs": ["routes", "window"],
                        "expected_type": "boolean",
                    },
                ],
            }
        ],
        "execution": {
            "mode": "local_only",
            "steps": [
                {
                    "id": "evaluate",
                    "executor": "local",
                    "assertion_refs": ["point_contained", "route_intersects"],
                    "depends_on": [],
                }
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": ["point_contained", "route_intersects"],
            "allow_additional_fields": True,
        },
    }


def test_polygon_and_multi_polyline_execute_through_canonical_contracts() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical
    from geotask_core.v1.validator import validate_canonical

    canonical = canonicalize(_document())
    assert canonical.objects["zone"].type == "polygon"
    assert canonical.objects["routes"].type == "multi_polyline"
    assert validate_canonical(canonical) == []

    result = execute_canonical(canonical)
    checks = {check.assertion_id: check for check in result.checks}
    assert checks["point_contained"].value is True
    assert checks["point_contained"].status == "verified"
    assert checks["route_intersects"].value is True
    assert checks["route_intersects"].status == "verified"


def test_polygon_boundary_is_contained_and_outside_point_is_not() -> None:
    from geotask_core.ops import point_in_polygon

    ring = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    assert point_in_polygon([0, 5], ring) is True
    assert point_in_polygon([5, 5], ring) is True
    assert point_in_polygon([15, 5], ring) is False


def test_multi_polyline_checks_every_member_and_boundary_contact() -> None:
    from geotask_core.ops import multi_polyline_intersects_rect

    bbox = [0, 0, 10, 10]
    miss_then_touch = [
        [[-10, -10], [-5, -5]],
        [[-2, 0], [0, 0]],
    ]
    all_miss = [
        [[-10, -10], [-5, -5]],
        [[20, 20], [30, 30]],
    ]
    assert multi_polyline_intersects_rect(miss_then_touch, bbox) is True
    assert multi_polyline_intersects_rect(all_miss, bbox) is False


def test_invalid_polygon_and_multi_polyline_fail_closed() -> None:
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    open_ring = _document()
    open_ring["objects"]["zone"]["coordinates"][-1] = [1, 1]
    diagnostics = validate_canonical(canonicalize(open_ring))
    assert any(
        diagnostic["code"] == "invalid_geometry"
        and "not closed" in diagnostic["message"]
        for diagnostic in diagnostics
    )

    invalid_member = _document()
    invalid_member["objects"]["routes"]["coordinates"][0] = [[0, 0]]
    diagnostics = validate_canonical(canonicalize(invalid_member))
    assert any(
        diagnostic["code"] == "invalid_geometry"
        and "at least 2 points" in diagnostic["message"]
        for diagnostic in diagnostics
    )

    non_finite = _document()
    non_finite["objects"]["zone"]["coordinates"][1][0] = float("inf")
    diagnostics = validate_canonical(canonicalize(non_finite))
    assert any(diagnostic["code"] == "invalid_coordinates" for diagnostic in diagnostics)


def test_public_schema_declares_new_object_shapes_and_validates_document() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "geotask-v1.0.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    object_types = schema["$defs"]["geoObject"]["properties"]["type"]["enum"]
    assert "polygon" in object_types
    assert "multi_polyline" in object_types
    assert schema["$defs"]["coordinateRing"]["minItems"] == 4
    assert schema["$defs"]["multiCoordinateList"]["minItems"] == 1
    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(_document())) == []

    short_ring = _document()
    short_ring["objects"]["zone"]["coordinates"] = [[0, 0], [1, 0], [0, 0]]
    assert list(validator.iter_errors(short_ring))

    empty_collection = _document()
    empty_collection["objects"]["routes"]["coordinates"] = []
    assert list(validator.iter_errors(empty_collection))

    wrapped = _document()
    wrapped["objects"]["zone"] = {
        "type": "polygon",
        "data": {
            "coordinates": [[0, 0], [1, 0], [1, 1], [0, 0]],
        },
    }
    wrapped["objects"]["routes"] = {
        "type": "multi_polyline",
        "data": {"lines": [[[0, 0], [1, 1]]]},
    }
    assert list(validator.iter_errors(wrapped)) == []

    wrapped["objects"]["zone"]["data"]["coordinates"] = [[0, 0], [1, 0]]
    assert list(validator.iter_errors(wrapped))


def test_public_example_validates_and_executes() -> None:
    from geotask_core.parser import load_geotask
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical
    from geotask_core.v1.validator import validate_canonical

    payload = load_geotask(ROOT / "examples" / "core" / "v1_polygon_multi_polyline.yaml")
    canonical = canonicalize(payload)
    assert validate_canonical(canonical) == []
    checks = {
        check.assertion_id: check.value
        for check in execute_canonical(canonical).checks
    }
    assert checks == {
        "point_contained": True,
        "route_intersects": True,
    }


def test_legacy_runner_and_verifier_support_new_registry_entries() -> None:
    from geotask_core.runner import run_geotask
    from geotask_core.verifier import verify_normalized_result

    legacy = {
        "geotask": {"version": "0.3", "name": "extensions", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "query": {"type": "point", "xy": [5, 5]},
            "zone": {
                "type": "polygon",
                "points": [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
            },
            "routes": {
                "type": "multi_polyline",
                "lines": [
                    [[-10, -10], [-5, -5]],
                    [[-2, 5], [12, 5]],
                ],
            },
            "window": {"type": "rect", "bbox": [0, 0, 10, 10]},
        },
        "ops": {
            "point_in_polygon": "containment",
            "multi_polyline_intersects_rect": "intersection",
        },
        "task": {},
    }
    local = run_geotask(copy.deepcopy(legacy))
    measurements = {item["name"]: item for item in local["measurements"]}
    assert measurements["zone_contains_query"]["value"] is True
    assert measurements["routes_intersects_window"]["value"] is True
    assert {item["operation"] for item in local["verified_by"]} == {
        "point_in_polygon",
        "multi_polyline_intersects_rect",
    }

    normalized = {
        "measurements": list(measurements.values()),
        "conclusion": {
            "summary": "fictional local verification",
            "external_data_used": False,
            "review_reasons": [],
        },
        "verified_by": local["verified_by"],
    }
    verified = verify_normalized_result(normalized, copy.deepcopy(legacy))
    assert {item["status"] for item in verified["measurements"]} == {"verified"}
    assert verified["conclusion"]["overall_status"] == "verified"


def test_legacy_runner_uses_exact_operator_names() -> None:
    from geotask_core.runner import run_geotask

    legacy = {
        "geotask": {"version": "0.3", "name": "exact-ops", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "query": {"type": "point", "xy": [0, 1]},
            "unused_point": {"type": "point", "xy": [10, 10]},
            "route": {"type": "line", "points": [[0, 0], [10, 0]]},
        },
        "ops": {"point_to_line_distance_2d": "distance"},
        "task": {},
    }
    result = run_geotask(legacy)
    assert [item["verified_by"] for item in result["measurements"]] == [
        "point_to_line_distance_2d"
    ]


def test_legacy_parser_and_public_api_expose_new_contracts() -> None:
    import geotask_core
    from geotask_core.parser import validate_geotask_diagnostics

    legacy = {
        "geotask": {"version": "0.3", "name": "extensions", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "zone": {
                "type": "polygon",
                "points": [[0, 0], [1, 0], [1, 1], [0, 0]],
            },
            "routes": {
                "type": "multi_polyline",
                "lines": [[[0, 0], [1, 1]]],
            },
        },
        "ops": {
            "point_in_polygon": "containment",
            "multi_polyline_intersects_rect": "intersection",
        },
        "task": {},
    }
    assert validate_geotask_diagnostics(copy.deepcopy(legacy)) == []
    assert geotask_core.PolygonObject.__name__ == "PolygonObject"
    assert geotask_core.MultiPolylineObject.__name__ == "MultiPolylineObject"
    assert callable(geotask_core.point_in_polygon)
    assert callable(geotask_core.multi_polyline_intersects_rect)
