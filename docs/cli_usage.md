# GeoTask Core CLI Usage

GeoTask Core CLI commands operate on public-safe Core YAML documents and local
deterministic operators. They do not call live LLM APIs, publish data, upload
packages, or provide domain-specific approval conclusions.

## Help

```bash
python -m geotask_core.cli --help
```

## Validate

```bash
python -m geotask_core.cli validate examples/geotask_core_lite.yaml
```

`validate` loads a GeoTask YAML file and checks the Core document structure.
Validation failures return a non-zero exit code.

## Run

```bash
python -m geotask_core.cli run examples/geotask_core_lite.yaml
```

Compatibility YAML remains the default. For the canonical v1 result contract, use machine-readable JSON:

```bash
python -m geotask_core.cli run \
  examples/core/uav_arrival_ground_clearance_release.yaml \
  --format v1-json \
  --output execution-result.json
```

`--format v1-json` executes the canonical document and serializes the exact
`GeotaskResult.to_dict()` shape. Its stdout contains JSON only; when `--output`
is supplied, stdout remains empty. `--compact` selects single-line v1 JSON.

Supported formats are:

- `yaml`: the existing compatibility result from `run_geotask()`;
- `v1-json`: the canonical result accepted by `control evaluate --result`.

`--output` may be `-` for stdout but cannot overwrite the input GeoTask file.
Unsupported formats, duplicate options, invalid documents, and write failures
return a non-zero exit code without a traceback.

The complete CLI pipeline is:

```bash
python -m geotask_core.cli run task.yaml \
  --format v1-json \
  --output execution-result.json

python -m geotask_core.cli artifact validate \
  geotask.execution-result execution-result.json \
  --format json > artifact-validation.json

python -m geotask_core.cli artifact validate \
  geotask.artifact-validation-report artifact-validation.json

python -m geotask_core.cli control evaluate task.yaml \
  --result execution-result.json \
  --state control-state.yaml \
  --output control-evaluation.json

python -m geotask_core.cli artifact validate \
  geotask.control-evaluation control-evaluation.json
```

## Artifact Validate

```bash
python -m geotask_core.cli artifact validate \
  geotask.document task.yaml

python -m geotask_core.cli artifact validate \
  geotask.execution-result execution-result.json \
  --format json

python -m geotask_core.cli artifact validate \
  geotask.control-evaluation control-evaluation.json \
  --format json

python -m geotask_core.cli artifact validate \
  geotask.artifact-validation-report artifact-validation.json \
  --format json
```

`artifact validate` is the canonical Registry-driven validation entry point. It
resolves the stable Artifact ID, verifies the installed Schema Bundle, then
reuses the artifact-specific strict semantic validator. All JSON reports use the
same `artifact_validation/1.0` envelope with Artifact and Schema identity,
`schema_verified`, source file, artifact-specific summary, and normalized
diagnostics.

JSON mode always emits a parseable report before returning non-zero for invalid
input. Text mode prints a compact success report or writes diagnostics to stderr.
The command never executes operators, reruns a task, reevaluates control
conditions, executes `next_action`, or releases outputs. When the selected
Artifact ID is `geotask.artifact-validation-report`, the command validates the
report envelope, Registry identity, scalar summary, diagnostics, and cross-field
invariants without repeating validation of the report's original target.

The original `validate`, `result validate`, and `control validate` commands remain
available for compatibility. The public Artifact Registry advertises
`artifact validate` as the canonical `validation_command`.

## Result Validate

```bash
python -m geotask_core.cli result validate execution-result.json
python -m geotask_core.cli result validate execution-result.json --format json
```

`result validate` checks the canonical `geotask_result` v1.0 contract without
executing the GeoTask document. Text mode prints a compact valid report or writes
invalid-result diagnostics to stderr. JSON mode always emits a parseable
`result_validation` report and uses a non-zero exit code for invalid input.

