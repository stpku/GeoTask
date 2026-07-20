"""YAML parser and validator for GeoTask Core Lite documents."""

import re
from pathlib import Path
from typing import Union

import yaml

from geotask_core.operator_registry import operator_names


# ═══════════════════════════════════════════════════════════════════════════════
#  Duplicate YAML Key Detection
# ═══════════════════════════════════════════════════════════════════════════════


class _UniqueKeyLoader(yaml.SafeLoader):
    """Custom YAML loader that rejects duplicate mapping keys at any depth."""


def _construct_mapping_no_dupes(loader: yaml.Loader, node: yaml.nodes.MappingNode, deep: bool = False) -> dict:
    """Construct a mapping, raising yaml.constructor.ConstructorError on duplicate keys.

    Works at all nesting levels because overriding the DEFAULT_MAPPING_TAG
    constructor replaces the default mapping construction for the entire
    YAML parse tree.
    """
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None,
                None,
                f"duplicate key '{key}'",
                key_node.start_mark,
            )
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_no_dupes,
)


VALID_OBJECT_TYPES = (
    "point", "line", "rect", "time", "altitude",
    # v1.0 object types
    "polyline", "time_interval", "altitude_interval", "feature_collection",
)
ALLOWED_TOP_LEVEL_KEYS = (
    "geotask", "stir", "space", "objects", "ops", "task",
    "assertions", "expected_results",
    # v1.0 top-level fields
    "tasks", "execution", "output_contract", "verification",
    "operator_set", "operator_contracts", "extensions",
)
ALLOWED_OBJECT_FIELDS = {
    "point": {"type", "xy", "coordinates"},
    "line": {"type", "points", "coordinates"},
    "rect": {"type", "bbox"},
    "time": {"type", "interval"},
    "altitude": {"type", "range"},
    # v1.0 object fields
    "polyline": {"type", "coordinates", "points"},
    "time_interval": {"type", "interval", "start", "end"},
    "altitude_interval": {"type", "range", "min", "max", "unit", "datum"},
    "feature_collection": {"type", "feature_type", "features"},
}
ALLOWED_ASSERTION_FIELDS = {
    "id", "operator", "object_refs",
    # v1.0 assertion fields
    "parameters", "expected_type", "unit", "tolerance",
    "depends_on", "condition", "on_error",
}
ALLOWED_EXPECTED_RESULT_FIELDS = {"name", "value", "unit"}

# v1.0 required top-level fields
V1_REQUIRED_TOP_LEVEL = ("geotask", "space", "objects", "tasks", "execution", "output_contract")
# v0.x required top-level fields
V0_REQUIRED_TOP_LEVEL = ("geotask", "space", "objects", "ops", "task")


