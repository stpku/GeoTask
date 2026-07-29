# GeoTask Execution Result v1.0

Status: implemented public contract  
Schema version: `1.0`  
JSON Schema: [`schemas/geotask-result-v1.0.schema.json`](../../schemas/geotask-result-v1.0.schema.json)  
Schema ID: `https://stpku.github.io/GeoTask/schemas/geotask-result-v1.0.schema.json`

## 1. Purpose

GeoTask Execution Result v1.0 is the canonical machine-readable output of a
GeoTask Core v1 execution. It is produced by `GeotaskResult.to_dict()` and by:

```bash
geotask run task.yaml --format v1-json --output execution-result.json
```

The result is suitable for storage, exchange, independent JSON Schema
validation, and subsequent read-only control evaluation.

## 2. Top-level shape

Every result uses one wrapper key and rejects additional top-level fields:

```json
{
  "geotask_result": {
    "schema_version": "1.0",
    "task_id": "example-task",
    "execution": {},
    "checks": [],
    "outputs": {},
    "summary": {},
    "overall": {},
    "warnings": [],
    "errors": []
  }
}
```

The wrapper is part of the contract. A bare result object is not a v1.0
GeoTask Execution Result.

## 3. Required fields

### 3.1 `execution`

Required fields:

- `mode`: `model_only`, `local_only`, `hybrid`, or `shadow_compare`;
- `status`: `pending`, `running`, `completed`, `partial`, `failed`, or `skipped`;
- `started_at`: timestamp string;
- `finished_at`: timestamp string.

### 3.2 `checks`

Each check requires:

```text
assertion_id
operator
object_refs
executor
value
unit
status
assurance_level
deterministic
evidence_refs
error
```

`executor` is one of:

```text
model
local
connector
human
runtime
```

`status` uses the public `ClaimStatus` values:

```text
proposed
computed
verified
contradicted
need_review
need_data
invalid_input
invalid_operator
invalid_reference
execution_error
unverifiable
```

`assurance_level` uses the lowercase public `AssuranceLevel` names:

```text
unverified
model_generated
model_self_checked
local_deterministic
model_local_agreement
independent_cross_verified
human_reviewed
```

`value` may contain any JSON-compatible value. `error` is either null or a JSON
object.

### 3.3 `outputs`

`outputs` is an object whose values may contain JSON-compatible values. Output
contents do not imply that an operational action, approval, or external command
has occurred.

### 3.4 `summary`

Required non-negative integer fields:

```text
total_checks
verified
contradicted
need_review
invalid
```

GeoTask Core additionally requires:

```text
summary.total_checks == len(checks)
```

Draft 2020-12 JSON Schema cannot express this sibling array-length equality, so
it is enforced by `GeotaskResult.from_dict()` and `geotask result validate`.

### 3.5 `overall`

`overall.status` uses `ClaimStatus`. `overall.assurance_level` uses
`AssuranceLevel` names. Control evaluation does not rewrite either field.

### 3.6 `warnings` and `errors`

`warnings` is an array of strings. `errors` is an array of JSON objects. These
fields describe execution diagnostics and remain distinct from control-gate
diagnostics.

## 4. Validation

Cross-language tools may validate the structural contract with the public JSON
Schema.

GeoTask Core provides a dependency-light CLI validator:

```bash
geotask result validate execution-result.json
```

Machine-readable report:

```bash
geotask result validate execution-result.json --format json
```

A valid JSON report has this shape:

```json
{
  "result_validation": {
    "valid": true,
    "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-result-v1.0.schema.json",
    "schema_version": "1.0",
    "file": "execution-result.json",
    "task_id": "example-task",
    "check_count": 1,
    "diagnostics": []
  }
}
```

For invalid data, JSON mode still emits a parseable report and exits non-zero.
Text mode writes invalid-result diagnostics to stderr.

The CLI rejects:

- malformed JSON;
- duplicate JSON keys;
- non-finite JSON numbers;
- missing or unknown fields;
- non-v1 schema versions;
- invalid field types;
- invalid enum values;
- negative summary counts;
- a `total_checks` value inconsistent with `checks`.

## 5. Public Python API

```python
from geotask_core import (
    GEOTASK_RESULT_SCHEMA_ID,
    GEOTASK_RESULT_SCHEMA_VERSION,
    GeotaskResult,
)

result = GeotaskResult.from_dict(payload)
```

`from_dict()` is intentionally strict and does not reinterpret legacy result
shapes as v1.0. Execution-result and control-result validation share the
[Versioned Payload Validation v1.0](geotask-versioned-payload-validation-v1.0.md)
framework for reports and diagnostics while retaining artifact-specific loaders.

## 6. CLI pipeline

A complete public CLI pipeline is:

```bash
geotask run task.yaml \
  --format v1-json \
  --output execution-result.json

geotask result validate execution-result.json

geotask control evaluate task.yaml \
  --result execution-result.json \
  --state control-state.yaml \
  --output control-evaluation.json
```

`result validate` only reads and validates the serialized result. It does not execute the task.
It also does not rerun operators, evaluate control expressions, execute
`next_action`, or authorize any output.

## 7. Versioning

Incompatible changes require:

- a new schema version;
- a new schema file;
- a new schema ID;
- corresponding loader and conformance tests.

Version `1.0` keeps the wrapper key and required fields stable.
