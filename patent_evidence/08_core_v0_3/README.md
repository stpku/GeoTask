# GeoTask Core Normalizer / Verifier v0.3 — Evidence Package

> **Production Core evidence.** v0.3 backfills stable v0.2 capabilities into GeoTask Core Normalizer and Verifier.
> 生产级 Core 证据。v0.3 将 v0.2 中稳定的能力回灌到 GeoTask Core Normalizer 和 Verifier。

## What v0.3 Is

v0.3 is the **production Core backfill** of capabilities demonstrated in Benchmark v0.2:

- **4 new operators** formally supported in Core Normalizer & Verifier;
- **8 error/status types** with production-grade detection;
- **Chinese negation** for all boolean operators (not just intersection);
- **Unit mismatch** detection (km vs meter);
- **Invalid operator / invalid reference** detection;
- **Unified status hierarchy**: invalid_operator > invalid_reference > contradicted > need_review > verified.

## What v0.3 Is NOT

- ❌ Not a live LLM API evaluation
- ❌ Not a replacement for Benchmark v0.2 (v0.2 provides broader structural coverage)
- ❌ Not a general NLP system
- ❌ Not a GIS library

## Evidence Relationship

| Version | Type | Operators | Role |
|---------|------|-----------|------|
| v0.1.1 | Core end-to-end | 2 | Production Normalizer + Verifier loop |
| v0.2 | Benchmark structural | 6 | Encoding extensibility evidence |
| **v0.3** | **Core backfill** | **6** | **Production multi-operator evidence** |

## Files

| File | Description |
|------|-------------|
| `README.md` | This overview |
| `core_v0_3_capability_summary.md` | New capabilities in v0.3 |
| `core_v0_3_end_to_end_cases.md` | Production end-to-end test case matrix |
| `core_v0_3_claim_support_update.md` | Updated claim-to-evidence mapping |
| `core_v0_3_boundary.md` | Evidence boundary and limitations |

## Test Results

```bash
pytest  # 363+ tests passing
python benchmarks/encoding_v0_1/run_benchmark.py  # v0.1 unchanged
python benchmarks/encoding_v0_2/run_benchmark.py  # v0.2 unchanged
python -m geotask_core.cli validate examples/geotask_core_lite.yaml
python -m geotask_core.cli run examples/geotask_core_lite.yaml
```

---

*Evidence artifact: `patent_evidence/08_core_v0_3/README.md`*
*Date: 2026-06-18 | Version: v0.3*
