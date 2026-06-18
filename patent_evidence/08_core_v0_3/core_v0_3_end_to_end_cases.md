# GeoTask Core v0.3 — End-to-End Production Test Cases

> All tests use production `normalize_model_output` + `verify_normalized_result`.
> No benchmark `local_verifier` is used.

## Correct Cases (verified)

| # | Case | Operator | Expected Status | Test |
|---|------|----------|----------------|------|
| 1 | Correct 2D distance | distance_2d | verified | `test_distance_2d_correct` |
| 2 | Correct intersection | line_intersects_rect | verified | `test_line_intersects_correct` |
| 3 | Correct point-to-line distance | point_to_line_distance_2d | verified | (multi-operator geotask) |
| 4 | Correct rect contains | rect_contains_point | verified | (multi-operator geotask) |
| 5 | Correct time overlap | time_overlap | verified | (multi-operator geotask) |
| 6 | Correct altitude overlap | altitude_overlap | verified | (multi-operator geotask) |

## Contradicted Cases

| # | Case | Operator | Expected Status | Test |
|---|------|----------|----------------|------|
| 7 | Wrong distance | distance_2d | contradicted | `test_wrong_distance_contradicted` |
| 8 | Wrong intersection | line_intersects_rect | contradicted | `test_wrong_intersection_contradicted` |

## Need Review / Invalid Cases

| # | Case | Reason | Expected Status | Test |
|---|------|--------|----------------|------|
| 9 | Missing operator | operator_reference_missing | need_review | `test_missing_operator_need_review` |
| 10 | Missing value | distance_value_not_found | need_review | `test_missing_value_need_review` |
| 11 | Invalid operator (haversine) | invalid_operator | invalid_operator | `test_invalid_operator_detected` |
| 12 | Unit mismatch (km) | unit_mismatch | need_review | `test_unit_mismatch_detected` |
| 13 | Chinese negation (相交) | — | verified | `test_chinese_negation_intersection` |
| 14 | Chinese negation (包含) | — | — | `test_chinese_negation_contains` |

## Evidence Files

| File | Test File |
|------|-----------|
| Production end-to-end | `tests/test_core_normalizer_verifier_v0_3.py` |
| Ops unit tests | `tests/test_ops_v0_3.py` |
| Evidence integrity | `tests/test_core_v0_3_evidence.py` |

---

*Evidence artifact: `patent_evidence/08_core_v0_3/core_v0_3_end_to_end_cases.md`*
