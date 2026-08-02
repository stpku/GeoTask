# GeoTask Artifact Registry v1.0

Status: implemented public registry  
Registry version: `1.0`  
JSON Schema: [`schemas/geotask-artifact-registry-v1.0.schema.json`](../../schemas/geotask-artifact-registry-v1.0.schema.json)

## 1. Purpose

GeoTask publishes several machine-readable artifacts with different producers,
wrappers, JSON Schemas, and validation commands. The Artifact Registry provides
one stable public discovery surface for those contracts.

The registry currently contains exactly eighteen artifacts:

1. GeoTask Document v1.0;
2. GeoTask Observation v0.1;
3. GeoTask World State v0.1;
4. GeoTask State Transition v0.1;
5. GeoTask Verification Session v0.1;
6. GeoTask Discrepancy Report v0.1;
7. GeoTask Correction Request v0.1;
8. GeoTask Execution Result v1.0;
9. GeoTask Control Evaluation Result v1.0;
10. GeoTask Agent Generation Preparation Report v0.1;
11. GeoTask Agent Revision Verification Report v0.1;
12. GeoTask Agent Revision Retry Report v0.1;
13. GeoTask Agent Evidence Recovery Report v0.1;
14. GeoTask Runtime Descriptor v0.1;
15. GeoTask Runtime Request v0.1;
16. GeoTask Runtime Response v0.1;
17. GeoTask Core Benchmark Report v0.1;
18. GeoTask Artifact Validation Report v1.0.

The world-model input contract uses `geotask.observation`; it records structured claims but does not verify truth or automatically update a World State. The snapshot contract uses `geotask.world-state`; it validates one explicit state snapshot but does not merge observations or materialize a later state. The transition contract uses `geotask.state-transition`; it binds two snapshot fingerprints and records explicit changes but does not calculate a diff, apply changes, verify truth, or authorize action. The audit-snapshot contract uses `geotask.verification-session`; it binds one World State to exact serialized artifacts plus eligibility and recheck records, but does not validate linked artifact semantics or execute the declared work. The discrepancy contract uses `geotask.discrepancy-report`; it records explicit expected/observed differences, declared impact, and bounded correction scope, but does not compare sources, propagate impact, apply correction, or authorize action. The correction contract uses `geotask.correction-request`; it binds an immutable base state and exact discrepancy reports, constrains successor-state changes and acceptance criteria, and keeps outputs/actions gated without applying changes or materializing the successor.

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
checks the Registry Schema plus all eighteen registered Artifact Schemas; exact
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
    OBSERVATION_SCHEMA_ID,
    OBSERVATION_SCHEMA_VERSION,
    load_observation,
    WORLD_STATE_SCHEMA_ID,
    WORLD_STATE_SCHEMA_VERSION,
    load_world_state,
    STATE_TRANSITION_SCHEMA_ID,
    STATE_TRANSITION_SCHEMA_VERSION,
    load_state_transition,
    validate_state_transition_bindings,
    VERIFICATION_SESSION_SCHEMA_ID,
    VERIFICATION_SESSION_SCHEMA_VERSION,
    load_verification_session,
    validate_verification_session_bindings,
    DISCREPANCY_REPORT_SCHEMA_ID,
    DISCREPANCY_REPORT_SCHEMA_VERSION,
    load_discrepancy_report,
    validate_discrepancy_report_bindings,
    CORRECTION_REQUEST_SCHEMA_ID,
    CORRECTION_REQUEST_SCHEMA_VERSION,
    load_correction_request,
    validate_correction_request_bindings,
    ARTIFACT_VALIDATION_SCHEMA_ID,
    ARTIFACT_VALIDATION_SCHEMA_VERSION,
    AGENT_GENERATION_PREPARATION_SCHEMA_ID,
    AGENT_GENERATION_PREPARATION_SCHEMA_VERSION,
    AGENT_REVISION_VERIFICATION_SCHEMA_ID,
    AGENT_REVISION_VERIFICATION_SCHEMA_VERSION,
    AGENT_REVISION_RETRY_SCHEMA_ID,
    AGENT_REVISION_RETRY_SCHEMA_VERSION,
    AGENT_EVIDENCE_RECOVERY_SCHEMA_ID,
    AGENT_EVIDENCE_RECOVERY_SCHEMA_VERSION,
    RUNTIME_DESCRIPTOR_SCHEMA_ID,
    RUNTIME_DESCRIPTOR_SCHEMA_VERSION,
    RUNTIME_REQUEST_SCHEMA_ID,
    RUNTIME_REQUEST_SCHEMA_VERSION,
    RUNTIME_RESPONSE_SCHEMA_ID,
    RUNTIME_RESPONSE_SCHEMA_VERSION,
    RuntimeInterfaceFormatError,
    load_runtime_descriptor,
    load_runtime_request,
    load_runtime_response,
    AgentArtifactFormatError,
    load_agent_generation_preparation_report,
    load_agent_revision_verification_report,
    load_agent_revision_retry_report,
    load_agent_evidence_recovery_report,
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

