"""Tests for GeoTask Core parser."""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Ensure src/ is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from geotask_core.parser import load_geotask, validate_geotask, load_stir, validate_stir


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_load_geotask_core_lite():
    """Parser can read geotask_core_lite.yaml."""
    path = EXAMPLES_DIR / "geotask_core_lite.yaml"
    data = load_geotask(path)
    assert "geotask" in data
    assert "space" in data
    assert "objects" in data
    assert "ops" in data
    assert "task" in data


def test_load_file_not_found():
    """Parser raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        load_geotask("nonexistent.yaml")


def test_validate_valid_document():
    """Validate returns no errors for a valid document."""
    path = EXAMPLES_DIR / "geotask_core_lite.yaml"
    data = load_geotask(path)
    errors = validate_geotask(data)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_validate_missing_top_level_key():
    """Validate detects missing top-level keys."""
    data = {
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
    }
    errors = validate_geotask(data)
    assert len(errors) > 0
    assert any("space" in e for e in errors)


def test_validate_unknown_object_type():
    """Validate rejects unknown object types."""
    data = {
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {
            "bad": {"type": "polygon", "coords": []},
        },
        "ops": {},
        "task": {},
    }
    errors = validate_geotask(data)
    assert any("unknown type" in e for e in errors)


def test_validate_point_missing_xy():
    """Validate rejects point without xy."""
    data = {
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {
            "p": {"type": "point"},
        },
        "ops": {},
        "task": {},
    }
    errors = validate_geotask(data)
    assert any("missing" in e.lower() and ("xy" in e.lower() or "coordinates" in e.lower()) for e in errors)


def test_validate_line_too_few_points():
    """Validate rejects line with fewer than 2 points."""
    data = {
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {
            "l": {"type": "line", "points": [[0, 0]]},
        },
        "ops": {},
        "task": {},
    }
    errors = validate_geotask(data)
    assert any("at least 2 points" in e for e in errors)


def test_validate_rect_missing_bbox():
    """Validate rejects rect without bbox."""
    data = {
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {
            "r": {"type": "rect"},
        },
        "ops": {},
        "task": {},
    }
    errors = validate_geotask(data)
    assert any("missing 'bbox'" in e for e in errors)


def test_validate_rect_bbox_wrong_length():
    """Validate rejects rect bbox with wrong length."""
    data = {
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {
            "r": {"type": "rect", "bbox": [0, 1, 2]},
        },
        "ops": {},
        "task": {},
    }
    errors = validate_geotask(data)
    assert any("bbox' must be" in e for e in errors)


# ── Backward compatibility tests ──────────────────────────────────────

def test_validate_old_stir_field_accepted():
    """Validate accepts old 'stir' top-level field but sets deprecated flag."""
    data = {
        "stir": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {},
        "ops": {},
        "task": {},
    }
    errors = validate_geotask(data)
    assert errors == [], f"Expected no errors for old 'stir' field, got: {errors}"
    assert data.get("_deprecated_stir_field") == True


def test_validate_both_fields_present():
    """Validate prefers 'geotask' when both fields present."""
    data = {
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "stir": {"version": "0.1", "name": "old", "goal": "old"},
        "space": {"crs": "local"},
        "objects": {},
        "ops": {},
        "task": {},
    }
    errors = validate_geotask(data)
    assert errors == [], f"Expected no errors, got: {errors}"
    assert data.get("_deprecated_stir_field") is not True


def test_validate_neither_field_error():
    """Validate errors when neither geotask nor stir field present."""
    data = {
        "space": {"crs": "local"},
        "objects": {},
        "ops": {},
        "task": {},
    }
    errors = validate_geotask(data)
    assert any("geotask" in e or "stir" in e for e in errors)


def test_old_load_stir_alias_works():
    """Old load_stir alias still functions."""
    path = EXAMPLES_DIR / "geotask_core_lite.yaml"
    data = load_stir(path)
    assert "geotask" in data or "objects" in data


def test_old_validate_stir_alias_works():
    """Old validate_stir alias still functions."""
    data = {
        "geotask": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {},
        "ops": {},
        "task": {},
    }
    errors = validate_stir(data)
    assert errors == []
