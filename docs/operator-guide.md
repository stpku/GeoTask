# Operator Guide

GeoTask Core ships with 6 built-in deterministic operators. This guide explains how to define and register additional operators.

## Quick Overview

An operator in GeoTask Core has three parts:

1. **Implementation.** A pure Python function in `geotask_core/ops.py` (or your own module).
2. **Contract.** An `OperatorContract` dataclass that declares the operator's interface and semantics.
3. **Registration.** Adding the contract to the `OperatorRegistry` so the dispatcher can find it.

## Step-by-Step: Adding a New Operator

Suppose you want to add `distance_3d`, which computes Euclidean distance between two 3D points.

### 1. Write the Implementation

Create a pure function that takes the declared input types and returns the declared output type:

```python
# geotask_core/ops.py

import math

def distance_3d(a: list[float], b: list[float]) -> float:
    """Euclidean distance between two 3D points."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)
```

The function must be:
- Deterministic (same inputs always produce same output).
- Free of side effects (no I/O, no network, no random).
- Importable from the module path declared in the contract.

### 2. Define the Contract

In `geotask_core/v1/operator_contracts.py`, add a new `OperatorContract`:

```python
DISTANCE_3D = OperatorContract(
    name="distance_3d",
    version="1.0",
    family="measurement",
    description="Euclidean distance between two 3D points.",
    arity=2,
    input_types=["point", "point"],
    output={
        "type": "number",
        "unit_behavior": "inherit_horizontal_unit",
    },
    deterministic=True,
    semantics={
        "formula": "sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)",
        "boundary_rules": [
            "Distance is non-negative.",
            "Identical points produce zero.",
        ],
    },
    invariants=[
        {"id": "non_negative", "expression": "result >= 0"},
        {"id": "symmetric", "expression": "distance(a,b) == distance(b,a)"},
    ],
    error_codes=[
        "invalid_coordinates",
        "arity_mismatch",
    ],
    implementation="geotask_core.ops.distance_3d",
)
```

### 3. Register the Contract

Add the new contract to the built-in list at the bottom of `operator_contracts.py`:

```python
_BUILTIN_CONTRACTS: list[OperatorContract] = [
    DISTANCE_2D,
    LINE_INTERSECTS_RECT,
    # ... existing contracts ...
    DISTANCE_3D,  # new
]
```

The `default_registry` will pick it up at import time. External packages can also register contracts programmatically:

```python
from geotask_core.v1.operator_contracts import OperatorRegistry, OperatorContract

registry = OperatorRegistry()
registry.register(my_custom_contract)
```

### 4. Use It

Reference the new operator in your YAML document:

```yaml
operator_set: [distance_3d]

tasks:
  - id: "calc"
    assertions:
      - id: "dist"
        operator: "distance_3d"
        object_refs: ["point_a", "point_b"]
```

The dispatcher resolves the operator, extracts data from both point objects, calls `ops.distance_3d`, and returns the result.

## OperatorContract Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | Yes | Unique identifier used in YAML `operator` fields |
| `version` | `str` | No | Contract version, default `"1.0"` |
| `family` | `str` | No | Category: `measurement`, `topology`, `interval` |
| `description` | `str` | No | Human-readable explanation |
| `arity` | `int` | Yes | Number of input objects |
| `input_types` | `list[str]` | Yes | Ordered expected GeoObject types |
| `output` | `dict` | No | `type` (`number`/`boolean`) and `unit_behavior` |
| `deterministic` | `bool` | No | Must be `True` for Core operators |
| `semantics` | `dict` | No | Formula, boundary rules, legacy aliases |
| `model_execution` | `dict` | No | Hints for model-based execution (not used by Core) |
| `invariants` | `list[dict]` | No | Properties that must hold for all inputs |
| `error_codes` | `list[str]` | No | Diagnostic codes this operator may surface |
| `examples` | `list[dict]` | No | Input/output examples for testing and documentation |
| `implementation` | `str` | Yes | Module path to the bound function |

## How the Dispatcher Works

The `AssertionDispatcher` connects assertions to implementations. When `dispatch(assertion, objects)` is called:

1. **Lookup.** Find the `OperatorContract` by name in the registry.
2. **Arity check.** Verify `len(assertion.object_refs) == contract.arity`.
3. **Parameter extraction.** For each `object_ref`, resolve the `GeoObject` from the objects dict and extract geometry data by its declared `input_type`:
   - `point` -> `data["coordinates"]` (fallback: `data["xy"]`)
   - `polyline` -> `data["coordinates"]` (fallback: `data["points"]`)
   - `rect` -> `data["bbox"]`
   - `time_interval` -> `[data["start"], data["end"]]`
   - `altitude_interval` -> `[data["min"], data["max"]]`
4. **Implementation binding.** Parse `contract.implementation` (e.g., `"geotask_core.ops.distance_2d"`), import the module, and retrieve the callable.
5. **Invocation.** Call `impl(*extracted_params, **assertion.parameters)`.

The dispatcher raises `ValueError` for arity mismatches, missing objects, or type mismatches. It raises `KeyError` for unregistered operators. The executor catches these and converts them to error diagnostics.

## Constraints

- Operator implementations must not depend on `geotask_core.v1` modules. `ops.py` is a leaf.
- Contracts live in `v1/operator_contracts.py` and depend only on `v1/ir.py` for the `OperatorContract` type.
- The registry and dispatcher are importable from `geotask_core.v1.operator_contracts` without pulling in the validator or executor.
