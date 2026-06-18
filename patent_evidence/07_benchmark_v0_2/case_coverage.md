# GeoTask Encoding Benchmark v0.2 — Case Coverage

> **Full matrix of 24 cases × 3 encodings × 2 directions = 144 files**

## Case-to-Operator Coverage Matrix

| Case ID | Group | Operators | Checks | Expected Status |
|---------|-------|-----------|--------|-----------------|
| `case_001` | basic_correct | `distance_2d` | point-to-point distance = 144.22m | verified |
| `case_002` | basic_correct | `line_intersects_rect` | line intersects rect = true | verified |
| `case_003` | basic_correct | `line_intersects_rect` | line NOT intersect rect = false | verified |
| `case_004` | basic_correct | `rect_contains_point` | rect contains point = true | verified |
| `case_005` | basic_correct | `rect_contains_point` | rect NOT contain point = false | verified |
| `case_006` | basic_correct | `point_to_line_distance_2d` | point-to-line dist = 50.0m | verified |
| `case_007` | basic_correct | `time_overlap` | times overlap = true | verified |
| `case_008` | basic_correct | `time_overlap` | times NOT overlap = false | verified |
| `case_009` | basic_correct | `altitude_overlap` | altitudes overlap = true | verified |
| `case_010` | basic_correct | `altitude_overlap` | altitudes NOT overlap = false | verified |
| `case_011` | contradicted | `distance_2d` | model outputs 120.0, truth is 144.22 | contradicted |
| `case_012` | contradicted | `line_intersects_rect` | model says false, truth is true | contradicted |
| `case_013` | contradicted | `rect_contains_point` | model says true, truth is false | contradicted |
| `case_014` | contradicted | `time_overlap` | model says true, truth is false | contradicted |
| `case_015` | contradicted | `altitude_overlap` | model says true, truth is false | contradicted |
| `case_016` | need_review | `distance_2d` + `line_intersects_rect` | correct values, missing operator refs | verified |
| `case_017` | need_review | `distance_2d` | missing numeric value in output | need_review |
| `case_018` | need_review | `distance_2d` | ambiguous object references | need_review |
| `case_019` | need_review | `distance_2d` | references non-existent "haversine" operator | need_review |
| `case_020` | need_review | `distance_2d` | references non-existent "airport" object | need_review |
| `case_021` | robustness | `distance_2d` | outputs "0.14 km" instead of "144.22 m" | need_review |
| `case_022` | robustness | `line_intersects_rect` | Chinese "不相交" negation ambiguity | verified* |
| `case_023` | robustness | `distance_2d` | Markdown-formatted output extraction | verified |
| `case_024` | robustness | `distance_2d` + `line_intersects_rect` | YAML-like structured output | verified |

*Note: case_022 NL status shows `contradicted` (correctly identifies Chinese negation issue), YAML/DSL show `verified`.

## Operator Coverage Count

| Operator | Correct | Wrong | Edge Cases | Total |
|----------|---------|-------|------------|-------|
| `distance_2d` | 1 | 1 | 3 (NL, missing, unit) | 5 |
| `line_intersects_rect` | 2 (yes+no) | 1 | 3 (missing, Chinese, YAML) | 6 |
| `point_to_line_distance_2d` | 1 | — | — | 1 |
| `rect_contains_point` | 2 (yes+no) | 1 | — | 3 |
| `time_overlap` | 2 (yes+no) | 1 | — | 3 |
| `altitude_overlap` | 2 (yes+no) | 1 | — | 3 |

## Error Type Coverage

| Error Type | Cases | Detection Mechanism |
|-----------|-------|-------------------|
| Wrong numeric value | case_011 | Value comparison (±0.05 tolerance) |
| Wrong boolean (intersection) | case_012 | Boolean comparison |
| Wrong boolean (contains) | case_013 | Boolean comparison |
| Wrong boolean (time) | case_014 | Boolean comparison |
| Wrong boolean (altitude) | case_015 | Boolean comparison |
| Missing operator reference | case_016 | Operator detection in output |
| Missing numeric value | case_017 | Value extraction failure |
| Ambiguous object reference | case_018 | Object name matching |
| Non-existent operator | case_019 | Invalid operator in output |
| Non-existent object reference | case_020 | Invalid object in output |
| Unit mismatch (km vs m) | case_021 | Unit conversion detection |
| Chinese negation (不相交) | case_022 | Chinese NLP negation detection |
| Markdown code extraction | case_023 | Regex-based value extraction |
| YAML structured output | case_024 | Cross-line YAML value extraction |

## Encoding File Map

```
benchmarks/encoding_v0_2/
├── cases.yaml                              ← 24 case definitions
├── generate_files.py                       ← File generator (144 files)
├── local_verifier.py                       ← v0.2-specific verifier
├── run_benchmark.py                        ← Benchmark runner
├── token_counter.py                        ← Token estimator
├── metrics.py                              ← Scoring formulas
├── render_charts.py                        ← 6 chart renderers
├── render_report.py                        ← Markdown report
├── inputs/                                 ← 72 input files
│   ├── natural_language/  (24 × .txt)
│   ├── geotask_yaml/      (24 × .yaml)
│   └── compact_dsl/       (24 × .gt)
├── simulated_model_outputs/                ← 72 output files
│   ├── natural_language/  (24 × _output.md)
│   ├── geotask_yaml/      (24 × _output.md)
│   └── compact_dsl/       (24 × _output.md)
└── outputs/                                ← Generated results
    ├── encoding_benchmark_v0_2_results.csv
    ├── encoding_benchmark_v0_2_results.json
    ├── encoding_benchmark_v0_2_summary.md
    └── charts/             (6 PNG files)
```

---

*Evidence artifact: `patent_evidence/07_benchmark_v0_2/case_coverage.md`*
