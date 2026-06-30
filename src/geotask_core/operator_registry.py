"""Public-safe metadata registry for deterministic GeoTask Core operators."""

REQUIRED_OPERATOR_METADATA_FIELDS = {
    "name",
    "input_shape",
    "output_type",
    "deterministic",
    "supported_geometry",
    "error_codes",
    "examples",
}


_OPERATORS: list[dict] = [
    {
        "name": "distance_2d",
        "input_shape": {"a": "point.xy [x, y]", "b": "point.xy [x, y]"},
        "output_type": "float",
        "deterministic": True,
        "supported_geometry": ["point", "point"],
        "error_codes": ["invalid_input", "invalid_coordinates"],
        "examples": [
            {
                "input": {"a": [0, 0], "b": [120, 80]},
                "output": 144.22,
            }
        ],
    },
    {
        "name": "line_intersects_rect",
        "input_shape": {
            "line_points": "line.points [[x1, y1], [x2, y2], ...]",
            "bbox": "rect.bbox [min_x, min_y, max_x, max_y]",
        },
        "output_type": "bool",
        "deterministic": True,
        "supported_geometry": ["line", "rect"],
        "error_codes": ["invalid_input", "unsupported_geometry"],
        "examples": [
            {
                "input": {
                    "line_points": [[-200, 0], [400, 0]],
                    "bbox": [250, -100, 350, 100],
                },
                "output": True,
            }
        ],
    },
    {
        "name": "point_to_line_distance_2d",
        "input_shape": {
            "point": "point.xy [x, y]",
            "line_points": "line.points [[x1, y1], [x2, y2], ...]",
        },
        "output_type": "float",
        "deterministic": True,
        "supported_geometry": ["point", "line"],
        "error_codes": ["invalid_input", "invalid_coordinates"],
        "examples": [
            {
                "input": {"point": [5, 7], "line_points": [[0, 2], [10, 2]]},
                "output": 5.0,
            }
        ],
    },
    {
        "name": "rect_contains_point",
        "input_shape": {
            "bbox": "rect.bbox [min_x, min_y, max_x, max_y]",
            "point": "point.xy [x, y]",
        },
        "output_type": "bool",
        "deterministic": True,
        "supported_geometry": ["rect", "point"],
        "error_codes": ["invalid_input", "unsupported_geometry"],
        "examples": [
            {
                "input": {"bbox": [0, 0, 10, 10], "point": [5, 5]},
                "output": True,
            }
        ],
    },
    {
        "name": "time_overlap",
        "input_shape": {
            "a": "time.interval [start, end] in HH:MM",
            "b": "time.interval [start, end] in HH:MM",
        },
        "output_type": "bool",
        "deterministic": True,
        "supported_geometry": ["time_interval"],
        "error_codes": ["invalid_input", "invalid_interval"],
        "examples": [
            {
                "input": {"a": ["08:00", "10:00"], "b": ["09:00", "11:00"]},
                "output": True,
            }
        ],
    },
    {
        "name": "altitude_overlap",
        "input_shape": {
            "a": "altitude.range [min, max]",
            "b": "altitude.range [min, max]",
        },
        "output_type": "bool",
        "deterministic": True,
        "supported_geometry": ["altitude_range"],
        "error_codes": ["invalid_input", "invalid_interval"],
        "examples": [
            {
                "input": {"a": [100, 200], "b": [150, 250]},
                "output": True,
            }
        ],
    },
]

_OPERATORS_BY_NAME = {operator["name"]: operator for operator in _OPERATORS}


def operator_names() -> list[str]:
    """Return production Core operator names in stable registry order."""
    return [operator["name"] for operator in _OPERATORS]


def list_operator_metadata() -> list[dict]:
    """Return metadata for all production Core operators."""
    return [dict(operator) for operator in _OPERATORS]


def get_operator_metadata(name: str) -> dict:
    """Return metadata for one operator, or raise a clear unsupported error."""
    try:
        return dict(_OPERATORS_BY_NAME[name])
    except KeyError as exc:
        supported = ", ".join(operator_names())
        raise KeyError(
            f"unsupported_operator: unknown operator '{name}'. "
            f"Supported operators: {supported}"
        ) from exc

