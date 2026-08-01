"""Container-first polygon containment operator contract and examples."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

from geotask_core.ops import point_in_polygon, polygon_contains_point
from geotask_core.parser import load_geotask
from geotask_core.runner import run_geotask
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical
from geotask_core.v1.operator_contracts import default_registry
from geotask_core.v1.validator import validate_canonical


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "core" / "v1_polygon_contains_point.yaml"
SCHEMA = ROOT / "schemas" / "geotask-v1.0.schema.json"
RING = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]


@pytest.mark.parametrize(
    ("point", "expected"),
    (
        ([5, 5], True),
        ([0, 5], True),
        ([0, 0], True),
        ([15, 5], False),
    ),
)
def test_container_first_predicate_matches_point_first_predicate(
    point: list[float], expected: bool
) -> None:
    assert polygon_contains_point(RING, point) is expected
    assert point_in_polygon(point, RING) is expected


def test_public_contract_declares_explicit_container_first_order() -> None:
    import geotask_core

    assert geotask_core.polygon_contains_point is polygon_contains_point
    contract = default_registry.get("polygon_contains_point")

    assert contract.input_types == ["polygon", "point"]
    assert contract.arity == 2
    assert contract.output == {"type": "boolean"}
    assert contract.deterministic is True
    assert contract.implementation == "geotask_core.ops.polygon_contains_point"
    assert contract.semantics["argument_order"] == ["polygon", "point"]
    assert contract.semantics["equivalent_predicate"] == (
        "point_in_polygon(point, polygon)"
    )
    assert any(
        item["id"] == "predicate_equivalence" for item in contract.invariants
    )


def test_public_example_matches_schema_validates_and_executes() -> None:
    payload = load_geotask(EXAMPLE)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(payload, schema)

    canonical = canonicalize(payload)
    assert validate_canonical(canonical) == []

    result = execute_canonical(canonical)
    checks = {
        check.assertion_id: (check.value, check.status, check.operator)
        for check in result.checks
    }
    assert checks == {
        "inside_contained": (True, "verified", "polygon_contains_point"),
        "edge_contained": (True, "verified", "polygon_contains_point"),
        "outside_contained": (False, "verified", "polygon_contains_point"),
    }


def test_reversed_object_order_fails_closed() -> None:
    payload = load_geotask(EXAMPLE)
    payload["tasks"][0]["assertions"][0]["object_refs"] = [
        "inside_point",
        "service_zone",
    ]
    canonical = canonicalize(payload)

    diagnostics = validate_canonical(canonical)
    assert any(item["code"] == "object_type_mismatch" for item in diagnostics)

    result = execute_canonical(canonical)
    assert result.execution.status == "failed"
    assert result.overall.assurance_level == "unverified"


def test_legacy_runner_preserves_alias_name_and_object_order() -> None:
    legacy = {
        "geotask": {"version": "0.3", "name": "alias", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "zone": {"type": "polygon", "points": copy.deepcopy(RING)},
            "query": {"type": "point", "xy": [5, 5]},
        },
        "ops": {"polygon_contains_point": "containment"},
        "task": {},
    }

    result = run_geotask(legacy)
    assert result["measurements"] == [
        {
            "name": "zone_contains_query",
            "value": True,
            "unit": None,
            "object_refs": ["zone", "query"],
            "verified_by": "polygon_contains_point",
        }
    ]
    assert result["verified_by"] == [
        {"operation": "polygon_contains_point", "result": "true"}
    ]


def test_schema_metadata_names_both_argument_orders() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    operator_name = schema["$defs"]["operatorName"]

    assert "polygon_contains_point(polygon, point)" in operator_name["description"]
    assert "polygon_contains_point" in operator_name["examples"]
