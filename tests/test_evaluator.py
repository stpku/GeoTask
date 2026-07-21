"""Tests for GeoTask Eval v0.1 evaluator -- 100-point scoring rubric."""

import math
import sys
from pathlib import Path
from typing import Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from geotask_core.evaluator import evaluate_model_output
from geotask_core.parser import load_geotask
from geotask_core.runner import run_geotask
from geotask_core.normalizer import normalize_model_output


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


# ── Helpers ──────────────────────────────────────────────────────────

def _make_core(dist_val: Optional[float] = 144.22, intersect_val: Optional[bool] = True):
    """Build a minimal core_result dict matching runner output."""
    measurements = []
    verified_by = []
    if dist_val is not None:
        measurements.append({
            "name": "takeoff_to_school_distance",
            "value": dist_val,
            "unit": "meter",
            "verified_by": "distance_2d",
        })
        verified_by.append({"operation": "distance_2d", "result": f"{dist_val} meter"})
    if intersect_val is not None:
        measurements.append({
            "name": "route_intersects_zone",
            "value": intersect_val,
            "unit": None,
            "verified_by": "line_intersects_rect",
        })
        verified_by.append({"operation": "line_intersects_rect", "result": str(intersect_val).lower()})
    return {
        "measurements": measurements,
        "conclusion": {"summary": "test", "external_data_used": False},
        "verified_by": verified_by,
    }


def _make_norm(dist_val: Optional[float] = 144.22, intersect_val: Optional[bool] = True,
               ops: Optional[list] = None, ext_data: bool = False):
    """Build a minimal normalized_output dict matching normalizer output."""
    measurements = []
    verified_by = []
    if dist_val is not None:
        measurements.append({
            "name": "takeoff_to_school_distance",
            "value": dist_val,
            "unit": "meter",
            "verified_by": "distance_2d",
        })
        verified_by.append({"operation": "distance_2d", "result": f"{dist_val} meter"})
    if intersect_val is not None:
        measurements.append({
            "name": "route_intersects_zone",
            "value": intersect_val,
            "unit": None,
            "verified_by": "line_intersects_rect",
        })
        verified_by.append({"operation": "line_intersects_rect", "result": str(intersect_val).lower()})
    # Override verified_by with specified ops if provided
    if ops is not None:
        verified_by = [{"operation": o, "result": ""} for o in ops]
    return {
        "measurements": measurements,
        "conclusion": {"summary": "test", "external_data_used": ext_data},
        "verified_by": verified_by,
    }


# ── Perfect match ────────────────────────────────────────────────────

def test_eval_perfect_score_100():
    """DeepSeek sample should score 100."""
    data = load_geotask(EXAMPLES_DIR / "geotask_core_lite.yaml")
    core_result = run_geotask(data)
    text = (EXAMPLES_DIR / "deepseek_output_sample.txt").read_text(encoding="utf-8")
    normalized = normalize_model_output(text)

    result = evaluate_model_output(core_result, normalized)
    assert result["score"]["total"] == 100
    assert result["score"]["distance_match"] == True
    assert result["score"]["intersection_match"] == True
    assert result["score"]["operator_match"] == True
    assert result["score"]["external_data_used_match"] == True
    assert result["errors"] == []


# ── Distance mismatch ────────────────────────────────────────────────

def test_eval_distance_mismatch():
    """Wrong distance -> total should be 60 (loss of 40)."""
    core = _make_core(dist_val=144.22)
    norm = _make_norm(dist_val=999.0)
    result = evaluate_model_output(core, norm)
    assert result["score"]["total"] == 60
    assert result["score"]["distance_match"] == False
    assert "distance_value_mismatch" in result["errors"]


def test_eval_distance_missing():
    """Missing distance in model -> total = 45 (only intersection + ext_data, no ops)."""
    core = _make_core(dist_val=144.22)
    norm = _make_norm(dist_val=None)
    result = evaluate_model_output(core, norm)
    # distance_match: false (0), intersection_match: true (40),
    # operator_match: false (distance_2d not in actual ops, 0),
    # external_data_used_match: true (5) -> 45
    assert result["score"]["total"] == 45
    assert result["score"]["distance_match"] == False
    assert "distance_value_missing" in result["errors"]


# ── Intersection mismatch ────────────────────────────────────────────

def test_eval_intersection_mismatch():
    """Wrong intersection -> total = 60."""
    core = _make_core(intersect_val=True)
    norm = _make_norm(intersect_val=False)
    result = evaluate_model_output(core, norm)
    assert result["score"]["total"] == 60
    assert result["score"]["intersection_match"] == False
    assert "intersection_value_mismatch" in result["errors"]


def test_eval_intersection_missing():
    """Missing intersection in model -- ops also missing since no intersect op."""
    # Core has both distance (144.22) and intersection (True)
    # Model has only distance (intersect_val=None)
    core = _make_core(dist_val=144.22, intersect_val=True)
    norm = _make_norm(dist_val=144.22, intersect_val=None)
    result = evaluate_model_output(core, norm)
    # distance: true (40), intersection: missing (0),
    # operator: line_intersects_rect not in actual (0), ext_data: true (5) -> 45
    assert result["score"]["total"] == 45
    assert result["score"]["intersection_match"] == False
    assert "intersection_value_missing" in result["errors"]


# ── Operator mismatch ────────────────────────────────────────────────

