"""YAML parser and validator for GeoTask Core Lite documents."""

from pathlib import Path
from typing import Union

import yaml


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


def _validate_objects(objects: dict) -> list[str]:
    """Validate the objects section. Returns list of error messages."""
    errors = []

    if not isinstance(objects, dict):
        errors.append("'objects' must be a mapping (dict)")
        return errors

    valid_types = {"point", "line", "rect"}

    for name, obj in objects.items():
        if not isinstance(obj, dict):
            errors.append(f"object '{name}': must be a dict")
            continue

        obj_type = obj.get("type", "")
        if obj_type not in valid_types:
            errors.append(
                f"object '{name}': unknown type '{obj_type}', "
                f"expected one of {valid_types}"
            )
            continue

        if obj_type == "point":
            xy = obj.get("xy")
            if xy is None:
                errors.append(f"object '{name}' (point): missing 'xy'")
            elif not isinstance(xy, list) or len(xy) != 2:
                errors.append(
                    f"object '{name}' (point): 'xy' must be [x, y]"
                )

        elif obj_type == "line":
            points = obj.get("points")
            if points is None:
                errors.append(f"object '{name}' (line): missing 'points'")
            elif not isinstance(points, list) or len(points) < 2:
                errors.append(
                    f"object '{name}' (line): 'points' must contain at least 2 points"
                )
            else:
                for i, pt in enumerate(points):
                    if not isinstance(pt, list) or len(pt) != 2:
                        errors.append(
                            f"object '{name}' (line): points[{i}] must be [x, y]"
                        )

        elif obj_type == "rect":
            bbox = obj.get("bbox")
            if bbox is None:
                errors.append(f"object '{name}' (rect): missing 'bbox'")
            elif not isinstance(bbox, list) or len(bbox) != 4:
                errors.append(
                    f"object '{name}' (rect): 'bbox' must be [min_x, min_y, max_x, max_y]"
                )

    return errors


def validate_geotask(data: dict) -> list[str]:
    """Validate a GeoTask document dict. Returns a list of error messages.

    An empty list means the document is valid.

    Checks performed:
      - Top-level keys: geotask (or stir for backward compat), space, objects, ops, task
      - geotask/stir section: version, name, goal
      - objects: valid types and required fields

    Backward compatibility: the old 'stir' top-level key is accepted
    but triggers a deprecation warning in CLI output.
    """
    errors = []

    # Check top-level keys -- accept either 'geotask' (preferred) or 'stir' (deprecated)
    has_geotask = "geotask" in data
    has_stir = "stir" in data

    if not has_geotask and not has_stir:
        errors.append("missing top-level key: 'geotask' (or deprecated 'stir')")

    # Validate metadata section (geotask or stir)
    meta_key = "geotask" if has_geotask else "stir"
    if has_stir and not has_geotask:
        # Only old 'stir' field present -- accept but flag deprecated
        data["_deprecated_stir_field"] = True

    if meta_key in data and isinstance(data[meta_key], dict):
        meta = data[meta_key]
        for field in ["version", "name", "goal"]:
            if field not in meta:
                errors.append(f"'{meta_key}.{field}' is missing")
    elif meta_key in data:
        errors.append(f"'{meta_key}' must be a mapping (dict)")

    # Check other required keys
    other_keys = ["space", "objects", "ops", "task"]
    for key in other_keys:
        if key not in data:
            errors.append(f"missing top-level key: '{key}'")

    # Validate objects
    if "objects" in data:
        errors.extend(_validate_objects(data["objects"]))

    return errors


# Deprecated alias for backward compatibility
validate_stir = validate_geotask
