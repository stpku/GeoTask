# GeoTask Core v0.3 Evidence Delivery Note

> **Audience**: Patent attorney, internal technical team, evidence archive.
> **读者**: 专利代理人、内部技术团队、证据归档。

---

## 1. Purpose

This delivery note accompanies the GeoTask Core Normalizer / Verifier v0.3 evidence package. It explains what was delivered, how it relates to prior versions, what it proves, and how to use it in patent prosecution.

> 本交付说明随 GeoTask Core Normalizer / Verifier v0.3 证据包一同提供，说明交付内容、与之前版本的关系、证据证明力及在专利审查中的使用方式。

---

## 2. Recommended Files for Attorney Review

Priority reading order for patent counsel:

| Priority | File | Description |
|----------|------|-------------|
| 1 | `patent_evidence/08_core_v0_3/core_v0_3_attorney_addendum.md` | Complete attorney-facing evidence summary |
| 2 | `patent_evidence/08_core_v0_3/core_v0_3_capability_summary.md` | Capability overview (6 ops, 8 error types, status hierarchy) |
| 3 | `patent_evidence/08_core_v0_3/core_v0_3_claim_support_update.md` | Claim-to-evidence mapping for v0.3 |
| 4 | `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` | Full claim-to-evidence matrix (all versions) |
| 5 | `patent_evidence/08_core_v0_3/core_v0_3_boundary.md` | Evidence boundaries and limitations |
| 6 | `docs/core_normalizer_verifier_v0_3.md` | Technical documentation |

Supporting technical files:

| File | Description |
|------|-------------|
| `patent_evidence/08_core_v0_3/README.md` | Evidence package overview |
| `patent_evidence/08_core_v0_3/core_v0_3_end_to_end_cases.md` | Test case matrix |
| `patent_evidence/EVIDENCE_MANIFEST.md` | Complete evidence inventory |
| `docs/patent_evidence_guide.md` | How to use evidence in prosecution |

---

## 3. What v0.3 Adds

v0.3 is the **production Core backfill** of stable capabilities from Benchmark v0.2.

### Operators (2 → 6)

| Operator | v0.1.1 Core | v0.2 Benchmark | v0.3 Core |
|----------|:-----------:|:--------------:|:---------:|
| `distance_2d` | ✅ | ✅ | ✅ |
| `line_intersects_rect` | ✅ | ✅ | ✅ |
| `point_to_line_distance_2d` | ❌ | ✅ (local verifier) | ✅ |
| `rect_contains_point` | ❌ | ✅ (local verifier) | ✅ |
| `time_overlap` | ❌ | ✅ (local verifier) | ✅ |
| `altitude_overlap` | ❌ | ✅ (local verifier) | ✅ |

### Error Types (2 → 8)

| Error Type | v0.1.1 | v0.2 | v0.3 |
|-----------|:------:|:----:|:----:|
| Wrong numeric | ✅ | ✅ | ✅ |
| Wrong boolean | ✅ | ✅ | ✅ |
| Missing operator | ❌ | ✅ | ✅ |
| Missing value | ❌ | ✅ | ✅ |
| Invalid operator | ❌ | ✅ (local verifier) | ✅ |
| Invalid reference | ❌ | ✅ (local verifier) | ✅ |
| Unit mismatch | ❌ | ✅ (local verifier) | ✅ |
| Chinese negation | ❌ | ✅ (local verifier) | ✅ |

### Status System

```
v0.1.1: verified, contradicted, need_review
v0.2:   verified, contradicted, need_review (benchmark-local)
v0.3:   invalid_operator > invalid_reference > contradicted > need_review > verified (production)
```

---

## 4. What v0.3 Closes from v0.2

> Benchmark v0.2 relied on a benchmark-local verifier for extended operator coverage. Core v0.3 moves stable operator and status handling into production GeoTask Core, reducing the evidence boundary identified in v0.2.

> Benchmark v0.2 依赖 benchmark 本地验证器扩展算子覆盖；Core v0.3 将稳定的算子与状态处理能力迁移到生产级 GeoTask Core，从而缩小了 v0.2 中识别出的证据边界。

### The v0.2 Boundary (now closed)

In v0.2, the following were **only** available through the benchmark-local verifier:
- `point_to_line_distance_2d`, `rect_contains_point`, `time_overlap`, `altitude_overlap` extraction
- `invalid_operator`, `invalid_reference` detection
- `unit_mismatch` detection
- Chinese negation for contains and altitude/time overlap

