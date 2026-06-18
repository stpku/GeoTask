# GeoTask Core v0.3 — Claim Support Update

> Maps v0.3 production Core evidence to patent technical features.
> Upgrades from v0.2 benchmark-local evidence to production Core evidence.

## Evidence Upgrade Path

```
v0.1.1: Core end-to-end (2 ops) ──→ Backbone evidence
v0.2:   Benchmark structural (6 ops) ──→ Extensibility evidence
v0.3:   Core backfill (6 ops) ──→ Production multi-operator evidence ✓
```

## Enhanced Patent Support

| Patent Feature | v0.2 (Benchmark) | v0.3 (Core) | Upgrade |
|---------------|-----------------|-------------|---------|
| 任务相关空间编码 | DSL 35% fewer tokens | Same + Core ops | Production-grade |
| 令牌预算约束 | Approximate tokens | Same | Expanded cases |
| 对象—算子—命题绑定 | 6 operators in benchmark | 6 operators in **Core** | Backfilled to Core |
| 模型输出归一化 | Local verifier | **Production Normalizer** | Core normalizer support |
| 本地确定性验证 | Local verifier | **Production Verifier** | Core verifier support |
| 可验证性分流 | 8 error types in benchmark | 8 error types in **Core** | Production status hierarchy |
| 状态化输出 | Benchmark status | **Unified Core status** | invalid_op/ref added |
| 编码模板优化 | Benchmark scores | Core end-to-end tests | Production evidence |

## Key v0.3 Evidence for Prosecution

### Closing the v0.2 Local-Verifier Boundary

v0.2 demonstrated structural extensibility but relied on `benchmarks/encoding_v0_2/local_verifier.py` — a benchmark-layer verifier. v0.3 moves stable multi-operator normalization and verification into production `src/geotask_core/`, strengthening patent support:

- **Stronger claim support**: v0.3 evidence is directly traceable to the claimed production system (normalizer.py + verifier.py), not a benchmark utility.
- **Broader operator coverage**: All 6 operators now in production Core, not just 2.
- **Production status routing**: invalid_operator and invalid_reference detection now in production verifier.

> v0.3 通过将稳定的多算子归一化和验证能力迁移至生产级 GeoTask Core，关闭了 v0.2 的 benchmark local verifier 证据边界，使专利支撑从 benchmark 结构证据升级为 production Core 可执行证据。

### Claim: Production Normalizer supports 6 operators

v0.3 normalizer (`src/geotask_core/normalizer.py`) now supports:
- distance_2d, line_intersects_rect (existing)
- point_to_line_distance_2d, rect_contains_point, time_overlap, altitude_overlap (NEW in Core)

### Claim: Unified status hierarchy

v0.3 verifier produces a priority-ordered overall status:
```
invalid_operator > invalid_reference > contradicted > need_review > verified
```

### Claim: Robust error detection in production code

8 error types detected in production Core code (not just benchmark):
- Wrong numeric values, wrong booleans, missing operators, missing values
- Invalid operators, invalid references, unit mismatch, Chinese negation

---

*Evidence artifact: `patent_evidence/08_core_v0_3/core_v0_3_claim_support_update.md`*
*Extends: `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md`*
