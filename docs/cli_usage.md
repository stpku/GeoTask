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

`run` validates the file and executes deterministic Core operators.

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