def load_geotask(path: Union[str, Path]) -> dict:
    """Load a GeoTask YAML file and return the parsed dict.

    Args:
        path: Path to a .yaml file.

    Returns:
        Parsed dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the YAML is malformed or contains duplicate keys.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"GeoTask file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    try:
        data = yaml.load(raw, Loader=_UniqueKeyLoader)
    except yaml.constructor.ConstructorError as e:
        raise yaml.YAMLError(f"Duplicate key detected in {path}: {e}") from e

    if data is None:
        raise ValueError(f"GeoTask file is empty or invalid: {path}")

    return data


# Deprecated alias for backward compatibility
load_stir = load_geotask


def _diagnostic(path: str, code: str, message: str, suggested_fix: str, severity: str = "error") -> dict:
    """Build a structured validation diagnostic."""
    return {
        "path": path,
        "code": code,
        "message": message,
        "suggested_fix": suggested_fix,
        "severity": severity,
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
            coords = obj.get("coordinates")
            # Accept either xy (legacy) or coordinates (v1.0)
            if xy is not None:
                if not isinstance(xy, list) or len(xy) != 2:
                    diagnostics.append(_diagnostic(
                        f"objects.{name}.xy",
                        "invalid_coordinates",
                        f"object '{name}' (point): 'xy' must be [x, y].",
                        "Use exactly two numeric coordinate values.",
                    ))
            elif coords is not None:
                if not isinstance(coords, list) or len(coords) != 2:
                    diagnostics.append(_diagnostic(
                        f"objects.{name}.coordinates",
                        "invalid_coordinates",
                        f"object '{name}' (point): 'coordinates' must be [x, y].",
                        "Use exactly two numeric coordinate values.",
                    ))
            else:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.xy",
                    "missing_field",
                    f"object '{name}' (point): missing coordinates (use 'xy' or 'coordinates').",
                    "Add xy: [x, y] or coordinates: [x, y].",
                ))

        elif obj_type in ("line", "polyline"):
            points = obj.get("points") or obj.get("coordinates")
            path = f"objects.{name}.{obj.get('points') and 'points' or 'coordinates'}"
            if points is None:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.points",
                    "missing_field",
                    f"object '{name}' ({obj_type}): missing points/coordinates.",
                    "Add points or coordinates with at least two [x, y] pairs.",
                ))
            elif not isinstance(points, list) or len(points) < 2:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.points",
                    "invalid_coordinates",
                    f"object '{name}' ({obj_type}): points/coordinates must contain at least 2 points.",
                    "Use points: [[x1, y1], [x2, y2], ...].",
                ))
            else:
                for i, pt in enumerate(points):
                    if not isinstance(pt, list) or len(pt) != 2:
                        diagnostics.append(_diagnostic(
                            f"objects.{name}.points[{i}]",
                            "invalid_coordinates",
                            f"object '{name}' ({obj_type}): points[{i}] must be [x, y].",
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

        elif obj_type in ("time", "time_interval"):
            interval = obj.get("interval")
            start = obj.get("start")
            end_v = obj.get("end")
            path = f"objects.{name}.interval"

            # v1.0 standard: start/end fields
            if start is not None or end_v is not None:
                if start is None or end_v is None:
                    diagnostics.append(_diagnostic(
                        f"objects.{name}",
                        "missing_field",
                        f"object '{name}' ({obj_type}): both 'start' and 'end' are required when using standard fields.",
                        "Provide both start: and end: values.",
                    ))
                elif not _is_valid_time_interval([start, end_v]):
                    diagnostics.append(_diagnostic(
                        f"objects.{name}",
                        "invalid_interval",
                        f"objects.{name}: invalid_interval: start must be <= end, both HH:MM.",
                        "Use valid HH:MM strings with start <= end.",
                    ))
                # Check for conflict with legacy interval
                if interval is not None and (start is not None and end_v is not None):
                    if interval != [start, end_v]:
                        diagnostics.append(_diagnostic(
                            f"objects.{name}",
                            "invalid_interval",
                            f"objects.{name}: conflicting 'interval' and 'start'/'end' values.",
                            "Use either 'interval' (legacy) or 'start'+'end' (standard), not both with different values.",
                        ))
            elif interval is None:
                diagnostics.append(_diagnostic(
                    path,
                    "missing_field",
                    f"object '{name}' ({obj_type}): missing interval (use 'interval' or 'start'+'end').",
                    "Add interval: ['HH:MM', 'HH:MM'] or start: 'HH:MM', end: 'HH:MM'.",
                ))
            elif not _is_valid_time_interval(interval):
                diagnostics.append(_diagnostic(
                    path,
                    "invalid_interval",
                    f"{path}: invalid_interval: must be ['HH:MM', 'HH:MM'] with start <= end.",
                    "Use a valid two-item HH:MM interval with start <= end.",
                ))

        elif obj_type in ("altitude", "altitude_interval"):
            altitude_range = obj.get("range")
            min_v = obj.get("min")
            max_v = obj.get("max")
            path = f"objects.{name}.range"

            # v1.0 standard: min/max fields
            if min_v is not None or max_v is not None:
                if min_v is None or max_v is None:
                    diagnostics.append(_diagnostic(
                        f"objects.{name}",
                        "missing_field",
                        f"object '{name}' ({obj_type}): both 'min' and 'max' are required when using standard fields.",
                        "Provide both min: and max: numeric values.",
                    ))
                elif not _is_valid_number_interval([min_v, max_v]):
                    diagnostics.append(_diagnostic(
                        f"objects.{name}",
                        "invalid_interval",
                        f"objects.{name}: invalid_interval: min must be <= max, both numbers.",
                        "Use valid numeric values with min <= max.",
                    ))
                # Check for conflict with legacy range
                if altitude_range is not None and (min_v is not None and max_v is not None):
                    if altitude_range != [min_v, max_v]:
                        diagnostics.append(_diagnostic(
                            f"objects.{name}",
                            "invalid_interval",
                            f"objects.{name}: conflicting 'range' and 'min'/'max' values.",
                            "Use either 'range' (legacy) or 'min'+'max' (standard), not both with different values.",
                        ))
            elif altitude_range is None:
                diagnostics.append(_diagnostic(
                    path,
                    "missing_field",
                    f"object '{name}' ({obj_type}): missing range (use 'range' or 'min'+'max').",
                    "Add range: [min, max] or min: N, max: N.",
                ))
            elif not _is_valid_number_interval(altitude_range):
                diagnostics.append(_diagnostic(
                    path,
                    "invalid_interval",
                    f"{path}: invalid_interval: must be [min, max] with min <= max.",
                    "Use a numeric two-item range with min <= max.",
                ))

        elif obj_type == "feature_collection":
            # Basic structural check only — v1.0 validator handles full validation
            if "features" not in obj:
                diagnostics.append(_diagnostic(
                    f"objects.{name}.features",
                    "missing_field",
                    f"object '{name}' (feature_collection): missing 'features'.",
                    "Add a 'features' list.",
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


def _validate_assertions_diagnostics(assertions, known_objects: set[str]) -> list[dict]:
    """Validate optional assertion entries."""
    diagnostics = []
    if not isinstance(assertions, list):
        return [_diagnostic(
            "assertions",
            "invalid_type",
            "'assertions' must be a list.",
            "Use a list of assertion entries with id, operator, and object_refs.",
        )]

    supported_operators = set(operator_names())
    for index, entry in enumerate(assertions):
        base_path = f"assertions[{index}]"
        if not isinstance(entry, dict):
            diagnostics.append(_diagnostic(
                base_path,
                "invalid_type",
                f"{base_path} must be a mapping (dict).",
                "Use a mapping with id, operator, and object_refs.",
            ))
            continue

        for field in entry.keys():
            if field not in ALLOWED_ASSERTION_FIELDS:
                diagnostics.append(_diagnostic(
                    f"{base_path}.{field}",
                    "unknown_field",
                    f"Unexpected field '{field}' in {base_path}.",
                    f"Remove '{field}' or replace it with one of: {', '.join(sorted(ALLOWED_ASSERTION_FIELDS))}.",
                ))

        if "id" not in entry:
            diagnostics.append(_diagnostic(
                f"{base_path}.id",
                "missing_field",
                f"'{base_path}.id' is missing.",
                "Add a stable assertion id.",
            ))

        operator = entry.get("operator")
        if operator is None:
            diagnostics.append(_diagnostic(
                f"{base_path}.operator",
                "missing_field",
                f"'{base_path}.operator' is missing.",
                "Add a registered Core operator name.",
            ))
        elif operator not in supported_operators:
            diagnostics.append(_diagnostic(
                f"{base_path}.operator",
                "invalid_operator",
                f"Unsupported operator '{operator}' in {base_path}.",
                f"Use one of: {', '.join(operator_names())}.",
            ))

        object_refs = entry.get("object_refs")
        if object_refs is None:
            diagnostics.append(_diagnostic(
                f"{base_path}.object_refs",
                "missing_field",
                f"'{base_path}.object_refs' is missing.",
                "Add a list of referenced object ids.",
            ))
        elif not isinstance(object_refs, list):
            diagnostics.append(_diagnostic(
                f"{base_path}.object_refs",
                "invalid_type",
                f"'{base_path}.object_refs' must be a list.",
                "Use a list of object id strings.",
            ))
        else:
            for ref_index, ref in enumerate(object_refs):
                if not isinstance(ref, str):
                    diagnostics.append(_diagnostic(
                        f"{base_path}.object_refs[{ref_index}]",
                        "invalid_type",
                        f"'{base_path}.object_refs[{ref_index}]' must be a string.",
                        "Use an existing object id string.",
                    ))
                elif ref not in known_objects:
                    diagnostics.append(_diagnostic(
                        f"{base_path}.object_refs[{ref_index}]",
                        "invalid_reference",
                        f"Unknown object reference '{ref}' in {base_path}.",
                        f"Use one of the known object ids: {', '.join(sorted(known_objects))}.",
                    ))

    return diagnostics


def _validate_expected_results_diagnostics(expected_results) -> list[dict]:
    """Validate optional expected result fixtures."""
    diagnostics = []
    if not isinstance(expected_results, list):
        return [_diagnostic(
            "expected_results",
            "invalid_type",
            "'expected_results' must be a list.",
            "Use a list of expected result entries with at least name and value.",
        )]

    for index, entry in enumerate(expected_results):
        base_path = f"expected_results[{index}]"
        if not isinstance(entry, dict):
            diagnostics.append(_diagnostic(
                base_path,
                "invalid_type",
                f"{base_path} must be a mapping (dict).",
                "Use a mapping with at least name and value.",
            ))
            continue

        for field in entry.keys():
            if field not in ALLOWED_EXPECTED_RESULT_FIELDS:
                diagnostics.append(_diagnostic(
                    f"{base_path}.{field}",
                    "unknown_field",
                    f"Unexpected field '{field}' in {base_path}.",
                    f"Remove '{field}' or replace it with one of: {', '.join(sorted(ALLOWED_EXPECTED_RESULT_FIELDS))}.",
                ))

        if "name" not in entry:
            diagnostics.append(_diagnostic(
                f"{base_path}.name",
                "missing_field",
                f"'{base_path}.name' is missing.",
                "Add the expected measurement or result name.",
            ))
        if "value" not in entry:
            diagnostics.append(_diagnostic(
                f"{base_path}.value",
                "missing_field",
                f"'{base_path}.value' is missing.",
                "Add the expected output value.",
            ))

    return diagnostics


def _validate_raw_schema(data: dict) -> list[dict]:
    """Validate a GeoTask document dict (raw schema only, no canonicalization).

    An empty list means the document is valid at the raw schema level.
    Each diagnostic includes: path, code, message, and suggested_fix.

    Checks performed:
      - Top-level keys: geotask (or stir for backward compat), space, objects, ops, task
      - geotask/stir section: version, name, goal
      - objects: valid types and required fields

    Backward compatibility: the old 'stir' top-level key is accepted
    but triggers a deprecation warning in CLI output.
    
    This is an internal function. External callers should use
    ``validate_document()`` for unified validation or
    ``validate_geotask_diagnostics()`` for backward compat.
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

    # Detect v1.0 documents (have tasks/execution or schema_version="1.0")
    is_v1 = (
        "tasks" in data
        or "execution" in data
        or (
            isinstance(data.get(meta_key), dict)
            and str(data[meta_key].get("schema_version", "")) == "1.0"
        )
    )

    if meta_key in data and isinstance(data[meta_key], dict):
        meta = data[meta_key]
        if is_v1:
            # v1.0: version/goal are optional; schema_version/name required
            if "schema_version" not in meta and "version" not in meta:
                diagnostics.append(_diagnostic(
                    f"{meta_key}.schema_version",
                    "missing_field",
                    f"'{meta_key}.schema_version' is missing.",
                    "Add 'schema_version' to the '{meta_key}' metadata section.",
                ))
            if "name" not in meta:
                diagnostics.append(_diagnostic(
                    f"{meta_key}.name",
                    "missing_field",
                    f"'{meta_key}.name' is missing.",
                    f"Add 'name' to the '{meta_key}' metadata section.",
                ))
        else:
            # Legacy: version, name, goal all required
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
    if is_v1:
        required_keys = ["space", "objects", "tasks", "execution", "output_contract"]
    else:
        required_keys = ["space", "objects", "ops", "task"]
    for key in required_keys:
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

    known_objects = set(data.get("objects", {}).keys()) if isinstance(data.get("objects"), dict) else set()

    if "assertions" in data:
        diagnostics.extend(_validate_assertions_diagnostics(data["assertions"], known_objects))

    if "expected_results" in data:
        diagnostics.extend(_validate_expected_results_diagnostics(data["expected_results"]))

    return diagnostics