The wheel and source distribution include all nineteen public JSON Schemas needed to
interpret the Registry and its eighteen registered Artifacts. Callers can load them
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
    "artifact_count": 18,
    "artifacts": [
      {
        "artifact_id": "geotask.document",
        "title": "GeoTask Document v1.0",
        "kind": "task_document",
        "schema_id": "https://github.com/stpku/GeoTask/schemas/geotask-v1.0.schema.json",
        "schema_version": "1.0",
        "schema_path": "schemas/geotask-v1.0.schema.json",
        "specification_path": "docs/spec/geotask-language-spec-v1.0.md",
        "ide_file_patterns": ["*.geotask.yaml", "*.geotask.yml", "examples/core/**/*.yaml", "examples/core/**/*.yml"],
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

The complete payload contains all eighteen descriptors in stable display order.

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
| `ide_file_patterns` | Portable glob patterns for IDE Schema association |
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

### 6.4 Agent Generation Preparation Report

```text
Artifact ID: geotask.agent-generation-preparation
Schema: schemas/geotask-agent-generation-preparation-v0.1.schema.json
Version: 0.1
Wrapper: agent_generation_preparation
Generation:
  geotask agent prepare <generated.yaml> --output <preparation-report.json>
Validation:
  geotask artifact validate geotask.agent-generation-preparation
    <preparation-report.json>
```

A structurally valid report may record `state=blocked`. Artifact validation checks
the serialized trace and its cross-field invariants without preparing or executing
the embedded document.

### 6.5 Agent Revision Verification Report

```text
Artifact ID: geotask.agent-revision-verification
Schema: schemas/geotask-agent-revision-verification-v0.1.schema.json
Version: 0.1
Wrapper: agent_revision_verification
Generation:
  geotask agent retry <blocked-report.json> <revised.yaml>
    --verification-output <revision-verification.json>
Validation:
  geotask artifact validate geotask.agent-revision-verification
    <revision-verification.json>
```

A structurally valid report may record `state=rejected`. Validation does not repeat
the changed-path comparison and never executes a task.

### 6.6 Agent Revision Retry Report

```text
Artifact ID: geotask.agent-revision-retry
Schema: schemas/geotask-agent-revision-retry-v0.1.schema.json
Version: 0.1
Wrapper: agent_revision_retry
Generation:
  geotask agent retry <blocked-report.json> <revised.yaml>
    --output <retry-report.json>
Validation:
  geotask artifact validate geotask.agent-revision-retry <retry-report.json>
```

The report composes a revision-verification report with an optional preparation
report. A valid Artifact may record `accepted`, `rejected`, or `blocked`; validation
does not repeat revision verification, preparation, or deterministic execution.

### 6.7 Agent Evidence Recovery Report

```text
Artifact ID: geotask.agent-evidence-recovery
Schema: schemas/geotask-agent-integration-v0.1.schema.json
Version: 0.1
Wrapper: agent_integration
Generation:
  geotask agent recover <task.yaml> --evidence <state.yaml>
    --output <recovery-report.json>
Validation:
  geotask artifact validate geotask.agent-evidence-recovery
    <recovery-report.json>
```

The report contains the initial execution and control evaluation, the supplied
evidence completeness decision, the resume control evaluation, and—only after all
checks pass—the resumed execution and final control evaluation. A structurally
valid Artifact may record `state=blocked`; validation does not reacquire evidence,
repeat recovery, execute `next_action`, or release outputs.

### 6.8 Runtime Descriptor

```text
Artifact ID: geotask.runtime-descriptor
Schema: schemas/geotask-runtime-descriptor-v0.1.schema.json
Version: 0.1
Wrapper: runtime_descriptor
Generation:
  geotask runtime inspect --format json
Validation:
  geotask artifact validate geotask.runtime-descriptor <runtime-descriptor.json>
```

The descriptor advertises Runtime identity, operations, input/output Artifact
contracts, authorization requirements, side-effect classes, and audit capability.
Validation never connects to or invokes the described Runtime.

### 6.9 Runtime Request

```text
Artifact ID: geotask.runtime-request
Schema: schemas/geotask-runtime-request-v0.1.schema.json
Version: 0.1
Wrapper: runtime_request
Generation: caller-authored after descriptor inspection
Validation:
  geotask artifact validate geotask.runtime-request <runtime-request.json>
```

The request contains registered input Artifacts, an explicit expected-output
contract, an idempotency key, and an optional opaque authorization reference.
Validation never submits the request or resolves credentials.

### 6.10 Runtime Response

```text
Artifact ID: geotask.runtime-response
Schema: schemas/geotask-runtime-response-v0.1.schema.json
Version: 0.1
Wrapper: runtime_response
Generation:
  geotask runtime mock <runtime-request.json> --output <runtime-response.json>
Validation:
  geotask artifact validate geotask.runtime-response <runtime-response.json>
```

A valid response may record `accepted`, `completed`, `blocked`, `rejected`, or
`failed`. Strict loading checks output Artifacts, diagnostics, retryability, audit
references, and side-effect declarations without repeating the Runtime operation.

### 6.11 Core Benchmark Report

```text
Artifact ID: geotask.core-benchmark-report
Schema: schemas/geotask-core-benchmark-v0.1.schema.json
Version: 0.1
Wrapper: core_benchmark
Generation:
  geotask benchmark core --format json --output core-benchmark.json
Validation:
  geotask artifact validate geotask.core-benchmark-report <core-benchmark.json>
```

The report records production-Core conformance over fixed fictional cases and local
pipeline timing observations. Validation checks its Schema and cross-field
consistency without rerunning the cases. It performs no model call or network
access, and its timing values are not comparable across different hardware.

### 6.12 Artifact Validation Report

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
- `load_agent_generation_preparation_report()`;
- `load_agent_revision_verification_report()`;
- `load_agent_revision_retry_report()`;
- `load_agent_evidence_recovery_report()`;
- `load_runtime_descriptor()`;
- `load_runtime_request()`;
- `load_runtime_response()`;
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
- stable artifact IDs for the eighteen current entries;
- deterministic registry ordering.

Adding a backward-compatible public artifact may keep registry version `1.0`.
Removing or renaming a field, changing an artifact ID, or changing field
semantics incompatibly requires a new registry version.
