"""Legacy compatibility tests — run_geotask with legacy documents,
EncodingType uppercase, and v1 execution via legacy runner.
"""

from __future__ import annotations

import math

from tests.v1.conftest import _PROJECT_ROOT, _load_yaml


def test_legacy_cli_keeps_working() -> None:
    """``run_geotask`` on legacy document (no assertions) returns old-style output."""
    from geotask_core.runner import run_geotask

    data = _load_yaml("examples/geotask_core_lite.yaml")
    result = run_geotask(data)

    assert "measurements" in result
    assert "conclusion" in result
    assert "verified_by" in result
    assert len(result["measurements"]) >= 2
    assert "144.22" in result["conclusion"]["summary"]
    assert result["conclusion"]["external_data_used"] == False


def test_v1_native_execution() -> None:
    """Load ``v1_minimal_distance.yaml`` via ``run_geotask`` — returns v1.0 ``to_dict()`` format."""
    from geotask_core.runner import run_geotask

    data = _load_yaml("examples/core/v1_minimal_distance.yaml")
    result = run_geotask(data)

    # run_geotask returns legacy format for backward compat
    assert result["measurements"], "expected measurements in result"
    m = result["measurements"][0]
    assert math.isclose(m["value"], 5.0, rel_tol=0.01)
    assert m["name"] == "ab_distance"
    assert m["verified_by"] == "distance_2d"
