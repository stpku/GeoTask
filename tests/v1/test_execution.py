"""Execution tests — operator dispatch, distance, intersects,
polyline handling, depends_on, on_error policies, conditions, and edge cases.
"""

from __future__ import annotations

import math
from pathlib import Path

from tests.v1.conftest import _PROJECT_ROOT


# ═══════════════════════════════════════════════════════════════════════════════
#  Test operator helpers — runtime failure injection
# ═══════════════════════════════════════════════════════════════════════════════


def _setup_failing_operator() -> None:
    """Register ``_test_always_fails`` operator for runtime failure testing."""
    import geotask_core.ops as ops_mod
    from geotask_core.v1.operator_contracts import OperatorContract, default_registry

    def _always_fails(*args, **kwargs):
        raise RuntimeError("test: always fails")

    setattr(ops_mod, "_test_always_fails", _always_fails)

    contract = OperatorContract(
        name="_test_always_fails",
        version="1.0",
        family="test",
        description="Always fails for testing.",
        arity=1,
        input_types=["point"],
        output={"type": "number"},
        deterministic=True,
        model_execution={},
        implementation="geotask_core.ops._test_always_fails",
    )

    if "_test_always_fails" in default_registry._contracts:
        del default_registry._contracts["_test_always_fails"]
    default_registry.register(contract)


def _teardown_failing_operator() -> None:
    """Remove ``_test_always_fails`` from registry and ops module."""
    import geotask_core.ops as ops_mod
    from geotask_core.v1.operator_contracts import default_registry

    if "_test_always_fails" in default_registry._contracts:
        del default_registry._contracts["_test_always_fails"]
    if hasattr(ops_mod, "_test_always_fails"):
        delattr(ops_mod, "_test_always_fails")


# ═══════════════════════════════════════════════════════════════════════════════
#  Execution correctness
# ═══════════════════════════════════════════════════════════════════════════════


def test_same_operator_called_twice() -> None:
    """Task with two ``distance_2d`` assertions on different object pairs — both produce correct values."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    doc = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "a": {"type": "point", "xy": [0, 0]},
            "b": {"type": "point", "xy": [3, 4]},
            "c": {"type": "point", "xy": [6, 8]},
        },
        "ops": {"distance_2d": "compute"},
        "task": {},
        "assertions": [
            {"id": "dist_ab", "operator": "distance_2d", "object_refs": ["a", "b"]},
            {"id": "dist_bc", "operator": "distance_2d", "object_refs": ["b", "c"]},
        ],
    })
    result = execute_canonical(doc)
    values = {chk.assertion_id: chk.value for chk in result.checks}

    assert math.isclose(values["dist_ab"], 5.0, rel_tol=1e-6)
    assert math.isclose(values["dist_bc"], 5.0, rel_tol=1e-6)


def test_object_order_independence() -> None:
    """Swapping object references in YAML yields the same execution result."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    doc_ab = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "a": {"type": "point", "xy": [0, 0]},
            "b": {"type": "point", "xy": [3, 4]},
        },
        "ops": {"distance_2d": "compute"},
        "task": {},
        "assertions": [
            {"id": "dist", "operator": "distance_2d", "object_refs": ["a", "b"]},
        ],
    })
    res_ab = execute_canonical(doc_ab)

    doc_ba = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "a": {"type": "point", "xy": [3, 4]},
            "b": {"type": "point", "xy": [0, 0]},
        },
        "ops": {"distance_2d": "compute"},
        "task": {},
        "assertions": [
            {"id": "dist", "operator": "distance_2d", "object_refs": ["b", "a"]},
        ],
    })
    res_ba = execute_canonical(doc_ba)

    assert math.isclose(res_ab.checks[0].value, res_ba.checks[0].value, rel_tol=1e-6)


# ═══════════════════════════════════════════════════════════════════════════════
#  Polyline segment handling
# ═══════════════════════════════════════════════════════════════════════════════


