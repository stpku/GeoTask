"""GeoTask Core v1.0 — Structured operator contracts with implementation binding.

This module defines all 6 current Core operators as v1.0 OperatorContracts
and provides an OperatorRegistry for lookup plus an AssertionDispatcher
that replaces the v0.x runner.py type-based auto-detection with
assertion-driven execution.
"""

from __future__ import annotations

import importlib
import math
from typing import Any, Callable

from geotask_core.v1.ir import Assertion, GeoObject, OperatorContract


# -- v1.0 Operator Contracts

DISTANCE_2D = OperatorContract(
    name="distance_2d",
    version="1.0",
    family="measurement",
    description="Euclidean distance between two planar points.",
    arity=2,
    input_types=["point", "point"],
    output={
        "type": "number",
        "unit_behavior": "inherit_horizontal_unit",
    },
    deterministic=True,
    semantics={
        "formula": "sqrt((x2-x1)^2 + (y2-y1)^2)",
        "boundary_rules": [
            "Distance is non-negative.",
            "Identical points produce zero.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 50,
        "precision_tolerance": 0.01,
    },
    invariants=[
        {"id": "non_negative", "expression": "result >= 0"},
        {"id": "symmetric", "expression": "distance(a,b) == distance(b,a)"},
    ],
    error_codes=[
        "invalid_coordinates",
        "arity_mismatch",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {"a": [0, 0], "b": [3, 4]},
            "expected": 5.0,
        },
    ],
    implementation="geotask_core.ops.distance_2d",
)

LINE_INTERSECTS_RECT = OperatorContract(
    name="line_intersects_rect",
    version="1.0",
    family="topology",
    description=(
        "Check if any segment of a polyline intersects "
        "an axis-aligned rectangle."
    ),
    arity=2,
    input_types=["polyline", "rect"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "boundary_rules": [
            "Boundary contact counts as intersection.",
            "All consecutive point pairs are checked as segments.",
        ],
        "legacy_input_aliases": {
            "line": "polyline",
        },
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 20,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
    ],
    error_codes=[
        "insufficient_points",
        "invalid_bbox",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "polyline": [[-200, 0], [400, 0]],
                "rect": [250, -100, 350, 100],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.line_intersects_rect",
)

POINT_TO_LINE_DISTANCE_2D = OperatorContract(
    name="point_to_line_distance_2d",
    version="1.0",
    family="measurement",
    description="Shortest distance from a point to a polyline.",
    arity=2,
    input_types=["point", "polyline"],
    output={
        "type": "number",
        "unit_behavior": "inherit_horizontal_unit",
    },
    deterministic=True,
    semantics={
        "note": (
            "Iterates all consecutive segments of the polyline "
            "and returns the minimum point-to-segment distance."
        ),
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 30,
        "precision_tolerance": 0.01,
    },
    invariants=[
        {"id": "non_negative", "expression": "result >= 0"},
        {
            "id": "zero_on_segment",
            "expression": "point on segment => result == 0",
        },
    ],
    error_codes=[
        "invalid_coordinates",
        "insufficient_line_points",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "point": [5, 7],
                "polyline": [[0, 2], [10, 2]],
            },
            "expected": 5.0,
        },
    ],
    implementation="geotask_core.ops.point_to_line_distance_2d",
)

