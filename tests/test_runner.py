"""Tests for GeoTask Core runner."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from geotask_core.parser import load_geotask
from geotask_core.runner import run_geotask, run_stir


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_runner_outputs_distance():
    """Runner outputs takeoff_to_school_distance: 144.22."""
    data = load_geotask(EXAMPLES_DIR / "geotask_core_lite.yaml")
    result = run_geotask(data)

    dist_entry = None
    for m in result["measurements"]:
        if m["name"] == "takeoff_to_school_distance":
            dist_entry = m
            break

    assert dist_entry is not None, "Missing takeoff_to_school_distance"
    assert math.isclose(dist_entry["value"], 144.22, rel_tol=0.01)
    assert dist_entry["unit"] == "meter"
    assert dist_entry["verified_by"] == "distance_2d"


def test_runner_outputs_intersection_true():
    """Runner outputs route_intersects_zone: true."""
    data = load_geotask(EXAMPLES_DIR / "geotask_core_lite.yaml")
    result = run_geotask(data)

    intersect_entry = None
    for m in result["measurements"]:
        if m["name"] == "route_intersects_zone":
            intersect_entry = m
            break

    assert intersect_entry is not None, "Missing route_intersects_zone"
    assert intersect_entry["value"] == True
    assert intersect_entry["verified_by"] == "line_intersects_rect"


def test_runner_has_verified_by():
    """Runner output includes verified_by entries for both ops."""
    data = load_geotask(EXAMPLES_DIR / "geotask_core_lite.yaml")
    result = run_geotask(data)

    ops = [v["operation"] for v in result["verified_by"]]
    assert "distance_2d" in ops
    assert "line_intersects_rect" in ops


def test_runner_conclusion_contains_summary():
    """Runner conclusion has a summary string."""
    data = load_geotask(EXAMPLES_DIR / "geotask_core_lite.yaml")
    result = run_geotask(data)

    assert "summary" in result["conclusion"]
    assert "144.22" in result["conclusion"]["summary"]
    assert "true" in result["conclusion"]["summary"]
    assert result["conclusion"]["external_data_used"] == False


def test_runner_no_matching_objects_empty():
    """Runner returns empty measurements when no known objects exist."""
    data = {
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local", "unit": "meter", "axes": {"x": "east", "y": "north"}},
        "objects": {
            "x": {"type": "point", "xy": [1, 2]},
        },
        "ops": {},
        "task": {},
    }
    result = run_geotask(data)
    assert result["measurements"] == []
    assert "no measurements" in result["conclusion"]["summary"]


def test_old_run_stir_alias_works():
    """Old run_stir alias still functions."""
    data = load_geotask(EXAMPLES_DIR / "geotask_core_lite.yaml")
    result = run_stir(data)
    assert len(result["measurements"]) == 2
    assert "144.22" in result["conclusion"]["summary"]
