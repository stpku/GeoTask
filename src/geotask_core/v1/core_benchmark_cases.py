"""Fixed fictional cases for the public GeoTask Core benchmark.

The cases exercise production Core APIs only. They contain no customer data,
external evidence, network access, model calls, or benchmark-local verifier.
"""

from __future__ import annotations

import json
from typing import Any


def _base_document(
    *,
    document_id: str,
    name: str,
    objects: dict[str, Any],
    operators: list[str],
    assertions: list[dict[str, Any]],
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "metadata": {
            "id": document_id,
            "name": name,
            "schema_version": "1.0",
            "language": "en",
            "domain": "general_spatial",
        },
        "space": {
            "crs": {
                "type": "local_cartesian",
                "identifier": "fictional_benchmark_grid_m",
            },
            "horizontal_unit": "meter",
            "vertical_unit": "meter",
            "coordinate_order": ["x", "y"],
            "boundary_semantics": "closed",
        },
        "objects": objects,
        "operator_set": operators,
        "tasks": [
            {
                "id": f"{document_id}.task",
                "family": "public_core_benchmark",
                "goal": "Exercise deterministic GeoTask Core contracts.",
                "assertions": assertions,
                "outputs": [item["id"] for item in assertions],
            }
        ],
        "execution": {"mode": "local_only", "steps": []},
        "verification": {
            "mode": "local_deterministic",
            "required_assurance": "local_deterministic",
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [item["id"] for item in assertions],
            "allow_additional_fields": False,
            "allow_model_inference": False,
        },
    }
    if provenance is not None:
        payload["provenance"] = provenance
    return payload


def _case(
    case_id: str,
    payload: dict[str, Any],
    *,
    expected_outputs: dict[str, Any],
    expected_evidence_refs: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "payload_json": json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
        "operators": tuple(payload["operator_set"]),
        "expected_outputs": expected_outputs,
        "expected_evidence_refs": expected_evidence_refs or {},
    }


