# GeoTask Artifact Validation v1.0

Status: implemented public contract  
Report version: `1.0`  
JSON Schema: [`schemas/geotask-artifact-validation-v1.0.schema.json`](../../schemas/geotask-artifact-validation-v1.0.schema.json)

## 1. Purpose

GeoTask exposes one read-only validation entry point for every artifact listed in
the public Artifact Registry:

```bash
geotask artifact validate <artifact-id> <file> [--format text|json]
```

The command resolves the stable Artifact ID, verifies the installed Schema Bundle,
loads the file with the artifact-specific strict loader, and returns one common
`artifact_validation/1.0` report. It never executes operators, reruns a task,
evaluates a new control decision, executes `next_action`, or releases outputs.

The original commands remain supported for compatibility:

```bash
geotask validate <task.yaml>
geotask result validate <execution-result.json>
geotask control validate <control-evaluation.json>
```

The Artifact Registry uses the unified command as its canonical
`validation_command` guidance.

## 2. Registered validators

| Artifact ID | File format | Validation implementation |
|---|---|---|
| `geotask.document` | YAML | strict YAML loading, raw document validation, canonicalization, and canonical validation |
| `geotask.execution-result` | JSON | duplicate/non-finite JSON rejection and `GeotaskResult.from_dict()` semantic validation |
| `geotask.control-evaluation` | JSON | duplicate/non-finite JSON rejection and `load_control_evaluation()` semantic validation |
| `geotask.artifact-validation-report` | JSON | duplicate/non-finite JSON rejection, Registry identity checks, report cross-field validation, and `load_artifact_validation_report()` |

Every validation first checks the corresponding installed Schema against the
versioned Schema Bundle Manifest. A failed digest, byte-size, filename, JSON, or
`$id` check makes validation fail closed with `schema_verified: false`.

## 3. CLI examples

Validate a task document:

```bash
geotask artifact validate \
  geotask.document \
  examples/core/uav_arrival_ground_clearance_release.yaml
```

Validate an execution result and emit JSON:

```bash
geotask artifact validate \
  geotask.execution-result \
  execution-result.json \
  --format json
```

Validate a control-evaluation result:

```bash
geotask artifact validate \
  geotask.control-evaluation \
  control-evaluation.json \
  --format json
```

Generate and then validate an Artifact Validation Report:

```bash
geotask artifact validate \
  geotask.execution-result \
  execution-result.json \
  --format json > artifact-validation.json

geotask artifact validate \
  geotask.artifact-validation-report \
  artifact-validation.json \
  --format json
```

The second command validates the report structure and Registry identity. It does
not repeat validation of `execution-result.json`. A structurally valid report may
truthfully contain `valid: false` for its original target and still be a valid
`geotask.artifact-validation-report` artifact.

When JSON validation fails, the command writes the complete report to stdout and
then exits non-zero. Argument errors use `artifact_validate_failed` on stderr and
do not emit a traceback.

## 4. Public Python API

```python
from geotask_core import (
    ARTIFACT_VALIDATION_SCHEMA_ID,
    ARTIFACT_VALIDATION_SCHEMA_VERSION,
    ARTIFACT_VALIDATION_REPORT_VERSION,
    ArtifactValidationFormatError,
    ArtifactValidationReport,
    load_artifact_validation_report,
    validate_artifact_payload,
    validate_artifact_file,
)

report = validate_artifact_file(
    "geotask.execution-result",
    "execution-result.json",
)

payload_report = validate_artifact_payload(
    "geotask.execution-result",
    execution_result_payload,
    file="execution-result.json",
)

loaded_report = load_artifact_validation_report(payload_report.to_dict())
```

`load_artifact_validation_report()` performs strict report loading without
revalidating the report's original target file. It raises
`ArtifactValidationFormatError` for Registry identity mismatches, unknown fields,
non-scalar summary values, invalid diagnostic shapes, or inconsistent
`valid`/`schema_verified`/severity combinations.

The same names are exported from `geotask_core.v1`.

Unknown Artifact IDs raise `KeyError`. Payload and file-format failures are
returned as invalid reports so callers can consume diagnostics uniformly.

## 5. Report envelope

```json
{
  "artifact_validation": {
    "report_version": "1.0",
    "valid": true,
    "artifact_id": "geotask.execution-result",
    "artifact_kind": "execution_result",
    "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-result-v1.0.schema.json",
    "schema_version": "1.0",
    "schema_verified": true,
    "file": "execution-result.json",
    "summary": {
      "task_id": "gt19-uav-arrival-ground-clearance-release",
      "check_count": 4
    },
    "diagnostics": []
  }
}
```

Required fields under `artifact_validation` are:

- `report_version`: currently `1.0`;
- `valid`: overall payload validity;
- `artifact_id` and `artifact_kind`: Registry identity;
- `schema_id` and `schema_version`: registered Schema metadata;
- `schema_verified`: whether the installed Schema passed Bundle integrity checks;
- `file`: source label or path;
- `summary`: artifact-specific counts and identifiers;
- `diagnostics`: normalized validation findings.

Each diagnostic contains:

```json
{
  "code": "invalid_artifact_file",
  "path": "",
  "message": "invalid JSON ...",
  "severity": "error",
  "suggested_fix": "Provide a readable artifact file ..."
}
```

Warnings remain in `diagnostics` but do not make a document invalid. Execution
results and control-evaluation results currently use strict error-only loaders.

## 6. Artifact-specific summaries

Task-document summaries include document name, object/operator/assertion/task
counts, and warning/error counts.

Execution-result summaries include `task_id` and `check_count`.

Control-evaluation summaries include `task_id` and `evaluation_count`.

Artifact Validation Report summaries include `validated_artifact_id`,
`validated_artifact_valid`, and `diagnostic_count`. These describe the inner
report without copying its diagnostics into the outer validation result.

## 7. Security and execution boundary

Unified Artifact validation is intentionally non-executing:

- it does not call the deterministic executor;
- it does not invoke Runtime or Domain Packs;
- it does not reevaluate control expressions;
- it does not execute `next_action`;
- it does not release blocked outputs;
- it does not access the network.

The command validates only the supplied serialized artifact and the installed
public Schema Bundle.
