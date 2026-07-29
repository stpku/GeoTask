# GeoTask Versioned Payload Validation v1.0

Status: implemented public framework  
Framework version: `1.0`

## 1. Purpose

GeoTask publishes more than one versioned machine-readable artifact:

- GeoTask Execution Result v1.0;
- Control Evaluation Result v1.0;
- future public result or evidence artifacts.

Each artifact needs its own strict semantic loader, but the surrounding
validation workflow should not be reimplemented for every file type. The
Versioned Payload Validation framework centralizes the common contract for:

- schema ID and version metadata;
- strict loader invocation;
- task ID and item-count extraction;
- stable diagnostics;
- text and JSON validation reports;
- valid and invalid exit-code behavior.

The framework does not replace artifact-specific validation rules.

## 2. Public API

```python
from geotask_core import (
    VersionedPayloadContract,
    VersionedPayloadValidationReport,
    validate_versioned_payload,
    invalid_versioned_payload_report,
    EXECUTION_RESULT_VALIDATION_CONTRACT,
    CONTROL_EVALUATION_VALIDATION_CONTRACT,
)
```

A contract contains:

```text
artifact_name
report_key
schema_id
schema_version
invalid_code
count_field
count_label
loader
task_id_getter
count_getter
```

The loader is responsible for all artifact-specific structural and semantic
checks. It must return the loaded object or raise `TypeError`/`ValueError` for
invalid serialized data.

## 3. Built-in contracts

### 3.1 Execution result

```text
Contract: EXECUTION_RESULT_VALIDATION_CONTRACT
Loader: GeotaskResult.from_dict
Schema: schemas/geotask-result-v1.0.schema.json
Report key: result_validation
Count field: check_count
Invalid code: invalid_geotask_result
```

The loader additionally enforces:

```text
summary.total_checks == len(checks)
```

### 3.2 Control evaluation result

```text
Contract: CONTROL_EVALUATION_VALIDATION_CONTRACT
Loader: load_control_evaluation
Schema: schemas/geotask-control-evaluation-v1.0.schema.json
Report key: control_validation
Count field: evaluation_count
Invalid code: invalid_control_evaluation
```

The strict control loader additionally enforces:

- `action_executed` is false at the result and block levels;
- context entries exactly match scalar leaves in context values;
- context entry values equal their corresponding context values;
- block state agrees with block type, value, and evaluation error;
- `satisfied` agrees with the evaluated value;
- expression field agrees with the block type;
- referenced identifiers agree with the serialized expression;
- unknown identifiers agree with unresolved context values;
- blocking and eligible outputs agree with gate state;
- top-level gate state agrees with all block evaluations;
- aggregate unknown, blocked, and eligible lists agree with block data;
- a missing control profile is represented only as `not_applicable`.

## 4. Common report shape

Every validation report contains:

```text
valid
schema_id
schema_version
file
task_id
artifact-specific count field
diagnostics
```

Execution-result JSON report:

```json
{
  "result_validation": {
    "valid": true,
    "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-result-v1.0.schema.json",
    "schema_version": "1.0",
    "file": "execution-result.json",
    "task_id": "example-task",
    "check_count": 2,
    "diagnostics": []
  }
}
```

Control-result JSON report:

```json
{
  "control_validation": {
    "valid": true,
    "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-control-evaluation-v1.0.schema.json",
    "schema_version": "1.0",
    "file": "control-evaluation.json",
    "task_id": "example-task",
    "evaluation_count": 1,
    "diagnostics": []
  }
}
```

Invalid JSON-mode reports remain parseable and use a non-zero process exit code.

## 5. CLI commands

```bash
geotask result validate execution-result.json
geotask result validate execution-result.json --format json

geotask control validate control-evaluation.json
geotask control validate control-evaluation.json --format json
```

Both commands use the same argument parser, JSON loader, report renderer, and
exit-code path. They differ only in their contract and strict loader.

The validation commands:

- do not execute GeoTask operators;
- do not evaluate control expressions;
- do not run `next_action`;
- do not release or authorize outputs;
- do not mutate the serialized input.

## 6. JSON safety

The shared CLI path rejects:

- malformed JSON;
- duplicate JSON keys;
- `NaN`, `Infinity`, and other non-finite values;
- a non-object top-level payload.

Artifact-specific loaders then validate the versioned payload body.

## 7. Adding a future artifact

A future public artifact should define:

1. a versioned JSON Schema and stable schema ID;
2. a strict loader with explicit format errors;
3. a `VersionedPayloadContract`;
4. structural and semantic conformance tests;
5. CLI or API exposure only after the public contract is stable.

The generic framework must not infer domain semantics or silently coerce legacy
formats into a newer versioned contract.

## 8. Versioning

Changing the common report fields or contract semantics incompatibly requires a
new framework version. Changing an artifact payload requires a new artifact
schema version even if the common validation framework remains at v1.0.
