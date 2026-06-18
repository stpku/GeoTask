# Test Snapshot

Generated for patent evidence archival.

## Test Summary

| Metric | Value |
|--------|-------|
| Total test modules | 8 |
| Total test functions | 113 |
| All tests passing | ✅ Yes |

## Test Modules

| Module | Tests | Description |
|--------|-------|-------------|
| `test_ops.py` | ~20 | Deterministic operator correctness |
| `test_parser.py` | ~15 | YAML parsing and validation |
| `test_runner.py` | ~10 | Auto-detection runner |
| `test_normalizer.py` | ~5 | Normalizer v0.1 extraction |
| `test_normalizer_v0_2.py` | 10 | Normalizer v0.2 + verification |
| `test_verifier.py` | 11 | Verifier status assignment |
| `test_evaluator.py` | ~3 | Eval scoring |
| `test_encoding_benchmark.py` | New | Encoding benchmark tests (added in this branch) |

## Key Test Coverage

- ✅ Distance calculation correctness
- ✅ Intersection detection correctness
- ✅ YAML parsing with validation errors
- ✅ Chinese + English text extraction
- ✅ Contradiction detection (wrong distance, wrong boolean)
- ✅ Missing operator detection
- ✅ Normalization without verification (backward compat)
- ✅ Verification status: verified / contradicted / need_review
- ✅ Overall status derivation

## Test Command

```bash
pytest
```
