# GeoTask Encoding Benchmark v0.1

Compares three encoding formats for spatial tasks:
- **natural_language**: Verbose English/Chinese text
- **geotask_yaml**: GeoTask Core YAML format  
- **compact_dsl**: Minimal DSL encoding

## Quick Start

```bash
# From repo root
python benchmarks/encoding_v0_1/run_benchmark.py
```

## What It Evaluates

1. **Token cost**: Approximate token count per encoding
2. **Normalization success**: Whether structured measurements can be extracted
3. **Verification success**: Whether model output matches deterministic ground truth
4. **Benchmark score**: Composite 0–100 score

## Design

- 4 test cases × 3 encodings = 12 runs
- Simulated model outputs (no real LLM API calls)
- Uses existing GeoTask Normalizer v0.2 + Verifier v0.2
- Lightweight token estimator (no tiktoken dependency)

## Output

```
benchmarks/encoding_v0_1/outputs/
├── encoding_benchmark_v0_1_results.csv
├── encoding_benchmark_v0_1_results.json
├── encoding_benchmark_v0_1_report.md
├── encoding_benchmark_v0_1_summary.md
└── charts/
    ├── token_cost_by_encoding.png
    ├── verification_success_by_encoding.png
    ├── normalization_success_by_encoding.png
    └── benchmark_score_by_encoding.png
```

Results are also copied to `patent_evidence/03_benchmark/`.

## Notes

- Model outputs are deterministic simulated outputs for reproducibility.
- Token counts are approximate and used only for relative comparison.
- This benchmark evaluates encoding cost, normalization, and verification behavior, not live LLM quality.