The validator checks required and unknown fields, schema version, field types,
public status and assurance enums, non-negative summary counts, and the Core
cross-field invariant `summary.total_checks == len(checks)`. It also rejects
malformed JSON, duplicate keys, and non-finite numbers.

The public structural contract is available at
`schemas/geotask-result-v1.0.schema.json`. Third-party tools may validate it
without importing GeoTask Python code; the CLI additionally enforces the
cross-field check-count invariant that JSON Schema Draft 2020-12 cannot express.

## Explain

```bash
python -m geotask_core.cli explain examples/geotask_core_lite.yaml
```

`explain` shows how requested document operators resolve to registry metadata,
including input shape, output type, deterministic status, and supported
geometry.

## Inspect

```bash
python -m geotask_core.cli inspect operators
python -m geotask_core.cli inspect operators distance_2d
python -m geotask_core.cli inspect schema
python -m geotask_core.cli inspect schemas
python -m geotask_core.cli inspect schemas --format json
python -m geotask_core.cli inspect schemas --verify --format json
python -m geotask_core.cli inspect schemas geotask.execution-result --format json
python -m geotask_core.cli inspect schemas geotask.execution-result --verify --format json
python -m geotask_core.cli inspect schemas geotask.artifact-validation-report --format json
python -m geotask_core.cli schema export geotask.execution-result
python -m geotask_core.cli schema export geotask.execution-result --output geotask-result.schema.json
python -m geotask_core.cli schema export geotask.artifact-validation-report --output artifact-validation.schema.json
python -m geotask_core.cli schema verify
python -m geotask_core.cli schema verify geotask.execution-result --format json
python -m geotask_core.cli inspect examples
```

- `inspect operators` lists public-safe Core operator registry metadata.
- `inspect schema` summarizes the minimal GeoTask document structure.
- `inspect schemas` lists the public Artifact Registry: the GeoTask document,
  execution result, control evaluation, four Agent reports, three Runtime
  interface messages, and Artifact Validation Report. Each entry includes Schema
  identity, repository paths, generation guidance, validation commands, and
  execution boundaries. YAML is the default; `--format json` emits clean
  machine-readable JSON. Supplying one stable Artifact ID returns a one-entry
  registry envelope; unknown IDs fail explicitly. `--verify` appends a sibling
  `schema_bundle_verification` report. With no Artifact ID it verifies the Registry
  Schema and all thirteen Artifact Schemas; with an Artifact ID it verifies only that
  Artifact's Schema. Without `--verify`, the Artifact Registry v1.0 envelope remains
  structurally compatible.
- `schema export <artifact-id>` writes the installed JSON Schema for one
  registered artifact. Output is formatted JSON on stdout by default;
  `--output <file>` saves it without status text, and `--compact` emits one-line
  JSON for pipelines. The command uses the wheel's offline Schema Bundle and
  never fetches a remote URL. Every load verifies the bundled file against its
  generated manifest before returning JSON.
- `schema verify` checks the versioned Bundle Manifest, expected filenames,
  byte sizes, SHA-256 digests, JSON parsing, and published Schema `$id` values.
  With no Artifact ID it checks all fourteen bundled Schemas; supplying one stable
  Artifact ID checks only that artifact. Text is the default and `--format json`
  emits a machine-readable report with stable non-zero failure behavior.
- `inspect examples` lists repository examples and marks public-safe Core
  examples separately from domain-pack examples.

## Report

```bash
python -m geotask_core.cli report examples/geotask_core_lite.yaml --format json
python -m geotask_core.cli report examples/geotask_core_lite.yaml --format markdown
```

`report` validates and runs a GeoTask file, then emits a compact deterministic
result report. Supported formats are `json` and `markdown`; unsupported formats
return `unsupported_report_format` with a non-zero exit code.

## Control Evaluate

```bash
python -m geotask_core.cli control evaluate \
  examples/core/uav_arrival_ground_clearance_release.yaml \
  --result execution-result.json \
  --state control-state.yaml
```

