# Evidence Manifest

## Repository Status

| Property | Value |
|----------|-------|
| Private repository | **Yes** — Do not make public |
| External APIs used | **No** — No LLM, map, search, or network APIs |
| Real filing documents included | **No** — Only checklists and placeholders |
| Customer data included | **No** |
| Third-party confidential materials | **No** |
| Git branch | `architecture/product-and-patent-v0.1` |
| Base branch | `core/normalizer-verifier-v0.3` |

---

## Evidence Package Contents

```
patent_evidence/
├── README.md                                    # Package overview + security warnings
├── EVIDENCE_MANIFEST.md                         # This file
├── DELIVERY_NOTE_v0_1_1.md                      # Attorney delivery note (NEW)
├── 00_attorney_brief/
│   └── attorney_one_page_summary.md             # One-page summary for patent prosecution
├── 01_filing/
│   ├── filing_checklist.md                      # Filing status template (no real data)
│   └── placeholder_do_not_commit_real_documents.md  # ⚠️ Reminder
├── 02_code_evidence/
│   ├── geotask_version_snapshot.md              # Code version and capability snapshot
│   ├── test_snapshot.md                         # Test results (113/113 passed)
│   └── cli_snapshot.md                          # CLI usage examples
├── 03_benchmark/
│   ├── encoding_benchmark_v0_1_results.csv      # Per-case metrics (12 rows)
│   ├── encoding_benchmark_v0_1_results.json     # Full results + aggregates
│   └── encoding_benchmark_v0_1_summary.md       # Summary with derived metrics
├── 04_prior_art_review/
│   └── novelty_creativity_positioning.md        # Novelty vs existing approaches
├── 05_invention_story/
│   └── technical_problem_solution_effect.md     # Problem → Solution → Effect
└── 06_claim_mapping/
    └── claim_to_evidence_matrix.md              # Patent features → evidence mapping
└── 07_benchmark_v0_2/                           # v0.2 benchmark evidence (NEW)
    ├── README.md                                 # v0.2 evidence summary
    ├── case_coverage.md                          # 24-case operator/error matrix
    ├── claim_support_update.md                   # v0.2 claim mapping updates
    ├── v0_2_normalizer_boundary.md               # ⚠️ Normalizer/verifier boundary explanation
    └── v0_2_attorney_addendum.md                 # Attorney-facing v0.2 evidence summary
└── 08_core_v0_3/                                 # v0.3 production Core evidence (NEW)
    ├── README.md                                 # v0.3 evidence overview
    ├── core_v0_3_capability_summary.md           # New capabilities in v0.3
    ├── core_v0_3_end_to_end_cases.md             # Production test case matrix
    ├── core_v0_3_claim_support_update.md         # v0.3 claim mapping
    ├── core_v0_3_boundary.md                     # Evidence boundary and limitations
    ├── core_v0_3_attorney_addendum.md            # Attorney-facing v0.3 evidence summary (DELIVERY)
    └── core_v0_3_delivery_note.md                # v0.3 delivery instructions (DELIVERY)
└── 09_product_architecture_v0_1/                 # v0.1 product architecture + patent portfolio
    ├── README.md                                 # Package overview
    ├── product_architecture_patent_positioning.md # Product architecture patent positioning
    ├── invention_ledger.md                       # 10 invention points ledger
    ├── patent_portfolio_roadmap.md               # P1-P5 patent portfolio roadmap
    ├── product_to_patent_mapping.md              # Module → patent mapping
    └── commercial_boundary_note.md               # Commercial boundary declaration
```

**Evidence version**: `core-normalizer-verifier-v0.3`
**Recommended tag**: `core-normalizer-verifier-v0.3`

---

## Benchmark Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Benchmark core | `benchmarks/encoding_v0_1/` | Runner, metrics, token counter, cases |
| Input files | `benchmarks/encoding_v0_1/inputs/` | 12 files (4 cases × 3 encodings) |
| Simulated outputs | `benchmarks/encoding_v0_1/simulated_model_outputs/` | 12 files (deterministic, no real LLM) |
| Results CSV | `benchmarks/encoding_v0_1/outputs/encoding_benchmark_v0_1_results.csv` | 12 rows |
| Results JSON | `benchmarks/encoding_v0_1/outputs/encoding_benchmark_v0_1_results.json` | Full data + aggregates |
| Full report | `benchmarks/encoding_v0_1/outputs/encoding_benchmark_v0_1_report.md` | Comprehensive report |
| Summary | `benchmarks/encoding_v0_1/outputs/encoding_benchmark_v0_1_summary.md` | Quick summary |

## v0.2 Benchmark Artifacts (NEW)

