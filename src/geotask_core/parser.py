"""YAML parser and validator for GeoTask Core Lite documents."""

import re
from pathlib import Path
from typing import Union

import yaml

from geotask_core.operator_registry import operator_names


VALID_OBJECT_TYPES = ("point", "line", "rect", "time", "altitude")
ALLOWED_TOP_LEVEL_KEYS = ("geotask", "stir", "space", "objects", "ops", "task", "assertions", "expected_results")
ALLOWED_OBJECT_FIELDS = {
    "point": {"type", "xy"},
    "line": {"type", "points"},
    "rect": {"type", "bbox"},
    "time": {"type", "interval"},
    "altitude": {"type", "range"},
}


def load_geotask(path: Union[str, Path]) -> dict:
    """Load a GeoTask YAML file and return the parsed dict.

    Args:
        path: Path to a .yaml file.

    Returns:
        Parsed dict with keys: geotask (or stir), space, objects, ops, task.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the YAML is malformed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"GeoTask file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"GeoTask file is empty or invalid: {path}")

    return data


# Deprecated alias for backward compatibility
load_stir = load_geotask


def _diagnostic(path: str, code: str, message: str, suggested_fix: str) -> dict:
    """Build a structured validation diagnostic."""
    return {
        "path": path,
        "code": code,
        "message": message,
        "suggested_fix": suggested_fix,
    }


def _format_diagnostic(diagnostic: dict) -> str:
    """Render a structured diagnostic as a backward-compatible string."""
    return (
        f"{diagnostic['path']}: {diagnostic['code']}: {diagnostic['message']} "
        f"Suggested fix: {diagnostic['suggested_fix']}"
    )


def _validate_objects_diagnostics(objects: dict) -> list[dict]:
    """Validate the objects section. Returns structured diagnostics."""
    diagnostics = []

    if not isinstance(objects, dict):
        diagnostics.append(_diagnostic(
            "objects",
            "invalid_type",
            "'objects' must be a mapping (dict).",
            "Change 'objects' to a mapping from object id to object definition.",
        ))
        return diagnostics

    for name, obj in objects.items():
        if not isinstance(obj, dict):
            diagnostics.append(_diagnostic(
                f"objects.{name}",
                "invalid_type",
                f"object '{name}': must be a dict.",
                "Use a mapping with at least a 'type' field.",
            ))
            continue

        obj_type = obj.get("type", "")
        if obj_type not in VALID_OBJECT_TYPES:
            expected = ", ".join(VALID_OBJECT_TYPES)
            diagnostics.append(_diagnostic(
                f"objects.{name}.type",
                "unknown_object_type",
                f"object '{name}': unknown type '{obj_type}', expected one of {expected}.",
                f"Use one of: {expected}.",
            ))
            continue

        allowed_fields = ALLOWED_OBJECT_FIELDS[obj_type]
        for field in obj.keys():
            if field not in allowed_fields:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.{field}",
                    "unknown_field",
                    f"Unexpected field '{field}' for object '{name}' of type '{obj_type}'.",
                    f"Remove '{field}' or replace it with one of: {', '.join(sorted(allowed_fields))}.",
                ))

        if obj_type == "point":
            xy = obj.get("xy")
            if xy is None:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.xy",
                    "missing_field",
                    f"object '{name}' (point): missing 'xy'.",
                    "Add xy: [x, y].",
                ))
            elif not isinstance(xy, list) or len(xy) != 2:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.xy",
                    "invalid_coordinates",
                    f"object '{name}' (point): 'xy' must be [x, y].",
                    "Use exactly two numeric coordinate values.",
                ))

        elif obj_type == "line":
            points = obj.get("points")
            if points is None:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.points",
                    "missing_field",
                    f"object '{name}' (line): missing 'points'.",
                    "Add points with at least two [x, y] coordinates.",
                ))
            elif not isinstance(points, list) or len(points) < 2:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.points",
                    "invalid_coordinates",
                    f"object '{name}' (line): 'points' must contain at least 2 points.",
                    "Use points: [[x1, y1], [x2, y2], ...].",
                ))
            else:
                for i, pt in enumerate(points):
                    if not isinstance(pt, list) or len(pt) != 2:
                        diagnostics.append(_diagnostic(
                            f"objects.{name}.points[{i}]",
                            "invalid_coordinates",
                            f"object '{name}' (line): points[{i}] must be [x, y].",
                            "Use exactly two numeric coordinate values for each point.",
                        ))

        elif obj_type == "rect":
            bbox = obj.get("bbox")
            if bbox is None:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.bbox",
                    "missing_field",
                    f"object '{name}' (rect): missing 'bbox'.",
                    "Add bbox: [min_x, min_y, max_x, max_y].",
                ))
            elif not isinstance(bbox, list) or len(bbox) != 4:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.bbox",
                    "invalid_coordinates",
                    f"object '{name}' (rect): 'bbox' must be [min_x, min_y, max_x, max_y].",
                    "Use exactly four numeric bbox values.",
                ))

        elif obj_type == "time":
            interval = obj.get("interval")
            path = f"objects.{name}.interval"
            if interval is None:
                diagnostics.append(_diagnostic(
                    path,
                    "missing_field",
                    f"object '{name}' (time): missing 'interval'.",
                    "Add interval: ['HH:MM', 'HH:MM'].",
                ))
            elif not _is_valid_time_interval(interval):
                diagnostics.append(_diagnostic(
                    path,
                    "invalid_interval",
                    f"{path}: invalid_interval: must be ['HH:MM', 'HH:MM'] with start <= end.",
                    "Use a valid two-item HH:MM interval with start <= end.",
                ))

        elif obj_type == "altitude":
            altitude_range = obj.get("range")
            path = f"objects.{name}.range"
            if altitude_range is None:
                diagnostics.append(_diagnostic(
                    path,
                    "missing_field",
                    f"object '{name}' (altitude): missing 'range'.",
                    "Add range: [min, max].",
                ))
            elif not _is_valid_number_interval(altitude_range):
                diagnostics.append(_diagnostic(
                    path,
                    "invalid_interval",
                    f"{path}: invalid_interval: must be [min, max] with min <= max.",
                    "Use a numeric two-item range with min <= max.",
                ))

    return diagnostics


def _is_valid_time_interval(value) -> bool:
    """Return True for a two-item HH:MM interval with start <= end."""
    if not isinstance(value, list) or len(value) != 2:
        return False
    try:
        start = _time_to_minutes(value[0])
        end = _time_to_minutes(value[1])
    except (TypeError, ValueError):
        return False
    return start <= end


def _time_to_minutes(value: str) -> int:
    """Parse an HH:MM time string into minutes since midnight."""
    if not isinstance(value, str) or not re.match(r"^\d{1,2}:\d{2}$", value):
        raise ValueError("invalid time")
    hour_str, minute_str = value.split(":")
    hour = int(hour_str)
    minute = int(minute_str)
    if hour > 23 or minute > 59:
        raise ValueError("invalid time")
    return hour * 60 + minute


def _is_valid_number_interval(value) -> bool:
    """Return True for a numeric two-item interval with min <= max."""
    if not isinstance(value, list) or len(value) != 2:
        return False
    low, high = value
    if isinstance(low, bool) or isinstance(high, bool):
        return False
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
        return False
    return low <= high


def validate_geotask_diagnostics(data: dict) -> list[dict]:
    """Validate a GeoTask document dict. Returns structured diagnostics.

    An empty list means the document is valid. Each diagnostic includes:
    path, code, message, and suggested_fix.

    Checks performed:
      - Top-level keys: geotask (or stir for backward compat), space, objects, ops, task
      - geotask/stir section: version, name, goal
      - objects: valid types and required fields

    Backward compatibility: the old 'stir' top-level key is accepted
    but triggers a deprecation warning in CLI output.
    """
    diagnostics = []

    # Check top-level keys -- accept either 'geotask' (preferred) or 'stir' (deprecated)
    has_geotask = "geotask" in data
    has_stir = "stir" in data

    if not has_geotask and not has_stir:
        diagnostics.append(_diagnostic(
            "geotask",
            "missing_field",
            "Missing top-level key: 'geotask' (or deprecated 'stir').",
            "Add a 'geotask' metadata section with version, name, and goal.",
        ))

    # Validate metadata section (geotask or stir)
    meta_key = "geotask" if has_geotask else "stir"
    if has_stir and not has_geotask:
        # Only old 'stir' field present -- accept but flag deprecated
        data["_deprecated_stir_field"] = True

    if meta_key in data and isinstance(data[meta_key], dict):
        meta = data[meta_key]
        for field in ["version", "name", "goal"]:
            if field not in meta:
                diagnostics.append(_diagnostic(
                    f"{meta_key}.{field}",
                    "missing_field",
                    f"'{meta_key}.{field}' is missing.",
                    f"Add '{field}' to the '{meta_key}' metadata section.",
                ))
    elif meta_key in data:
        diagnostics.append(_diagnostic(
            meta_key,
            "invalid_type",
            f"'{meta_key}' must be a mapping (dict).",
            f"Change '{meta_key}' to a mapping with version, name, and goal.",
        ))

    for key in data.keys():
        if key == "_deprecated_stir_field":
            continue
        if key not in ALLOWED_TOP_LEVEL_KEYS:
            diagnostics.append(_diagnostic(
                key,
                "unknown_field",
                f"Unexpected top-level field '{key}'.",
                f"Remove '{key}' or move it under a supported section.",
            ))

    # Check other required keys
    other_keys = ["space", "objects", "ops", "task"]
    for key in other_keys:
        if key not in data:
            diagnostics.append(_diagnostic(
                key,
                "missing_field",
                f"Missing top-level key: '{key}'.",
                f"Add a '{key}' section.",
            ))

    # Validate objects
    if "objects" in data:
        diagnostics.extend(_validate_objects_diagnostics(data["objects"]))

    if "ops" in data:
        ops = data["ops"]
        if not isinstance(ops, dict):
            diagnostics.append(_diagnostic(
                "ops",
                "invalid_type",
                "'ops' must be a mapping (dict).",
                "Change 'ops' to a mapping from operator name to description.",
            ))
        else:
            supported = set(operator_names())
            for op_name in ops.keys():
                if str(op_name) not in supported:
                    diagnostics.append(_diagnostic(
                        f"ops.{op_name}",
                        "invalid_operator",
                        f"Unsupported operator '{op_name}' in ops.",
                        f"Use one of: {', '.join(operator_names())}.",
                    ))

    return diagnostics


def validate_geotask(data: dict) -> list[str]:
    """Validate a GeoTask document dict. Returns a list of error messages.

    This legacy API is kept for backward compatibility. New callers should use
    validate_geotask_diagnostics() for path/code/message/suggested_fix fields.
    """
    return [_format_diagnostic(d) for d in validate_geotask_diagnostics(data)]


# Deprecated alias for backward compatibility
validate_stir = validate_geotask
validate_stir_diagnostics = validate_geotask_diagnostics
