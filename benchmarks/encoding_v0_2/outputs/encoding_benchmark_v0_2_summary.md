# GeoTask Encoding Benchmark v0.2 — Summary

> Deterministic simulated benchmark. Does not claim live LLM accuracy.

## Aggregate by Encoding

| Encoding | Cases | Avg In Tok | Avg Out Tok | Avg Tot Tok | Norm Rate | Status Match | Score |
|----------|-------|-----------|------------|------------|-----------|-------------|-------|
| natural_language | 24 | 59 | 10 | 69 | 1.00 | 0.96 | 83.0 |
| geotask_yaml | 24 | 90 | 38 | 128 | 1.00 | 1.00 | 79.2 |
| compact_dsl | 24 | 46 | 6 | 51 | 1.00 | 1.00 | 91.2 |

## Token Reduction

- geotask_yaml vs NL: -85.7% reduction, 0.5x compression
- compact_dsl vs NL: 25.5% reduction, 1.3x compression

## Notes
- Model outputs are deterministic simulated outputs.
- Token counts approximate, relative comparison only.