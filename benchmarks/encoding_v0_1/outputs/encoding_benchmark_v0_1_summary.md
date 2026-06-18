# GeoTask Encoding Benchmark v0.1 — Summary

## Per-Case Results

| Case | Encoding | Input Tokens | Output Tokens | Total Tokens | Norm OK | Status | Expected | Match | Score |
|------|----------|-------------|---------------|--------------|--------|--------|----------|-------|-------|
| case_001_distance_intersection | natural_language | 174 | 227 | 401 | OK | verified | verified | PASS | 84.6 |
| case_001_distance_intersection | geotask_yaml | 197 | 72 | 269 | OK | verified | verified | PASS | 86.8 |
| case_001_distance_intersection | compact_dsl | 79 | 13 | 92 | OK | verified | verified | PASS | 100.0 |
| case_002_wrong_distance | natural_language | 174 | 169 | 343 | OK | contradicted | contradicted | PASS | 75.2 |
| case_002_wrong_distance | geotask_yaml | 197 | 72 | 269 | OK | contradicted | contradicted | PASS | 76.7 |
| case_002_wrong_distance | compact_dsl | 79 | 11 | 90 | OK | contradicted | contradicted | PASS | 90.0 |
| case_003_not_intersect | natural_language | 174 | 365 | 539 | OK | contradicted | contradicted | PASS | 73.4 |
| case_003_not_intersect | geotask_yaml | 197 | 72 | 269 | OK | contradicted | contradicted | PASS | 76.8 |
| case_003_not_intersect | compact_dsl | 79 | 13 | 92 | OK | contradicted | contradicted | PASS | 90.0 |
| case_004_missing_operator | natural_language | 174 | 157 | 331 | OK | verified | verified | PASS | 85.3 |
| case_004_missing_operator | geotask_yaml | 197 | 43 | 240 | OK | verified | verified | PASS | 87.3 |
| case_004_missing_operator | compact_dsl | 79 | 9 | 88 | OK | verified | verified | PASS | 100.0 |

## Aggregate by Encoding

| Encoding | Cases | Avg Input Tokens | Avg Output Tokens | Avg Total Tokens | Norm Rate | Status Match | Avg Score | Token Eff |
|----------|-------|-----------------|------------------|-----------------|----------|-------------|-----------|-----------|
| natural_language | 4 | 174 | 230 | 404 | 1.00 | 1.00 | 79.6 | 0.232 |
| geotask_yaml | 4 | 197 | 65 | 262 | 1.00 | 1.00 | 81.9 | 0.347 |
| compact_dsl | 4 | 79 | 12 | 90 | 1.00 | 1.00 | 95.0 | 1.000 |

## Notes

- Model outputs are deterministic simulated outputs for benchmark reproducibility. This benchmark evaluates encoding cost, normalization, and verification behavior, not live LLM quality.
- Token counts are approximate and used only for relative comparison between encoding formats.