def test_eval_operator_missing():
    """Missing operator -> total = 85 (loss of 15)."""
    core = _make_core()
    norm = _make_norm(ops=["distance_2d"])  # only one op
    result = evaluate_model_output(core, norm)
    assert result["score"]["total"] == 85
    assert result["score"]["operator_match"] == False
    assert "operator_missing" in result["errors"]


def test_eval_operator_all_missing():
    """No operators at all -> total = 85."""
    core = _make_core()
    norm = _make_norm(ops=[])
    result = evaluate_model_output(core, norm)
    assert result["score"]["total"] == 85
    assert "operator_missing" in result["errors"]


# ── external_data_used tests ─────────────────────────────────────────

def test_eval_external_data_used_missing_warning():
    """Missing external_data_used -> warning, not error, still full score."""
    core = _make_core()
    norm_raw = _make_norm()
    del norm_raw["conclusion"]["external_data_used"]
    result = evaluate_model_output(core, norm_raw)
    assert result["score"]["external_data_used_match"] == True
    assert result["score"]["total"] == 100
    assert "external_data_used_missing_assumed_false" in result["warnings"]
    assert "external_data_used_mismatch" not in result["errors"]


def test_eval_external_data_used_mismatch():
    """external_data_used differs -> -5 pts."""
    core = _make_core()
    norm = _make_norm(ext_data=True)
    result = evaluate_model_output(core, norm)
    assert result["score"]["total"] == 95
    assert result["score"]["external_data_used_match"] == False
    assert "external_data_used_mismatch" in result["errors"]


# ── Multiple failures ────────────────────────────────────────────────

def test_eval_all_wrong():
    """Everything wrong -> total = 0."""
    core = _make_core(dist_val=144.22, intersect_val=True)
    norm = _make_norm(dist_val=999.0, intersect_val=False, ops=[], ext_data=True)
    result = evaluate_model_output(core, norm)
    assert result["score"]["total"] == 0
    assert len(result["errors"]) >= 4


# ── Float tolerance ──────────────────────────────────────────────────

def test_eval_distance_within_tolerance():
    """Distance within 0.01 tolerance -> still 100."""
    core = _make_core(dist_val=144.22)
    norm = _make_norm(dist_val=144.225)  # diff = 0.005 < 0.01
    result = evaluate_model_output(core, norm)
    assert result["score"]["distance_match"] == True
    assert result["score"]["total"] == 100


def test_eval_distance_outside_tolerance():
    """Distance outside 0.01 tolerance -> -40."""
    core = _make_core(dist_val=144.22)
    norm = _make_norm(dist_val=144.24)  # diff = 0.02 > 0.01
    result = evaluate_model_output(core, norm)
    assert result["score"]["distance_match"] == False
    assert result["score"]["total"] == 60


# ── Details fields populated ─────────────────────────────────────────

def test_eval_details_populated():
    """Details fields are correctly populated."""
    core = _make_core(dist_val=144.22, intersect_val=True)
    norm = _make_norm(dist_val=144.22, intersect_val=True)
    result = evaluate_model_output(core, norm)
    d = result["details"]
    assert d["expected_distance"] == 144.22
    assert d["actual_distance"] == 144.22
    assert d["expected_intersection"] == True
    assert d["actual_intersection"] == True
    assert "distance_2d" in d["expected_operations"]
    assert "line_intersects_rect" in d["expected_operations"]


# ── CLI integration test ─────────────────────────────────────────────

def test_cli_eval_outputs_total_100():
    """CLI eval on DeepSeek sample should produce YAML with total: 100."""
    import subprocess
    import os

    proj_root = str(Path(__file__).resolve().parent.parent)
    env = {**os.environ, "PYTHONPATH": str(Path(proj_root) / "src")}
    result = subprocess.run(
        [
            sys.executable, "-m", "geotask_core.cli", "eval",
            str(EXAMPLES_DIR / "geotask_core_lite.yaml"),
            str(EXAMPLES_DIR / "deepseek_output_sample.txt"),
        ],
        capture_output=True,
        text=True,
        cwd=proj_root,
        env=env,
    )
    assert result.returncode == 0
    # YAML output should contain "total: 100"
    assert "total: 100" in result.stdout


# ── Existing tests not broken ────────────────────────────────────────

def test_existing_parser_still_works():
    """Parser tests can still be imported."""
    from geotask_core.parser import load_geotask, validate_geotask
    data = load_geotask(EXAMPLES_DIR / "geotask_core_lite.yaml")
    assert validate_geotask(data) == []


def test_existing_ops_still_works():
    """Ops still work."""
    from geotask_core.ops import distance_2d, line_intersects_rect
    assert math.isclose(distance_2d([0, 0], [3, 4]), 5.0)
    assert line_intersects_rect([[-200, 0], [400, 0]], [250, -100, 350, 100]) == True


def test_existing_runner_still_works():
    """Runner still works."""
    from geotask_core.runner import run_geotask
    data = load_geotask(EXAMPLES_DIR / "geotask_core_lite.yaml")
    result = run_geotask(data)
    assert len(result["measurements"]) == 2


def test_existing_normalizer_still_works():
    """Normalizer still works."""
    from geotask_core.normalizer import normalize_model_output
    text = (EXAMPLES_DIR / "deepseek_output_sample.txt").read_text(encoding="utf-8")
    result = normalize_model_output(text)
    assert len(result["measurements"]) >= 2
