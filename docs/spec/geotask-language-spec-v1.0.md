# GeoTask Language and Execution Specification v1.0

**Status:** Implemented Public Profile  
**Normative target:** current `geotask_core.v1` parser, canonical IR, validator, executor, result model, public tests, and `schemas/geotask-v1.0.schema.json`  
**Not the same as:** the broader [target specification status](target-specification-status.md)

This document defines the GeoTask v1.0 document profile implemented by the current public Core repository. It uses the terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** as normative requirements.

---

## 1. Conformance

A document conforms to this profile when it:

1. is valid YAML or JSON;
2. satisfies the structural requirements in this document and the JSON Schema;
3. canonicalizes into a `CanonicalDocument` without validation errors;
4. references only known objects and supported operators;
5. can be executed in the declared public execution mode;
6. does not redefine Core operator semantics through `extensions`.

An implementation conforms when it can parse, canonicalize, validate, and execute conforming documents for every Core operator it claims to support.

The public CLI is the reference interface:

```bash
geotask validate task.yaml
geotask run task.yaml
geotask inspect operators
```

---

## 2. Identifier Rules

GeoTask ids MUST:

- begin with an ASCII letter;
- contain only letters, digits, `_`, `.`, and `-` after the first character;
- be no longer than 128 characters.

Examples:

```text
valid:   task-01
valid:   route.conflict_a
invalid: 01-task
invalid: route conflict
```

Object ids, task ids, assertion ids, and execution-step ids SHOULD be unique within their applicable scope. Assertion ids referenced by execution steps MUST resolve to exactly one assertion.

---

## 3. Top-Level Document

A native v1.0 document SHOULD use this shape:

```yaml
geotask:
space:
objects:
operator_set:
operator_contracts:   # optional

tasks:
execution:            # optional, defaults to local execution behavior
verification:         # optional
output_contract:      # optional
extensions:           # optional
expected_results:     # optional
```

### 3.1 Required Sections

The user-facing native profile requires:

- `geotask`
- `space`
- `objects`
- `operator_set`
- `tasks`

The canonical serializer may use `metadata` instead of `geotask`. Consumers SHOULD accept either shape when reading a serialized CanonicalDocument, but authored examples SHOULD use `geotask`.

### 3.2 Unknown Fields

Unknown top-level fields SHOULD be rejected or reported as diagnostics. Domain-specific data MUST be placed under `extensions`, unless a Domain Pack defines a separate validated profile.

---

## 4. `geotask` Metadata

Example:

```yaml
geotask:
  id: "minimal-distance-v1"
  name: "Minimal v1.0 Distance"
  description: "Compute a deterministic distance between two local points."
  schema_version: "1.0"
  language: "en"
  domain: "general_spatial"
  created_at: "2026-07-27T00:00:00Z"
  tags: ["distance", "example"]
```

| Field | Type | Required | Meaning |
|---|---:|---:|---|
| `id` | string | yes | Stable document id. |
| `name` | string | yes | Human-readable name. |
| `description` | string | no | Purpose or summary. |
| `goal` | string | no | Compatibility alias used by examples; canonicalized as description when needed. |
| `schema_version` | string | yes | MUST begin with `1.` for native v1 input. |
| `language` | string | no | Content language, default `en`. |
| `domain` | string | no | Domain label, default `general_spatial`. |
| `created_at` | string | no | Timestamp or date string. |
| `tags` | array[string] | no | Search and classification tags. |

`schema_version` identifies the document schema, not the Python package version.

---

## 5. `space`

Example:

```yaml
space:
  crs:
    type: "local_cartesian"
    identifier: "warehouse_xy_m"
  axes:
    x: "east"
    y: "north"
  horizontal_unit: "meter"
  vertical_unit: "meter"
  coordinate_order: ["x", "y"]
  precision:
    decimal_places: 3
    tolerance: 0.01
```

### 5.1 CRS

`space.crs` MAY be a string for compatibility, but native v1 documents SHOULD use:

```yaml
crs:
  type: local_cartesian
  identifier: local_xy_m
```

Supported descriptive CRS types include:

- `local_cartesian`
- `projected`
- `geographic`
- `unknown`

The current Core does not perform CRS transformations. All objects used in one assertion MUST already be expressed in a compatible coordinate system.

### 5.2 Units

`horizontal_unit` and `vertical_unit` are descriptive contract fields. The current Core does not automatically convert units. Inputs to one operator MUST use compatible units.

### 5.3 Boundary Semantics

Core interval and rectangle operators use closed boundaries unless an operator contract states otherwise. Touching the boundary therefore counts as intersection, containment, or overlap.

---

## 6. `objects`

