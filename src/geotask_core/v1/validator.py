"""v1.0 CanonicalDocument validator — produces structured diagnostics.

Validates every aspect of a CanonicalDocument against the v1.0 specification.
Returns a flat list of diagnostic dicts; an empty list means the document is
fully valid.

All functions are pure — no side effects, no mutation of the input document.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from geotask_core.v1.enums import (
    _ID_PATTERN,
    ARITY_MISMATCH,
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
    UNKNOWN_OBJECT_TYPE,
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
from geotask_core.v1.operator_contracts import default_registry

if TYPE_CHECKING:
    pass


# -- Diagnostic helpers

_VALID_CRS_TYPES: set[str] = {"local_cartesian", "projected", "geographic", "unknown"}

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


def _check_space(space: SpaceDefinition) -> list[dict]:
    diags: list[dict] = []

    # crs.type must be valid
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

    # horizontal_unit must be non-empty string
    if not isinstance(space.horizontal_unit, str) or not space.horizontal_unit:
        diags.append(
            _diagnostic(
                "space.horizontal_unit",
                MISSING_FIELD,
                "space.horizontal_unit is empty or missing.",
                'Set horizontal_unit to a unit string, e.g. "meter".',
            )
        )

    return diags


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

    return diags


def _check_object_data(path: str, obj: GeoObject) -> list[dict]:
    """Dispatch to the appropriate per-type validation function."""
    data = obj.data
    obj_type = obj.type

    if obj_type == "point":
        return _check_point_data(path, data)
    elif obj_type == "polyline":
        return _check_polyline_data(path, data)
    elif obj_type == "rect":
        return _check_rect_data(path, data)
    elif obj_type == "time_interval":
        return _check_time_interval_data(path, data)
    elif obj_type == "altitude_interval":
        return _check_altitude_interval_data(path, data)
    elif obj_type == "feature_collection":
        return _check_feature_collection_data(path, data)
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
        diagnostics.extend(_check_space(doc.space))
    except Exception as exc:
        diagnostics.append(
            _diagnostic(
                "space",
                EXECUTION_ERROR,
                f"Unexpected error validating space: {exc}",
                severity="error",
            )
        )

    # (c) Objects
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

    return diagnostics