def test_polyline_all_segments() -> None:
    """Polyline with 3+ points — ``point_to_line_distance_2d`` checks all segments.

    Point [12, 5] to polyline [[0,0], [10,0], [10,10]]:
    - Segment 1 ([0,0]→[10,0]): projection t=1.0 → [10,0] → distance sqrt(29) ≈ 5.385
    - Segment 2 ([10,0]→[10,10]): projection t=0.5 → [10,5] → distance 2.0
    Minimum = 2.0 (closest segment is the second one).
    """
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    doc = canonicalize({
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local_xy_m", "unit": "meter"},
        "objects": {
            "query_pt": {"type": "point", "xy": [12, 5]},
            "poly": {"type": "line", "points": [[0, 0], [10, 0], [10, 10]]},
        },
        "ops": {"point_to_line_distance_2d": "distance from point to polyline"},
        "task": {},
        "assertions": [
            {"id": "ptl", "operator": "point_to_line_distance_2d",
             "object_refs": ["query_pt", "poly"]},
        ],
    })
    result = execute_canonical(doc)
    check = result.checks[0]

    # Correct multi-segment distance: minimum is 2.0 (second segment)
    assert math.isclose(check.value, 2.0, rel_tol=1e-6), (
        f"Expected min-segment distance 2.0, got {check.value:.4f}"
    )
    assert check.status == "verified"