| Artifact | Path | Description |
|----------|------|-------------|
| Benchmark core | `benchmarks/encoding_v0_2/` | Runner, metrics, token counter, local verifier, charts, report |
| Cases definition | `benchmarks/encoding_v0_2/cases.yaml` | 24 cases (5 groups, 6 operators) |
| Input files | `benchmarks/encoding_v0_2/inputs/` | 72 files (24 cases × 3 encodings) |
| Simulated outputs | `benchmarks/encoding_v0_2/simulated_model_outputs/` | 72 files (deterministic, no real LLM) |
| Results CSV | `benchmarks/encoding_v0_2/outputs/encoding_benchmark_v0_2_results.csv` | 72 rows |
| Results JSON | `benchmarks/encoding_v0_2/outputs/encoding_benchmark_v0_2_results.json` | Full data + aggregates |
| Full report | `benchmarks/encoding_v0_2/outputs/encoding_benchmark_v0_2_report.md` | Comprehensive report |
| Summary | `benchmarks/encoding_v0_2/outputs/encoding_benchmark_v0_2_summary.md` | Quick summary |
| Test suite | `tests/test_encoding_benchmark_v0_2.py` | 166 automated tests |

---

## Generated Charts

| Chart | Path |
|-------|------|
| Token Cost by Encoding | `benchmarks/encoding_v0_1/outputs/charts/token_cost_by_encoding.png` |
| Verification Success by Encoding | `benchmarks/encoding_v0_1/outputs/charts/verification_success_by_encoding.png` |
| Normalization Success by Encoding | `benchmarks/encoding_v0_1/outputs/charts/normalization_success_by_encoding.png` |
| Benchmark Score by Encoding | `benchmarks/encoding_v0_1/outputs/charts/benchmark_score_by_encoding.png` |

---

## Test Snapshot

| Metric | Value |
|--------|-------|
| Total test modules | 13+ |
| Total test functions | 406+ |
| All tests passing | ✅ Yes |
| Last run | `pytest` — 406 passed |

Test modules:
- `test_ops.py`, `test_ops_v0_3.py`, `test_parser.py`, `test_runner.py` — Core functionality
- `test_normalizer.py`, `test_normalizer_v0_2.py` — Extraction
- `test_verifier.py` — Verification
- `test_evaluator.py` — Eval scoring
- `test_core_normalizer_verifier_v0_3.py` — v0.3 production E2E
- `test_encoding_benchmark.py`, `test_encoding_benchmark_v0_2.py` — Benchmark validation
- `test_evidence_hardening.py`, `test_evidence_delivery_note.py` — Evidence integrity
- `test_runtime_contracts_v0_1.py` — Runtime contract validation
- `test_mock_runtime_v0_1.py` — Mock runtime pipeline
- `test_product_architecture_evidence_v0_1.py` — Architecture evidence integrity

---

## Key Benchmark Results

| Metric | Natural Language | GeoTask YAML | Compact DSL |
|--------|-----------------:|-------------:|------------:|
| Avg Total Tokens | 404 | 262 | 90 |
| Normalization Success | 100% | 100% | 100% |
| Verification Success | 100% | 100% | 100% |
| Benchmark Score | 79.6 | 81.9 | 95.0 |
| Token Reduction vs NL | — | 35.1% | 77.7% |
| Compression Ratio vs NL | — | 1.5× | 4.5× |

---

## Delivery Package (v0.1.1)

The following files form the core delivery package for attorney review:

| File | Type |
|------|------|
| `DELIVERY_NOTE_v0_1_1.md` | Attorney delivery note with key findings and recommended wording |
| `00_attorney_brief/attorney_one_page_summary.md` | One-page technical summary |
| `06_claim_mapping/claim_to_evidence_matrix.md` | Patent feature → evidence mapping |
| `03_benchmark/encoding_benchmark_v0_1_summary.md` | Benchmark results with derived metrics |

**Evidence version**: v0.1.1  
**Recommended tag**: `evidence-encoding-v0.1.1`

---

## Confidentiality Notes

1. **This repository is private.** Do not make it public without explicit authorization.
2. **No real filing documents are stored here.** Filing receipts, application numbers, attorney correspondence, and client data must be stored in a separate secure location.
3. **The benchmark uses deterministic simulated outputs**, not real LLM API calls. This is explicitly stated in all reports and summaries.
4. **When sharing evidence with an attorney**: reference the files listed in this manifest. Do not share the entire repository unless access policy allows it.
5. **Patent claims are retained separately** from the MIT-licensed code. See `docs/patent_boundary.md`.

---

## Reproducibility Commands

```bash
# Reproduce all benchmark results and charts
python benchmarks/encoding_v0_1/run_benchmark.py

# Run all tests (existing + evidence integrity)
pytest

# Verify evidence package integrity
pytest tests/test_evidence_hardening.py -v
```

---

## Integrity Checklist

- [ ] `pytest` passes (all tests)
- [ ] `python benchmarks/encoding_v0_1/run_benchmark.py` succeeds
- [ ] All 4 charts exist in `outputs/charts/`
- [ ] CSV, JSON, and Markdown outputs are current
- [ ] Attorney brief references correct metric values
- [ ] Claim mapping matrix references existing evidence files
- [ ] No real filing documents in `01_filing/`
- [ ] All reports include simulated benchmark boundary disclaimer
- [ ] Repository is private (verify on Gitee)