RECT_CONTAINS_POINT = OperatorContract(
    name="rect_contains_point",
    version="1.0",
    family="topology",
    description=(
        "Check if a point is inside or on the boundary of "
        "an axis-aligned rectangle."
    ),
    arity=2,
    input_types=["rect", "point"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "boundary_rules": [
            "Boundary contact counts as containment.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 100,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
        {
            "id": "self_contains",
            "expression": "point inside rect => result == True",
        },
    ],
    error_codes=[
        "invalid_bbox",
        "invalid_coordinates",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "rect": [0, 0, 10, 10],
                "point": [5, 5],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.rect_contains_point",
)

TIME_OVERLAP = OperatorContract(
    name="time_overlap",
    version="1.0",
    family="temporal",
    description=(
        "Check if two time intervals overlap. "
        "Boundary contact counts as overlap."
    ),
    arity=2,
    input_types=["time_interval", "time_interval"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "time_format": "HH:MM (24-hour)",
        "boundary_rules": [
            "Boundary contact counts as overlap.",
            "Intervals in any order are supported.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 50,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
        {
            "id": "symmetric",
            "expression": "overlap(a,b) == overlap(b,a)",
        },
    ],
    error_codes=[
        "invalid_time_format",
        "invalid_interval",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "a": ["08:00", "10:00"],
                "b": ["09:00", "11:00"],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.time_overlap",
)

ALTITUDE_OVERLAP = OperatorContract(
    name="altitude_overlap",
    version="1.0",
    family="vertical",
    description=(
        "Check if two altitude ranges overlap. "
        "Boundary contact counts as overlap."
    ),
    arity=2,
    input_types=["altitude_interval", "altitude_interval"],
    output={"type": "boolean"},
    deterministic=True,
    semantics={
        "unit": "meter (relative or absolute)",
        "boundary_rules": [
            "Boundary contact counts as overlap.",
            "Ranges in any order are supported.",
        ],
    },
    model_execution={
        "level": "M1",
        "supported": True,
        "recommended_max_items": 50,
    },
    invariants=[
        {"id": "bool_output", "expression": "result in (True, False)"},
        {
            "id": "symmetric",
            "expression": "overlap(a,b) == overlap(b,a)",
        },
    ],
    error_codes=[
        "invalid_altitude_range",
        "object_type_mismatch",
    ],
    examples=[
        {
            "inputs": {
                "a": [100, 200],
                "b": [150, 250],
            },
            "expected": True,
        },
    ],
    implementation="geotask_core.ops.altitude_overlap",
)


# -- Operator Registry


class OperatorRegistry:
    """Registry of v1.0 operator contracts with name-based lookup.

    All 6 Core operators are registered at construction time. Additional
    contracts can be registered via :meth:`register`.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, OperatorContract] = {}
        for contract in _BUILTIN_CONTRACTS:
            self.register(contract)

    def register(self, contract: OperatorContract) -> None:
        """Register an operator contract.

        Args:
            contract: The OperatorContract to register.

        Raises:
            ValueError: If a contract with the same name is already registered.
        """
        if contract.name in self._contracts:
            raise ValueError(
                f"Operator '{contract.name}' is already registered."
            )
        self._contracts[contract.name] = contract

    def get(self, name: str) -> OperatorContract:
        """Get an operator contract by name.

        Args:
            name: The operator name to look up.

        Returns:
            The matching OperatorContract.

        Raises:
            KeyError: If no contract is registered under *name*.
        """
        if name not in self._contracts:
            raise KeyError(
                f"Operator '{name}' is not registered. "
                f"Available: {self.list_names()}"
            )
        return self._contracts[name]

    def list_names(self) -> list[str]:
        """Return all registered operator names in insertion order."""
        return list(self._contracts.keys())

    def list_all(self) -> list[OperatorContract]:
        """Return all registered operator contracts in insertion order."""
        return list(self._contracts.values())

    def is_registered(self, name: str) -> bool:
        """Check whether an operator is registered.

        Args:
            name: The operator name to check.

        Returns:
            ``True`` if *name* is a registered operator.
        """
        return name in self._contracts


# -- Assertion Dispatcher


class AssertionDispatcher:
    """Assertion-driven execution dispatcher for v1.0.

    Replaces the v0.x runner.py type-based auto-detection with
    contract-bound dispatch:

    1. Look up the operator contract from the registry.
    2. Validate arity against the assertion's object_refs.
    3. Resolve object references to actual GeoObject data.
    4. Call the bound implementation with extracted parameters.
    """

    def __init__(self, registry: OperatorRegistry) -> None:
        self._registry = registry

    # -- Public API

    def dispatch(
        self,
        assertion: Assertion,
        objects: dict[str, GeoObject],
    ) -> Any:
        """Execute an assertion against a set of GeoObjects.

        Args:
            assertion: The Assertion describing what to compute.
            objects: Dictionary mapping object ids to GeoObject instances.

        Returns:
            The result of calling the operator implementation with the
            resolved parameters.

        Raises:
            KeyError: If the operator is not registered.
            ValueError: If arity does not match or object refs are missing.
        """
        contract = self._registry.get(assertion.operator)

        # Validate arity
        if len(assertion.object_refs) != contract.arity:
            raise ValueError(
                f"Operator '{contract.name}' expects {contract.arity} "
                f"object ref(s), got {len(assertion.object_refs)}: "
                f"{assertion.object_refs}"
            )

        # Extract parameters
        params = self._extract_params(
            contract, assertion.object_refs, objects
        )

        # Get and call implementation — pass assertion.parameters as kwargs
        impl = self._get_implementation(contract)
        kwargs: dict[str, Any] = dict(assertion.parameters) if assertion.parameters else {}
        return impl(*params, **kwargs)

    # -- Parameter Extraction

    def _extract_params(
        self,
        contract: OperatorContract,
        obj_refs: list[str],
        objects: dict[str, GeoObject],
    ) -> list:
        """Extract positional parameters from GeoObjects.

        Mapping rules by type:
          - ``point`` → ``data["coordinates"]`` (fallback: ``data["xy"]``)
          - ``polyline`` / ``line`` → ``data["coordinates"]``
            (fallback: ``data["points"]``)
          - ``rect`` → ``data["bbox"]``
          - ``time_interval`` → ``[data["start"], data["end"]]``
            (fallback: ``data["interval"]``)
          - ``altitude_interval`` → ``[data["min"], data["max"]]``
            (fallback: ``data["range"]``)
        """
        params: list = []
        for ref, expected_type in zip(obj_refs, contract.input_types):
            obj = objects.get(ref)
            if obj is None:
                raise ValueError(
                    f"Object reference '{ref}' not found in objects dict. "
                    f"Available: {list(objects.keys())}"
                )
            value = self._extract_typed_param(obj, expected_type)
            params.append(value)
        return params

    def _extract_typed_param(
        self, obj: GeoObject, expected_type: str
    ) -> Any:
        """Extract the geometry data from a single GeoObject.

        Handles legacy type aliases (e.g. ``line`` → ``polyline``) and
        field fallbacks for backward compatibility with v0.x data shapes.
        """
        data = obj.data
        obj_type = obj.type

        # point
        if expected_type == "point":
            if obj_type not in ("point",):
                raise ValueError(
                    f"Expected type 'point' for '{obj.id}', "
                    f"got '{obj_type}'"
                )
            coords = data.get("coordinates") or data.get("xy")
            if coords is None:
                raise ValueError(
                    f"Point object '{obj.id}' has no coordinates or xy field."
                )
            return coords

        # polyline (legacy alias: line)
        if expected_type == "polyline":
            if obj_type not in ("polyline", "line"):
                raise ValueError(
                    f"Expected type 'polyline' (or legacy 'line') "
                    f"for '{obj.id}', got '{obj_type}'"
                )
            coords = data.get("coordinates") or data.get("points")
            if coords is None:
                raise ValueError(
                    f"Polyline object '{obj.id}' has no coordinates "
                    f"or points field."
                )
            return coords

        # rect
        if expected_type == "rect":
            if obj_type not in ("rect",):
                raise ValueError(
                    f"Expected type 'rect' for '{obj.id}', "
                    f"got '{obj_type}'"
                )
            bbox = data.get("bbox")
            if bbox is None:
                raise ValueError(
                    f"Rect object '{obj.id}' has no bbox field."
                )
            return bbox

        # time_interval
        if expected_type == "time_interval":
            if obj_type not in ("time_interval", "time"):
                raise ValueError(
                    f"Expected type 'time_interval' for '{obj.id}', "
                    f"got '{obj_type}'"
                )
            interval = None
            if "start" in data and "end" in data:
                interval = [data["start"], data["end"]]
            elif "interval" in data:
                interval = data["interval"]
            if interval is None:
                raise ValueError(
                    f"Time interval object '{obj.id}' has no "
                    f"start/end or interval field."
                )
            return interval

        # altitude_interval
        if expected_type == "altitude_interval":
            if obj_type not in ("altitude_interval", "altitude"):
                raise ValueError(
                    f"Expected type 'altitude_interval' for '{obj.id}', "
                    f"got '{obj_type}'"
                )
            range_val = None
            if "min" in data and "max" in data:
                range_val = [data["min"], data["max"]]
            elif "range" in data:
                range_val = data["range"]
            if range_val is None:
                raise ValueError(
                    f"Altitude interval object '{obj.id}' has no "
                    f"min/max or range field."
                )
            return range_val

        raise ValueError(
            f"Unsupported expected type '{expected_type}' "
            f"for object '{obj.id}'."
        )

    # -- Implementation Binding

    def _get_implementation(self, contract: OperatorContract) -> Callable:
        """Dynamically import and return the bound implementation.

        Parses the ``implementation`` field of the contract (e.g.
        ``"geotask_core.ops.distance_2d"``), imports the module,
        and returns the named callable.

        Returns:
            The imported callable.

        Raises:
            ImportError: If the module cannot be imported.
            AttributeError: If the function is not found in the module.
        """
        impl_path: str = contract.implementation
        if not impl_path:
            raise ValueError(
                f"Operator '{contract.name}' has no implementation bound."
            )

        module_name, func_name = impl_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        func = getattr(module, func_name, None)
        if func is None:
            raise AttributeError(
                f"Function '{func_name}' not found in module '{module_name}' "
                f"(bound by operator '{contract.name}')."
            )
        if not callable(func):
            raise TypeError(
                f"'{impl_path}' is not callable "
                f"(bound by operator '{contract.name}')."
            )
        return func


# -- Built-in contract list & default registry

_BUILTIN_CONTRACTS: list[OperatorContract] = [
    DISTANCE_2D,
    LINE_INTERSECTS_RECT,
    POINT_TO_LINE_DISTANCE_2D,
    RECT_CONTAINS_POINT,
    TIME_OVERLAP,
    ALTITUDE_OVERLAP,
]

#: Default pre-populated registry with all 6 Core operators.
default_registry = OperatorRegistry()
