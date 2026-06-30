# Foundation Upgrade v0.2 Final Test Report

Date: 2026-06-30

## Test Counts

- Original target baseline: `476/476 passed`.
- Repaired baseline before feature loops: `476 passed`.
- Final test count: `509 passed`.
- New tests added: `33`.

## Pytest

Final command:

```bash
pytest
```

Result:

```text
509 passed
```

## CLI Smoke

Passed:

- `python -m geotask_core.cli validate examples/geotask_core_lite.yaml`
- `python -m geotask_core.cli run examples/geotask_core_lite.yaml`
- `python -m geotask_core.cli inspect operators`
- `python -m geotask_core.cli inspect schema`
- `python -m geotask_core.cli inspect examples`
- `python -m geotask_core.cli report examples/core/minimal_valid.yaml --format json`
- `python -m geotask_core.cli report examples/core/minimal_valid.yaml --format markdown`
- `python -m geotask_core.cli validate examples/core/time_altitude_overlap.yaml`
- `python -m geotask_core.cli inspect schema`
- `python -m geotask_runtime.mock_runtime examples/geotask_core_lite.yaml`

## Benchmark Smoke

Passed with exit code 0:

- `python benchmarks/encoding_v0_1/run_benchmark.py`
- `python benchmarks/encoding_v0_2/run_benchmark.py`

Benchmark v0.2 still reports its existing simulated natural-language case 022
status mismatch in command output. The benchmark exits successfully and reports
aggregate status match of `0.96` for natural language and `1.00` for both
structured encodings.

## Docs Updated

- `docs/operator_registry.md`
- `docs/cli_usage.md`
- `docs/geotask_yaml_schema.md`
- `docs/encoding_benchmark_v0_2.md`
- `docs/reports/foundation_upgrade_v0_2/*`

## Examples Added

- `examples/core/minimal_valid.yaml`
- `examples/core/time_altitude_overlap.yaml`
- `examples/core/assertions_expected_results.yaml`
- `examples/README.md`

## Public-Safe Boundary

- P2/P5 touched: no.
- Patent evidence modified: no.
- LowAlt industry rules expanded: no.
- Push performed: no.
- Release/package upload performed: no.

## Known Remaining Issues

- Parser diagnostics now cover interval issues, unknown fields, and unsupported
  operators, invalid references, and minimal expected result section semantics,
  but are not yet broadened across duplicate ids and deeper task/assertion
  semantics.
- CLI `--debug` traceback behavior is not yet implemented.
- Domain pack interface genericization remains a future loop.
