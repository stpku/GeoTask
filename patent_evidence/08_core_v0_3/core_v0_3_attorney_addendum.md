# Attorney Addendum: GeoTask Core Normalizer / Verifier v0.3

> **Purpose**: Internal evidence summary for patent attorney review and prosecution reference.
> **用途**: 供专利代理人和内部归档使用的技术证据摘要。

---

## 1. Executive Summary

GeoTask Core Normalizer / Verifier v0.3 is the **production Core backfill** of stable multi-operator capabilities demonstrated in Benchmark v0.2 (24 cases, 6 operators, 8 error types).

**Key facts**:

| Item | Detail |
|------|--------|
| Version | v0.3 (production Core) |
| Branch | `core/normalizer-verifier-v0.3` |
| Commit | `4669d29` |
| Tag | `core-normalizer-verifier-v0.3` |
| Operators in production Core | 6 (up from 2 in v0.1.1) |
| Error types handled | 8 |
| Test status | 347/347 passed |
| External APIs used | None |
| Live LLM accuracy claimed | No |
| Real map data used | No |

v0.3 **does not** call any live LLM API. All tests are deterministic simulated-output tests that evaluate the production-grade normalization, verification, and status routing pipeline.

> v0.3 将 v0.2 中稳定的多算子能力回灌到 production GeoTask Core 的 Normalizer 和 Verifier，通过确定性测试证明 production Core 对 6 类空间算子、8 类错误状态的支持能力。

---

## 2. Why v0.3 Matters

```
v0.2 demonstrated structural extensibility through a benchmark-local verifier.
v0.3 converts the stable part of that structural evidence into production Core capability.
```

> v0.2 通过 benchmark 本地验证器证明结构化扩展性；v0.3 将其中稳定部分转化为生产级 Core 能力。

In v0.2, the 4 new operators (`point_to_line_distance_2d`, `rect_contains_point`, `time_overlap`, `altitude_overlap`) were verified only through `benchmarks/encoding_v0_2/local_verifier.py` — a benchmark-layer verifier, not the production GeoTask Core Normalizer. This created an evidence boundary:

> v0.2 proves the **encoding structure** is extensible, but does not prove the **production Core** handles all 6 operators.

v0.3 closes this boundary: the 4 new operators now have production-grade extraction, normalization, and verification in `src/geotask_core/normalizer.py` and `src/geotask_core/verifier.py`.

---

## 3. Relationship with v0.1.1 and v0.2

| Evidence layer | Version | Focus | Operators | Verification path | Role |
|---|---|---|---|---|---|
| End-to-end seed evidence | v0.1.1 | Core loop | 2 | Core Normalizer + Core Verifier | Proves initial end-to-end loop |
| Structural coverage evidence | v0.2 | Broad benchmark | 6 | Benchmark local verifier | Proves encoding extensibility |
| **Production backfill evidence** | **v0.3** | **Core multi-operator loop** | **6** | **Production Core Normalizer + Verifier** | **Closes v0.2 local verifier boundary** |

### Evidence upgrade path

```
v0.1.1: 2 operators, production Core end-to-end       → Backbone evidence
v0.2:   6 operators, benchmark-local structural coverage → Extensibility evidence
v0.3:   6 operators, production Core end-to-end         → Closed-boundary evidence ✓
```

### Recommended prosecution narrative

1. **Start with v0.1.1** to establish the initial end-to-end Core loop (2 operators, production normalizer + verifier).
2. **Introduce v0.2** to show the encoding structure scales to 6 operators and 24 cases.
3. **Present v0.3** to show the scalable structure is now operational in production Core code, closing the benchmark-local verifier boundary.

---

## 4. Production Core Capabilities

### Supported Operators (6 total)

| # | Operator | Input Types | Output | Since |
|---|----------|-------------|--------|-------|
| 1 | `distance_2d` | point, point | float | v0.1 |
| 2 | `line_intersects_rect` | line, rect | bool | v0.1 |
| 3 | `point_to_line_distance_2d` | point, line | float | **v0.3** |
| 4 | `rect_contains_point` | rect, point | bool | **v0.3** |
| 5 | `time_overlap` | time, time | bool | **v0.3** |
| 6 | `altitude_overlap` | altitude, altitude | bool | **v0.3** |

### Error / Exception Types Handled (8 total)

