from __future__ import annotations

from geotask_core.spatial_scope import rect_contains_rect, rect_intersects_rect


def test_rect_contains_rect_closed_boundary_semantics() -> None:
    outer = (-10.0, -5.0, 10.0, 5.0)

    assert rect_contains_rect(outer, outer)
    assert rect_contains_rect(outer, (-5.0, -2.0, 5.0, 2.0))
    assert rect_contains_rect(outer, (-10.0, -5.0, 0.0, 0.0))
    assert not rect_contains_rect(outer, (-11.0, -2.0, 5.0, 2.0))
    assert not rect_contains_rect(outer, (-5.0, -2.0, 11.0, 2.0))


def test_rect_intersects_rect_includes_touching_and_containment() -> None:
    base = (0.0, 0.0, 10.0, 10.0)

    assert rect_intersects_rect(base, base)
    assert rect_intersects_rect(base, (2.0, 2.0, 4.0, 4.0))
    assert rect_intersects_rect(base, (8.0, 8.0, 12.0, 12.0))
    assert rect_intersects_rect(base, (10.0, 2.0, 12.0, 4.0))
    assert rect_intersects_rect(base, (10.0, 10.0, 12.0, 12.0))
    assert not rect_intersects_rect(base, (10.0001, 2.0, 12.0, 4.0))


def test_rect_intersection_is_symmetric() -> None:
    a = (-2.0, -2.0, 1.0, 1.0)
    b = (0.0, 0.0, 3.0, 3.0)
    c = (4.0, 4.0, 5.0, 5.0)

    assert rect_intersects_rect(a, b) == rect_intersects_rect(b, a)
    assert rect_intersects_rect(a, c) == rect_intersects_rect(c, a)
