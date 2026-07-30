# GeoTask Artifact Registry v1.0

Status: implemented public registry  
Registry version: `1.0`  
JSON Schema: [`schemas/geotask-artifact-registry-v1.0.schema.json`](../../schemas/geotask-artifact-registry-v1.0.schema.json)

## 1. Purpose

GeoTask publishes several machine-readable artifacts with different producers,
wrappers, JSON Schemas, and validation commands. The Artifact Registry provides
one stable public discovery surface for those contracts.

The registry currently contains exactly four artifacts:

1. GeoTask Document v1.0;
2. GeoTask Execution Result v1.0;
3. GeoTask Control Evaluation Result v1.0;
4. GeoTask Artifact Validation Report v1.0.

It does not scan the filesystem, discover private modules, or infer unpublished
contracts. New entries require an explicit public contract and compatibility
review.

## 2. CLI discovery

Default YAML output:

```bash
geotask inspect schemas
```

Machine-readable JSON output:

```bash
geotask inspect schemas --format json
```

Exact lookup by stable Artifact ID:

```bash
geotask inspect schemas geotask.execution-result --format json
```

Exact lookup keeps the same versioned registry wrapper and returns
`artifact_count: 1`. Unknown Artifact IDs fail with a non-zero exit code rather
than silently returning an empty registry.

Discovery can include installed Bundle integrity results:

```bash
geotask inspect schemas --verify --format json
geotask inspect schemas geotask.execution-result --verify --format json
```

`--verify` appends a sibling `schema_bundle_verification` object. Full discovery
checks the registry Schema plus all four registered artifact Schemas; exact
lookup checks only the selected artifact Schema. An invalid Bundle still emits
the composite JSON or YAML report and exits non-zero. Without `--verify`, output
remains the original Artifact Registry v1.0 payload and continues to validate
against `geotask-artifact-registry-v1.0.schema.json`.

The existing singular command remains unchanged:

```bash
geotask inspect schema
```

`inspect schema` describes the GeoTask document structure. `inspect schemas`
lists all registered public versioned artifacts.

## 3. Public API

```python
from geotask_core import (
    ARTIFACT_REGISTRY_SCHEMA_ID,
    ARTIFACT_REGISTRY_VERSION,
    GEOTASK_DOCUMENT_SCHEMA_ID,
    GEOTASK_DOCUMENT_SCHEMA_VERSION,
    ARTIFACT_VALIDATION_SCHEMA_ID,
    ARTIFACT_VALIDATION_SCHEMA_VERSION,
    ArtifactDescriptor,
    list_artifact_descriptors,
    get_artifact_descriptor,
    artifact_registry_payload,
    SCHEMA_BUNDLE_VERSION,
    SCHEMA_BUNDLE_MANIFEST_FILENAME,
    BUNDLED_SCHEMA_IDS,
    list_bundled_schema_ids,
    schema_bundle_manifest,
    load_bundled_schema,
    load_artifact_schema,
    verify_schema_bundle,
    ARTIFACT_VALIDATION_REPORT_VERSION,
    ArtifactValidationFormatError,
    ArtifactValidationReport,
    load_artifact_validation_report,
    validate_artifact_payload,
    validate_artifact_file,
)
```

The same names are exported from `geotask_core.v1`.

### 3.1 Installed Schema Bundle

The wheel and source distribution include all five public JSON Schemas needed to
interpret the registry and its four registered artifacts. Callers can load them
without network access:

```python
from geotask_core import (
    ARTIFACT_REGISTRY_SCHEMA_ID,
    load_artifact_schema,
    load_bundled_schema,
)

registry_schema = load_bundled_schema(ARTIFACT_REGISTRY_SCHEMA_ID)
result_schema = load_artifact_schema("geotask.execution-result")
```

`load_bundled_schema()` accepts a published Schema `$id`.
`load_artifact_schema()` resolves the stable Artifact ID through the registry.
Both return a fresh dictionary and verify the installed file against the
versioned Bundle Manifest before parsing it. Verification covers filename,
byte size, SHA-256 digest, JSON shape, and the published `$id`. Unknown
identifiers and integrity failures fail explicitly.

Repository-level files under `schemas/` remain the authoritative source. The
package build mirrors them into `geotask_core.schemas` and generates
`schema-bundle-manifest-v1.0.json` from those exact bytes, avoiding a second
hand-maintained Schema or checksum definition. A repository checkout may compute
an equivalent manifest only when the running module is inside that repository's
`src/geotask_core` layout. An installed package never reconstructs a missing
manifest: missing installed trust metadata fails closed even when individual
Schema files are still present. `schema_bundle_manifest()` exposes the validated
manifest and `verify_schema_bundle()` returns a structured all-Schema or
single-artifact verification report.

### 3.2 CLI Schema export

Installed users can materialize one registered Schema without Python code or
network access:

```bash
geotask schema export geotask.document
geotask schema export geotask.execution-result --compact
geotask schema export geotask.control-evaluation \
  --output control-evaluation.schema.json
geotask schema export geotask.artifact-validation-report \
  --output artifact-validation.schema.json
```

The command accepts exactly one stable Artifact ID. Standard output contains
only JSON, so it can be redirected or piped directly. When `--output` names a
file, the command writes the Schema without informational text. Unknown IDs,
missing values, duplicate options, integrity failures, and file-write failures
return a non-zero exit code without a traceback.

### 3.3 CLI Schema verification

Installed users can verify the full Bundle or one registered artifact:

```bash
geotask schema verify
geotask schema verify geotask.execution-result
geotask schema verify geotask.control-evaluation --format json
```