| # | Error Type | Detection Mechanism | Status |
|---|-----------|-------------------|--------|
| 1 | Wrong numeric value | Tolerance comparison (>0.05) | contradicted |
| 2 | Wrong boolean | Exact match fail | contradicted |
| 3 | Missing operator | Operator reference detection | need_review |
| 4 | Missing value | Value extraction fail | need_review |
| 5 | Invalid operator | Operator name validation | invalid_operator |
| 6 | Invalid reference | Object name validation | invalid_reference |
| 7 | Unit mismatch | km detection in meter context | need_review |
| 8 | Chinese negation | Negation-first pattern matching | verified/contradicted |

### Unified Status Hierarchy

```
invalid_operator > invalid_reference > contradicted > need_review > verified
```

The overall status for a GeoTask result is determined by the **highest-priority** status among all individual measurements and operator verifications. This ensures that any structural error (invalid operator/reference) outweighs content errors (contradicted values), which in turn outweigh missing information (need_review).

### Chinese Negation Support

| Boolean Type | Negation Pattern | Correct Detection |
|-------------|-----------------|-------------------|
| Intersection | 不相交, 不存在相交, 无相交 | ✅ False |
| Contains | 不包含, 不含, 不在矩形内 | ✅ False |
| Time overlap | 时间不重叠, 无时间重叠 | ✅ False |
| Altitude overlap | 高度不重叠, 无高度重叠 | ✅ False |

---

## 5. Key Technical Evidence

### Production Code Changes

| File | v0.3 Change |
|------|------------|
| `src/geotask_core/normalizer.py` | Multi-operator extraction, invalid op/ref detection, unit mismatch, Chinese negation for contains |
| `src/geotask_core/verifier.py` | Unified status priority, operator validation, reference validation |
| `src/geotask_core/runner.py` | Generic type-based auto-detection for 6 operators |
| `src/geotask_core/result_schema.py` | New statuses (invalid_operator, invalid_reference), review reason constants, priority-based `compute_overall_status` |

### New Test Evidence

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/test_ops_v0_3.py` | 21 | All 6 operators with boundary conditions |
| `tests/test_core_normalizer_verifier_v0_3.py` | 12 | Production end-to-end: correct, contradicted, need_review, invalid_op, Chinese negation |
| `tests/test_core_v0_3_evidence.py` | 13 | Evidence package integrity |

### Reproducibility

```bash
# Full test suite (347 tests)
pytest

# v0.3 production tests
pytest tests/test_ops_v0_3.py
pytest tests/test_core_normalizer_verifier_v0_3.py

# Benchmark (unchanged from v0.2)
python benchmarks/encoding_v0_2/run_benchmark.py

