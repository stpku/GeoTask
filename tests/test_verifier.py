"""Tests for GeoTask Verifier v0.2."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from geotask_core.verifier import verify_normalized_result
from geotask_core.parser import load_geotask
from geotask_core.runner import run_geotask
from geotask_core.result_schema import (
    STATUS_VERIFIED,
    STATUS_CONTRADICTED,
    STATUS_NEED_REVIEW,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
GEOTASK_FILE = EXAMPLES_DIR / "geotask_core_lite.yaml"


def _make_normalized(dist_val=None, intersect_val=None, ops=None):
    """Build a minimal normalized dict."""
    measurements = []
    verified_by = []
    if dist_val is not None:
        measurements.append({
            "name": "takeoff_to_school_distance",
            "value": dist_val,
            "unit": "meter",
            "object_refs": ["takeoff", "school"],
            "verified_by": "distance_2d",
        })
        verified_by.append({"operation": "distance_2d", "result": f"{dist_val} meter"})
    if intersect_val is not None:
        measurements.append({
            "name": "route_intersects_zone",
            "value": intersect_val,
            "unit": None,
            "object_refs": ["route", "zone"],
            "verified_by": "line_intersects_rect",
        })
        verified_by.append({"operation": "line_intersects_rect", "result": str(intersect_val).lower()})
    if ops is not None:
        verified_by = [{"operation": o, "result": ""} for o in ops]
    return {
        "measurements": measurements,
        "conclusion": {"summary": "test", "external_data_used": False, "review_reasons": []},
        "verified_by": verified_by,
    }


def _load_geotask():
    return load_geotask(GEOTASK_FILE)


# ── Verified numeric ─────────────────────────────────────────────────

def test_verified_numeric():
    """Exact distance match → verified."""
    gd = _load_geotask()
    norm = _make_normalized(dist_val=144.22, intersect_val=True, ops=["distance_2d", "line_intersects_rect"])
    result = verify_normalized_result(norm, gd)
    dist = _find(result, "takeoff_to_school_distance")
    assert dist["status"] == STATUS_VERIFIED
    assert math.isclose(dist["expected_value"], 144.22, rel_tol=0.01)
    assert result["conclusion"]["overall_status"] == STATUS_VERIFIED


# ── Contradicted numeric ─────────────────────────────────────────────

def test_contradicted_numeric():
    """Wrong distance → contradicted."""
    gd = _load_geotask()
    norm = _make_normalized(dist_val=150.0, intersect_val=True, ops=["distance_2d", "line_intersects_rect"])
    result = verify_normalized_result(norm, gd)
    dist = _find(result, "takeoff_to_school_distance")
    assert dist["status"] == STATUS_CONTRADICTED
    assert dist["difference"] > 5.0
    assert result["conclusion"]["overall_status"] == STATUS_CONTRADICTED


def test_contradicted_numeric_within_tolerance():
    """Value within tolerance → verified (not contradicted)."""
    gd = _load_geotask()
    norm = _make_normalized(dist_val=144.25, intersect_val=True, ops=["distance_2d", "line_intersects_rect"])
    result = verify_normalized_result(norm, gd)
    dist = _find(result, "takeoff_to_school_distance")
    assert dist["status"] == STATUS_VERIFIED


# ── Verified boolean ─────────────────────────────────────────────────

def test_verified_boolean():
    """Correct boolean → verified."""
    gd = _load_geotask()
    norm = _make_normalized(dist_val=144.22, intersect_val=True, ops=["distance_2d", "line_intersects_rect"])
    result = verify_normalized_result(norm, gd)
    intr = _find(result, "route_intersects_zone")
    assert intr["status"] == STATUS_VERIFIED
    assert intr["expected_value"] == True


# ── Contradicted boolean ─────────────────────────────────────────────

def test_contradicted_boolean():
    """Wrong boolean → contradicted."""
    gd = _load_geotask()
    norm = _make_normalized(dist_val=144.22, intersect_val=False, ops=["distance_2d", "line_intersects_rect"])
    result = verify_normalized_result(norm, gd)
    intr = _find(result, "route_intersects_zone")
    assert intr["status"] == STATUS_CONTRADICTED
    assert intr["expected_value"] == True
    assert result["conclusion"]["overall_status"] == STATUS_CONTRADICTED


# ── Need review ──────────────────────────────────────────────────────

def test_need_review_missing_value():
    """Missing model value → need_review."""
    gd = _load_geotask()
    norm = _make_normalized(dist_val=None, intersect_val=True, ops=["line_intersects_rect"])
    result = verify_normalized_result(norm, gd)
    dist = _find(result, "takeoff_to_school_distance")
    assert dist["status"] == STATUS_NEED_REVIEW


# ── Overall status ───────────────────────────────────────────────────

def test_overall_contradicted_wins():
    """One contradicted out of many → overall = contradicted."""
    gd = _load_geotask()
    norm = _make_normalized(dist_val=999.0, intersect_val=True, ops=["distance_2d", "line_intersects_rect"])
    result = verify_normalized_result(norm, gd)
    assert result["conclusion"]["overall_status"] == STATUS_CONTRADICTED


# ── Helpers ──────────────────────────────────────────────────────────

def _find(result: dict, name: str) -> dict | None:
    for m in result.get("measurements", []):
        if m.get("name") == name:
            return m
    return None
