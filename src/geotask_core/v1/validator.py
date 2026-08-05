"""v1.0 CanonicalDocument validator — produces structured diagnostics.

Validates every aspect of a CanonicalDocument against the v1.0 specification.
Returns a flat list of diagnostic dicts; an empty list means the document is
fully valid.

All functions are pure — no side effects, no mutation of the input document.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING

from geotask_core.v1.enums import (
    _ID_PATTERN,
    ARITY_MISMATCH,
    BOUNDARY_SEMANTICS_MISMATCH,
    CYCLIC_DEPENDENCY,
    DUPLICATE_ID,
    EXECUTION_ERROR,
    INVALID_COORDINATES,
    INVALID_CRS,
    INVALID_GEOMETRY,
    INVALID_INTERVAL,
    INVALID_OPERATOR,
    INVALID_REFERENCE,
    INVALID_TYPE,
    LEGACY_OBJECT_TYPE_MAP,
    MISSING_DATA,
    MISSING_FIELD,
    OBJECT_TYPE_MISMATCH,
    OUTPUT_CONTRACT_VIOLATION,
    UNKNOWN_FIELD,
    UNKNOWN_OBJECT_TYPE,
    UNIT_MISMATCH,
    UNSUPPORTED_EXECUTION_MODE,
    UNVERIFIABLE_CLAIM,
    VALID_OBJECT_TYPES,
    AssuranceLevel,
    ExecutionMode,
    is_valid_geotask_id,
)
from geotask_core.v1.ir import (
    Assertion,
    CanonicalDocument,
    ExecutionDefinition,
    ExecutionStep,
    GeoObject,
    GeotaskMetadata,
    OutputContract,
    SpaceDefinition,
    Task,
    VerificationDefinition,
)
from geotask_core.v1.extension_profiles import validate_extension_profiles
from geotask_core.v1.operator_contracts import default_registry
from geotask_core.v1.provenance import validate_provenance

if TYPE_CHECKING:
    pass


# -- Diagnostic helpers

_VALID_CRS_TYPES: set[str] = {"local_cartesian", "projected", "geographic", "unknown"}
_PLANAR_OPERATOR_NAMES: frozenset[str] = frozenset(
    {
        "distance_2d",
        "line_intersects_rect",
        "multi_polyline_intersects_rect",
        "point_in_polygon",
        "polygon_contains_point",
        "point_to_line_distance_2d",
        "rect_contains_point",
        "trajectory_segment_metrics",
        "trajectory_segment_classifications",
    }
)
_BOUNDARY_SENSITIVE_OPERATOR_NAMES: frozenset[str] = frozenset(
    {
        "line_intersects_rect",
        "multi_polyline_intersects_rect",
        "point_in_polygon",
        "polygon_contains_point",
        "rect_contains_point",
        "time_overlap",
        "altitude_overlap",
    }
)
_UNIT_ALIASES: dict[str, str] = {
    "m": "meter",
    "meter": "meter",
    "meters": "meter",
    "metre": "meter",
    "metres": "meter",
    "km": "kilometer",
    "kilometer": "kilometer",
    "kilometers": "kilometer",
    "kilometre": "kilometer",
    "kilometres": "kilometer",
    "ft": "foot",
    "foot": "foot",
    "feet": "foot",
    "deg": "degree",
    "degree": "degree",
    "degrees": "degree",
}

_VALID_EXECUTION_MODES: set[str] = {e.value for e in ExecutionMode}

#: Maximum AssuranceLevel integer achievable by each execution mode.
_MAX_ACHIEVABLE_BY_MODE: dict[str, int] = {
    "model_only": AssuranceLevel.model_self_checked.value,
    "local_only": AssuranceLevel.local_deterministic.value,
    "hybrid": AssuranceLevel.model_local_agreement.value,
    "shadow_compare": AssuranceLevel.model_local_agreement.value,
}


def _diagnostic(
    path: str,
    code: str,
    message: str,
    suggested_fix: str = "",
    severity: str = "error",
) -> dict:
    """Build a structured diagnostic dict."""
    d: dict = {"path": path, "code": code, "message": message, "severity": severity}
    if suggested_fix:
        d["suggested_fix"] = suggested_fix
    return d


def _is_finite_number(x: object) -> bool:
    """Return True if *x* is a finite number (int or float) and NOT a bool."""
    if isinstance(x, bool):
        return False
    if isinstance(x, int):
        return True  # Python ints are always finite
    if isinstance(x, float):
        return math.isfinite(x)
    return False


def _normalize_unit(value: object) -> str:
    """Normalize common unit spellings without performing conversion."""
    if not isinstance(value, str):
        return ""
    normalized = value.strip().casefold()
    return _UNIT_ALIASES.get(normalized, normalized)


def _units_equivalent(left: object, right: object) -> bool:
    """Return whether two unit labels denote the same non-empty unit."""
    left_normalized = _normalize_unit(left)
    right_normalized = _normalize_unit(right)
    return bool(left_normalized and left_normalized == right_normalized)


def _is_valid_hhmm(s: object) -> bool:
    """Return True if *s* is a string in HH:MM format (00:00–23:59)."""
    if not isinstance(s, str):
        return False
    parts = s.split(":")
    if len(parts) != 2:
        return False
    try:
        h = int(parts[0])
        m = int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except (ValueError, TypeError):
        return False


def _hhmm_to_minutes(s: str) -> int:
    """Convert HH:MM string to minutes since midnight."""
    h, m = s.split(":")
    return int(h) * 60 + int(m)


# -- Document structure


def _check_metadata(meta: GeotaskMetadata) -> list[dict]:
    diags: list[dict] = []

    # metadata.id must be non-empty and match ID_PATTERN
    if not meta.id:
        diags.append(
            _diagnostic(
                "metadata.id",
                MISSING_FIELD,
                "metadata.id is empty or missing.",
                'Set metadata.id to a valid identifier (starts with letter, max 128 chars, pattern: '
                + _ID_PATTERN.pattern
                + ")",
            )
        )
    elif not is_valid_geotask_id(meta.id):
        diags.append(
            _diagnostic(
                "metadata.id",
                INVALID_TYPE,
                f"metadata.id '{meta.id}' does not match required pattern.",
                f"Must match pattern: {_ID_PATTERN.pattern}",
            )
        )

    # metadata.schema_version must be present
    if not meta.schema_version:
        diags.append(
            _diagnostic(
                "metadata.schema_version",
                MISSING_FIELD,
                "metadata.schema_version is empty or missing.",
                'Set schema_version to "1.0".',
            )
        )

    return diags


def _check_duplicate_ids(doc: CanonicalDocument) -> list[dict]:
    diags: list[dict] = []

    # Duplicate task IDs
    task_ids: list[str] = []
    for task in doc.tasks:
        if task.id in task_ids:
            diags.append(
                _diagnostic(
                    f"tasks[{task.id}]",
                    DUPLICATE_ID,
                    f"Duplicate task id '{task.id}'.",
                    "Ensure all task ids are unique.",
                )
            )
        else:
            task_ids.append(task.id)

    # Duplicate assertion IDs across all tasks
    seen_assertion_ids: set[str] = set()
    for task in doc.tasks:
        for assertion in task.assertions:
            if assertion.id in seen_assertion_ids:
                diags.append(
                    _diagnostic(
                        f"tasks.{task.id}.assertions[{assertion.id}]",
                        DUPLICATE_ID,
                        f"Duplicate assertion id '{assertion.id}'.",
                        "Ensure all assertion ids are unique across the document.",
                    )
                )
            else:
                seen_assertion_ids.add(assertion.id)

    return diags


# -- Space


def _coordinate_order_is_valid(coordinate_order: object) -> bool:
    return (
        isinstance(coordinate_order, (list, tuple))
        and len(coordinate_order) == 2
        and all(isinstance(axis, str) and axis.strip() for axis in coordinate_order)
        and coordinate_order[0].strip().casefold()
        != coordinate_order[1].strip().casefold()
    )


def _normalized_boundary_semantics(space: SpaceDefinition) -> str:
    if not isinstance(space.boundary_semantics, str):
        return ""
    return space.boundary_semantics.strip().casefold()


def _check_space_structure(space: SpaceDefinition) -> list[dict]:
    diags: list[dict] = []
    crs_type = space.crs.type if space.crs else ""
    if crs_type not in _VALID_CRS_TYPES:
        diags.append(
            _diagnostic(
                "space.crs.type",
                INVALID_CRS,
                f"Invalid CRS type '{crs_type}'. "
                f"Must be one of: {sorted(_VALID_CRS_TYPES)}.",
                f"Set space.crs.type to one of: {', '.join(sorted(_VALID_CRS_TYPES))}.",
            )
        )

    for field_name, value in (
        ("horizontal_unit", space.horizontal_unit),
        ("vertical_unit", space.vertical_unit),
    ):
        if not isinstance(value, str) or not value.strip():
            diags.append(
                _diagnostic(
                    f"space.{field_name}",
                    MISSING_FIELD,
                    f"space.{field_name} is empty or missing.",
                    f'Set {field_name} to a unit string, e.g. "meter".',
                )
            )

    if not _coordinate_order_is_valid(space.coordinate_order):
        diags.append(
            _diagnostic(
                "space.coordinate_order",
                INVALID_COORDINATES,
                "space.coordinate_order must contain exactly two distinct non-empty axis names.",
                'Use a two-item order such as ["x", "y"].',
            )
        )

    boundary_semantics = _normalized_boundary_semantics(space)
    if boundary_semantics not in {"closed", "open"}:
        diags.append(
            _diagnostic(
                "space.boundary_semantics",
                INVALID_TYPE,
                f"Unsupported boundary semantics '{space.boundary_semantics}'.",
                'Set boundary_semantics to "closed" or "open".',
            )
        )
    return diags


def _check_planar_space_contract(
    space: SpaceDefinition,
    assertions: list[Assertion],
) -> list[dict]:
    planar_assertions = [
        assertion
        for assertion in assertions
        if assertion.operator in _PLANAR_OPERATOR_NAMES
    ]
    if not planar_assertions:
        return []

    diags: list[dict] = []
    crs_type = space.crs.type if space.crs else ""
    if crs_type not in {"local_cartesian", "projected"}:
        operator_names = sorted({a.operator for a in planar_assertions})
        diags.append(
            _diagnostic(
                "space.crs.type",
                INVALID_CRS,
                f"Planar operators {operator_names} cannot execute with CRS type "
                f"'{crs_type}'. Core does not project geographic coordinates or "
                "execute planar geometry under an unknown CRS.",
                "Use a local_cartesian or projected CRS, or transform coordinates "
                "outside Core before execution.",
            )
        )
    elif crs_type == "projected" and not (
        isinstance(space.crs.identifier, str) and space.crs.identifier.strip()
    ):
        diags.append(
            _diagnostic(
                "space.crs.identifier",
                INVALID_CRS,
                "Projected CRS requires a non-empty identifier.",
                'Provide an identifier such as "EPSG:3857" after verifying it is appropriate.',
            )
        )

    if _coordinate_order_is_valid(space.coordinate_order):
        normalized_order = [
            axis.strip().casefold() for axis in space.coordinate_order
        ]
        if normalized_order != ["x", "y"]:
            diags.append(
                _diagnostic(
                    "space.coordinate_order",
                    INVALID_COORDINATES,
                    f"Planar Core operators require coordinate_order [x, y], got {space.coordinate_order!r}.",
                    "Reorder coordinates outside Core and declare coordinate_order: [x, y].",
                )
            )
    return diags


def _check_boundary_space_contract(
    space: SpaceDefinition,
    assertions: list[Assertion],
) -> list[dict]:
    boundary_assertions = [
        assertion
        for assertion in assertions
        if assertion.operator in _BOUNDARY_SENSITIVE_OPERATOR_NAMES
    ]
    boundary_semantics = _normalized_boundary_semantics(space)
    if not boundary_assertions or boundary_semantics not in {"closed", "open"}:
        return []
    if boundary_semantics == "closed":
        return []

    operator_names = sorted({a.operator for a in boundary_assertions})
    return [
        _diagnostic(
            "space.boundary_semantics",
            BOUNDARY_SEMANTICS_MISMATCH,
            f"Operators {operator_names} implement closed-boundary semantics, "
            f"but the document declares '{boundary_semantics}'.",
            'Set boundary_semantics to "closed" or use an external operator '
            "whose contract explicitly implements the requested semantics.",
        )
    ]


def _check_space_unit_contracts(
    space: SpaceDefinition,
    tasks: list[Task],
    objects: dict[str, GeoObject],
) -> list[dict]:
    diags: list[dict] = []
    for task in tasks:
        for assertion_index, assertion in enumerate(task.assertions):
            if not default_registry.is_registered(assertion.operator):
                continue
            contract = default_registry.get(assertion.operator)
            if contract.output.get("unit_behavior") == "inherit_horizontal_unit":
                if assertion.unit and not _units_equivalent(
                    assertion.unit, space.horizontal_unit
                ):
                    diags.append(
                        _diagnostic(
                            f"tasks.{task.id}.assertions[{assertion_index}].unit",
                            UNIT_MISMATCH,
                            f"Assertion unit '{assertion.unit}' conflicts with "
                            f"space.horizontal_unit '{space.horizontal_unit}'. Core does not convert units.",
                            "Use the document horizontal unit or convert coordinates and expected values outside Core.",
                        )
                    )

    for object_id, obj in objects.items():
        if obj.type != "altitude_interval":
            continue
        object_unit = obj.data.get("unit")
        if object_unit and not _units_equivalent(object_unit, space.vertical_unit):
            diags.append(
                _diagnostic(
                    f"objects.{object_id}.data.unit",
                    UNIT_MISMATCH,
                    f"Altitude object unit '{object_unit}' conflicts with "
                    f"space.vertical_unit '{space.vertical_unit}'. Core does not convert vertical units.",
                    "Use the document vertical unit or convert the altitude interval outside Core.",
                )
            )

    for task in tasks:
        for assertion_index, assertion in enumerate(task.assertions):
            if assertion.operator != "altitude_overlap" or len(assertion.object_refs) != 2:
                continue
            left = objects.get(assertion.object_refs[0])
            right = objects.get(assertion.object_refs[1])
            if left is None or right is None:
                continue
            left_datum = left.data.get("datum")
            right_datum = right.data.get("datum")
            if (
                isinstance(left_datum, str)
                and left_datum.strip()
                and isinstance(right_datum, str)
                and right_datum.strip()
                and left_datum.strip().casefold() != right_datum.strip().casefold()
            ):
                diags.append(
                    _diagnostic(
                        f"tasks.{task.id}.assertions[{assertion_index}].object_refs",
                        INVALID_CRS,
                        f"Altitude overlap compares incompatible vertical datums "
                        f"'{left_datum}' and '{right_datum}'.",
                        "Transform both altitude intervals to the same verified vertical datum outside Core.",
                    )
                )
    return diags


def _check_space(
    space: SpaceDefinition,
    tasks: list[Task],
    objects: dict[str, GeoObject],
) -> list[dict]:
    """Validate the document-wide spatial execution contract.

    GeoTask Core does not transform CRS, reorder coordinates, convert units, or
    switch boundary semantics per task. Every task therefore shares one explicit
    fail-closed space contract.
    """
    assertions = [
        assertion
        for task in tasks
        for assertion in task.assertions
        if assertion.operator
    ]
    diagnostics = _check_space_structure(space)
    diagnostics.extend(_check_planar_space_contract(space, assertions))
    diagnostics.extend(_check_boundary_space_contract(space, assertions))
    diagnostics.extend(_check_space_unit_contracts(space, tasks, objects))
    return diagnostics


# -- Objects


def _check_objects(objects: dict[str, GeoObject]) -> list[dict]:
    diags: list[dict] = []

    for obj_id, obj in objects.items():
        obj_path = f"objects.{obj_id}"

        # Object id must match ID_PATTERN
        if not is_valid_geotask_id(obj_id):
            diags.append(
                _diagnostic(
                    obj_path,
                    INVALID_TYPE,
                    f"Object id '{obj_id}' does not match required pattern.",
                    f"Must match pattern: {_ID_PATTERN.pattern}",
                )
            )
            # Don't skip — continue validating the rest even with bad id

        # Object type must be valid
        if obj.type not in VALID_OBJECT_TYPES:
            diags.append(
                _diagnostic(
                    f"{obj_path}.type",
                    UNKNOWN_OBJECT_TYPE,
                    f"Unknown object type '{obj.type}' for '{obj_id}'.",
                    f"Must be one of: {sorted(VALID_OBJECT_TYPES)}.",
                )
            )
            continue  # skip per-type validation for unknown types

        # Per-type data validation
        diags.extend(_check_object_data(obj_path, obj))

    # A trajectory is meaningful only when it binds to one declared moving object.
    for obj_id, obj in objects.items():
        if obj.type != "trajectory":
            continue
        subject_ref = obj.data.get("subject_ref")
        if not isinstance(subject_ref, str) or not subject_ref:
            continue
        subject = objects.get(subject_ref)
        if subject is None:
            diags.append(
                _diagnostic(
                    f"objects.{obj_id}.data.subject_ref",
                    INVALID_REFERENCE,
                    f"Trajectory subject_ref '{subject_ref}' does not resolve.",
                    "Reference one declared moving_object id.",
                )
            )
        elif subject.type != "moving_object":
            diags.append(
                _diagnostic(
                    f"objects.{obj_id}.data.subject_ref",
                    OBJECT_TYPE_MISMATCH,
                    f"Trajectory subject_ref '{subject_ref}' has type '{subject.type}', expected 'moving_object'.",
                    "Bind the trajectory to a moving_object, not a static geometry.",
                )
            )

    return diags


def _check_object_data(path: str, obj: GeoObject) -> list[dict]:
    """Dispatch to the appropriate per-type validation function."""
    data = obj.data
    obj_type = obj.type

    if obj_type == "point":
        return _check_point_data(path, data)
    elif obj_type == "polyline":
        return _check_polyline_data(path, data)
    elif obj_type == "multi_polyline":
        return _check_multi_polyline_data(path, data)
    elif obj_type == "polygon":
        return _check_polygon_data(path, data)
    elif obj_type == "rect":
        return _check_rect_data(path, data)
    elif obj_type == "time_interval":
        return _check_time_interval_data(path, data)
    elif obj_type == "altitude_interval":
        return _check_altitude_interval_data(path, data)
    elif obj_type == "feature_collection":
        return _check_feature_collection_data(path, data)
    elif obj_type == "moving_object":
        return _check_moving_object_data(path, data)
    elif obj_type == "trajectory":
        return _check_trajectory_data(path, data)
    return []


def _check_point_data(path: str, data: dict) -> list[dict]:
    diags: list[dict] = []

    coords = data.get("coordinates") or data.get("xy")

    if coords is None:
        diags.append(
            _diagnostic(
                f"{path}.data",
                MISSING_DATA,
                "Point object missing coordinates (neither 'coordinates' nor 'xy' field).",
                'Provide data with {"coordinates": [x, y]} or {"xy": [x, y]}.',
            )
        )
        return diags

    if not isinstance(coords, (list, tuple)) or len(coords) != 2:
        diags.append(
            _diagnostic(
                f"{path}.data.coordinates",
                INVALID_COORDINATES,
                "Point coordinates must be exactly 2 values.",
                "Provide exactly 2 finite numbers, e.g. [x, y].",
            )
        )
        return diags

    for i, val in enumerate(coords):
        if not _is_finite_number(val):
            diags.append(
                _diagnostic(
                    f"{path}.data.coordinates[{i}]",
                    INVALID_COORDINATES,
                    f"Point coordinate[{i}] is not a finite number: {val!r}.",
                    "All coordinates must be finite numbers (not bool, NaN, or Inf).",
                )
            )

    return diags


def _check_polyline_data(path: str, data: dict) -> list[dict]:
    diags: list[dict] = []

    coords = data.get("coordinates") or data.get("points")

    if coords is None:
        diags.append(
            _diagnostic(
                f"{path}.data",
                MISSING_DATA,
                "Polyline object missing coordinates (neither 'coordinates' nor 'points' field).",
                'Provide data with {"coordinates": [[x1,y1], [x2,y2], ...]} or {"points": [...]}.',
            )
        )
        return diags

    if not isinstance(coords, (list, tuple)):
        diags.append(
            _diagnostic(
                f"{path}.data.coordinates",
                INVALID_GEOMETRY,
                "Polyline coordinates must be a list of points.",
                "Provide a list of 2+ points, each with 2 finite numbers.",
            )
        )
        return diags

    if len(coords) < 2:
        diags.append(
            _diagnostic(
                f"{path}.data.coordinates",
                INVALID_GEOMETRY,
                f"Polyline must have at least 2 points, got {len(coords)}.",
                "Provide at least 2 points, each with 2 finite numbers.",
            )
        )

    for pi, point in enumerate(coords):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            diags.append(
                _diagnostic(
                    f"{path}.data.coordinates[{pi}]",
                    INVALID_GEOMETRY,
                    f"Polyline point[{pi}] must be exactly 2 values, got {point!r}.",
                    "Each point must be [x, y] with 2 finite numbers.",
                )
            )
            continue
        for ci, val in enumerate(point):
            if not _is_finite_number(val):
                diags.append(
                    _diagnostic(
                        f"{path}.data.coordinates[{pi}][{ci}]",
                        INVALID_COORDINATES,
                        f"Polyline point[{pi}][{ci}] is not a finite number: {val!r}.",
                        "All coordinates must be finite numbers (not bool, NaN, or Inf).",
                    )
                )

    return diags


def _check_multi_polyline_data(path: str, data: dict) -> list[dict]:
    diags: list[dict] = []
    lines = data.get("coordinates") or data.get("lines")

    if lines is None:
        return [
            _diagnostic(
                f"{path}.data",
                MISSING_DATA,
                "Multi-polyline object missing coordinates or lines field.",
                'Provide data with {"coordinates": [[[x1,y1], [x2,y2]], ...]}.',
            )
        ]
    if not isinstance(lines, (list, tuple)) or not lines:
        return [
            _diagnostic(
                f"{path}.data.coordinates",
                INVALID_GEOMETRY,
                "Multi-polyline coordinates must contain at least one polyline.",
                "Provide one or more polylines, each containing at least two points.",
            )
        ]

    for line_index, line in enumerate(lines):
        line_path = f"{path}.data.coordinates[{line_index}]"
        if not isinstance(line, (list, tuple)) or len(line) < 2:
            diags.append(
                _diagnostic(
                    line_path,
                    INVALID_GEOMETRY,
                    f"Multi-polyline member[{line_index}] must contain at least 2 points.",
                    "Provide at least two [x, y] points for every member polyline.",
                )
            )
            continue
        for point_index, point in enumerate(line):
            point_path = f"{line_path}[{point_index}]"
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                diags.append(
                    _diagnostic(
                        point_path,
                        INVALID_GEOMETRY,
                        f"Multi-polyline point[{line_index}][{point_index}] must be exactly 2 values.",
                        "Each point must be [x, y] with two finite numbers.",
                    )
                )
                continue
            for coordinate_index, value in enumerate(point):
                if not _is_finite_number(value):
                    diags.append(
                        _diagnostic(
                            f"{point_path}[{coordinate_index}]",
                            INVALID_COORDINATES,
                            f"Multi-polyline coordinate is not finite: {value!r}.",
                            "All coordinates must be finite numbers (not bool, NaN, or Inf).",
                        )
                    )
    return diags


def _check_polygon_data(path: str, data: dict) -> list[dict]:
    diags: list[dict] = []
    ring = data.get("coordinates") or data.get("points")

    if ring is None:
        return [
            _diagnostic(
                f"{path}.data",
                MISSING_DATA,
                "Polygon object missing coordinates or points field.",
                'Provide a closed ring such as {"coordinates": [[0,0], [1,0], [1,1], [0,0]]}.',
            )
        ]
    if not isinstance(ring, (list, tuple)) or len(ring) < 4:
        return [
            _diagnostic(
                f"{path}.data.coordinates",
                INVALID_GEOMETRY,
                "Polygon ring must contain at least 4 points including closure.",
                "Provide at least three vertices and repeat the first point at the end.",
            )
        ]

    shape_valid = True
    finite_valid = True
    for point_index, point in enumerate(ring):
        point_path = f"{path}.data.coordinates[{point_index}]"
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            shape_valid = False
            diags.append(
                _diagnostic(
                    point_path,
                    INVALID_GEOMETRY,
                    f"Polygon point[{point_index}] must be exactly 2 values.",
                    "Each point must be [x, y] with two finite numbers.",
                )
            )
            continue
        for coordinate_index, value in enumerate(point):
            if not _is_finite_number(value):
                finite_valid = False
                diags.append(
                    _diagnostic(
                        f"{point_path}[{coordinate_index}]",
                        INVALID_COORDINATES,
                        f"Polygon coordinate is not finite: {value!r}.",
                        "All coordinates must be finite numbers (not bool, NaN, or Inf).",
                    )
                )

    if shape_valid and finite_valid:
        normalized_ring = [tuple(point) for point in ring]
        if normalized_ring[0] != normalized_ring[-1]:
            diags.append(
                _diagnostic(
                    f"{path}.data.coordinates",
                    INVALID_GEOMETRY,
                    "Polygon ring is not closed.",
                    "Repeat the first coordinate as the final coordinate.",
                )
            )
        if len(set(normalized_ring[:-1])) < 3:
            diags.append(
                _diagnostic(
                    f"{path}.data.coordinates",
                    INVALID_GEOMETRY,
                    "Polygon ring must contain at least 3 distinct vertices.",
                    "Provide at least three distinct vertices before the closing point.",
                )
            )
    return diags


def _check_rect_data(path: str, data: dict) -> list[dict]:
    diags: list[dict] = []

    bbox = data.get("bbox")

    if bbox is None:
        diags.append(
            _diagnostic(
                f"{path}.data",
                MISSING_DATA,
                "Rect object missing bbox field.",
                'Provide data with {"bbox": [min_x, min_y, max_x, max_y]}.',
            )
        )
        return diags

    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        diags.append(
            _diagnostic(
                f"{path}.data.bbox",
                INVALID_GEOMETRY,
                "Rect bbox must be exactly 4 values [min_x, min_y, max_x, max_y].",
                "Provide exactly 4 finite numbers.",
            )
        )
        return diags

    axis_labels = ["min_x", "min_y", "max_x", "max_y"]
    for i, val in enumerate(bbox):
        if not _is_finite_number(val):
            diags.append(
                _diagnostic(
                    f"{path}.data.bbox[{i}]",
                    INVALID_COORDINATES,
                    f"Rect bbox {axis_labels[i]} is not a finite number: {val!r}.",
                    "All bbox values must be finite numbers (not bool, NaN, or Inf).",
                )
            )

    # If all four are valid numbers, check ordering constraints
    if all(_is_finite_number(v) for v in bbox):
        min_x, min_y, max_x, max_y = bbox
        if min_x > max_x:
            diags.append(
                _diagnostic(
                    f"{path}.data.bbox",
                    INVALID_GEOMETRY,
                    f"Rect bbox min_x ({min_x}) > max_x ({max_x}).",
                    "Ensure min_x <= max_x.",
                )
            )
        if min_y > max_y:
            diags.append(
                _diagnostic(
                    f"{path}.data.bbox",
                    INVALID_GEOMETRY,
                    f"Rect bbox min_y ({min_y}) > max_y ({max_y}).",
                    "Ensure min_y <= max_y.",
                )
            )

    return diags


def _check_time_interval_data(path: str, data: dict) -> list[dict]:
    diags: list[dict] = []

    has_individual = "start" in data and "end" in data
    has_interval = "interval" in data

    if not has_individual and not has_interval:
        diags.append(
            _diagnostic(
                f"{path}.data",
                MISSING_DATA,
                "Time interval missing 'start'/'end' or 'interval' fields.",
                'Provide {"start": "HH:MM", "end": "HH:MM"} or {"interval": ["HH:MM", "HH:MM"]}.',
            )
        )
        return diags

    if has_individual:
        start = data.get("start")
        end = data.get("end")
        diags.extend(_validate_time_pair(path, start, end, "start", "end"))
    elif has_interval:
        interval = data["interval"]
        if not isinstance(interval, (list, tuple)) or len(interval) != 2:
            diags.append(
                _diagnostic(
                    f"{path}.data.interval",
                    INVALID_INTERVAL,
                    "Time interval list must be exactly 2 values.",
                    'Provide {"interval": ["HH:MM", "HH:MM"]}.',
                )
            )
        else:
            diags.extend(_validate_time_pair(path, interval[0], interval[1], "interval[0]", "interval[1]"))

    return diags


def _validate_time_pair(
    path: str, start: object, end: object, start_label: str, end_label: str
) -> list[dict]:
    """Validate a pair of HH:MM time strings with start <= end."""
    diags: list[dict] = []

    if not _is_valid_hhmm(start):
        diags.append(
            _diagnostic(
                f"{path}.data.{start_label}",
                INVALID_INTERVAL,
                f"Invalid time format for {start_label}: {start!r}. Expected HH:MM.",
                'Provide time in "HH:MM" format (e.g. "08:00").',
            )
        )
    if not _is_valid_hhmm(end):
        diags.append(
            _diagnostic(
                f"{path}.data.{end_label}",
                INVALID_INTERVAL,
                f"Invalid time format for {end_label}: {end!r}. Expected HH:MM.",
                'Provide time in "HH:MM" format (e.g. "10:00").',
            )
        )

    # Only compare if both are valid
    if isinstance(start, str) and isinstance(end, str) and _is_valid_hhmm(start) and _is_valid_hhmm(end):
        if _hhmm_to_minutes(start) > _hhmm_to_minutes(end):
            diags.append(
                _diagnostic(
                    f"{path}.data",
                    INVALID_INTERVAL,
                    f"Time interval start '{start}' is after end '{end}'.",
                    "Ensure start <= end.",
                )
            )

    return diags


def _check_altitude_interval_data(path: str, data: dict) -> list[dict]:
    diags: list[dict] = []

    has_individual = "min" in data and "max" in data
    has_range = "range" in data

    if not has_individual and not has_range:
        diags.append(
            _diagnostic(
                f"{path}.data",
                MISSING_DATA,
                "Altitude interval missing 'min'/'max' or 'range' fields.",
                'Provide {"min": 100, "max": 200} or {"range": [100, 200]}.',
            )
        )
        return diags

    if has_individual:
        min_val = data.get("min")
        max_val = data.get("max")
        diags.extend(_validate_altitude_pair(path, min_val, max_val, "min", "max"))
    elif has_range:
        range_val = data["range"]
        if not isinstance(range_val, (list, tuple)) or len(range_val) != 2:
            diags.append(
                _diagnostic(
                    f"{path}.data.range",
                    INVALID_INTERVAL,
                    "Altitude range list must be exactly 2 values.",
                    'Provide {"range": [min, max]}.',
                )
            )
        else:
            diags.extend(_validate_altitude_pair(path, range_val[0], range_val[1], "range[0]", "range[1]"))

    return diags


def _validate_altitude_pair(
    path: str, min_val: object, max_val: object, min_label: str, max_label: str
) -> list[dict]:
    """Validate a pair of altitude numbers with min <= max."""
    diags: list[dict] = []

    if not _is_finite_number(min_val):
        diags.append(
            _diagnostic(
                f"{path}.data.{min_label}",
                INVALID_INTERVAL,
                f"Altitude {min_label} is not a finite number: {min_val!r}.",
                "Altitude values must be finite numbers (not bool, NaN, or Inf).",
            )
        )
    if not _is_finite_number(max_val):
        diags.append(
            _diagnostic(
                f"{path}.data.{max_label}",
                INVALID_INTERVAL,
                f"Altitude {max_label} is not a finite number: {max_val!r}.",
                "Altitude values must be finite numbers (not bool, NaN, or Inf).",
            )
        )

    # Only compare if both are valid numbers
    # _is_finite_number already verified both are numeric; type-narrower can't infer this
    if _is_finite_number(min_val) and _is_finite_number(max_val) and min_val > max_val:  # type: ignore[operator]
        diags.append(
            _diagnostic(
                f"{path}.data",
                INVALID_INTERVAL,
                f"Altitude min ({min_val}) > max ({max_val}).",
                "Ensure min <= max.",
            )
        )

    return diags


def _check_moving_object_data(path: str, data: dict) -> list[dict]:
    """Validate the minimal identity-only moving-object contract."""
    diags: list[dict] = []
    allowed = {"object_class", "identity"}
    for field_name in sorted(set(data) - allowed):
        diags.append(
            _diagnostic(
                f"{path}.data.{field_name}",
                UNKNOWN_FIELD,
                f"Moving object contains unsupported field '{field_name}'.",
                "Keep position and time observations in a separate trajectory object.",
            )
        )
    for field_name in ("object_class", "identity"):
        value = data.get(field_name)
        if not isinstance(value, str) or not value.strip():
            diags.append(
                _diagnostic(
                    f"{path}.data.{field_name}",
                    MISSING_FIELD,
                    f"Moving object {field_name} must be a non-empty string.",
                    f"Provide data.{field_name} as a stable caller-declared string.",
                )
            )
    return diags


def _parse_trajectory_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _check_trajectory_data(path: str, data: dict) -> list[dict]:
    """Validate discrete trajectory samples without inferring intermediate state."""
    diags: list[dict] = []
    allowed = {"subject_ref", "interpolation", "samples"}
    for field_name in sorted(set(data) - allowed):
        diags.append(
            _diagnostic(
                f"{path}.data.{field_name}",
                UNKNOWN_FIELD,
                f"Trajectory contains unsupported field '{field_name}'.",
                "Use only subject_ref, interpolation, and explicit samples.",
            )
        )

    subject_ref = data.get("subject_ref")
    if not isinstance(subject_ref, str) or not is_valid_geotask_id(subject_ref):
        diags.append(
            _diagnostic(
                f"{path}.data.subject_ref",
                INVALID_REFERENCE,
                "Trajectory subject_ref must be a valid non-empty GeoTask id.",
                "Reference one declared moving_object id.",
            )
        )

    if data.get("interpolation") != "none":
        diags.append(
            _diagnostic(
                f"{path}.data.interpolation",
                INVALID_TYPE,
                "Trajectory interpolation must be exactly 'none'.",
                "Set interpolation to 'none'; Core does not infer intermediate positions.",
            )
        )

    samples = data.get("samples")
    if not isinstance(samples, list) or len(samples) < 2:
        diags.append(
            _diagnostic(
                f"{path}.data.samples",
                MISSING_DATA,
                "Trajectory must contain at least two explicit samples.",
                "Provide two or more timestamped coordinate samples.",
            )
        )
        return diags

    previous_time: datetime | None = None
    for index, sample in enumerate(samples):
        sample_path = f"{path}.data.samples[{index}]"
        if not isinstance(sample, dict):
            diags.append(
                _diagnostic(
                    sample_path,
                    INVALID_TYPE,
                    "Trajectory sample must be an object.",
                    "Provide observed_at and coordinates fields.",
                )
            )
            continue

        sample_allowed = {"observed_at", "coordinates"}
        for field_name in sorted(set(sample) - sample_allowed):
            diags.append(
                _diagnostic(
                    f"{sample_path}.{field_name}",
                    UNKNOWN_FIELD,
                    f"Trajectory sample contains unsupported field '{field_name}'.",
                    "Keep each sample limited to observed_at and coordinates.",
                )
            )

        observed_at = _parse_trajectory_time(sample.get("observed_at"))
        if observed_at is None:
            diags.append(
                _diagnostic(
                    f"{sample_path}.observed_at",
                    INVALID_INTERVAL,
                    "Trajectory observed_at must be a timezone-aware ISO date-time.",
                    "Use RFC3339/ISO 8601 with Z or an explicit UTC offset.",
                )
            )
        elif previous_time is not None and observed_at <= previous_time:
            diags.append(
                _diagnostic(
                    f"{sample_path}.observed_at",
                    INVALID_INTERVAL,
                    "Trajectory sample times must be strictly increasing.",
                    "Order samples chronologically and remove duplicate timestamps.",
                )
            )
        if observed_at is not None:
            previous_time = observed_at

        coordinates = sample.get("coordinates")
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) != 2:
            diags.append(
                _diagnostic(
                    f"{sample_path}.coordinates",
                    INVALID_COORDINATES,
                    "Trajectory coordinates must be exactly two values.",
                    "Provide [x, y] in the document coordinate order.",
                )
            )
            continue
        for coordinate_index, value in enumerate(coordinates):
            if not _is_finite_number(value):
                diags.append(
                    _diagnostic(
                        f"{sample_path}.coordinates[{coordinate_index}]",
                        INVALID_COORDINATES,
                        f"Trajectory coordinate is not finite: {value!r}.",
                        "Use finite numeric coordinates only.",
                    )
                )
    return diags


def _check_feature_collection_data(path: str, data: dict) -> list[dict]:
    diags: list[dict] = []

    if "features" not in data:
        diags.append(
            _diagnostic(
                f"{path}.data",
                MISSING_DATA,
                "Feature collection missing 'features' field.",
                'Provide data with {"feature_type": "point", "features": [...]}.',
            )
        )
    elif not isinstance(data["features"], list):
        diags.append(
            _diagnostic(
                f"{path}.data.features",
                INVALID_TYPE,
                "Feature collection 'features' must be a list.",
                "Provide a list of feature objects.",
            )
        )

    if "feature_type" not in data:
        diags.append(
            _diagnostic(
                f"{path}.data",
                MISSING_DATA,
                "Feature collection missing 'feature_type' field.",
                'Provide data with {"feature_type": "<type>", "features": [...]}.',
            )
        )
    elif not isinstance(data["feature_type"], str) or not data["feature_type"]:
        diags.append(
            _diagnostic(
                f"{path}.data.feature_type",
                INVALID_TYPE,
                "Feature collection 'feature_type' must be a non-empty string.",
                'Provide a valid feature type string, e.g. "point".',
            )
        )

    return diags


# -- Tasks and Assertions


def _check_tasks_and_assertions(
    tasks: list[Task], objects: dict[str, GeoObject]
) -> list[dict]:
    diags: list[dict] = []
    seen_task_ids: set[str] = set()
    all_assertion_ids: set[str] = set()
    depends_on_map: dict[str, list[str]] = {}

    for task in tasks:
        task_path = f"tasks.{task.id}"

        # Unique task id
        if task.id in seen_task_ids:
            diags.append(
                _diagnostic(
                    task_path,
                    DUPLICATE_ID,
                    f"Duplicate task id '{task.id}'.",
                    "Ensure all task ids are unique.",
                )
            )
        seen_task_ids.add(task.id)

        for ai, assertion in enumerate(task.assertions):
            apath = f"{task_path}.assertions[{ai}]"

            # Required fields
            if not assertion.id:
                diags.append(
                    _diagnostic(
                        apath,
                        MISSING_FIELD,
                        "Assertion missing 'id'.",
                        "Every assertion must have a unique id.",
                    )
                )
                continue
            if not assertion.operator:
                diags.append(
                    _diagnostic(
                        f"{apath}.operator",
                        MISSING_FIELD,
                        f"Assertion '{assertion.id}' missing 'operator'.",
                        "Every assertion must have an operator.",
                    )
                )

            # Unique assertion id
            actual_id = f"{task.id}/assertions/{assertion.id}"
            if assertion.id in all_assertion_ids:
                diags.append(
                    _diagnostic(
                        apath,
                        DUPLICATE_ID,
                        f"Duplicate assertion id '{assertion.id}'.",
                        "Ensure all assertion ids are unique across the document.",
                    )
                )
            all_assertion_ids.add(assertion.id)

            # operator registered
            if assertion.operator and not default_registry.is_registered(assertion.operator):
                diags.append(
                    _diagnostic(
                        f"{apath}.operator",
                        INVALID_OPERATOR,
                        f"Operator '{assertion.operator}' is not registered. "
                        f"Available: {default_registry.list_names()}.",
                        "Use a registered operator or register a new one.",
                        severity="error",
                    )
                )

            # object_refs must reference existing objects
            for ri, ref in enumerate(assertion.object_refs):
                if ref not in objects:
                    diags.append(
                        _diagnostic(
                            f"{apath}.object_refs[{ri}]",
                            INVALID_REFERENCE,
                            f"Assertion '{assertion.id}' references unknown object '{ref}'.",
                            "Ensure object_refs reference existing object ids.",
                            severity="error",
                        )
                    )

            # depends_on must reference existing assertion IDs
            depends_on_map[assertion.id] = assertion.depends_on
            for di_idx, dep_id in enumerate(assertion.depends_on):
                # We'll check after collecting all assertion IDs
                pass  # deferred to after all assertions are collected

    # Now validate all depends_on references (need all assertion IDs)
    for task in tasks:
        for ai, assertion in enumerate(task.assertions):
            apath = f"tasks.{task.id}.assertions[{ai}]"
            for di_idx, dep_id in enumerate(assertion.depends_on):
                if dep_id not in all_assertion_ids:
                    diags.append(
                        _diagnostic(
                            f"{apath}.depends_on[{di_idx}]",
                            INVALID_REFERENCE,
                            f"Assertion '{assertion.id}' depends_on unknown assertion '{dep_id}'.",
                            "Ensure depends_on references existing assertion ids.",
                        )
                    )

    # Cycle detection in assertion dependencies
    cycle = _detect_cycle_in_graph(all_assertion_ids, depends_on_map)
    if cycle:
        diags.append(
            _diagnostic(
                "tasks.*.assertions.depends_on",
                CYCLIC_DEPENDENCY,
                f"Cyclic dependency detected among assertions: {' -> '.join(cycle)}.",
                "Break the dependency cycle by removing or reordering dependencies.",
                severity="error",
            )
        )

    return diags


# -- Operator binding


def _check_operator_binding(
    tasks: list[Task], objects: dict[str, GeoObject]
) -> list[dict]:
    diags: list[dict] = []

    for task in tasks:
        for ai, assertion in enumerate(task.assertions):
            apath = f"tasks.{task.id}.assertions[{ai}]"

            if not assertion.operator or not default_registry.is_registered(assertion.operator):
                continue  # already reported above

            contract = default_registry.get(assertion.operator)

            # Arity check
            if len(assertion.object_refs) != contract.arity:
                diags.append(
                    _diagnostic(
                        f"{apath}.object_refs",
                        ARITY_MISMATCH,
                        f"Operator '{assertion.operator}' expects {contract.arity} "
                        f"object ref(s), got {len(assertion.object_refs)}.",
                        f"Provide exactly {contract.arity} object references.",
                    )
                )

            # Object type match (when arity matches)
            if len(assertion.object_refs) == contract.arity:
                for ri, (ref, expected_type) in enumerate(
                    zip(assertion.object_refs, contract.input_types)
                ):
                    obj = objects.get(ref)
                    if obj is None:
                        continue  # already reported as invalid reference

                    actual_type = obj.type
                    # Normalize through legacy map
                    normalized_actual = LEGACY_OBJECT_TYPE_MAP.get(actual_type, actual_type)

                    if normalized_actual != expected_type:
                        diags.append(
                            _diagnostic(
                                f"{apath}.object_refs[{ri}]",
                                OBJECT_TYPE_MISMATCH,
                                f"Operator '{assertion.operator}' expects type '{expected_type}' "
                                f"for argument {ri}, but object '{ref}' is type '{actual_type}'.",
                                f"Use a '{expected_type}' object or a compatible operator.",
                            )
                        )

            if assertion.operator == "trajectory_segment_classifications":
                diags.extend(
                    _check_trajectory_classification_parameters(
                        f"{apath}.parameters", assertion.parameters
                    )
                )

    return diags


def _check_trajectory_classification_parameters(path: str, parameters: dict) -> list[dict]:
    """Validate the exact caller-authored trajectory classification thresholds."""
    diags: list[dict] = []
    required = {
        "stationary_radius_in_horizontal_unit",
        "minimum_stationary_duration_seconds",
        "maximum_observation_gap_seconds",
        "allow_observation_gap",
    }
    actual = set(parameters)
    for name in sorted(required - actual):
        diags.append(
            _diagnostic(
                f"{path}.{name}",
                MISSING_FIELD,
                f"trajectory_segment_classifications requires parameter '{name}'.",
                "Declare every GT35 threshold explicitly; Core does not choose defaults.",
            )
        )
    for name in sorted(actual - required):
        diags.append(
            _diagnostic(
                f"{path}.{name}",
                UNKNOWN_FIELD,
                f"Unknown trajectory classification parameter '{name}'.",
                f"Use only {sorted(required)}.",
            )
        )

    numeric_rules = {
        "stationary_radius_in_horizontal_unit": "non_negative",
        "minimum_stationary_duration_seconds": "positive",
        "maximum_observation_gap_seconds": "positive",
    }
    for name, rule in numeric_rules.items():
        if name not in parameters:
            continue
        value = parameters[name]
        valid = _is_finite_number(value)
        if valid and rule == "non_negative":
            valid = value >= 0
        if valid and rule == "positive":
            valid = value > 0
        if not valid:
            expectation = (
                "a finite non-negative number"
                if rule == "non_negative"
                else "a finite positive number"
            )
            diags.append(
                _diagnostic(
                    f"{path}.{name}",
                    INVALID_TYPE,
                    f"Parameter '{name}' must be {expectation}.",
                    "Provide an explicit numeric threshold in the document's declared units.",
                )
            )

    if "allow_observation_gap" in parameters and not isinstance(
        parameters["allow_observation_gap"], bool
    ):
        diags.append(
            _diagnostic(
                f"{path}.allow_observation_gap",
                INVALID_TYPE,
                "Parameter 'allow_observation_gap' must be boolean.",
                "Use true to permit observation_gap, or false to return unverifiable.",
            )
        )
    return diags


# -- Execution


def _check_execution(
    execution: ExecutionDefinition, tasks: list[Task]
) -> list[dict]:
    diags: list[dict] = []

    # execution.mode must be valid
    if execution.mode not in _VALID_EXECUTION_MODES:
        diags.append(
            _diagnostic(
                "execution.mode",
                UNSUPPORTED_EXECUTION_MODE,
                f"Invalid execution mode '{execution.mode}'. "
                f"Must be one of: {sorted(_VALID_EXECUTION_MODES)}.",
                f"Set execution.mode to one of: {', '.join(sorted(_VALID_EXECUTION_MODES))}.",
            )
        )

    # Collect all assertion IDs
    all_assertion_ids: set[str] = set()
    for task in tasks:
        for assertion in task.assertions:
            all_assertion_ids.add(assertion.id)

    # Execution steps validation
    step_ids: set[str] = set()
    step_depends_on: dict[str, list[str]] = {}

    for si, step in enumerate(execution.steps):
        spath = f"execution.steps[{si}]"

        if not isinstance(step, ExecutionStep):
            diags.append(
                _diagnostic(
                    spath,
                    INVALID_TYPE,
                    f"Expected ExecutionStep, got {type(step).__name__}.",
                    "Ensure all execution steps are ExecutionStep instances.",
                )
            )
            continue

        # Unique step id
        if step.id in step_ids:
            diags.append(
                _diagnostic(
                    f"{spath}.id",
                    DUPLICATE_ID,
                    f"Duplicate execution step id '{step.id}'.",
                    "Ensure all execution step ids are unique.",
                )
            )
        step_ids.add(step.id)

        # assertion_refs must reference existing assertion IDs
        for ri, ref in enumerate(step.assertion_refs):
            if ref not in all_assertion_ids:
                diags.append(
                    _diagnostic(
                        f"{spath}.assertion_refs[{ri}]",
                        INVALID_REFERENCE,
                        f"Execution step '{step.id}' references unknown assertion '{ref}'.",
                        "Ensure assertion_refs reference existing assertion ids.",
                    )
                )

        # depends_on must reference existing step IDs (deferred)
        step_depends_on[step.id] = step.depends_on

    # Validate step depends_on references (after collecting all step IDs)
    for si, step in enumerate(execution.steps):
        if not isinstance(step, ExecutionStep):
            continue
        spath = f"execution.steps[{si}]"
        for di_idx, dep_id in enumerate(step.depends_on):
            if dep_id not in step_ids:
                diags.append(
                    _diagnostic(
                        f"{spath}.depends_on[{di_idx}]",
                        INVALID_REFERENCE,
                        f"Execution step '{step.id}' depends_on unknown step '{dep_id}'.",
                        "Ensure depends_on references existing step ids.",
                    )
                )

    # Cycle detection in execution step dependencies
    cycle = _detect_cycle_in_graph(step_ids, step_depends_on)
    if cycle:
        diags.append(
            _diagnostic(
                "execution.steps.*.depends_on",
                CYCLIC_DEPENDENCY,
                f"Cyclic dependency detected among execution steps: {' -> '.join(cycle)}.",
                "Break the dependency cycle by removing or reordering dependencies.",
                severity="error",
            )
        )

    return diags


# -- Output contract


def _check_output_contract(oc: OutputContract) -> list[dict]:
    diags: list[dict] = []

    # required_fields must not contain duplicates
    required = oc.required_fields
    if len(required) != len(set(required)):
        seen: set[str] = set()
        for field in required:
            if field in seen:
                diags.append(
                    _diagnostic(
                        "output_contract.required_fields",
                        DUPLICATE_ID,
                        f"Duplicate required field '{field}'.",
                        "Remove duplicate entries from required_fields.",
                    )
                )
                break
            seen.add(field)

    # numeric_precision.decimal_places must be non-negative integer if present
    np_dict = oc.numeric_precision
    dp = np_dict.get("decimal_places") if isinstance(np_dict, dict) else None
    if dp is not None:
        if not isinstance(dp, int) or isinstance(dp, bool) or dp < 0:
            diags.append(
                _diagnostic(
                    "output_contract.numeric_precision.decimal_places",
                    INVALID_TYPE,
                    f"decimal_places must be a non-negative integer, got {dp!r}.",
                    "Set decimal_places to a non-negative integer (e.g. 2).",
                )
            )

    # ordering must reference fields in required_fields if present
    ordering = oc.ordering
    if isinstance(ordering, dict) and ordering:
        required_set = set(required)
        by_field = ordering.get("by", "")
        direction = ordering.get("direction", "")

        # Only check ordering.by value against required_fields — the keys
        # ("by", "direction") and the direction value ("ascending",
        # "descending") are NOT field names.
        if by_field and by_field not in required_set:
            diags.append(
                _diagnostic(
                    "output_contract.ordering.by",
                    OUTPUT_CONTRACT_VIOLATION,
                    f"Ordering 'by' field '{by_field}' not in required_fields.",
                    f"Add '{by_field}' to required_fields or change ordering.by.",
                    severity="warning",
                )
            )

        # Validate direction
        if direction and direction not in ("ascending", "descending"):
            diags.append(
                _diagnostic(
                    "output_contract.ordering.direction",
                    OUTPUT_CONTRACT_VIOLATION,
                    f"Ordering direction must be 'ascending' or "
                    f"'descending', got '{direction}'.",
                    f"Set ordering.direction to 'ascending' or 'descending'.",
                    severity="warning",
                )
            )

    return diags


# -- Assurance reachability


def _check_assurance_reachability(
    execution: ExecutionDefinition, verification: VerificationDefinition
) -> list[dict]:
    diags: list[dict] = []
    mode = execution.mode
    required = verification.required_assurance

    if not required or required == "none":
        return diags

    # Map assurance string to integer level
    try:
        required_level = AssuranceLevel[required].value
    except KeyError:
        diags.append(
            _diagnostic(
                "verification.required_assurance",
                INVALID_TYPE,
                f"Unknown assurance level '{required}'.",
                f"Must be one of: {[e.name for e in AssuranceLevel]}.",
            )
        )
        return diags

    # Check model agreement specifically for local_only
    if mode == "local_only" and required_level >= AssuranceLevel.model_local_agreement.value:
        diags.append(
            _diagnostic(
                "verification.required_assurance",
                UNVERIFIABLE_CLAIM,
                f"Execution mode 'local_only' cannot achieve assurance level "
                f"'{required}' (requires model agreement).",
                "Switch to 'hybrid' or 'shadow_compare' mode for model agreement, "
                "or lower required_assurance to 'local_deterministic' or below.",
                severity="warning",
            )
        )

    # General achievability check
    max_level = _MAX_ACHIEVABLE_BY_MODE.get(mode, 0)
    if required_level > max_level:
        # Avoid duplicate if we already flagged model agreement above
        if not (mode == "local_only" and required_level >= AssuranceLevel.model_local_agreement.value):
            diags.append(
                _diagnostic(
                    "verification.required_assurance",
                    UNVERIFIABLE_CLAIM,
                    f"Execution mode '{mode}' can achieve at most "
                    f"AssuranceLevel.{AssuranceLevel(max_level).name} ({max_level}), "
                    f"but required_assurance is '{required}' ({required_level}).",
                    f"Change execution mode or lower required_assurance to at most "
                    f"level {max_level}.",
                    severity="warning",
                )
            )

    return diags


# -- Graph cycle detection


def _detect_cycle_in_graph(
    node_ids: set[str], adjacency: dict[str, list[str]]
) -> list[str] | None:
    """DFS-based cycle detection. Returns a cycle path or None.

    *adjacency* maps a node to the list of nodes it depends on.
    Edges go from a node TO its dependencies.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {nid: WHITE for nid in node_ids}

    def dfs(u: str, path: list[str]) -> list[str] | None:
        color[u] = GRAY
        path.append(u)
        for v in adjacency.get(u, []):
            if v not in color:
                continue  # unknown node, skip
            if color[v] == GRAY:
                # Found a cycle — extract it from the path
                cycle_start = path.index(v)
                return path[cycle_start:] + [v]
            if color[v] == WHITE:
                result = dfs(v, path)
                if result:
                    return result
        path.pop()
        color[u] = BLACK
        return None

    for nid in node_ids:
        if color[nid] == WHITE:
            result = dfs(nid, [])
            if result:
                return result
    return None