`control evaluate` is a read-only command for documents that declare
`geotask.control/1.0`. It requires a canonical execution-result JSON file
produced by `GeotaskResult.to_dict()`. An optional state file may be JSON or
YAML and supplies explicit finite scalar domain values used by the control
expressions.

The command writes schema-compatible Control Evaluation Result JSON to stdout.
Use `--output <file.json>` to write the payload to a file without adding status
text to stdout, and use `--compact` for single-line JSON.

```bash
python -m geotask_core.cli control evaluate \
  examples/core/uav_arrival_ground_clearance_release.yaml \
  --result execution-result.json \
  --state control-state.json \
  --output control-evaluation.json \
  --compact
```

The result reports `blocked_outputs`, `eligible_outputs`, unknown identifiers,
and provenance. `eligible_outputs` means only that the evaluated conditions are
currently satisfied. The command never executes `next_action`, changes the
execution result, authorizes an operation, or releases an output. Every result
therefore keeps `action_executed: false`.

The execution result must belong to the same GeoTask document: its `task_id`
must match the document ID, and every serialized check must reference an
assertion declared by that document. Malformed, legacy-shaped, cross-task, or
partially shaped result files fail with a non-zero exit code and no traceback.
Duplicate JSON or YAML keys and non-finite JSON numbers are also rejected.
`--output` cannot overwrite the GeoTask, execution-result, or state input file.

## Control Validate

```bash
python -m geotask_core.cli control validate control-evaluation.json
python -m geotask_core.cli control validate control-evaluation.json --format json
```

`control validate` strictly loads a serialized Control Evaluation Result v1.0.
It checks the public JSON shape plus Core invariants including immutable context
entry/value consistency, control-block state derivation, aggregate unknown and
output lists, `gate_satisfied`, and the required `action_executed: false` value.

Text mode prints a compact valid report or writes invalid diagnostics to stderr.
JSON mode always emits a parseable `control_validation` report and returns a
non-zero exit code for invalid data. The command does not evaluate expressions,
rerun a GeoTask, execute `next_action`, or release outputs.

`result validate` and `control validate` share the same versioned payload
validation framework for argument handling, schema metadata, diagnostics, and
text/JSON reports. Their strict loaders remain artifact-specific.

## Agent Integration Preview

Discover the model-neutral Agent tool contract:

```bash
python -m geotask_core.cli agent inspect --format json
```

The profile exposes `inspect_artifacts`, `validate_artifact`, `execute_task`, and
`evaluate_control`. It also declares mandatory rules: unknown is not a boolean,
blocked outputs remain blocked, recovered assertions are recomputed, and
`next_action` is never executed by Core.

Prepare an Agent-generated draft before trusting or executing it:

```bash
python -m geotask_core.cli agent prepare \
  examples/core/agent_generated_distance_draft.yaml \
  --repaired-output prepared.yaml \
  --output preparation-report.json
```

`agent prepare` runs strict validation, applies only mechanical protocol repairs,
revalidates, and then executes with `local_only`. It may add Schema metadata,
stable task/assertion IDs, `operator_set`, local execution defaults, and a
fail-closed output contract. It never changes coordinates, chooses an operator,
infers `object_refs`, invents evidence, or runs a non-local mode.

A `valid` or `repaired` report exits successfully. A `blocked` report is still
written as JSON but exits with code `2`, and `--repaired-output` is not created.
Its `revision_request.required_changes` lists unresolved paths, action types, and
safe candidate inventories. Candidate values are never selected automatically.
Use the returned `prepared_document` as the revision base, preserve the blocked
report, and submit the revision through the changed-path gate:

```bash
geotask agent prepare examples/core/agent_generated_distance_blocked.yaml \
  --output blocked-preparation.json
# Agent revises only after selecting explicit semantics.
geotask agent retry \
  blocked-preparation.json \
  examples/core/agent_generated_distance_revised.yaml \
  --verification-output revision-verification.json \
  --prepared-output prepared.yaml \
  --output retry-report.json
```