def test_line_intersects_second_segment() -> None:
    """Polyline where first segment misses rect but second segment crosses it → True.

    Rect: [0, 0, 5, 5]
    Polyline: [[-2, 6], [6, 6], [2, 2]]
      Segment 1: (-2,6)→(6,6) — entirely above rect (y=6 > max_y=5) → no intersection
      Segment 2: (6,6)→(2,2) — enters rect [0,0,5,5] at ~(4.3,5) or internally → intersection
    """
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "seg-test",
            "name": "Segment Intersection",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "poly": {
                "type": "polyline",
                "data": {"coordinates": [[-2, 6], [6, 6], [2, 2]]},
            },
            "zone": {
                "type": "rect",
                "data": {"bbox": [0, 0, 5, 5]},
            },
        },
        "operator_set": ["line_intersects_rect"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "intersects",
                    "operator": "line_intersects_rect",
                    "object_refs": ["poly", "zone"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["intersects"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    assert len(result.checks) == 1
    assert result.checks[0].value is True, (
        f"Expected intersection (second segment), got {result.checks[0].value}"
    )
    assert result.checks[0].status == "verified"


def test_point_to_polyline_nearest_not_first() -> None:
    """Point closest to non-first segment of a polyline → correct min distance.

    Point [12, 5] to polyline [[0,0], [10,0], [10,10]]:
      Segment 1 ([0,0]→[10,0]): distance ≈ 5.385
      Segment 2 ([10,0]→[10,10]): distance = 2.0  (closest)
    Min distance = 2.0 — NOT from the first segment.
    """
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "ptl-test",
            "name": "Point-to-Line Nearest",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "pt": {
                "type": "point",
                "data": {"coordinates": [12, 5]},
            },
            "poly": {
                "type": "polyline",
                "data": {"coordinates": [[0, 0], [10, 0], [10, 10]]},
            },
        },
        "operator_set": ["point_to_line_distance_2d"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "min_dist",
                    "operator": "point_to_line_distance_2d",
                    "object_refs": ["pt", "poly"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["min_dist"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    assert len(result.checks) == 1
    assert math.isclose(result.checks[0].value, 2.0, rel_tol=1e-6), (
        f"Expected min distance 2.0 (from second segment), got {result.checks[0].value}"
    )
    assert result.checks[0].status == "verified"


# ═══════════════════════════════════════════════════════════════════════════════
#  Summary / depends_on
# ═══════════════════════════════════════════════════════════════════════════════


def test_execution_summary_counts() -> None:
    """Execution result summary correctly counts verified checks."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

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
            {"id": "dist_ba", "operator": "distance_2d", "object_refs": ["b", "a"]},
        ],
    })
    result = execute_canonical(doc)
    assert result.summary.total_checks == 2
    assert result.summary.verified == 2
    assert result.summary.invalid == 0


def test_depends_on_skip() -> None:
    """Assertion whose dependency fails is skipped."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    _setup_failing_operator()
    try:
        doc = canonicalize({
            "geotask": {"version": "0.1", "name": "test", "goal": "test"},
            "space": {"crs": "local_xy_m", "unit": "meter"},
            "objects": {
                "a": {"type": "point", "xy": [0, 0]},
            },
            "ops": {"distance_2d": "compute", "_test_always_fails": "test"},
            "task": {},
            # Use empty steps so executor uses task-based iteration (no step on_error break)
            "execution": {"mode": "local_only", "steps": []},
            "assertions": [
                {"id": "bad", "operator": "_test_always_fails", "object_refs": ["a"], "on_error": "continue"},
                {"id": "dep", "operator": "distance_2d", "object_refs": ["a", "a"], "depends_on": ["bad"]},
            ],
        })
        result = execute_canonical(doc)
        dep_check = next((c for c in result.checks if c.assertion_id == "dep"), None)
        assert dep_check is not None, f"Expected 'dep' assertion in checks, got: {[c.assertion_id for c in result.checks]}"
        assert dep_check.status == "skipped"
    finally:
        _teardown_failing_operator()


# ═══════════════════════════════════════════════════════════════════════════════
#  Assertion parameter passing
# ═══════════════════════════════════════════════════════════════════════════════


def test_assertion_parameters_passed() -> None:
    """Create a test operator that verifies assertion parameters are received as kwargs."""
    import geotask_core.ops as ops_mod
    from geotask_core.v1.operator_contracts import OperatorContract, default_registry
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    # Define a test implementation that captures parameters
    def _test_params_receiver(coords: list, **kwargs) -> dict:
        """Return received kwargs unchanged — proves parameters are passed through."""
        return {"coords": coords, "received_params": kwargs}

    # Monkey-patch it into the ops module so the impl path resolves
    setattr(ops_mod, "_test_params_receiver", _test_params_receiver)  # pyright: ignore[reportAttributeAccessIssue]

    # Register a temporary operator contract
    test_contract = OperatorContract(
        name="_test_params_op",
        version="1.0",
        family="test",
        description="Test operator that captures parameters",
        arity=1,
        input_types=["point"],
        output={"type": "object"},
        deterministic=True,
        model_execution={},
        implementation="geotask_core.ops._test_params_receiver",
    )

    try:
        default_registry.register(test_contract)

        data = {
            "geotask": {
                "id": "params-test",
                "name": "Params Test",
                "schema_version": "1.0",
            },
            "space": {
                "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
                "horizontal_unit": "meter",
            },
            "objects": {
                "p": {"type": "point", "data": {"coordinates": [10, 20]}},
            },
            "operator_set": ["_test_params_op"],
            "tasks": [{
                "id": "t1",
                "assertions": [
                    {
                        "id": "param_check",
                        "operator": "_test_params_op",
                        "object_refs": ["p"],
                        "parameters": {"tolerance": 0.01, "mode": "strict"},
                    },
                ],
            }],
            "execution": {
                "mode": "local_only",
                "steps": [
                    {"id": "test_step", "executor": "local", "assertion_refs": ["param_check"]},
                ],
            },
            "output_contract": {
                "format": "structured",
                "required_fields": [],
            },
        }

        doc = canonicalize(data)
        result = execute_canonical(doc)

        # The check result value should contain the returned dict with received_params
        check = result.checks[0]
        assert check.status == "verified", f"Expected verified, got {check.status}"
        params = check.value.get("received_params", {})
        assert params.get("tolerance") == 0.01, (
            f"Expected tolerance=0.01 in params, got {params}"
        )
        assert params.get("mode") == "strict", (
            f"Expected mode='strict' in params, got {params}"
        )

    finally:
        # Clean up
        if "_test_params_op" in default_registry._contracts:
            del default_registry._contracts["_test_params_op"]
        if hasattr(ops_mod, "_test_params_receiver"):
            delattr(ops_mod, "_test_params_receiver")


# ═══════════════════════════════════════════════════════════════════════════════
#  Condition handling
# ═══════════════════════════════════════════════════════════════════════════════


def test_condition_false_next_assertion_executes() -> None:
    """condition=false on first assertion — second assertion still executes normally."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "cond-false-test",
            "name": "Condition False",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "a": {"type": "point", "data": {"coordinates": [0, 0]}},
            "b": {"type": "point", "data": {"coordinates": [3, 4]}},
        },
        "operator_set": ["distance_2d"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "skip_me",
                    "operator": "distance_2d",
                    "object_refs": ["a", "b"],
                    "condition": "false",
                },
                {
                    "id": "run_me",
                    "operator": "distance_2d",
                    "object_refs": ["a", "b"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    skip_check = next((c for c in result.checks if c.assertion_id == "skip_me"), None)
    run_check = next((c for c in result.checks if c.assertion_id == "run_me"), None)

    assert skip_check is not None, "Expected 'skip_me' in checks"
    assert run_check is not None, "Expected 'run_me' in checks"
    assert skip_check.status == "skipped", (
        f"Expected 'skip_me' status='skipped', got '{skip_check.status}'"
    )
    assert run_check.status == "verified", (
        f"Expected 'run_me' status='verified', got '{run_check.status}'"
    )


def test_invalid_condition_is_unverifiable() -> None:
    """condition='garbage' → assertion status is 'unverifiable'."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "bad-cond",
            "name": "Bad Condition",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "a": {"type": "point", "data": {"coordinates": [0, 0]}},
            "b": {"type": "point", "data": {"coordinates": [3, 4]}},
        },
        "operator_set": ["distance_2d"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "weird_cond",
                    "operator": "distance_2d",
                    "object_refs": ["a", "b"],
                    "condition": "garbage_value",
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)
    check = result.checks[0]
    assert check.status == "unverifiable", (
        f"Expected 'unverifiable', got '{check.status}'"
    )
    assert check.error is not None
    assert check.error["code"] == "unverifiable_condition"


# ═══════════════════════════════════════════════════════════════════════════════
#  On-error policy semantics
# ═══════════════════════════════════════════════════════════════════════════════


def test_on_error_stop() -> None:
    """stop policy halts current task — remaining assertions are skipped."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    _setup_failing_operator()
    try:
        data = {
            "geotask": {
                "id": "stop-test",
                "name": "Stop Test",
                "schema_version": "1.0",
            },
            "space": {
                "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
                "horizontal_unit": "meter",
            },
            "objects": {
                "a": {"type": "point", "data": {"coordinates": [0, 0]}},
            },
            "operator_set": ["distance_2d", "_test_always_fails"],
            "tasks": [{
                "id": "t1",
                "assertions": [
                    {
                        "id": "bad_ref",
                        "operator": "_test_always_fails",
                        "object_refs": ["a"],  # runtime failure
                        "on_error": "stop",
                    },
                    {
                        "id": "should_skip",
                        "operator": "distance_2d",
                        "object_refs": ["a", "a"],
                    },
                ],
            }],
            "execution": {
                "mode": "local_only",
                "steps": [],
            },
            "output_contract": {
                "format": "structured",
                "required_fields": [],
            },
        }
        doc = canonicalize(data)
        result = execute_canonical(doc)

        should_skip = next((c for c in result.checks if c.assertion_id == "should_skip"), None)
        assert should_skip is not None, "Expected 'should_skip' in checks"
        assert should_skip.status == "skipped", (
            f"Expected 'skipped' due to stop policy, got '{should_skip.status}'"
        )
    finally:
        _teardown_failing_operator()


def test_on_error_continue() -> None:
    """continue policy keeps executing after a failed assertion."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    _setup_failing_operator()
    try:
        data = {
            "geotask": {
                "id": "continue-test",
                "name": "Continue Test",
                "schema_version": "1.0",
            },
            "space": {
                "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
                "horizontal_unit": "meter",
            },
            "objects": {
                "a": {"type": "point", "data": {"coordinates": [0, 0]}},
                "b": {"type": "point", "data": {"coordinates": [3, 4]}},
            },
            "operator_set": ["distance_2d", "_test_always_fails"],
            "tasks": [{
                "id": "t1",
                "assertions": [
                    {
                        "id": "bad_ref",
                        "operator": "_test_always_fails",
                        "object_refs": ["a"],
                        "on_error": "continue",
                    },
                    {
                        "id": "good_one",
                        "operator": "distance_2d",
                        "object_refs": ["a", "b"],
                    },
                ],
            }],
            "execution": {
                "mode": "local_only",
                "steps": [],
            },
            "output_contract": {
                "format": "structured",
                "required_fields": [],
            },
        }
        doc = canonicalize(data)
        result = execute_canonical(doc)

        good = next((c for c in result.checks if c.assertion_id == "good_one"), None)
        assert good is not None, "Expected 'good_one' in checks"
        assert good.status == "verified", (
            f"Expected 'verified' after continue, got '{good.status}'"
        )
    finally:
        _teardown_failing_operator()


def test_on_error_skip() -> None:
    """skip policy marks the failed assertion as skipped and continues."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    _setup_failing_operator()
    try:
        data = {
            "geotask": {
                "id": "skip-test",
                "name": "Skip Test",
                "schema_version": "1.0",
            },
            "space": {
                "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
                "horizontal_unit": "meter",
            },
            "objects": {
                "a": {"type": "point", "data": {"coordinates": [0, 0]}},
                "b": {"type": "point", "data": {"coordinates": [3, 4]}},
            },
            "operator_set": ["distance_2d", "_test_always_fails"],
            "tasks": [{
                "id": "t1",
                "assertions": [
                    {
                        "id": "bad_ref",
                        "operator": "_test_always_fails",
                        "object_refs": ["a"],
                        "on_error": "skip",
                    },
                    {
                        "id": "good_one",
                        "operator": "distance_2d",
                        "object_refs": ["a", "b"],
                    },
                ],
            }],
            "execution": {
                "mode": "local_only",
                "steps": [],
            },
            "output_contract": {
                "format": "structured",
                "required_fields": [],
            },
        }
        doc = canonicalize(data)
        result = execute_canonical(doc)

        bad = next((c for c in result.checks if c.assertion_id == "bad_ref"), None)
        good = next((c for c in result.checks if c.assertion_id == "good_one"), None)
        assert bad is not None
        assert good is not None
        assert bad.status == "skipped", f"Expected 'skipped', got '{bad.status}'"
        assert good.status == "verified", f"Expected 'verified', got '{good.status}'"
    finally:
        _teardown_failing_operator()


def test_on_error_need_review() -> None:
    """need_review policy converts failure to 'need_review' status and continues."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    _setup_failing_operator()
    try:
        data = {
            "geotask": {
                "id": "review-test",
                "name": "Review Test",
                "schema_version": "1.0",
            },
            "space": {
                "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
                "horizontal_unit": "meter",
            },
            "objects": {
                "a": {"type": "point", "data": {"coordinates": [0, 0]}},
                "b": {"type": "point", "data": {"coordinates": [3, 4]}},
            },
            "operator_set": ["distance_2d", "_test_always_fails"],
            "tasks": [{
                "id": "t1",
                "assertions": [
                    {
                        "id": "bad_ref",
                        "operator": "_test_always_fails",
                        "object_refs": ["a"],
                        "on_error": "need_review",
                    },
                    {
                        "id": "good_one",
                        "operator": "distance_2d",
                        "object_refs": ["a", "b"],
                    },
                ],
            }],
            "execution": {
                "mode": "local_only",
                "steps": [],
            },
            "output_contract": {
                "format": "structured",
                "required_fields": [],
            },
        }
        doc = canonicalize(data)
        result = execute_canonical(doc)

        bad = next((c for c in result.checks if c.assertion_id == "bad_ref"), None)
        good = next((c for c in result.checks if c.assertion_id == "good_one"), None)
        assert bad is not None
        assert good is not None
        assert bad.status == "need_review", (
            f"Expected 'need_review', got '{bad.status}'"
        )
        assert good.status == "verified", f"Expected 'verified', got '{good.status}'"
    finally:
        _teardown_failing_operator()


def test_on_error_fallback_no_target() -> None:
    """fallback policy without a target → status becomes 'unverifiable'."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    _setup_failing_operator()
    try:
        data = {
            "geotask": {
                "id": "fallback-test",
                "name": "Fallback Test",
                "schema_version": "1.0",
            },
            "space": {
                "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
                "horizontal_unit": "meter",
            },
            "objects": {
                "a": {"type": "point", "data": {"coordinates": [0, 0]}},
            },
            "operator_set": ["_test_always_fails"],
            "tasks": [{
                "id": "t1",
                "assertions": [
                    {
                        "id": "bad_ref",
                        "operator": "_test_always_fails",
                        "object_refs": ["a"],
                        "on_error": "fallback",
                    },
                ],
            }],
            "execution": {
                "mode": "local_only",
                "steps": [],
            },
            "output_contract": {
                "format": "structured",
                "required_fields": [],
            },
        }
        doc = canonicalize(data)
        result = execute_canonical(doc)

        check = result.checks[0]
        assert check.status == "unverifiable", (
            f"Expected 'unverifiable' for fallback without target, got '{check.status}'"
        )
        assert check.assurance_level == "unverified", (
            f"Expected 'unverified' assurance, got '{check.assurance_level}'"
        )
    finally:
        _teardown_failing_operator()


# ═══════════════════════════════════════════════════════════════════════════════
#  v1.0 object types — time_interval and altitude_interval
# ═══════════════════════════════════════════════════════════════════════════════


def test_time_interval_start_end() -> None:
    """time_interval objects with start/end fields work in time_overlap operator."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "time-test",
            "name": "Time Interval Test",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "t1": {
                "type": "time_interval",
                "data": {"start": "08:00", "end": "10:00"},
            },
            "t2": {
                "type": "time_interval",
                "data": {"start": "09:00", "end": "11:00"},
            },
        },
        "operator_set": ["time_overlap"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "overlap",
                    "operator": "time_overlap",
                    "object_refs": ["t1", "t2"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["overlap"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    assert len(result.checks) == 1
    assert result.checks[0].value is True, (
        f"Expected time_overlap(08-10, 09-11) == True, got {result.checks[0].value}"
    )
    assert result.checks[0].status == "verified"


def test_altitude_interval_min_max() -> None:
    """altitude_interval objects with min/max fields work in altitude_overlap operator."""
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.executor import execute_canonical

    data = {
        "geotask": {
            "id": "alt-test",
            "name": "Altitude Interval Test",
            "schema_version": "1.0",
        },
        "space": {
            "crs": {"type": "local_cartesian", "identifier": "local_xy_m"},
            "horizontal_unit": "meter",
        },
        "objects": {
            "a1": {
                "type": "altitude_interval",
                "data": {"min": 100, "max": 200},
            },
            "a2": {
                "type": "altitude_interval",
                "data": {"min": 150, "max": 250},
            },
        },
        "operator_set": ["altitude_overlap"],
        "tasks": [{
            "id": "t1",
            "assertions": [
                {
                    "id": "overlap",
                    "operator": "altitude_overlap",
                    "object_refs": ["a1", "a2"],
                },
            ],
        }],
        "execution": {
            "mode": "local_only",
            "steps": [
                {"id": "calc", "executor": "local", "assertion_refs": ["overlap"]},
            ],
        },
        "output_contract": {
            "format": "structured",
            "required_fields": [],
        },
    }
    doc = canonicalize(data)
    result = execute_canonical(doc)

    assert len(result.checks) == 1
    assert result.checks[0].value is True, (
        f"Expected altitude_overlap(100-200, 150-250) == True, got {result.checks[0].value}"
    )
    assert result.checks[0].status == "verified"
