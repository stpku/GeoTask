# Claim-to-Evidence Mapping Matrix

> Maps patent technical features to concrete benchmark evidence files and results.
> For use in patent prosecution to demonstrate technical effect with experimental data.

---

## Overview

This matrix maps each patent technical feature (from the GeoTask system and method claims) to specific evidence files and benchmark results. Each mapping includes the file path, a summary of the supporting result, and notes on how the evidence should be interpreted.

**All model outputs are deterministic simulated outputs. This benchmark does not claim live LLM accuracy.**

---

## Mapping Table

| # | Patent Technical Feature | Evidence File(s) | Benchmark Result | Notes |
|---|--------------------------|-----------------|------------------|-------|
| 1 | **任务相关空间编码生成** (Task-related spatial encoding generation) | `benchmarks/encoding_v0_1/inputs/compact_dsl/*.gt` | Compact DSL avg total tokens: 90 vs NL: 404 | Supports encoding generation under token budget constraints. Demonstrated across 4 cases. |
| 2 | **令牌预算约束** (Token budget constraint) | `patent_evidence/03_benchmark/encoding_benchmark_v0_1_results.json` | 77.7% reduction, 4.5× compression (DSL vs NL) | Approximate tokens — for relative comparison only. Not model-specific billing. |
| 3 | **对象—算子—命题绑定** (Object–operator–proposition binding) | `benchmarks/encoding_v0_1/inputs/geotask_yaml/*.yaml`, `benchmarks/encoding_v0_1/inputs/compact_dsl/*.gt` | Outputs consumable by Normalizer/Verifier; measurements linked to operators | Supports claim that encoding binds spatial objects to deterministic operators. |
| 4 | **模型输出归一化** (Model output normalization) | `simulated_model_outputs/` + `geotask_core/normalizer.py` | Normalization success rate: 100% across all 12 runs | Normalizer extracts values, units, object_refs, and verified_by from unstructured output. |
| 5 | **本地确定性验证** (Local deterministic verification) | `geotask_core/verifier.py` + benchmark results CSV | wrong_distance and not_intersect correctly flagged as contradicted | Verifier cross-checks model claims against locally computed ground truth (distance_2d, line_intersects_rect). |
| 6 | **可验证性分流** (Verifiability triage) | `patent_evidence/03_benchmark/encoding_benchmark_v0_1_results.json` (case_004) | operator_reference_missing detected in 3/3 encodings for case_004 | Missing information converted to review_reasons. Supports need_review/review reason generation. |
| 7 | **状态化输出** (Status-aware output) | `patent_evidence/03_benchmark/encoding_benchmark_v0_1_results.json` | Each measurement tagged: verified / contradicted / need_review | Supports unified spatial task result format with actionable status for downstream consumers. |
| 8 | **编码模板优化** (Encoding template optimization) | `benchmarks/encoding_v0_1/outputs/charts/benchmark_score_by_encoding.png` | DSL score: 95.0, YAML: 81.9, NL: 79.6 | Benchmark score formula combines token efficiency (40%) + verification (40%) + normalization (20%). |
| 9 | **上下文缺口生成** (Context gap generation) | `benchmarks/encoding_v0_1/inputs/` (all encoding types) | Encoding defines what LLM needs vs. what can be left to model knowledge | The encoding format explicitly scopes the task boundary for LLM consumption. |
| 10 | **最小充分空间任务表示** (Minimal sufficient spatial task representation) | `benchmarks/encoding_v0_1/inputs/compact_dsl/*.gt` | Only essential fields: OBJ (coordinates), CHK (operator+type), ASK (output spec) | Minimal encoding preserves all information needed for deterministic verification. |

---

## How to Use This Matrix

1. **During patent examination**: Reference specific rows to support arguments about technical effect.
2. **When responding to office actions**: Cite the evidence file and benchmark result that directly supports the claimed feature.
3. **When explaining to an attorney**: Use the "Notes" column to understand the evidence scope and limitations.

### Key Caveats for Prosecution

- The benchmark uses **deterministic simulated outputs** — not real LLM inference.
- Token counts are **approximate** and for relative comparison only.
- The benchmark is **descriptive** (n=4 cases), not statistically inferential.
- This evidence supports **engineering claims** about encoding behavior, not claims about general LLM accuracy.

---

## Limitations

1. Simulated outputs — no real LLM API calls.
2. Approximate token counting — not model-specific.
3. Small case set (4 cases) — limited generalization.
4. Narrow operator set (2 operators) — requires expansion for comprehensive coverage.
5. No statistical significance testing.
6. Single spatial scene — broader scenarios needed.

---

## Evidence Artifacts Referenced

| Artifact | Path |
|----------|------|
| Benchmark raw data (JSON) | `patent_evidence/03_benchmark/encoding_benchmark_v0_1_results.json` |
| Benchmark raw data (CSV) | `patent_evidence/03_benchmark/encoding_benchmark_v0_1_results.csv` |
| Benchmark summary | `patent_evidence/03_benchmark/encoding_benchmark_v0_1_summary.md` |
| Full report | `benchmarks/encoding_v0_1/outputs/encoding_benchmark_v0_1_report.md` |
| Attorney brief | `patent_evidence/00_attorney_brief/attorney_one_page_summary.md` |
| Encoding inputs | `benchmarks/encoding_v0_1/inputs/` |
| Simulated outputs | `benchmarks/encoding_v0_1/simulated_model_outputs/` |
| Charts | `benchmarks/encoding_v0_1/outputs/charts/` |

---

## v0.3 Core Backfill (NEW)

v0.3 backfills stable v0.2 capabilities into production GeoTask Core:

| Patent Feature | v0.3 Production Evidence |
|---------------|-------------------------|
| Multi-operator normalization | 6 operators in Core Normalizer (up from 2) |
| Production verification | Core Verifier with unified status hierarchy |
| invalid_operator detection | Non-existent operators rejected (e.g., haversine) |
| invalid_reference detection | Object reference validation against geotask_data |
| Unit mismatch | km vs meter detection in production code |
| Chinese negation | 不相交, 不包含 correctly detected |

**Evidence**: `patent_evidence/08_core_v0_3/` | `tests/test_core_normalizer_verifier_v0_3.py`

## v0.2 Evidence Extension

v0.2 extends this matrix to 24 cases and 6 operators. See `patent_evidence/07_benchmark_v0_2/claim_support_update.md` for the extended mapping.

> **Boundary note**: v0.2 should be used as **structural encoding and verification-readiness evidence**. For end-to-end Core Normalizer + Verifier evidence, use v0.1.1 (this matrix) or v0.3 (production backfill).

> **边界说明**: v0.2 应作为结构化编码和验证就绪度证据使用；端到端 Core Normalizer + Verifier 闭环证据应引用 v0.1.1 或 v0.3。

---

## Reproducibility

```bash
# Reproduce v0.1.1 benchmark results
python benchmarks/encoding_v0_1/run_benchmark.py

# Reproduce v0.2 benchmark results
python benchmarks/encoding_v0_2/run_benchmark.py

# Run all tests
pytest
```