`agent retry` reconstructs the revision request, verifies the base SHA-256, and
rejects changes outside requested paths before validation or execution. A revised
operator may update `operator_set`, but the inventory must exactly match operators
used by revised assertions. Coordinate, evidence, metadata, goal, control-policy,
and task-order changes are rejected unless explicitly requested. Rejection exits
with code `2`, writes a machine-readable report, and never creates
`--prepared-output`.

The preparation, revision-verification, and retry traces are registered public
Artifacts backed by offline Schemas. Validate retained reports without repeating
the workflow:

```bash
geotask artifact validate geotask.agent-generation-preparation blocked-preparation.json --format json
geotask artifact validate geotask.agent-revision-verification revision-verification.json --format json
geotask artifact validate geotask.agent-revision-retry retry-report.json --format json
geotask artifact validate geotask.agent-evidence-recovery recovery-report.json --format json
```

Artifact validity is structural: a valid report may record `blocked` or `rejected`.
Use `--compact` for one-line JSON and `--format text` for a concise summary.

Run the GT08 end-to-end recovery demo:

```bash
python -m geotask_core.cli agent recover \
  examples/core/evidence_request_plan.yaml \
  --evidence examples/core/evidence_request_verified_state.yaml \
  --output recovery-report.json
```

`agent recover` first executes the unchanged document and preserves the trigger
assertion as `unverifiable`. It then verifies every declared required evidence
field, evaluates `resume_when`, materializes only the trigger's single named
condition to literal `true` in an in-memory copy, reruns the task, and evaluates
the final control state.

The command defaults to structured JSON. `--compact` emits one-line JSON,
`--format text` prints a concise summary, and `--output <file.json>` writes JSON
without status text. A complete but unsatisfied or incomplete evidence state is
an expected `blocked` report and exits successfully; malformed contracts and
unsupported condition shapes fail non-zero. The command never mutates the input
GeoTask, calls a model, executes `next_action`, or releases an output.

The output is the registered `geotask.agent-evidence-recovery` Artifact backed by
`geotask-agent-integration-v0.1.schema.json`. Validating that file is read-only and
does not reacquire evidence or repeat recovery. A structurally valid file may still
record `state=blocked`.

## Core Benchmark

Run the public offline conformance and local performance-regression gate:

```bash
geotask benchmark core \
  --iterations 30 \
  --warmup 3 \
  --max-p95-ms 100 \
  --enforce-performance \
  --format json \
  --output core-benchmark.json
```

The five fixed fictional cases cover all eight public deterministic operators,
strict Result round trips, replay semantic hashes, and Provenance evidence refs.
Timing covers JSON decoding, Canonical construction, validation, production
execution, and Result serialization. `--enforce-performance` makes a failed p95
guardrail return exit code `2`; without it, the timing result remains observational.
The guardrail is for controlled local regression checks only and does not support
cross-hardware rankings or production latency claims.

Validate a retained report without rerunning the benchmark:

```bash
geotask artifact validate \
  geotask.core-benchmark-report \
  core-benchmark.json \
  --format json
```

## Runtime Interface

Inspect the public fail-closed reference Runtime or the machine-readable interface
profile:

```bash
geotask runtime inspect
geotask runtime inspect --format json > runtime-descriptor.json
geotask runtime inspect --profile --format json > runtime-profile.json
geotask runtime inspect \
  examples/core/runtime_reference_descriptor.json \
  --format json
```

Validate the Runtime Descriptor and example Request without connecting to a
Runtime, then check that the Request matches the Descriptor contract:

```bash
geotask artifact validate \
  geotask.runtime-descriptor \
  examples/core/runtime_reference_descriptor.json \
  --format json

geotask artifact validate \
  geotask.runtime-request \
  examples/core/runtime_validate_artifact_request.json \
  --format json

geotask runtime check \
  examples/core/runtime_reference_descriptor.json \
  examples/core/runtime_validate_artifact_request.json \
  --format json
```

`runtime check` reports `submitted=false` and `side_effects_executed=false`. It
compares Runtime ID, operation, input Artifact inventory, expected outputs, and
authorization requirements without invoking the adapter.

Submit the example to the public reference adapter:

```bash
geotask runtime mock \
  examples/core/runtime_validate_artifact_request.json \
  --output runtime-response.json \
  --compact

geotask artifact validate \
  geotask.runtime-response runtime-response.json --format json
```

The reference Runtime performs only the existing read-only Artifact validation
operation. It never calls a model, resolves external evidence, accesses connector
credentials, or executes a production action. Unsupported operations return a
structured `rejected` response with `side_effects_executed=false` and CLI exit code
`2`. Malformed messages and invalid CLI arguments return exit code `1`.

After any adapter returns, `submit_runtime_request()` applies the three-way exchange
contract across the inspected Descriptor, submitted Request, and returned Response.
It rejects missing or unexpected completed outputs, asynchronous acceptance from a
synchronous operation, side-effect claims that contradict the Descriptor, audit
references from a Runtime that declared no audit support, and any non-rejected
response to a Request that violated the advertised operation contract.

For a real external transport example, see
[`examples/adapters/http_json_runtime_adapter.py`](../examples/adapters/http_json_runtime_adapter.py).
It keeps `describe()` offline, performs one explicit HTTP JSON POST, rejects redirects,
embedded URL credentials, duplicate keys, non-finite JSON, non-JSON and oversized
responses, and leaves authentication, retries, model calls, evidence access, and
production actions outside `geotask_core`. HTTP failures remain transport errors
rather than being converted into Runtime states.

The paired loopback-only Endpoint can be started separately:

```bash
python examples/endpoints/reference_runtime_http_server.py
```

It accepts only `POST /runtime`. Malformed transport input returns non-2xx Problem
JSON, while a valid Request Artifact refused by the Runtime returns HTTP `200` with
a contract-valid `rejected` Runtime Response. It does not expose online Descriptor
discovery, credentials, remote binding, hosted models, external evidence, or actions.

The independently buildable provider-neutral model Adapter skeleton is under
[`examples/model_adapters/provider_neutral/`](../examples/model_adapters/provider_neutral/).
Its Mock Provider performs no model call. The Adapter maps `execute-nonlocal`, validates
registered input/output Artifacts, and rejects model output that claims deterministic
or independently verified assurance.

The first provider-specific package is under
[`examples/model_adapters/openai_responses/`](../examples/model_adapters/openai_responses/).
Private startup code supplies an authenticated official SDK client by opaque authorization
reference. The package performs one no-retry Responses API call with strict Structured
Outputs, disabled storage, no tools or conversation state, and audit-bound failure handling.
Repository tests use a fake SDK-shaped client and perform no live call.

The three registered Runtime Artifacts are:

- `geotask.runtime-descriptor`;
- `geotask.runtime-request`;
- `geotask.runtime-response`.

Validating these files never invokes a Runtime or repeats an external side effect.
The full contract is defined in
[`geotask-runtime-interface-profile-v0.1.md`](spec/geotask-runtime-interface-profile-v0.1.md).

## Normalize And Eval

```bash
python -m geotask_core.cli normalize examples/deepseek_output_sample.txt
python -m geotask_core.cli eval examples/geotask_core_lite.yaml examples/deepseek_output_sample.txt
```

These older commands remain available for compatibility with the existing
normalizer and evaluation tests.

## Boundary

The CLI is a developer tool for Core validation, deterministic execution,
inspection, and reporting. Domain-specific extensions should remain in domain
packs, and patent-sensitive or non-public material should not be copied into
Core CLI output or public-safe docs.