CORE_BENCHMARK_CASES: tuple[dict[str, Any], ...] = (
    _case(
        "distance_2d",
        _base_document(
            document_id="benchmark.distance",
            name="Distance benchmark",
            objects={
                "point_a": {"type": "point", "data": {"coordinates": [0, 0]}},
                "point_b": {"type": "point", "data": {"coordinates": [3, 4]}},
            },
            operators=["distance_2d"],
            assertions=[
                {
                    "id": "distance_value",
                    "operator": "distance_2d",
                    "object_refs": ["point_a", "point_b"],
                    "expected_type": "number",
                    "unit": "meter",
                }
            ],
        ),
        expected_outputs={"distance_value": 5.0},
    ),
    _case(
        "planar_topology",
        _base_document(
            document_id="benchmark.planar-topology",
            name="Planar topology benchmark",
            objects={
                "query_point": {
                    "type": "point",
                    "data": {"coordinates": [1, 2]},
                },
                "route": {
                    "type": "polyline",
                    "data": {"coordinates": [[0, 0], [4, 0]]},
                },
                "work_rect": {
                    "type": "rect",
                    "data": {"bbox": [0, 0, 4, 4]},
                },
            },
            operators=[
                "point_to_line_distance_2d",
                "line_intersects_rect",
                "rect_contains_point",
            ],
            assertions=[
                {
                    "id": "point_line_distance",
                    "operator": "point_to_line_distance_2d",
                    "object_refs": ["query_point", "route"],
                    "expected_type": "number",
                    "unit": "meter",
                },
                {
                    "id": "route_intersects",
                    "operator": "line_intersects_rect",
                    "object_refs": ["route", "work_rect"],
                    "expected_type": "boolean",
                },
                {
                    "id": "point_contained",
                    "operator": "rect_contains_point",
                    "object_refs": ["work_rect", "query_point"],
                    "expected_type": "boolean",
                },
            ],
        ),
        expected_outputs={
            "point_line_distance": 2.0,
            "route_intersects": True,
            "point_contained": True,
        },
    ),
    _case(
        "polygon_multi_polyline",
        _base_document(
            document_id="benchmark.polygon-multi",
            name="Polygon and grouped-route benchmark",
            objects={
                "query_point": {
                    "type": "point",
                    "data": {"coordinates": [2, 2]},
                },
                "service_polygon": {
                    "type": "polygon",
                    "data": {
                        "coordinates": [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]
                    },
                },
                "grouped_routes": {
                    "type": "multi_polyline",
                    "data": {
                        "coordinates": [
                            [[-4, -4], [-3, -3]],
                            [[-1, 2], [5, 2]],
                        ]
                    },
                },
                "service_rect": {
                    "type": "rect",
                    "data": {"bbox": [0, 0, 4, 4]},
                },
            },
            operators=["point_in_polygon", "multi_polyline_intersects_rect"],
            assertions=[
                {
                    "id": "point_in_service_polygon",
                    "operator": "point_in_polygon",
                    "object_refs": ["query_point", "service_polygon"],
                    "expected_type": "boolean",
                },
                {
                    "id": "grouped_route_intersects",
                    "operator": "multi_polyline_intersects_rect",
                    "object_refs": ["grouped_routes", "service_rect"],
                    "expected_type": "boolean",
                },
            ],
        ),
        expected_outputs={
            "point_in_service_polygon": True,
            "grouped_route_intersects": True,
        },
    ),
    _case(
        "time_altitude",
        _base_document(
            document_id="benchmark.time-altitude",
            name="Time and altitude benchmark",
            objects={
                "window_a": {
                    "type": "time_interval",
                    "data": {"start": "08:00", "end": "10:00"},
                },
                "window_b": {
                    "type": "time_interval",
                    "data": {"start": "09:30", "end": "11:00"},
                },
                "altitude_a": {
                    "type": "altitude_interval",
                    "data": {
                        "min": 100,
                        "max": 200,
                        "unit": "meter",
                        "datum": "fictional_local_datum",
                    },
                },
                "altitude_b": {
                    "type": "altitude_interval",
                    "data": {
                        "min": 200,
                        "max": 260,
                        "unit": "meter",
                        "datum": "fictional_local_datum",
                    },
                },
            },
            operators=["time_overlap", "altitude_overlap"],
            assertions=[
                {
                    "id": "time_conflict",
                    "operator": "time_overlap",
                    "object_refs": ["window_a", "window_b"],
                    "expected_type": "boolean",
                },
                {
                    "id": "altitude_conflict",
                    "operator": "altitude_overlap",
                    "object_refs": ["altitude_a", "altitude_b"],
                    "expected_type": "boolean",
                },
            ],
        ),
        expected_outputs={"time_conflict": True, "altitude_conflict": True},
    ),
    _case(
        "provenance_evidence",
        _base_document(
            document_id="benchmark.provenance",
            name="Provenance benchmark",
            objects={
                "source_point": {
                    "type": "point",
                    "data": {"coordinates": [0, 0]},
                },
                "target_point": {
                    "type": "point",
                    "data": {"coordinates": [6, 8]},
                },
            },
            operators=["distance_2d"],
            assertions=[
                {
                    "id": "evidenced_distance",
                    "operator": "distance_2d",
                    "object_refs": ["source_point", "target_point"],
                    "expected_type": "number",
                    "unit": "meter",
                }
            ],
            provenance={
                "sources": [
                    {
                        "id": "fictional_dataset",
                        "kind": "dataset",
                        "title": "Fictional benchmark coordinates",
                        "uri": "urn:geotask:benchmark:fictional-dataset:0.1",
                        "version": "0.1",
                        "sha256": "3333333333333333333333333333333333333333333333333333333333333333",
                        "issued_at": "2026-08-01T00:00:00+00:00",
                        "retrieved_at": "2026-08-01T00:01:00+00:00",
                        "verified_at": "2026-08-01T00:02:00+00:00",
                    }
                ],
                "evidence_bindings": [
                    {
                        "assertion_id": "evidenced_distance",
                        "source_refs": ["fictional_dataset"],
                    }
                ],
                "audit": {
                    "generated_by": "geotask-public-core-benchmark",
                    "generator_version": "0.1",
                    "generated_at": "2026-08-01T00:03:00+00:00",
                    "audit_ref": "audit:geotask:public-core-benchmark:0.1",
                    "source_refs": ["fictional_dataset"],
                },
            },
        ),
        expected_outputs={"evidenced_distance": 10.0},
        expected_evidence_refs={"evidenced_distance": ["fictional_dataset"]},
    ),
)


CORE_BENCHMARK_OPERATOR_COVERAGE: tuple[str, ...] = tuple(
    sorted(
        {
            operator
            for case in CORE_BENCHMARK_CASES
            for operator in case["operators"]
        }
    )
)


__all__ = ["CORE_BENCHMARK_CASES", "CORE_BENCHMARK_OPERATOR_COVERAGE"]