`objects` is a mapping from object id to object definition. The public Canonical IR defines `point`, `polyline`, `rect`, `time_interval`, `altitude_interval`, and `feature_collection`.

Native v1 objects MAY store fields inline:

```yaml
objects:
  point_a:
    type: point
    coordinates: [0, 0]
```

Canonical objects MAY use a `data` wrapper:

```yaml
objects:
  point_a:
    type: point
    data:
      coordinates: [0, 0]
```

The canonicalizer normalizes both forms.

### 6.1 Point

```yaml
point_a:
  type: point
  coordinates: [3, 4]
```

Requirements:

- exactly two numeric coordinates;
- coordinate order follows `space.coordinate_order`;
- legacy `xy` is accepted for compatibility.

### 6.2 Polyline

```yaml
route:
  type: polyline
  coordinates:
    - [0, 0]
    - [10, 0]
    - [10, 5]
```

Requirements:

- at least two coordinate pairs;
- each pair contains exactly two numbers;
- legacy type `line` and field `points` are accepted by the compatibility layer.

`line_intersects_rect` evaluates the polyline segments according to the registered operator implementation. Consumers MUST NOT assume that only the first segment is used in v1 examples.

### 6.3 Rectangle

```yaml
restricted_zone:
  type: rect
  bbox: [0, 0, 10, 10]
```

`bbox` MUST be `[min_x, min_y, max_x, max_y]`, with minimum values not greater than maximum values.

### 6.4 Time Interval

Preferred native form:

```yaml
flight_window:
  type: time_interval
  start: "08:00"
  end: "09:00"
```

Compatibility form:

```yaml
flight_window:
  type: time_interval
  interval: ["08:00", "09:00"]
```

Requirements:

- `HH:MM` values;
- start MUST be less than or equal to end;
- current public operator treats the interval as closed;
- legacy type `time` is accepted.

### 6.5 Altitude Interval

Preferred native form:

```yaml
flight_band:
  type: altitude_interval
  min: 100
  max: 150
  unit: meter
  datum: relative
```

Compatibility form:

```yaml
flight_band:
  type: altitude_interval
  range: [100, 150]
```

Requirements:

- numeric minimum and maximum;
- minimum MUST be less than or equal to maximum;
- both intervals compared by `altitude_overlap` MUST use compatible unit and datum;
- legacy type `altitude` is accepted.

### 6.6 Feature Collection

```yaml
site_candidates:
  type: feature_collection
  feature_type: point
  features:
    - id: site_a
      coordinates: [0, 0]
```

`feature_collection` is represented in the Canonical IR, but individual Core operators MAY not accept it directly. A task MUST use only object/operator combinations declared by the operator registry.

---

## 7. `operator_set`

Example:

```yaml
operator_set:
  - distance_2d
  - line_intersects_rect
```

The list declares operators used by the document. Every assertion operator SHOULD appear in `operator_set`. The public Core currently supports:

| Operator | Input types | Output | Boundary rule |
|---|---|---|---|
| `distance_2d` | point, point | number | n/a |
| `line_intersects_rect` | polyline, rect | bool | contact counts |
| `point_to_line_distance_2d` | point, polyline | number | segment distance |
| `rect_contains_point` | rect, point | bool | boundary counts |
| `time_overlap` | time_interval, time_interval | bool | endpoint contact counts |
| `altitude_overlap` | altitude_interval, altitude_interval | bool | endpoint contact counts |

The runtime registry is authoritative. Inspect it with:

```bash
geotask inspect operators
```

---

## 8. `operator_contracts`

A document MAY include descriptive operator contracts:

```yaml
operator_contracts:
  distance_2d:
    name: distance_2d
    version: "1.0"
    family: measurement
    description: Euclidean distance in a local 2D plane.
    arity: 2
    input_types: [point, point]
    output:
      type: number
      unit_from: space.horizontal_unit
    deterministic: true
```

Document contracts MUST NOT override the implementation semantics of a registered Core operator. They are useful for model context, transport, inspection, and conformance checking.

---

## 9. `tasks`

A document MUST contain at least one task.

```yaml
tasks:
  - id: compute_distance
    family: measurement
    goal: Calculate the Euclidean distance.
    inputs: [point_a, point_b]
    constraints: []
    assertions:
      - id: ab_distance
        operator: distance_2d
        object_refs: [point_a, point_b]
        expected_type: number
        unit: meter
    outputs: [ab_distance]
```

| Field | Type | Required | Meaning |
|---|---:|---:|---|
| `id` | string | yes | Task id. |
| `family` | string | no | Classification label. |
| `goal` | string | no | Human-readable intent. |
| `inputs` | array | no | Input ids or descriptions. |
| `constraints` | array | no | Explicit task-level constraints. |
| `assertions` | array | yes | Verifiable propositions. |
| `outputs` | array | no | Requested outputs. |

