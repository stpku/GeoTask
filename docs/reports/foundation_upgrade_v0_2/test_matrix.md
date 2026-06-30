# Foundation Upgrade v0.2 Test Matrix

## Baseline

| Command | Result | Notes |
|---|---:|---|
| `pytest` | Failed | Initial collection error: `benchmarks` import unavailable from v0.1 benchmark test. |
| `pytest` | Failed | After import fix: `475 passed`, one docs boundary assertion failed. |
| `pytest tests/test_benchmark_v0_2_evidence_addendum.py::test_docs_benchmark_has_local_verifier_boundary` | Passed | Confirms restored local verifier boundary wording. |
| `pytest` | Passed | `476 passed` after baseline repairs. |

## Pending Final Smoke

- `python -m geotask_core.cli validate examples/geotask_core_lite.yaml`
- `python -m geotask_core.cli run examples/geotask_core_lite.yaml`
- `python -m geotask_runtime.mock_runtime examples/geotask_core_lite.yaml`
- `python benchmarks/encoding_v0_1/run_benchmark.py`
- `python benchmarks/encoding_v0_2/run_benchmark.py`

## Loop A

| Command | Result | Notes |
|---|---:|---|
| `pytest tests/test_operator_registry.py tests/test_cli_inspect.py` | Failed | Expected RED: missing registry module and inspect command. |
| `pytest tests/test_operator_registry.py tests/test_cli_inspect.py` | Passed | `7 passed` after registry, CLI, and docs implementation. |
| `python -m geotask_core.cli inspect operators` | Passed | Requires local editable install or equivalent package setup. |
| `python -m geotask_core.cli inspect operators distance_2d` | Passed | Single-operator metadata output works. |

## Loop B

| Command | Result | Notes |
|---|---:|---|
| `pytest tests/test_cli_foundation_commands.py` | Failed | Expected RED: missing CLI explain/report/schema/examples surfaces. |
| `pytest tests/test_cli_foundation_commands.py` | Passed | `8 passed` after CLI implementation and docs. |
| `python -m geotask_core.cli inspect schema` | Passed | Emits minimal public-safe YAML schema summary. |
| `python -m geotask_core.cli inspect examples` | Passed | Lists examples and marks domain-pack examples as not public-safe Core examples. |
| `python -m geotask_core.cli explain examples/geotask_core_lite.yaml` | Passed | Resolves document operators to registry metadata. |
| `python -m geotask_core.cli report examples/geotask_core_lite.yaml --format json` | Passed | Emits parseable JSON report. |
| `python -m geotask_core.cli report examples/geotask_core_lite.yaml --format markdown` | Passed | Emits compact Markdown report. |

## Loop C

| Command | Result | Notes |
|---|---:|---|
| `pytest tests/test_core_examples_v0_2.py` | Failed | Expected RED: parser did not accept generic time/altitude objects and examples/docs were missing. |
| `pytest tests/test_core_examples_v0_2.py` | Passed | `6 passed` after parser, examples, README, and schema docs. |
| `python -m geotask_core.cli validate examples/core/minimal_valid.yaml` | Passed | New public-safe Core example validates. |
| `python -m geotask_core.cli run examples/core/minimal_valid.yaml` | Passed | Computes distance `5.0 meter`. |
| `python -m geotask_core.cli validate examples/core/time_altitude_overlap.yaml` | Passed | Generic time/altitude example validates. |
| `python -m geotask_core.cli run examples/core/time_altitude_overlap.yaml` | Passed | Computes `time_overlap` and `altitude_overlap`. |

## Final Verification

| Command | Result | Notes |
|---|---:|---|
| `pytest` | Passed | `497 passed`. |
| `python -m geotask_core.cli validate examples/geotask_core_lite.yaml` | Passed | Exit 0. |
| `python -m geotask_core.cli run examples/geotask_core_lite.yaml` | Passed | Exit 0. |
| `python -m geotask_runtime.mock_runtime examples/geotask_core_lite.yaml` | Passed | Exit 0, `Overall Status: verified`. |
| `python benchmarks/encoding_v0_1/run_benchmark.py` | Passed | Exit 0, benchmark complete. |
| `python benchmarks/encoding_v0_2/run_benchmark.py` | Passed | Exit 0, benchmark complete; one known simulated natural-language case remains mismatched while aggregate status match remains 0.96 for natural language and 1.00 for structured encodings. |
| `python -m geotask_core.cli inspect operators` | Passed | Exit 0. |
| `python -m geotask_core.cli inspect schema` | Passed | Exit 0. |
| `python -m geotask_core.cli inspect examples` | Passed | Exit 0. |
| `python -m geotask_core.cli report examples/core/minimal_valid.yaml --format json` | Passed | Exit 0. |
| `python -m geotask_core.cli report examples/core/minimal_valid.yaml --format markdown` | Passed | Exit 0. |