The default text report prints each verified Schema ID and its SHA-256 digest.
JSON mode emits `schema_bundle_verification` with bundle version, checked count,
per-Schema expected and actual digests, sizes, validity, and diagnostics. Invalid
bundles return a non-zero exit code; JSON mode remains machine-readable on
standard output.

The SHA-256 values establish internal package consistency with the generated
Bundle Manifest. They are not a digital signature or an external publisher
attestation.

### 3.4 Unified Artifact validation

The Registry advertises one canonical validation command shape for every entry:

```bash
geotask artifact validate <artifact-id> <file> [--format text|json]
```

The command verifies the installed Schema Bundle, dispatches to the registered
artifact-specific strict validator, and emits one `artifact_validation/1.0`
report. Original validation commands remain supported for compatibility, but
`validation_command` uses the unified form so Agent and CI clients need only one
command contract. See `geotask-artifact-validation-v1.0.md` for the full report
and non-execution boundary.

## 4. Registry payload

```json
{
  "artifact_registry": {
    "schema_id": "https://stpku.github.io/GeoTask/schemas/geotask-artifact-registry-v1.0.schema.json",
    "registry_version": "1.0",
    "artifact_count": 4,
    "artifacts": [
      {
        "artifact_id": "geotask.document",
        "title": "GeoTask Document v1.0",
        "kind": "task_document",
        "schema_id": "https://github.com/stpku/GeoTask/schemas/geotask-v1.0.schema.json",
        "schema_version": "1.0",
        "schema_path": "schemas/geotask-v1.0.schema.json",
        "specification_path": "docs/spec/geotask-language-spec-v1.0.md",
        "wrapper_key": null,
        "generation_command": null,
        "generation_note": "Authored input. GeoTask Core does not synthesize task documents; public case starters may be created with tools/scaffold_case.py.",
        "validation_command": "geotask artifact validate geotask.document <task.yaml>",
        "description": "Declarative spatial-task input consumed by GeoTask Core validation and deterministic execution.",
        "execution_boundary": "Validation does not execute operators."
      }
    ]
  }
}
```

The complete payload contains all four descriptors in stable display order.

## 5. Descriptor fields

Each `ArtifactDescriptor` contains:

| Field | Meaning |
|---|---|
| `artifact_id` | Stable logical artifact identifier |
| `title` | Human-readable contract title |
| `kind` | Machine-oriented artifact category |
| `schema_id` | Published JSON Schema `$id` |
| `schema_version` | Artifact schema version |
| `schema_path` | Repository-relative Schema file |
| `specification_path` | Repository-relative normative specification |
| `wrapper_key` | Top-level JSON wrapper, or `null` for the task document |
| `generation_command` | CLI producer command, or `null` for authored input |
| `generation_note` | Producer and authorship explanation |
| `validation_command` | Public validation command |
| `description` | Concise semantic description |
| `execution_boundary` | Explicit non-execution or authorization boundary |

## 6. Registered artifacts

### 6.1 GeoTask Document

```text
Artifact ID: geotask.document
Schema: schemas/geotask-v1.0.schema.json
Version: 1.0
Wrapper: none
Generation: authored input
Validation: geotask artifact validate geotask.document <task.yaml>
```

GeoTask Core does not claim to generate task documents. Public case starter
files may be generated by `tools/scaffold_case.py`, but that tool is not a
general semantic task synthesizer.

### 6.2 Execution Result

```text
Artifact ID: geotask.execution-result
Schema: schemas/geotask-result-v1.0.schema.json
Version: 1.0
Wrapper: geotask_result
Generation:
  geotask run <task.yaml> --format v1-json --output <execution-result.json>
Validation:
  geotask artifact validate geotask.execution-result <execution-result.json>
```

Result validation does not rerun the GeoTask.

### 6.3 Control Evaluation Result

```text
Artifact ID: geotask.control-evaluation
Schema: schemas/geotask-control-evaluation-v1.0.schema.json
Version: 1.0
Wrapper: control_evaluation
Generation:
  geotask control evaluate <task.yaml> --result <execution-result.json>
    [--state <state.yaml>] --output <control-evaluation.json>
Validation:
  geotask artifact validate geotask.control-evaluation <control-evaluation.json>
```

Control evaluation and validation never execute `next_action` or release
outputs.

### 6.4 Artifact Validation Report

```text
Artifact ID: geotask.artifact-validation-report
Schema: schemas/geotask-artifact-validation-v1.0.schema.json
Version: 1.0
Wrapper: artifact_validation
Generation:
  geotask artifact validate <artifact-id> <file> --format json
    > <artifact-validation.json>
Validation:
  geotask artifact validate geotask.artifact-validation-report
    <artifact-validation.json>
```

The strict loader checks that the report's target Artifact ID exists and that
its `artifact_kind`, `schema_id`, and `schema_version` exactly match current
Registry metadata. It also enforces the relationship among `valid`,
`schema_verified`, and error diagnostics. Validating a report does not repeat
the original target validation.

## 7. Relationship to validation contracts

The Artifact Registry is a discovery layer. It does not replace:

- GeoTask document validation;
- `GeotaskResult.from_dict()`;
- `load_control_evaluation()`;
- `load_artifact_validation_report()`;
- the Versioned Payload Validation framework;
- artifact-specific JSON Schemas.

Registry metadata points users and tools to those contracts without executing
or validating an artifact itself.

## 8. Stability and versioning

Registry v1.0 guarantees:

- the `artifact_registry` wrapper;
- the self-describing `schema_id`;
- `registry_version` and `artifact_count`;
- the descriptor field set documented above;
- stable artifact IDs for the four current entries;
- deterministic registry ordering.

Adding a backward-compatible public artifact may keep registry version `1.0`.
Removing or renaming a field, changing an artifact ID, or changing field
semantics incompatibly requires a new registry version.
