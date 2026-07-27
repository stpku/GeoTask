# GeoTask Quickstart

This tutorial creates, validates, executes, and inspects a first GeoTask document using the current public Core.

## 1. Install in a fresh virtual environment

GeoTask Core requires Python 3.10 or later. Create a clean environment:

```bash
python -m venv .venv
```

Activate it on Linux or macOS:

```bash
source .venv/bin/activate
```

Or on Windows PowerShell:

```powershell
.venv\\Scripts\\Activate.ps1
```

Install the exact Public Preview release from PyPI and check the CLI:

```bash
python -m pip install --no-cache-dir geotask-core==0.1.0
geotask --help
geotask inspect operators
```

Check the installed distribution version:

```bash
python -c "from importlib.metadata import version; print(version('geotask-core'))"
```

The expected version is `0.1.0`. The public Core does not require a model key, network service, GIS database, or external geometry library.

## 2. Create a Task

Create `my_distance.yaml`:

```yaml
geotask:
  id: my-distance
  name: My First GeoTask
  description: Compute a deterministic local distance.
  schema_version: "1.0"

space:
  crs:
    type: local_cartesian
    identifier: local_xy_m
  horizontal_unit: meter
  coordinate_order: [x, y]

objects:
  start:
    type: point
    coordinates: [0, 0]
  target:
    type: point
    coordinates: [3, 4]

operator_set:
  - distance_2d

tasks:
  - id: calculate-distance
    family: measurement
    goal: Calculate the distance from start to target.
    assertions:
      - id: start-to-target
        operator: distance_2d
        object_refs: [start, target]
        expected_type: number
        unit: meter

execution:
  mode: local_only
  steps:
    - id: run-distance
      executor: local
      assertion_refs: [start-to-target]

output_contract:
  format: structured
  required_fields: [start-to-target]
```

## 3. Validate

```bash
geotask validate my_distance.yaml
```

Validation checks document structure, object data, ids, operators, object references, arity, execution references, and other canonical constraints.

A structural error should produce a diagnostic with a path, code, explanation, and suggested fix. Fix errors before execution; do not treat an auto-repaired prompt as the same task.

## 4. Execute

```bash
geotask run my_distance.yaml
```

The deterministic result should contain a check equivalent to:

```text
assertion_id: start-to-target
value: 5.0
unit: meter
status: verified
assurance_level: local_deterministic
```

`execution.status = completed` means the plan finished. Always inspect individual check statuses and assurance; completion alone is not a correctness guarantee.

## 5. Use the Python API

```python
from geotask_core.parser import load_geotask, validate_document
from geotask_core.v1.canonicalizer import canonicalize
from geotask_core.v1.executor import execute_canonical

raw = load_geotask("my_distance.yaml")
diagnostics = validate_document(raw)
errors = [item for item in diagnostics if item.get("severity", "error") == "error"]
if errors:
    raise ValueError(errors)

canonical = canonicalize(raw)
result = execute_canonical(canonical)

for check in result.checks:
    print(check.assertion_id, check.value, check.unit, check.status)
```

## 6. Add a Spatial Constraint

Add a route and a rectangular work zone:

```yaml
objects:
  route:
    type: polyline
    coordinates:
      - [0, 0]
      - [10, 0]
      - [10, 10]
  work_zone:
    type: rect
    bbox: [8, -1, 12, 3]

operator_set:
  - line_intersects_rect
```

Then add an assertion:

```yaml
- id: route-enters-work-zone
  operator: line_intersects_rect
  object_refs: [route, work_zone]
  expected_type: bool
```

Boundary contact counts as intersection. Do not assume different boundary semantics without using a different operator contract.

## 7. Add Time and Altitude

Time interval:

```yaml
flight-window:
  type: time_interval
  start: "08:00"
  end: "09:00"
```

Altitude interval:

```yaml
flight-band:
  type: altitude_interval
  min: 100
  max: 150
  unit: meter
  datum: relative
```

Use `time_overlap` and `altitude_overlap` only with compatible object types and units.

## 8. Represent Application Logic Safely

Core operators should calculate general deterministic facts. Put scenario-level policy under `extensions`:

```yaml
extensions:
  application_context:
    scenario: vehicle_clearance
  clearance_budget:
    available_width_m: 2.4
    required_width_m: 2.7
    passable: false
  passage_gate:
    status: blocked
    blocked_outputs:
      - autonomous_passage
    resume_when: available_width_m >= required_width_m
    next_action: recover_clearance_margin
```

Rules for extensions:

1. derived values should be reproducible from explicit inputs;
2. extensions must not redefine Core operator behavior;
3. workflow status must not masquerade as a Core claim status;
4. safety approval should not claim local deterministic assurance unless its governing rule has actually been executed;
5. customer-specific or patent-sensitive rules should live in a Domain Pack or private Runtime.

## 9. Validate Against JSON Schema

```bash
python -c "import json, yaml; from jsonschema import validate; schema=json.load(open('schemas/geotask-v1.0.schema.json', encoding='utf-8')); doc=yaml.safe_load(open('my_distance.yaml', encoding='utf-8')); validate(doc, schema); print('schema ok')"
```

The JSON Schema provides editor validation and basic structure checks. The Core validator remains authoritative for semantic checks such as object reference resolution and operator compatibility.

## 10. Give a Task to a Model

A model may read a GeoTask document and propose objects, assertions, or an action. Mark model-produced fields as `model_generated`. Then run a separate local path.

Recommended pattern:

```text
natural-language request
  → model proposes GeoTask or action
  → Core validates objects and assertions
  → local operators execute
  → comparator checks model claim
  → verified / contradicted / unverifiable / review
```

Do not let the same model both invent a value and declare that the value has been locally verified.

## 11. Contribute to development (source install)

Use an editable source install only when modifying GeoTask, running the full repository checks, or preparing a contribution:

```bash
git clone https://github.com/stpku/GeoTask.git
cd GeoTask
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
```

## 12. Run Tests

In a source development environment:

```bash
pytest
```

Useful focused tests:

```bash
pytest tests/v1 -q
pytest tests/test_core_examples_v0_2.py -q
pytest tests/test_documentation_system.py -q
```

## 13. Continue Learning

- [Implemented Language Specification](../spec/geotask-language-spec-v1.0.md)
- [Operator Registry](../operator_registry.md)
- [Status and Assurance Model](../reference/status-model.md)
- [Evidence and Recovery](../reference/evidence-and-recovery.md)
- [GT01–GT13 Cookbook](../cookbook/gt01-gt13.md)
- [White Paper](../whitepaper/GeoTask_White_Paper_v0.1.md)