# CLI
python -m geotask_core.cli validate examples/geotask_core_lite.yaml
python -m geotask_core.cli run examples/geotask_core_lite.yaml
```

---

## 6. Patent Claim Support

| Patent Technical Feature | v0.3 Support |
|---|---|
| 任务相关空间编码 | Multi-operator task outputs extractable by production normalizer across 6 operators |
| 对象—算子—命题绑定 | All 6 operators enter the production Core verification chain |
| 模型输出归一化 | v0.3 normalizer supports numeric, boolean, negation, unit, and exception extraction |
| 本地确定性验证 | v0.3 verifier validates numeric (tolerance-based) and boolean propositions |
| 可验证性分流 | invalid_operator / invalid_reference / need_review / contradicted / verified hierarchy productionized |
| 统一状态输出 | Status priority chain implemented in production Core |
| 编码模板优化 | v0.3 inherits v0.2's structured encoding advantages, now in production Core loop |

**Strengthened claims vs. v0.2**:

- v0.2 proved the structure **can** handle 6 operators; v0.3 proves the production Core **does** handle them.
- v0.2 relied on a benchmark-local verifier; v0.3 uses production normalizer + verifier, making the evidence directly traceable to the claimed system.
- v0.3 adds invalid_operator and invalid_reference detection, strengthening the "verifiability-based routing" claim.
- v0.3's unified status hierarchy provides a clear, reproducible priority chain for status assignment.

---

## 7. Boundary Note

> ⚠️ **v0.3 is still a deterministic local test and evidence package.** It does not claim live LLM accuracy, does not use external map data, and does not perform real-world regulatory approval.

> v0.3 仍然是确定性的本地测试与证据包，不声明真实大模型准确率，不使用外部地图数据，也不执行现实监管审批。

**What v0.3 proves**:
- ✅ Production Core supports 6 operators in the normalization and verification pipeline
- ✅ Production Core handles 8 error/exception types
- ✅ Production normalizer + verifier form a multi-operator end-to-end loop
- ✅ v0.3 supports patent claims for normalization, deterministic verification, verifiability-based routing, and unified status output

**What v0.3 does NOT prove**:
- ❌ Real LLM accuracy rates
- ❌ All spatial operators are supported (only 6 core operators)
- ❌ Complex GIS capabilities (polygon, 3D, real coordinate systems)
- ❌ Real-world map data processing
- ❌ Regulatory approval or human review replacement

---

## 8. Recommended Attorney Wording

### English

> Core v0.3 closes the Benchmark v0.2 local-verifier boundary by moving stable multi-operator capabilities into the production GeoTask Core Normalizer and Verifier. This strengthens the evidence for the claimed task-related spatial encoding, model-output normalization, deterministic verification, and verifiability-based status routing mechanisms. All 6 operators now execute through the production normalization and verification pipeline, with a unified status hierarchy (invalid_operator > invalid_reference > contradicted > need_review > verified) that routes model outputs based on structural validity, content accuracy, and data completeness.

### 中文

> Core v0.3 通过将稳定的多算子能力迁移至生产级 GeoTask Core Normalizer 和 Verifier，关闭了 Benchmark v0.2 中本地 benchmark 验证器的边界问题，从而增强了任务相关空间编码、模型输出归一化、确定性验证和可验证性分流机制的证据支撑。全部 6 类算子现已通过生产级归一化和验证管线执行，统一的状态层级（invalid_operator > invalid_reference > contradicted > need_review > verified）根据结构有效性、内容准确性和数据完整性对模型输出进行分流。

---

## 9. Suggested Use in Prosecution

### When to cite which version

| Scenario | Cite |
|----------|------|
| Examiner questions whether Core has any end-to-end loop | v0.1.1 |
| Examiner questions whether encoding structure scales beyond 2 operators | v0.2 |
| Examiner questions whether scalable structure is production-grade, not just benchmark | **v0.3** |
| Examiner argues this is "just prompt compression" | v0.2 + v0.3: emphasize object references, operator references, spatial propositions, verification requirements, and status routing entering the production verification chain |
| Examiner argues this is "just an LLM-GIS agent" | v0.3: emphasize this is not tool calling — it is task encoding → normalization → deterministic verification → status routing, a middleware layer |

### Anti-misunderstanding guard

- v0.3 is **not** a replacement for v0.1.1 or v0.2 — all three serve different evidentiary purposes.
- v0.3 is **not** a live LLM evaluation — it uses deterministic simulated outputs.
- v0.3 is **not** a general-purpose spatial engine — it covers 6 core operators for lightweight spatial task verification.

---

## 10. Next Evidence Plan (v0.4)

### v0.4 Goal

Introduce live LLM API benchmark to supplement deterministic tests with real model output evaluation.

### Proposed v0.4 Design (plan only, no immediate execution)

| Parameter | Value |
|-----------|-------|
| Encodings | 3 (natural language, GeoTask YAML, compact DSL) |
| Cases | 12 (subset of v0.2's 24 cases) |
| Models | 2 (e.g., DeepSeek, Qwen) |
| Runs per case | 1 |
| Total API calls | 3 × 12 × 2 × 1 = 72 |

### Prerequisites before v0.4 execution

- [ ] API cost estimation and budget approval
- [ ] Model version pinning (to ensure reproducibility)
- [ ] Randomness handling (temperature = 0, seed control)
- [ ] Data compliance boundary (no real customer or UAV data)
- [ ] Statistical significance design (≥3 runs per case recommended for meaningful variance)

### v0.4 Relationship to v0.3

- v0.3 proves the production pipeline works with deterministic inputs.
- v0.4 would prove the pipeline works with real LLM outputs.
- v0.4 does **not** replace v0.3 — it is a complementary evidence layer for the real model output dimension.

---

*Evidence artifact: `patent_evidence/08_core_v0_3/core_v0_3_attorney_addendum.md`*
*Date: 2026-06-18 | Version: v0.3 Evidence Delivery Addendum*
