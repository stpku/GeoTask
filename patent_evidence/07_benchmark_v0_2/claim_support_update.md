# GeoTask Encoding Benchmark v0.2 — Claim Support Update

> Maps encoding benchmark v0.2 findings to patent claim features.
> Extends v0.1 claim-to-evidence mapping with new operators, error types, and benchmark scale.

## New Claim Support from v0.2

| Patent Feature | v0.1 Evidence | **v0.2 Evidence** | Strength Increase |
|---------------|---------------|-------------------|-------------------|
| Spatial task representation | 2 operators, 4 cases | **6 operators, 24 cases** | 6× coverage |
| Encoding-agnostic verification | 3 encodings, basic | **3 encodings, extended** | Error robustness |
| Deterministic operator execution | 2 operators | **6 operators** | Multi-dimensional |
| Contradiction detection | 1 error type | **8 error types** | Error coverage |
| Review reason generation | 1 reason type | **4 reason types** | Diagnostic depth |
| Chinese NLP robustness | Not tested | **Chinese negation test** | NLP coverage |
| Unit mismatch handling | Not tested | **km→m detection** | Unit awareness |
| Invalid operator detection | Not tested | **Haversine rejection** | Ops validation |
| Invalid object detection | Not tested | **Name rejection** | Object validation |
| Token efficiency | Basic comparison | **35% DSL reduction** | Quantified |

## Key v0.2 Evidence for Patent Claims

### Claim: Encoding-format-independent spatial task representation
- **Evidence**: All 3 encodings (NL, YAML, DSL) consistently normalize to the same structured verification format across 24 diverse cases.
- **v0.2 adds**: The benchmark now demonstrates that this independence holds even with Chinese text, Markdown formatting, YAML structure, unit mismatches, and missing values.

### Claim: Deterministic operator verification
- **Evidence**: 6 operators (distance_2d, line_intersects_rect, point_to_line_distance_2d, rect_contains_point, time_overlap, altitude_overlap) verified deterministically without external APIs.
- **v0.2 adds**: New spatial dimensions — point-to-line distance, containment, temporal overlap, vertical (altitude) overlap — all verified locally.

### Claim: Robust error detection
- **Evidence**: 8 error types detected with 96%+ accuracy, generating appropriate review reasons.
- **v0.2 adds**: Unit mismatch, invalid operators, invalid references, Chinese negation — all correctly detected.

### Claim: Token efficiency
- **Evidence**: Compact DSL uses 35% fewer tokens than natural language while maintaining 100% verification status match.
- **v0.2 adds**: Quantified efficiency across 24 diverse cases (not just 4 simple ones).

## v0.2 Benchmark Artifacts

| Artifact | Location | Description |
|----------|----------|-------------|
| Cases definition | `benchmarks/encoding_v0_2/cases.yaml` | 24 case definitions |
| Benchmark runner | `benchmarks/encoding_v0_2/run_benchmark.py` | Deterministic benchmark |
| Results CSV | `benchmarks/encoding_v0_2/outputs/` | 72-row results |
| Results JSON | `benchmarks/encoding_v0_2/outputs/` | Structured results |
| Charts (6 PNG) | `benchmarks/encoding_v0_2/outputs/charts/` | Visualizations |
| Test suite | `tests/test_encoding_benchmark_v0_2.py` | 20+ automated tests |
| Evidence summary | `patent_evidence/07_benchmark_v0_2/README.md` | This evidence package |

## Reproducibility

```bash
# Generate benchmark
python benchmarks/encoding_v0_2/run_benchmark.py

# Validate
pytest tests/test_encoding_benchmark_v0_2.py -v
```

---

*Evidence artifact: `patent_evidence/07_benchmark_v0_2/claim_support_update.md`*
*Extends: `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md`*
