"""Tests for GeoTask Normalizer v0.2 — enhanced extraction + verification."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from geotask_core.normalizer import normalize_model_output
from geotask_core.parser import load_geotask
from geotask_core.result_schema import (
    STATUS_VERIFIED,
    STATUS_CONTRADICTED,
    STATUS_NEED_REVIEW,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
MODEL_OUTPUTS_DIR = EXAMPLES_DIR / "model_outputs"
GEOTASK_FILE = EXAMPLES_DIR / "geotask_core_lite.yaml"


def _load_geotask():
    return load_geotask(GEOTASK_FILE)


# ── Basic extraction (no verification) ───────────────────────────────

def test_extract_distance_cn():
    """Correct Chinese output extracts distance 144.22."""
    text = (MODEL_OUTPUTS_DIR / "deepseek_cn.md").read_text(encoding="utf-8")
    result = normalize_model_output(text)
    dist = _find_measurement(result, "takeoff_to_school_distance")
    assert dist is not None
    assert math.isclose(dist["value"], 144.22, rel_tol=0.01)


def test_extract_intersection_cn():
    """Correct Chinese output extracts intersection true."""
    text = (MODEL_OUTPUTS_DIR / "deepseek_cn.md").read_text(encoding="utf-8")
    result = normalize_model_output(text)
    intr = _find_measurement(result, "route_intersects_zone")
    assert intr is not None
    assert intr["value"] == True


def test_not_intersect_not_confused():
    """'不相交' is not confused with '相交'."""
    text = (MODEL_OUTPUTS_DIR / "not_intersect.md").read_text(encoding="utf-8")
    result = normalize_model_output(text)
    intr = _find_measurement(result, "route_intersects_zone")
    assert intr is not None
    assert intr["value"] == False


def test_yaml_like_extraction():
    """YAML-like output extracts distance and intersection."""
    text = (MODEL_OUTPUTS_DIR / "gpt_yaml_like.md").read_text(encoding="utf-8")
    result = normalize_model_output(text)
    dist = _find_measurement(result, "takeoff_to_school_distance")
    intr = _find_measurement(result, "route_intersects_zone")
    assert dist is not None
    assert math.isclose(dist["value"], 144.22, rel_tol=0.01)
    assert intr is not None
    assert intr["value"] == True


def test_markdown_extraction():
    """Markdown output extracts distance and intersection."""
    text = (MODEL_OUTPUTS_DIR / "gpt_markdown.md").read_text(encoding="utf-8")
    result = normalize_model_output(text)
    dist = _find_measurement(result, "takeoff_to_school_distance")
    intr = _find_measurement(result, "route_intersects_zone")
    assert dist is not None
    assert math.isclose(dist["value"], 144.22, rel_tol=0.01)
    assert intr is not None
    assert intr["value"] == True


# ── Verification (with geotask_data) ─────────────────────────────────

def test_wrong_distance_contradicted():
    """Wrong distance → verifier marks contradicted."""
    text = (MODEL_OUTPUTS_DIR / "wrong_distance.md").read_text(encoding="utf-8")
    geotask_data = _load_geotask()
    result = normalize_model_output(text, geotask_data=geotask_data)

    dist = _find_measurement(result, "takeoff_to_school_distance")
    assert dist is not None
    assert dist["status"] == STATUS_CONTRADICTED
    assert math.isclose(dist["expected_value"], 144.22, rel_tol=0.01)
    assert dist["difference"] > 1.0  # diff should be ~5.78
    assert result["conclusion"]["overall_status"] == STATUS_CONTRADICTED


def test_not_intersect_contradicted():
    """'不相交' → verifier marks contradicted (actual = true)."""
    text = (MODEL_OUTPUTS_DIR / "not_intersect.md").read_text(encoding="utf-8")
    geotask_data = _load_geotask()
    result = normalize_model_output(text, geotask_data=geotask_data)

    intr = _find_measurement(result, "route_intersects_zone")
    assert intr is not None
    assert intr["status"] == STATUS_CONTRADICTED
    assert intr["expected_value"] == True
    assert intr["value"] == False
    assert result["conclusion"]["overall_status"] == STATUS_CONTRADICTED


def test_missing_operator_review():
    """Missing operator → review_reasons includes operator_reference_missing."""
    text = (MODEL_OUTPUTS_DIR / "missing_operator.md").read_text(encoding="utf-8")
    geotask_data = _load_geotask()
    result = normalize_model_output(text, geotask_data=geotask_data)

    review_reasons = result["conclusion"].get("review_reasons", [])
    assert "operator_reference_missing" in review_reasons
    # Values should still be extracted and verified
    dist = _find_measurement(result, "takeoff_to_school_distance")
    assert dist is not None
    assert dist["status"] == STATUS_VERIFIED


def test_deepseek_cn_verified():
    """Correct DeepSeek CN output → verified with geotask_data."""
    text = (MODEL_OUTPUTS_DIR / "deepseek_cn.md").read_text(encoding="utf-8")
    geotask_data = _load_geotask()
    result = normalize_model_output(text, geotask_data=geotask_data)

    assert result["conclusion"]["overall_status"] == STATUS_VERIFIED
    dist = _find_measurement(result, "takeoff_to_school_distance")
    intr = _find_measurement(result, "route_intersects_zone")
    assert dist["status"] == STATUS_VERIFIED
    assert intr["status"] == STATUS_VERIFIED


# ── Backward compatibility ───────────────────────────────────────────

def test_old_normalize_still_works():
    """Old normalize_model_output(text) still works without geotask_data."""
    import examples
    old_text = (EXAMPLES_DIR / "deepseek_output_sample.txt").read_text(encoding="utf-8")
    result = normalize_model_output(old_text)
    assert len(result["measurements"]) >= 2


# ── Helpers ──────────────────────────────────────────────────────────

def _find_measurement(result: dict, name: str) -> dict | None:
    for m in result.get("measurements", []):
        if m.get("name") == name:
            return m
    return None
