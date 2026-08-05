"""Public-safe metadata projection for deterministic GeoTask Core operators.

The v1 :class:`OperatorContract` registry is the single source of truth.  This
module only projects those contracts into the compact metadata shape consumed
by the CLI, verifier, documentation, and compatibility APIs.
"""

from __future__ import annotations

from copy import deepcopy

from geotask_core.v1.ir import OperatorContract
from geotask_core.v1.operator_contracts import default_registry


REQUIRED_OPERATOR_METADATA_FIELDS = {
    "name",
    "input_shape",
    "output_type",
    "deterministic",
    "supported_geometry",
    "error_codes",
    "examples",
}


_TYPE_SHAPES = {
    "point": "point.coordinates [x, y]",
    "polyline": "polyline.coordinates [[x1, y1], [x2, y2], ...]",
    "multi_polyline": (
        "multi_polyline.coordinates [[[x1, y1], [x2, y2], ...], ...]"
    ),
    "polygon": "polygon.coordinates [[x1, y1], ..., [x1, y1]]",
    "rect": "rect.bbox [min_x, min_y, max_x, max_y]",
    "time_interval": "time_interval [start, end] in HH:MM",
    "altitude_interval": "altitude_interval [min, max]",
    "trajectory": (
        "trajectory.samples [{observed_at: RFC3339, coordinates: [x, y]}, ...]"
    ),
}

_OUTPUT_TYPES = {
    "number": "float",
    "boolean": "bool",
    "string": "str",
    "object": "dict",
    "array": "list",
}


def _example_argument_names(contract: OperatorContract) -> list[str]:
    """Return stable argument labels from the first contract example."""
    if contract.examples:
        inputs = contract.examples[0].get("inputs", {})
        if isinstance(inputs, dict) and len(inputs) == contract.arity:
            return list(inputs.keys())
    return [f"arg{index + 1}" for index in range(contract.arity)]


def _project_example(example: dict) -> dict:
    """Convert a v1 contract example to the public compact representation."""
    return {
        "input": deepcopy(example.get("inputs", {})),
        "output": deepcopy(example.get("expected")),
    }


def _project_contract(contract: OperatorContract) -> dict:
    """Project one full operator contract into public-safe metadata."""
    argument_names = _example_argument_names(contract)
    input_shape = {
        name: _TYPE_SHAPES.get(input_type, input_type)
        for name, input_type in zip(argument_names, contract.input_types)
    }
    output_kind = str(contract.output.get("type", ""))
    return {
        "name": contract.name,
        "version": contract.version,
        "family": contract.family,
        "description": contract.description,
        "arity": contract.arity,
        "input_shape": input_shape,
        "output_type": _OUTPUT_TYPES.get(output_kind, output_kind or "unknown"),
        "deterministic": contract.deterministic,
        "supported_geometry": list(contract.input_types),
        "error_codes": list(contract.error_codes),
        "examples": [_project_example(example) for example in contract.examples],
        "semantics": deepcopy(contract.semantics),
        "invariants": deepcopy(contract.invariants),
        "model_execution": deepcopy(contract.model_execution),
    }


def operator_names() -> list[str]:
    """Return production Core operator names in stable contract order."""
    return default_registry.list_names()


def list_operator_metadata() -> list[dict]:
    """Return metadata projected from all production operator contracts."""
    return [_project_contract(contract) for contract in default_registry.list_all()]


def get_operator_metadata(name: str) -> dict:
    """Return metadata for one operator, or raise a clear unsupported error."""
    try:
        return _project_contract(default_registry.get(name))
    except KeyError as exc:
        supported = ", ".join(operator_names())
        raise KeyError(
            f"unsupported_operator: unknown operator '{name}'. "
            f"Supported operators: {supported}"
        ) from exc
