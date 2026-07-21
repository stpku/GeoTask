"""Canonicalization tests — legacy→v1, idempotent, xy→coordinates,
line→polyline, assertions→tasks, and roundtrip behavior.
"""

from __future__ import annotations

from tests.v1.conftest import _PROJECT_ROOT, _load_yaml


def test_legacy_to_canonical() -> None:
    """Load ``geotask_core_lite.yaml``, canonicalize — objects contain takeoff/school/route/zone."""
    from geotask_core.v1.canonicalizer import canonicalize

    data = _load_yaml("examples/geotask_core_lite.yaml")
    doc = canonicalize(data)

    assert "takeoff" in doc.objects
    assert "school" in doc.objects
    assert "route" in doc.objects
    assert "zone" in doc.objects
    assert doc.objects["takeoff"].type == "point"
    assert doc.objects["route"].type == "polyline"  # line → polyline mapping


def test_canonicalize_idempotent() -> None:
    """``canonicalize(canonicalize(doc).to_dict())`` produces the same CanonicalDocument."""
    from geotask_core.v1.canonicalizer import canonicalize, document_to_dict

    data = _load_yaml("examples/geotask_core_lite.yaml")
    first = canonicalize(data)
    roundtripped = canonicalize(document_to_dict(first))

    # Compare semantically — objects, metadata, operators
    assert first.metadata.id == roundtripped.metadata.id
    assert first.metadata.name == roundtripped.metadata.name
    assert sorted(first.objects.keys()) == sorted(roundtripped.objects.keys())
    assert first.operator_set == roundtripped.operator_set
    assert first.execution.mode == roundtripped.execution.mode
    assert first._source_schema_version == roundtripped._source_schema_version


def test_xy_to_coordinates() -> None:
    """Legacy point with ``xy: [1, 2]`` converts to ``data["coordinates"]: [1, 2]``."""
    from geotask_core.v1.canonicalizer import canonicalize

    doc = canonicalize({
        "ops": {},
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {"p": {"type": "point", "xy": [1, 2]}},
        "task": {},
    })
    p = doc.objects["p"]
    assert p.data.get("coordinates") == [1, 2]
    assert "xy" not in p.data  # xy should be mapped away


def test_line_to_polyline() -> None:
    """Legacy ``line`` object type maps to ``polyline`` in canonical IR."""
    from geotask_core.v1.canonicalizer import canonicalize

    doc = canonicalize({
        "ops": {"line_intersects_rect": "check"},
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "route": {"type": "line", "points": [[0, 0], [10, 10]]},
            "zone": {"type": "rect", "bbox": [0, 0, 5, 5]},
        },
        "task": {},
    })
    assert doc.objects["route"].type == "polyline"
    assert doc.objects["zone"].type == "rect"


def test_top_level_assertions_to_tasks() -> None:
    """Document with top-level ``assertions`` → they become ``tasks[0].assertions``."""
    from geotask_core.v1.canonicalizer import canonicalize

    doc = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "a": {"type": "point", "xy": [0, 0]},
            "b": {"type": "point", "xy": [3, 4]},
        },
        "ops": {"distance_2d": "compute"},
        "task": {},
        "assertions": [
            {"id": "dist_ab", "operator": "distance_2d", "object_refs": ["a", "b"]},
        ],
    })
    assert len(doc.tasks) >= 1
    task_assertions = doc.tasks[0].assertions
    assert len(task_assertions) >= 1
    assert task_assertions[0].id == "dist_ab"


def test_canonicalize_roundtrip() -> None:
    """Legacy → canonical → document_to_dict → canonicalize → same canonical."""
    from geotask_core.v1.canonicalizer import canonicalize, document_to_dict

    data = _load_yaml("examples/geotask_core_lite.yaml")
    first = canonicalize(data)
    second = canonicalize(document_to_dict(first))

    # Check objects identical
    assert sorted(first.objects.keys()) == sorted(second.objects.keys())
    for obj_id in first.objects:
        o1 = first.objects[obj_id]
        o2 = second.objects[obj_id]
        assert o1.type == o2.type
        assert o1.data == o2.data

    # Check tasks have same assertions
    assert len(first.tasks) == len(second.tasks)
    for t1, t2 in zip(first.tasks, second.tasks):
        assert len(t1.assertions) == len(t2.assertions)
        for a1, a2 in zip(t1.assertions, t2.assertions):
            assert a1.id == a2.id
            assert a1.operator == a2.operator
            assert a1.object_refs == a2.object_refs

    # Check execution
    assert first.execution.mode == second.execution.mode
    assert len(first.execution.steps) == len(second.execution.steps)

    # Check metadata
    assert first.metadata.id == second.metadata.id
    assert first.metadata.name == second.metadata.name
