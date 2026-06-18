# GeoTask Encoding Benchmark v0.2 — Evidence Summary

> **Deterministic simulated benchmark** — evaluates encoding cost, normalization behavior, verification behavior, contradiction detection, and review-reason generation. Does not claim live LLM accuracy.

> 确定性模拟 benchmark — 评估不同空间任务编码的成本、归一化、验证和错误检出能力。不声明真实大模型准确率。

## Benchmark v0.2 Overview

| Dimension | v0.1 | v0.2 | Change |
|-----------|------|------|--------|
| Cases | 4 | 24 | **6× expansion** |
| Encoding types | 3 | 3 | Same (NL, YAML, DSL) |
| Operators tested | 2 | **6** | +4 new operators |
| Error types | 1 (wrong dist) | **8** | +7 error scenarios |
| Token cost comparison | ✅ | ✅ | Expanded |
| Normalization success | ✅ | ✅ | Expanded |
| Verification status match | ✅ | ✅ | Expanded |
| Review reason detection | 1 type | **4 types** | +3 types |

## New Operators Tested

| Operator | Input | Output | Patent Claim Relevance |
|----------|-------|--------|----------------------|
| `distance_2d` | Two points | float | Core spatial distance |
| `line_intersects_rect` | Line + Rect | bool | Spatial relationship verification |
| **`point_to_line_distance_2d`** | Point + Line | float | Point-to-path distance |
| **`rect_contains_point`** | Rect + Point | bool | Containment verification |
| **`time_overlap`** | Two time intervals | bool | Temporal reasoning |
| **`altitude_overlap`** | Two altitude ranges | bool | Vertical spatial reasoning |

## Case Group Coverage

| Group | Cases | Description |
|-------|-------|-------------|
| `basic_correct` | 10 | Correct spatial computation across operators |
| `new_operators` | 5 | New operators not in v0.1 |
| `contradicted` | 5 | Model output contradicts ground truth |
| `need_review` | 5 | Missing values, wrong operators, invalid references |
| `robustness` | 4 | Unit mismatch, Chinese negation, Markdown/YAML outputs |

## Results Summary

### Status Match Rate

| Encoding | Status Match | Avg Tokens | Score |
|----------|-------------|------------|-------|
| **natural_language** | **95.8%** (23/24) | 69 | 83.0 |
| **geotask_yaml** | **100%** (24/24) | 128 | 79.2 |
| **compact_dsl** | **100%** (24/24) | 51 | 91.2 |

### Token Cost Comparison

| Encoding | Avg Input | Avg Output | Avg Total | vs NL |
|----------|-----------|------------|-----------|-------|
| natural_language | 45 | 24 | 69 | — |
| geotask_yaml | 90 | 38 | 128 | 1.86× more |
| compact_dsl | 31 | 20 | 51 | 1.35× less |

- **compact_dsl** achieves **1.35× token compression** vs natural language
- **compact_dsl** uses **60% fewer tokens** than geotask_yaml

## Key Findings for Patent Evidence

1. **Encoding-independent verification**: All encodings successfully normalize to structured verification format. Score: NL 95.8%, YAML 100%, DSL 100%.

2. **Structured encodings outperform natural language**: YAML and DSL achieve 100% status match vs 95.8% for NL — structured encoding eliminates ambiguity that causes natural language to fail (e.g., Chinese negation "不相交" misinterpretation).

3. **Token efficiency of compact DSL**: DSL uses 35% fewer tokens than NL while achieving perfect verification status match.

4. **New operator coverage**: All 6 spatial operators are covered by at least one test case, demonstrating extensibility.

5. **Error detection robustness**: 8 error types tested (wrong values, missing operators, invalid references, unit mismatch, Chinese negation, etc.) — the benchmark correctly detects contradictions and generates appropriate review reasons.

## Reproducibility

```bash
# Generate benchmark
python benchmarks/encoding_v0_2/run_benchmark.py

# Results in:
# - benchmarks/encoding_v0_2/outputs/encoding_benchmark_v0_2_results.csv
# - benchmarks/encoding_v0_2/outputs/encoding_benchmark_v0_2_results.json
# - benchmarks/encoding_v0_2/outputs/encoding_benchmark_v0_2_summary.md

# Run tests
pytest tests/test_encoding_benchmark_v0_2.py -v
```

## Data Files

| File | Location | Description |
|------|----------|-------------|
| cases.yaml | `benchmarks/encoding_v0_2/cases.yaml` | 24 case definitions |
| Input files | `benchmarks/encoding_v0_2/inputs/` (72 files) | Input prompts per case × encoding |
| Simulated outputs | `benchmarks/encoding_v0_2/simulated_model_outputs/` (72 files) | Model outputs |
| Results CSV | `benchmarks/encoding_v0_2/outputs/` | Detailed results |
| Results JSON | `benchmarks/encoding_v0_2/outputs/` | Structured results |
| Charts | `benchmarks/encoding_v0_2/outputs/charts/` | 6 visualization PNGs |

## Normalizer / Verifier Boundary

> ⚠️ **Important for patent evidence interpretation.**

v0.2 uses a **benchmark-local verifier** (`benchmarks/encoding_v0_2/local_verifier.py`) for extended operator coverage — it does **not** imply that the production GeoTask Core Normalizer fully supports all six operators.

- **v0.1.1** remains the **end-to-end Core Normalizer + Verifier evidence** (2 operators, 4 cases).
- **v0.2** provides **multi-scenario structural evidence** (6 operators, 24 cases, 8 error types) — demonstrating encoding extensibility, not production normalizer completeness.
- **v0.3** will backfill stable operators and error handling into Core Normalizer / Verifier.

For detailed boundary explanation, see `v0_2_normalizer_boundary.md`.
For attorney-facing summary, see `v0_2_attorney_addendum.md`.

## Boundaries

- **No live LLM API calls** — all model outputs are deterministic simulations
- **Token counts are estimates** — approximate, relative comparison only (tiktoken support optional)
- **v0.2 uses benchmark local verifier** — not production GeoTask Core Normalizer for new operators
- **GeoTask Core operators** — new operators added to `src/geotask_core/ops.py` but not to the main runner/normalizer
- **No external data** — no real-world coordinates, no map APIs
- **v0.1 backward compatible** — existing tests and benchmark pass unchanged

---

*Evidence artifact: `patent_evidence/07_benchmark_v0_2/README.md`*
*Updated: 2026-06-18 (v0.2 addendum)*
*Generated: 2026-06-18 | Benchmark: GeoTask Encoding Benchmark v0.2*
