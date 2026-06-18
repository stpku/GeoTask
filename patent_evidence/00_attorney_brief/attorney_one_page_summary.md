# Attorney One-Page Summary: GeoTask Encoding Benchmark v0.1

> **CONFIDENTIAL — For internal patent prosecution use only.**
> This document summarizes experimental evidence from the GeoTask Encoding Benchmark v0.1.
> Model outputs are deterministic simulated outputs. This benchmark does **not** claim live LLM accuracy.

---

## Purpose

To provide a concise, self-contained summary of the GeoTask Encoding Benchmark v0.1 for use in patent prosecution — specifically, to demonstrate the technical effect of task-related spatial encoding on token cost, normalization success, and deterministic verification.

---

## Technical Problem

1. **High token cost** — Redundant spatial context in natural language input inflates LLM token consumption.
2. **Insufficient local spatial data and GIS operators** — LLMs lack access to local spatial datasets and deterministic operators.
3. **Unstable LLM output format** — LLM outputs vary in structure, language, and precision across calls.
4. **Potential LLM spatial calculation errors** — LLMs may produce incorrect spatial calculations while appearing confident.
5. **Difficulty integrating results into business systems** — Unstructured LLM outputs are hard to consume programmatically.

---

## Technical Solution

1. **Task-related spatial encoding** — GeoTask YAML and Compact DSL replace verbose natural language with minimal sufficient representations.
2. **Object–operator–proposition binding** — Each spatial task binds objects to operators and produces verifiable propositions.
3. **Model output normalization** — GeoTask Normalizer extracts structured measurements from unstructured LLM text.
4. **Local deterministic verification** — GeoTask Verifier cross-checks model claims against locally computed ground truth.
5. **Status-aware output** — Each measurement is tagged `verified`, `contradicted`, or `need_review`.

---

## Experimental Setup

| Parameter | Value |
|-----------|-------|
| Cases | 4 (correct, wrong distance, wrong boolean, missing operator) |
| Encoding types | 3 (natural_language, geotask_yaml, compact_dsl) |
| Total runs | 12 (4 × 3) |
| Model outputs | Deterministic simulated (no real LLM API calls) |
| Ground truth | GeoTask Core ops: distance_2d, line_intersects_rect |
| Verification | GeoTask Normalizer v0.2 + Verifier v0.2 |
| Token estimation | Lightweight heuristic estimator (not tiktoken) |

---

## Key Evidence

<!-- METRICS BELOW ARE AUTO-POPULATED FROM BENCHMARK JSON -->
<!-- Run: python benchmarks/encoding_v0_1/run_benchmark.py to regenerate -->

### Token Cost

| Encoding | Avg Input Tokens | Avg Output Tokens | Avg Total Tokens |
|----------|-----------------:|------------------:|-----------------:|
| natural_language | **174** | **230** | **404** |
| geotask_yaml | **197** | **65** | **262** |
| compact_dsl | **79** | **12** | **90** |

**Token reduction**: Compact DSL vs Natural Language: **77.7%** reduction  
**Compression ratio**: **4.5×** compression

### Normalization & Verification

| Encoding | Normalization Success | Verification Success (Status Match) | Benchmark Score (0–100) |
|----------|----------------------:|------------------------------------:|------------------------:|
| natural_language | 100% | 100% | 79.6 |
| geotask_yaml | 100% | 100% | 81.9 |
| compact_dsl | 100% | 100% | 95.0 |

### Error Detection

- **Wrong distance** (case_002): Correctly flagged as `contradicted` across all 3 encodings.
- **Wrong intersection** (case_003): Correctly flagged as `contradicted` across all 3 encodings.
- **Missing operator reference** (case_004): `operator_reference_missing` detected across all 3 encodings.

---

## Patent Claim Support

| Patent Technical Feature | How the Evidence Supports It |
|--------------------------|------------------------------|
| Task-related spatial encoding under token budget constraints | Compact DSL achieves 4.5× compression vs NL while retaining spatial semantics |
| Object–operator–proposition binding | Structured encodings enable deterministic verification of each measurement |
| Model output normalization | 100% normalization success across all encodings (simulated conditions) |
| Local deterministic verification | Verifier correctly distinguishes verified/contradicted/need_review |
| Verifiability triage | Missing operator references converted to review_reasons |
| Encoding template optimization | Benchmark score quantifies token–verification tradeoff |

---

## Limitations (Must Be Stated in Prosecution)

1. **Deterministic simulated outputs** — Not real LLM inference. Does not claim live LLM accuracy.
2. **Approximate token counter** — Not model-specific (no tiktoken). Relative comparison only.
3. **Small case set** — 4 cases, single spatial scene. Descriptive, not inferential.
4. **Narrow operator set** — 2 operators only (distance_2d, line_intersects_rect).
5. **No real LLM evaluation** — Cannot measure encoding impact on actual model reasoning quality.

---

## Suggested Use in Prosecution

**Recommended phrasing:**

> "The benchmark does not prove general LLM superiority. It supports the engineering claim that task-related spatial encodings can reduce token cost while preserving normalizable and verifiable output structure under deterministic simulated conditions."

> "该 benchmark 不证明大模型通用准确率提升，而是支撑一个工程性主张：在确定性模拟条件下，任务相关空间编码能够降低 token 成本，同时保持可归一化、可验证的输出结构。"

**Files to reference:**

- `patent_evidence/03_benchmark/encoding_benchmark_v0_1_results.json` — Raw data
- `benchmarks/encoding_v0_1/outputs/encoding_benchmark_v0_1_report.md` — Full report
- `benchmarks/encoding_v0_1/outputs/charts/` — Visual evidence (4 PNG charts)
- `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` — Claim mapping

---

*Generated from benchmark JSON. Reproducible via: `python benchmarks/encoding_v0_1/run_benchmark.py`*
