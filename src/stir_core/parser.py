"""YAML parser and validator for STIR-Core Lite documents."""

from pathlib import Path
from typing import Union

import yaml


def load_stir(path: Union[str, Path]) -> dict:
    """Load a STIR YAML file and return the parsed dict.

    Args:
        path: Path to a .yaml file.

    Returns:
        Parsed dict with keys: stir, space, objects, ops, task.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the YAML is malformed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"STIR file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"STIR file is empty or invalid: {path}")

    return data


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


def validate_stir(data: dict) -> list[str]:
    """Validate a STIR document dict. Returns a list of error messages.

    An empty list means the document is valid.

    Checks performed:
      - Top-level keys: stir, space, objects, ops, task
      - stir section: version, name, goal
      - objects: valid types and required fields
    """
    errors = []

    # Check top-level keys
    required_keys = ["stir", "space", "objects", "ops", "task"]
    for key in required_keys:
        if key not in data:
            errors.append(f"missing top-level key: '{key}'")

    # Validate stir section
    if "stir" in data and isinstance(data["stir"], dict):
        stir = data["stir"]
        for field in ["version", "name", "goal"]:
            if field not in stir:
                errors.append(f"'stir.{field}' is missing")
    elif "stir" in data:
        errors.append("'stir' must be a mapping (dict)")

    # Validate objects
    if "objects" in data:
        errors.extend(_validate_objects(data["objects"]))

    return errors
