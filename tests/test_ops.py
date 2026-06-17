"""Tests for GeoTask Core spatial operators."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from geotask_core.ops import distance_2d, line_intersects_rect


def test_distance_2d_basic():
    """distance_2d([0,0], [3,4]) == 5.0"""
    result = distance_2d([0, 0], [3, 4])
    assert math.isclose(result, 5.0, rel_tol=1e-6)


def test_distance_2d_same_point():
    """Distance to self is zero."""
    assert distance_2d([10, 20], [10, 20]) == 0.0


def test_distance_2d_negative_coords():
    """Works with negative coordinates."""
    result = distance_2d([-3, -4], [0, 0])
    assert math.isclose(result, 5.0, rel_tol=1e-6)


def test_line_intersects_rect_true():
    """Line through rect -> True (test case from specification)."""
    line = [[-200, 0], [400, 0]]
    bbox = [250, -100, 350, 100]
    assert line_intersects_rect(line, bbox) == True


def test_line_intersects_rect_false():
    """Line far above rect -> False (test case from specification)."""
    line = [[-200, 200], [400, 200]]
    bbox = [250, -100, 350, 100]
    assert line_intersects_rect(line, bbox) == False


def test_line_intersects_rect_endpoint_inside():
    """Line endpoint inside rect -> True."""
    line = [[300, 0], [500, 0]]  # (300,0) is inside the rect
    bbox = [250, -100, 350, 100]
    assert line_intersects_rect(line, bbox) == True


def test_line_intersects_rect_touches_boundary():
    """Line touches rect boundary -> True."""
    line = [[250, 0], [500, 0]]  # touches left edge at x=250
    bbox = [250, -100, 350, 100]
    assert line_intersects_rect(line, bbox) == True


def test_line_intersects_rect_corner_touch():
    """Line touches rect corner -> True."""
    line = [[250, -100], [500, 200]]  # touches corner (250, -100)
    bbox = [250, -100, 350, 100]
    assert line_intersects_rect(line, bbox) == True


def test_line_intersects_rect_short_line():
    """Short line with fewer than 2 points -> False."""
    line = [[0, 0]]
    bbox = [0, 0, 10, 10]
    assert line_intersects_rect(line, bbox) == False


def test_line_intersects_rect_vertical():
    """Vertical line through rect -> True."""
    line = [[300, -200], [300, 200]]
    bbox = [250, -100, 350, 100]
    assert line_intersects_rect(line, bbox) == True


def test_line_intersects_rect_completely_outside_left():
    """Line completely left of rect -> False."""
    line = [[-100, 0], [-50, 0]]
    bbox = [250, -100, 350, 100]
    assert line_intersects_rect(line, bbox) == False
