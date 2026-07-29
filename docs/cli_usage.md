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

python -m geotask_core.cli result validate execution-result.json

python -m geotask_core.cli control evaluate task.yaml \
  --result execution-result.json \
  --state control-state.yaml \
  --output control-evaluation.json
```

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
python -m geotask_core.cli inspect examples
```

- `inspect operators` lists public-safe Core operator registry metadata.
- `inspect schema` summarizes the minimal YAML structure.
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
