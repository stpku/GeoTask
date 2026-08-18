"""Deterministic spatial-scope relation primitives for GeoTask Core.

TC2.0 promotes only the smallest cross-domain capability demonstrated by the
TC1 real proofs: relation checks between already-normalized axis-aligned
rectangles.  This module does not perform CRS transformation, infer task scopes,
or modify Task Context contracts.

Rectangles use ``[min_x, min_y, max_x, max_y]`` in one common, already
normalized coordinate space.  Document/provider validation remains responsible
for shape, finite-number, CRS, coordinate-order, and min/max correctness before
execution, matching the existing deterministic operator design.
"""

from __future__ import annotations

from collections.abc import Sequence


Rect = Sequence[float]


def rect_contains_rect(container: Rect, target: Rect) -> bool:
    """Return whether *container* fully contains *target*.

    The relation is closed-boundary: equality is containment and a target edge
    may coincide with a container edge.  No CRS or unit conversion is performed.
    """

    return (
        container[0] <= target[0]
        and container[1] <= target[1]
        and container[2] >= target[2]
        and container[3] >= target[3]
    )


def rect_intersects_rect(a: Rect, b: Rect) -> bool:
    """Return whether two axis-aligned rectangles intersect or touch.

    Boundary contact counts as intersection, consistent with GeoTask's existing
    closed-boundary ``line_intersects_rect`` and interval-overlap semantics.
    The predicate is symmetric and includes containment/equality cases.
    """

    return not (
        a[2] < b[0]
        or b[2] < a[0]
        or a[3] < b[1]
        or b[3] < a[1]
    )