def validate_document(data: dict) -> list[dict]:
    """Unified validation: raw schema + canonicalization + canonical validation.
    
    Execution order:
      1. Raw Schema Validation (_validate_raw_schema)
      2. Canonicalization (canonicalize)  
      3. Canonical Validation (validate_canonical)
      4. Deduplicate diagnostics by (path, code)
    
    Returns:
        List of diagnostic dicts, each with: path, code, message, suggested_fix, severity.
        severity is "error" or "warning". Warnings do not block execution.
    """
    from geotask_core.v1.canonicalizer import canonicalize
    from geotask_core.v1.validator import validate_canonical

    diagnostics: list[dict] = list(_validate_raw_schema(data))

    # Step 2: Canonicalization — catch errors and convert to diagnostics
    try:
        doc = canonicalize(data)
    except Exception as exc:
        diagnostics.append(_diagnostic(
            "canonicalize",
            "canonicalization_error",
            f"Failed to canonicalize document: {exc}",
            "Check document structure and field values for correctness.",
            severity="error",
        ))
        return diagnostics

    # Step 3: Canonical Validation
    try:
        canon_diags = validate_canonical(doc)
    except Exception as exc:
        diagnostics.append(_diagnostic(
            "validate_canonical",
            "canonical_validation_error",
            f"Failed to run canonical validation: {exc}",
            "Check document structure and field values for correctness.",
            severity="error",
        ))
        return diagnostics

    # Step 4: Deduplicate by (path, code) — keep more severe, then first seen
    seen: dict[tuple, dict] = {}
    for d in diagnostics + canon_diags:
        key = (d.get("path", ""), d.get("code", ""))
        sev = d.get("severity", "error")
        if key not in seen:
            if "severity" not in d:
                d["severity"] = "error"
            seen[key] = d
        else:
            existing_sev = seen[key].get("severity", "error")
            # Keep error over warning; if same, keep first
            if sev == "error" and existing_sev == "warning":
                if "severity" not in d:
                    d["severity"] = "error"
                seen[key] = d

    return list(seen.values())


def validate_geotask_diagnostics(data: dict) -> list[dict]:
    """Validate a GeoTask document dict. Returns structured diagnostics.

    This function delegates to validate_document() for unified validation
    (raw schema + canonicalization + canonical validation).

    An empty list means the document is valid. Each diagnostic includes:
    path, code, message, and suggested_fix, plus severity ("error" or "warning").
    """
    return validate_document(data)


def validate_geotask(data: dict) -> list[str]:
    """Validate a GeoTask document dict. Returns a list of error messages.

    This legacy API is kept for backward compatibility. New callers should use
    validate_document() for structured diagnostics or
    validate_geotask_diagnostics() for the legacy wrapper.
    """
    return [_format_diagnostic(d) for d in validate_document(data)]


# Deprecated alias for backward compatibility
validate_stir = validate_geotask
validate_stir_diagnostics = validate_geotask_diagnostics
