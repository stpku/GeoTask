"""Tests for STIR-Core parser."""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Ensure src/ is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stir_core.parser import load_stir, validate_stir


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_load_stir_core_lite():
    """Parser can read stir_core_lite.yaml."""
    path = EXAMPLES_DIR / "stir_core_lite.yaml"
    data = load_stir(path)
    assert "stir" in data
    assert "space" in data
    assert "objects" in data
    assert "ops" in data
    assert "task" in data


def test_load_file_not_found():
    """Parser raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        load_stir("nonexistent.yaml")


def test_validate_valid_document():
    """Validate returns no errors for a valid document."""
    path = EXAMPLES_DIR / "stir_core_lite.yaml"
    data = load_stir(path)
    errors = validate_stir(data)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_validate_missing_top_level_key():
    """Validate detects missing top-level keys."""
    data = {
        "stir": {"version": "0.1", "name": "test", "goal": "test"},
    }
    errors = validate_stir(data)
    assert len(errors) > 0
    assert any("space" in e for e in errors)


def test_validate_unknown_object_type():
    """Validate rejects unknown object types."""
    data = {
        "stir": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {
            "bad": {"type": "polygon", "coords": []},
        },
        "ops": {},
        "task": {},
    }
    errors = validate_stir(data)
    assert any("unknown type" in e for e in errors)


def test_validate_point_missing_xy():
    """Validate rejects point without xy."""
    data = {
        "stir": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {
            "p": {"type": "point"},
        },
        "ops": {},
        "task": {},
    }
    errors = validate_stir(data)
    assert any("missing 'xy'" in e for e in errors)


def test_validate_line_too_few_points():
    """Validate rejects line with fewer than 2 points."""
    data = {
        "stir": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {
            "l": {"type": "line", "points": [[0, 0]]},
        },
        "ops": {},
        "task": {},
    }
    errors = validate_stir(data)
    assert any("at least 2 points" in e for e in errors)


def test_validate_rect_missing_bbox():
    """Validate rejects rect without bbox."""
    data = {
        "stir": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {
            "r": {"type": "rect"},
        },
        "ops": {},
        "task": {},
    }
    errors = validate_stir(data)
    assert any("missing 'bbox'" in e for e in errors)


def test_validate_rect_bbox_wrong_length():
    """Validate rejects rect bbox with wrong length."""
    data = {
        "stir": {"version": "0.1", "name": "test", "goal": "test"},
        "space": {"crs": "local"},
        "objects": {
            "r": {"type": "rect", "bbox": [0, 1, 2]},
        },
        "ops": {},
        "task": {},
    }
    errors = validate_stir(data)
    assert any("bbox' must be" in e for e in errors)
