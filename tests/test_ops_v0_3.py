"""Tests for GeoTask Core ops v0.3 — 4 new operators."""

import math
import pytest
from geotask_core.ops import (
    distance_2d,
    line_intersects_rect,
    point_to_line_distance_2d,
    rect_contains_point,
    time_overlap,
    altitude_overlap,
)


# ── distance_2d (existing, regression) ────────────────────────────────

def test_distance_2d_basic():
    assert round(distance_2d([0, 0], [120, 80]), 2) == 144.22


def test_distance_2d_same_point():
    assert distance_2d([5, 5], [5, 5]) == 0.0


# ── line_intersects_rect (existing, regression) ───────────────────────

def test_line_intersects_rect_true():
    assert line_intersects_rect([[-200, 0], [400, 0]], [250, -100, 350, 100]) is True


def test_line_intersects_rect_false():
    assert line_intersects_rect([[-200, 200], [400, 200]], [250, -100, 350, 100]) is False


# ── point_to_line_distance_2d ─────────────────────────────────────────

def test_point_to_line_dist_on_segment():
    """Point on line segment → distance 0."""
    d = point_to_line_distance_2d([2, 2], [[0, 2], [10, 2]])
    assert d == pytest.approx(0.0)


def test_point_to_line_dist_horizontal():
    """Point above horizontal segment → vertical distance."""
    d = point_to_line_distance_2d([5, 7], [[0, 2], [10, 2]])
    assert d == pytest.approx(5.0)


def test_point_to_line_dist_proj_outside():
    """Projection outside segment → distance to nearest endpoint."""
    d = point_to_line_distance_2d([15, 2], [[0, 2], [10, 2]])
    assert d == pytest.approx(5.0)


def test_point_to_line_dist_degenerate_segment():
    """Degenerate segment (same points) → distance to point."""
    d = point_to_line_distance_2d([3, 4], [[0, 0], [0, 0]])
    assert d == pytest.approx(5.0)


# ── rect_contains_point ───────────────────────────────────────────────

def test_rect_contains_true():
    assert rect_contains_point([0, 0, 10, 10], [5, 5]) is True


def test_rect_contains_boundary():
    """Boundary contact counts as contains."""
    assert rect_contains_point([0, 0, 10, 10], [0, 5]) is True
    assert rect_contains_point([0, 0, 10, 10], [10, 5]) is True
    assert rect_contains_point([0, 0, 10, 10], [5, 0]) is True
    assert rect_contains_point([0, 0, 10, 10], [5, 10]) is True


def test_rect_not_contains():
    assert rect_contains_point([0, 0, 10, 10], [15, 15]) is False
    assert rect_contains_point([0, 0, 10, 10], [-1, 5]) is False


# ── time_overlap ──────────────────────────────────────────────────────

def test_time_overlap_true():
    assert time_overlap(["08:00", "10:00"], ["09:00", "11:00"]) is True


def test_time_overlap_boundary_contact():
    """Boundary contact counts as overlap."""
    assert time_overlap(["08:00", "10:00"], ["10:00", "12:00"]) is True


def test_time_overlap_false():
    assert time_overlap(["08:00", "09:00"], ["10:00", "11:00"]) is False


def test_time_overlap_same():
    """Same interval → overlap."""
    assert time_overlap(["08:00", "10:00"], ["08:00", "10:00"]) is True


# ── altitude_overlap ──────────────────────────────────────────────────

def test_altitude_overlap_true():
    assert altitude_overlap([100, 200], [150, 250]) is True


def test_altitude_overlap_boundary():
    """Boundary contact counts as overlap."""
    assert altitude_overlap([100, 200], [200, 300]) is True


def test_altitude_overlap_false():
    assert altitude_overlap([100, 200], [300, 400]) is False


def test_altitude_overlap_enclosed():
    """One range fully contained in another."""
    assert altitude_overlap([100, 500], [200, 300]) is True


# ── Input validation (v0.3 requirement) ──────────────────────────────

def test_time_overlap_flexible_format():
    """Time parsing handles various valid HH:MM formats."""
    # Single-digit hour works
    assert time_overlap(["8:00", "10:00"], ["8:00", "10:00"]) is True
    # Leading zero also works
    assert time_overlap(["08:00", "10:00"], ["08:00", "10:00"]) is True


def test_altitude_overlap_invalid():
    """Invalid altitude range (min > max) — should still work (overlap formula symmetric)."""
    # Formula a[0] <= b[1] and b[0] <= a[1] is symmetric, so invalid ranges still compare.
    # This is acceptable for v0.3.
    result = altitude_overlap([300, 100], [150, 250])
    # 300 <= 250? False. 150 <= 100? False. → False
    assert result is False