Task constraints MAY contain domain-level descriptions, but constraints that affect deterministic results SHOULD be represented as typed objects, assertion parameters, or validated extensions.

---

## 10. Assertions

Example:

```yaml
- id: route_intersects_zone
  operator: line_intersects_rect
  object_refs: [route, restricted_zone]
  parameters: {}
  expected_type: bool
  unit: ""
  tolerance: 0
  depends_on: []
  condition: ""
  on_error: stop
```

### 10.1 Required Fields

An assertion MUST include:

- `id`
- `operator`
- `object_refs`

### 10.2 Object References

Every `object_refs` value MUST resolve to an object in the same document. The number and types of referenced objects MUST match the operator contract.

### 10.3 Expected Type

`expected_type` SHOULD be one of:

- `number`
- `bool`
- another type explicitly declared by an operator contract

A mismatch SHOULD produce a diagnostic or failed check rather than silent coercion.

### 10.4 Tolerance

`tolerance` applies only to compatible numeric comparisons. It MUST NOT be used to alter geometric boundary semantics or to make an invalid object valid.

### 10.5 Dependencies

`depends_on` declares assertion dependencies. References MUST resolve and MUST NOT form a cycle.

### 10.6 Error Policy

Supported policy values include:

- `stop`
- `skip`
- `continue`
- `need_review`
- `fallback`

Implementations MAY support only a subset in public local execution, but MUST report unsupported policies rather than silently changing them.

---

## 11. `execution`

```yaml
execution:
  mode: local_only
  allowed_modes: [local_only]
  steps:
    - id: run_local_checks
      executor: local
      assertion_refs: [ab_distance]
      depends_on: []
      on_error: stop
```

### 11.1 Execution Modes

Defined protocol modes are:

- `model_only`
- `local_only`
- `hybrid`
- `shadow_compare`

The public Core reference executor performs local deterministic execution only. It does not call a hosted model or store model credentials. `model_only` returns an explicit model-generated skeleton without making a model call. `hybrid` and `shadow_compare` are protocol labels reserved for Runtime implementations; public Core returns `unverifiable` checks with `unsupported_execution_mode` and MUST NOT substitute local execution. Documents intended for direct public Core execution SHOULD use `local_only`.

### 11.2 Executors

Defined executor labels are:

- `model`
- `local`
- `connector`
- `human`
- `runtime`

The presence of a label does not mean the public Core implements that executor. Public Core executes only `local` steps. A `model`, `connector`, `human`, or `runtime` step returns `unverifiable` with `unsupported_executor`; it MUST NOT be routed through the local operator dispatcher.

### 11.3 Steps

Each step MUST have an id and executor. `assertion_refs` MUST reference existing assertions. Step dependencies MUST NOT be cyclic.

---

## 12. `verification`

```yaml
verification:
  mode: local_deterministic
  required_assurance: local_deterministic
  compare: {}
  failure_policy: {}
```

Defined verification modes:

- `none`
- `model_self_check`
- `local_deterministic`
- `model_local_compare`
- `cross_model_compare`
- `human_review`

A verification mode describes the requested process. It MUST NOT be confused with the assurance level actually achieved.

---

## 13. `output_contract`

```yaml
output_contract:
  format: structured
  required_fields: [ab_distance]
  allow_additional_fields: true
  allow_model_inference: false
  numeric_precision:
    decimal_places: 3
  ordering: {}
```

| Field | Meaning |
|---|---|
| `format` | Output representation, normally `structured`. |
| `required_fields` | Fields that MUST be present in the final result. |
| `allow_additional_fields` | Whether unlisted output fields are permitted. |
| `allow_model_inference` | Whether model-derived fields may appear. |
| `numeric_precision` | Numeric formatting or comparison rules. |
| `ordering` | Optional deterministic ordering requirements. |

Output contracts constrain result shape. They do not alter operator values.

---

## 14. `extensions`

`extensions` is an open mapping for task- or domain-level semantics:

```yaml
extensions:
  application_context:
    scenario: uav_delivery_energy_reserve
  energy_budget:
    available_range_km: 12
    total_required_range_km: 13
  mission_gate:
    status: blocked
    blocked_outputs: [launch_clearance]
    resume_when: available_range_km >= total_required_range_km
    next_action: recover_energy_margin
```

Rules:

1. extensions MUST NOT mutate registered Core operator semantics;
2. deterministic derived values SHOULD be reproducible from explicit inputs;
3. workflow states SHOULD identify their namespace or context;
4. safety or approval decisions MUST NOT claim Core verification unless the relevant rule is implemented and executed;
5. sensitive customer rules SHOULD live in a separate Domain Pack or private Runtime.