# -- Public API


def validate_canonical(doc: CanonicalDocument) -> list[dict]:
    """Validate a v1.0 CanonicalDocument, returning structured diagnostics.

    Args:
        doc: The canonical document to validate.

    Returns:
        A list of diagnostic dicts, each with keys:
          - path: str       — dotted path to the problematic field
          - code: str       — error code constant (from enums)
          - message: str    — human-readable description
          - suggested_fix: str (optional) — how to resolve the issue
          - severity: str   — "error" or "warning"

        An empty list means the document is valid.
    """
    diagnostics: list[dict] = []

    # (a) Document structure
    try:
        diagnostics.extend(_check_metadata(doc.metadata))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "metadata",
                EXECUTION_ERROR,
                f"Unexpected error validating metadata: {exc}",
                severity="error",
            )
        )

    try:
        diagnostics.extend(_check_duplicate_ids(doc))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "tasks",
                EXECUTION_ERROR,
                f"Unexpected error checking duplicate IDs: {exc}",
                severity="error",
            )
        )

    # (b) Space
    try:
        diagnostics.extend(_check_space(doc.space, doc.tasks, doc.objects))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "space",
                EXECUTION_ERROR,
                f"Unexpected error validating space: {exc}",
                severity="error",
            )
        )

    # (c) Provenance
    try:
        diagnostics.extend(validate_provenance(doc.provenance, doc.tasks))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "provenance",
                EXECUTION_ERROR,
                f"Unexpected error validating provenance: {exc}",
                severity="error",
            )
        )

    # (d) Objects
    try:
        diagnostics.extend(_check_objects(doc.objects))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "objects",
                EXECUTION_ERROR,
                f"Unexpected error validating objects: {exc}",
                severity="error",
            )
        )

    # (d) Tasks and Assertions
    try:
        diagnostics.extend(_check_tasks_and_assertions(doc.tasks, doc.objects))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "tasks",
                EXECUTION_ERROR,
                f"Unexpected error validating tasks/assertions: {exc}",
                severity="error",
            )
        )

    # (e) Operator binding
    try:
        diagnostics.extend(_check_operator_binding(doc.tasks, doc.objects))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "tasks.*.operator",
                EXECUTION_ERROR,
                f"Unexpected error validating operator binding: {exc}",
                severity="error",
            )
        )

    # (f) Execution
    try:
        diagnostics.extend(_check_execution(doc.execution, doc.tasks))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "execution",
                EXECUTION_ERROR,
                f"Unexpected error validating execution: {exc}",
                severity="error",
            )
        )

    # (g) Output contract
    try:
        diagnostics.extend(_check_output_contract(doc.output_contract))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "output_contract",
                EXECUTION_ERROR,
                f"Unexpected error validating output contract: {exc}",
                severity="error",
            )
        )

    # (h) Assurance reachability
    try:
        diagnostics.extend(
            _check_assurance_reachability(doc.execution, doc.verification)
        )
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "verification",
                EXECUTION_ERROR,
                f"Unexpected error validating assurance reachability: {exc}",
                severity="error",
            )
        )

    # (i) Versioned extension profiles
    try:
        assertion_ids = {
            assertion.id
            for task in doc.tasks
            for assertion in task.assertions
            if assertion.id
        }
        diagnostics.extend(
            validate_extension_profiles(
                doc.extensions,
                assertion_ids=assertion_ids,
            )
        )
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "extensions.extension_profile",
                EXECUTION_ERROR,
                f"Unexpected error validating extension profile: {exc}",
                severity="error",
            )
        )

    return diagnostics