In v0.3, all of the above are available in production `src/geotask_core/normalizer.py` and `verifier.py`.

### Evidence chain after v0.3

```
v0.1.1 → Proves 2-operator end-to-end Core loop
v0.2   → Proves encoding structure scales to 6 operators
v0.3   → Proves production Core loop scales to 6 operators (boundary closed)
```

---

## 5. Claim Support Summary

| Patent Claim Element | v0.3 Evidence |
|---|---|
| Spatial task encoding for LLMs | 6 operators encoded in production pipeline |
| Object–operator–proposition binding | All 6 operator types autodetected from object types |
| Model output normalization | Multi-type extraction (numeric, boolean, negated) |
| Deterministic local verification | Tolerance-based numeric + exact boolean comparison |
| Verifiability-based routing | 5-level unified status hierarchy |
| Unified status output | Priority-ordered overall_status |
| Encoding template optimization | Inherits v0.2 structured encoding advantages |

---

## 6. What This Evidence Proves

- ✅ Production Core Normalizer supports 6 spatial operators
- ✅ Production Core Verifier handles all 6 operators with correct status assignment
- ✅ Production normalizer + verifier form a complete multi-operator end-to-end loop
- ✅ 8 error/exception types are detected in production code
- ✅ Unified status hierarchy (invalid_operator > invalid_reference > contradicted > need_review > verified) is operational
- ✅ Chinese negation is correctly handled for intersection and contains
- ✅ Unit mismatch (km vs meter) is detected
- ✅ Invalid operator and reference names are rejected
- ✅ All existing tests (v0.1, v0.2) continue to pass (backward compatible)

---

## 7. What This Evidence Does NOT Prove

- ❌ Real LLM accuracy rates (all tests use deterministic simulated outputs)
- ❌ All spatial operators are supported (6 core operators only; no polygon, 3D, geodesic)
- ❌ Complex GIS capabilities (no GDAL, PostGIS, Shapely, GeoPandas)
- ❌ Real-world map data processing (no external data connectors)
- ❌ Regulatory approval or human review replacement
- ❌ Statistical significance (deterministic tests, not inferential)
- ❌ General NLP capability (regex-based extraction, not ML-based)

---

## 8. Reproducibility Commands

```bash
# Full test suite
pytest
# Expected: 347 passed (1 pre-existing import error in test_encoding_benchmark.py excluded)

# v0.3-specific tests
pytest tests/test_ops_v0_3.py                          # 21 tests
pytest tests/test_core_normalizer_verifier_v0_3.py      # 12 tests
pytest tests/test_core_v0_3_evidence.py                 # 13 tests
pytest tests/test_core_v0_3_delivery_addendum.py        # 17 tests (NEW)

# Benchmarks (unchanged)
python benchmarks/encoding_v0_1/run_benchmark.py
python benchmarks/encoding_v0_2/run_benchmark.py

# CLI validation
python -m geotask_core.cli validate examples/geotask_core_lite.yaml
python -m geotask_core.cli run examples/geotask_core_lite.yaml
```

---

## 9. Confidentiality Notes

> ⚠️ This delivery package is for **private patent evidence** only.

- Do **NOT** commit real CNIPA filing receipts or application numbers.
- Do **NOT** commit attorney correspondence or client communications.
- Do **NOT** commit third-party confidential materials.
- Do **NOT** make the repository public without explicit authorization.

The evidence package (`patent_evidence/`) is maintained in a private repository and should remain private.

> 本交付包仅供私有专利证据使用。不要提交真实受理通知书、申请号、代理通信或第三方保密材料。未经明确授权，不得公开仓库。

---

## 10. Next Step: v0.4 Live LLM Benchmark

### Plan (not immediate execution)

| Parameter | Design |
|-----------|--------|
| Encodings | 3 (NL, YAML, DSL) |
| Cases | 12 (subset of v0.2) |
| Models | 2 |
| Runs | 1 (≥3 recommended for statistics) |
| Calls | ~72 |

### Prerequisites

- API cost estimation
- Model version pinning
- Randomness control (temperature = 0)
- Data compliance boundary
- Statistical design

### Relationship

- v0.3 → proves production pipeline works (deterministic)
- v0.4 → proves pipeline works with real LLM outputs
- Complementary, not replacement

---

*Evidence artifact: `patent_evidence/08_core_v0_3/core_v0_3_delivery_note.md`*
*Date: 2026-06-18 | Version: v0.3 Evidence Delivery Addendum*