The JSON Schema intentionally allows arbitrary nested extension content.

---

## 15. `expected_results`

`expected_results` MAY store fixtures used by examples and tests:

```yaml
expected_results:
  - name: ab_distance
    value: 5.0
    unit: meter
```

Expected results are not execution results. An implementation MUST execute the assertions and compare results rather than treating fixtures as computed truth.

---

## 16. Result and Status Semantics

### 16.1 Execution Status

Execution lifecycle values include:

- `pending`
- `running`
- `completed`
- `partial`
- `failed`
- `skipped`

`completed` means the execution plan finished; it does not by itself guarantee that every claim is verified.

### 16.2 Claim Status

Core claim states include:

- `proposed`
- `computed`
- `verified`
- `contradicted`
- `need_review`
- `need_data`
- `invalid_input`
- `invalid_operator`
- `invalid_reference`
- `execution_error`
- `unverifiable`

Application extensions MAY use states such as `blocked`, `conflicted`, `coordinated`, or `insufficient_margin`, but MUST NOT present them as Core `ClaimStatus` values unless the enum is extended in code and tests.

### 16.3 Assurance Level

Ordered assurance levels are:

```text
0 unverified
1 model_generated
2 model_self_checked
3 local_deterministic
4 model_local_agreement
5 independent_cross_verified
6 human_reviewed
```

An implementation MUST NOT report an assurance level stronger than the completed verification process.

See [Status and Assurance Model](../reference/status-model.md).

---

## 17. Diagnostics

Validation diagnostics SHOULD include:

- `path`
- `code`
- `message`
- `suggested_fix`
- `severity`

Stable categories include:

- `missing_field`
- `unknown_field`
- `invalid_type`
- `duplicate_id`
- `unknown_object_type`
- `invalid_coordinates`
- `invalid_interval`
- `invalid_crs`
- `unit_mismatch`
- `invalid_operator`
- `invalid_reference`
- `arity_mismatch`
- `object_type_mismatch`
- `cyclic_dependency`
- `missing_data`
- `output_contract_violation`

A validator MUST NOT silently repair a document in a way that changes task meaning. A canonicalizer MAY normalize supported compatibility aliases while preserving warnings.

---

## 18. Compatibility

The repository retains compatibility with older `0.x` documents that use fields such as:

```yaml
geotask:
  version: "0.2"
ops:
task:
```

and object aliases:

- `line` → `polyline`
- `time` → `time_interval`
- `altitude` → `altitude_interval`
- `xy` → `coordinates`
- `points` → `coordinates`

New documents SHOULD use native v1 fields. Compatibility support does not make the legacy shape part of the normative v1 authoring profile.

---

## 19. Minimal Conforming Example

```yaml
geotask:
  id: example-distance
  name: Example Distance
  schema_version: "1.0"

space:
  crs:
    type: local_cartesian
    identifier: local_xy_m
  horizontal_unit: meter

objects:
  a:
    type: point
    coordinates: [0, 0]
  b:
    type: point
    coordinates: [3, 4]

operator_set: [distance_2d]

tasks:
  - id: calculate
    assertions:
      - id: ab_distance
        operator: distance_2d
        object_refs: [a, b]
        expected_type: number
        unit: meter

execution:
  mode: local_only
  steps:
    - id: run
      executor: local
      assertion_refs: [ab_distance]

output_contract:
  format: structured
  required_fields: [ab_distance]
```

Expected deterministic value: `5.0 meter` with `local_deterministic` assurance after successful local execution.

---

## 20. Conformance Checklist

A document author SHOULD verify:

- [ ] ids follow the identifier grammar;
- [ ] CRS and units are explicit;
- [ ] every object has a supported type and valid data;
- [ ] every assertion references existing objects;
- [ ] operator arity and object types match the registry;
- [ ] execution steps reference existing assertions;
- [ ] output requirements are explicit;
- [ ] extension-derived decisions are reproducible or clearly marked for review;
- [ ] model-generated values do not claim local assurance;
- [ ] the document passes `geotask validate`;
- [ ] the task passes the JSON Schema and public tests.

---

## 21. Related Documents

- [White Paper](../whitepaper/GeoTask_White_Paper_v0.1.md)
- [JSON Schema](../../schemas/geotask-v1.0.schema.json)
- [Quickstart](../tutorials/quickstart.md)
- [Operator Registry](../operator_registry.md)
- [Status and Assurance Model](../reference/status-model.md)
- [Evidence and Recovery](../reference/evidence-and-recovery.md)
- [Legacy YAML Schema Notes](../geotask_yaml_schema.md)
- [Target Specification Status](target-specification-status.md)
