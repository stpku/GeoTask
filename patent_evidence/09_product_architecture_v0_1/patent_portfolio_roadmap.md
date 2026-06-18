# Patent Portfolio Roadmap — GeoTask

> **CONFIDENTIAL — PRIVATE REPOSITORY**
> This document defines the recommended patent portfolio and filing sequence.
> Technical details of candidate patents (P2–P5) MUST NOT be disclosed in any public material.

> **机密 — 私有仓库**
> 本文档定义推荐的专利组合及提交顺序。
> 候选专利（P2–P5）的技术细节不得在任何公开材料中披露。

---

## Portfolio Overview

| Patent | Title (Working) | Layer | Status | Invention IDs |
|--------|-----------------|-------|--------|---------------|
| P1 | Spatial Task Encoding, Model Knowledge Augmentation, Verifiability Triage, and Deterministic Verification | Core | **Filed** | INV-001 – INV-005 |
| P2 | Encoding Planning Under Token Budget Constraints and Model Routing with Verification Cost Optimization | Runtime | **Candidate** | INV-006, INV-007 |
| P3 | Multi-Source Spatial Context Gap Identification and Data Supplement Orchestration | Context Gap | **Candidate** | INV-008 |
| P4 | Industry Rule Pack, Spatial Task Template Synergy, and Human Review Feedback-Driven Optimization | Domain Pack | **Candidate** | INV-009, INV-010 |
| P5 | Model-Enhanced Spatial Constraint Verification for Low-Altitude Site Precheck or Flight Mission Precheck | Low-Altitude Vertical | **Candidate** | (derived from P1 + P4) |

---

## P1 — Filed

### Scope

- Task-related spatial encoding generation
- Model knowledge augmentation via candidate task generation
- Verifiability-based triage (verified / contradicted / need_review)
- Deterministic verification using local spatial operators

### Evidence Base

| Evidence Type | Path |
|---------------|------|
| Benchmark v0.1 (4 cases, 2 operators) | `patent_evidence/03_benchmark/` |
| Benchmark v0.2 (24 cases, 6 operators) | `patent_evidence/07_benchmark_v0_2/` |
| Core v0.3 production backfill | `patent_evidence/08_core_v0_3/` |
| Invention story | `patent_evidence/05_invention_story/technical_problem_solution_effect.md` |
| Claim mapping matrix | `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` |
| Code evidence | `patent_evidence/02_code_evidence/` |
| Attorney brief | `patent_evidence/00_attorney_brief/attorney_one_page_summary.md` |
| Production code | `src/geotask_core/` (ops.py, normalizer.py, verifier.py, runner.py) |
| Test suite | 460 passing tests |

### Filing Status

Filed. Evidence versions v0.1.1, v0.2, and v0.3 delivered to counsel.

---

## P2 — Candidate: Runtime Encoding & Routing

> **CRITICAL WARNING / 严重警告**
>
> At minimum, before the technical solution is finalized and the patent application is prepared, DO NOT disclose key encoding selection logic, model routing strategies, or cost optimization mechanisms in public repositories, public README, public papers, or public presentation materials.
>
> 在技术方案定稿并准备专利申请之前，**严禁**在公开仓库、公开 README、公开论文或公开演示材料中披露关键的编码选择逻辑、模型路由策略或成本优化机制。

### Technical Problem Solved

When multiple encoding templates exist (natural language, YAML, Compact DSL, and future variants) and multiple models are available, the system must decide: (a) which encoding template minimizes token cost while maintaining verification capability for the given task, and (b) which model to route the spatial task to, considering both inference cost and expected verification cost.

### Core Technical Approach

[REDACTED — Candidate patent mechanism. Technical details restricted to internal design documents and patent drafts.]

### Difference from P1

P1 defines the **encoding format** and **verification method**. P2 addresses the **runtime decision layer** — the system that selects encoding templates and routes tasks to models. P1 operates at the level of "what to encode and how to verify"; P2 operates at the level of "which encoding to choose and which model to use."

### Suitable for Immediate Filing?

Not yet. Requires internal prototype implementation and benchmark evidence demonstrating encoding selection effectiveness and routing optimization.

### Code/Evidence Needed Before Filing

| Requirement | Status |
|------------|--------|
| Encoding selection prototype | Not started |
| Multi-template benchmark (token cost vs. verification success) | Partial — v0.1 benchmark provides cross-encoding token comparison |
| Model routing prototype | Not started |
| Joint cost optimization benchmark | Not started |
| Internal design document | Not started |

### Disclosure Risk

**HIGH**. No patent protection exists for these mechanisms. Premature disclosure in public materials, README, documentation, or presentations would destroy novelty and prevent future patent filing.

---

## P3 — Candidate: Context Gap Identification

> **WARNING**: Technical details of this candidate patent MUST NOT be disclosed publicly.

### Technical Problem Solved

Before encoding a spatial task, the system must identify what spatial data is missing — which objects lack coordinates, which relationships are undefined, which data sources have gaps. This pre-encoding analysis across multiple heterogeneous data sources enables the system to orchestrate data supplement before task execution.

### Core Technical Approach

[REDACTED — Candidate patent mechanism. Technical details restricted to internal design documents and patent drafts.]

### Difference from P1

P1 generates candidate spatial content within a **single encoding** using model knowledge. P3 addresses **pre-encoding data analysis** — identifying gaps across multiple data sources before the encoding is constructed. P1 is encoding-level; P3 is data-source-level.

### Suitable for Immediate Filing?

Not yet. Requires prototype for multi-source gap identification and data supplement orchestration.

### Code/Evidence Needed Before Filing

| Requirement | Status |
|------------|--------|
| Gap identification prototype | Not started |
| Multi-source data connector prototype | Not started |
| Gap-to-supplement orchestration tests | Not started |
| Internal design document | Not started |

### Disclosure Risk

**HIGH**. No existing protection. Premature disclosure destroys novelty.

---

## P4 — Candidate: Domain Pack & Human Feedback

> **WARNING**: Technical details of this candidate patent MUST NOT be disclosed publicly.

### Technical Problem Solved

Different industries (aviation, construction, environmental monitoring) have domain-specific spatial constraints. The system must: (a) map industry rules to spatial task templates and constraint verification operators, and (b) use human review feedback (confirmed, corrected, rejected) to improve encoding templates and verification thresholds over time.

### Core Technical Approach

[REDACTED — Candidate patent mechanism. Technical details restricted to internal design documents and patent drafts.]

### Difference from P1

P1 provides **general-purpose** spatial verification. P4 extends to **domain-specific** constraint verification (e.g., aviation altitude restrictions, construction setback rules) and adds a **closed-loop optimization** mechanism driven by human review outcomes. P1 is domain-agnostic; P4 is domain-aware and self-improving.

### Suitable for Immediate Filing?

Not yet. Requires at least one domain pack implementation (recommended: UAV rule pack) and initial human review feedback data.

### Code/Evidence Needed Before Filing

| Requirement | Status |
|------------|--------|
| First domain pack implementation (UAV) | Not started — GeoTask UAV is a planned component |
| Rule-to-template mapping prototype | Not started |
| Constraint verification operator tests | Not started |
| Human review feedback loop prototype | Not started |
| Before/after template quality comparison | Not started |
| Internal design document | Not started |

### Disclosure Risk

**MEDIUM**. Domain pack concept is mentioned at a high level in the public README architecture diagram. However, the specific rule mapping mechanisms, template synergy algorithms, and feedback loop implementations are not disclosed. Avoid further public detail.

---

## P5 — Candidate: Low-Altitude Spatial Verification

> **WARNING**: Technical details of this candidate patent MUST NOT be disclosed publicly.

### Technical Problem Solved

Low-altitude operations (drone flights, urban air mobility) require spatial constraint verification against regulatory zones, altitude restrictions, time windows, and ground obstacles. The system must verify that a proposed flight path or site location satisfies all applicable spatial constraints before mission execution.

### Core Technical Approach

[REDACTED — Candidate patent mechanism. Technical details restricted to internal design documents and patent drafts.]

### Difference from P1

P1 provides general spatial verification with abstract operators. P5 applies the P1 verification framework and the P4 domain pack to a **specific vertical** — low-altitude operations — with additional regulatory constraints, safety margins, and real-time data integration requirements.

### Suitable for Immediate Filing?

Not yet. P5 depends on P4 (domain pack framework). Filing P5 before P4 would create dependency gaps in the claims. However, mock MVP evidence is now available.

### Code/Evidence Needed Before Filing

| Requirement | Status |
|------------|--------|
| UAV domain pack (depends on P4) | Not started |
| Low-altitude constraint operator set | Partial — altitude_overlap and time_overlap operators exist in Core v0.3 |
| LowAlt site precheck mock MVP | **Done** — `src/geotask_domain_packs/lowalt_site_precheck/`, 14 tests passing |
| Regulatory zone verification tests | Partial — mock tests with fictional coordinates |
| Flight path spatial constraint benchmark | Not started |
| Internal design document | Partial — `docs/lowalt_site_precheck_pack_v0_1.md` |

### Mock MVP Evidence

- **Status**: Candidate — Mock evidence in progress — DO NOT DISCLOSE
- **Evidence**: `patent_evidence/11_lowalt_site_precheck_v0_1/`
- **Code**: `src/geotask_domain_packs/lowalt_site_precheck/`
- **Tests**: `tests/test_lowalt_site_precheck_v0_1.py` (14 tests)
- **Documentation**: `docs/lowalt_site_precheck_pack_v0_1.md`

### Disclosure Risk

**MEDIUM**. The public README mentions "GeoTask UAV" as a planned component, but no mechanism details are disclosed. The existence of altitude_overlap and time_overlap operators in the open-source Core does not disclose the P5-specific verification mechanisms.

---

## Recommended Filing Sequence

```
P1 (Filed) ──→ P2 (Next priority) ──→ P3 ──→ P4 ──→ P5
     │                                          │
     └── Core format & verification             └── P5 depends on P4
```

| Priority | Patent | Rationale |
|----------|--------|-----------|
| 1 (Done) | P1 | Foundation — encoding, verification, triage |
| 2 (Next) | P2 | Runtime is the commercial core; encoding selection and model routing are key competitive differentiators |
| 3 | P3 | Context gap identification adds value but requires multi-source data integration infrastructure |
| 4 | P4 | Domain pack requires at least one domain implementation for credible evidence |
| 5 | P5 | Vertical application; depends on P4 domain pack framework |

---

## 中文摘要

### 专利组合路线图

- **P1（已提交）**：任务相关空间编码、模型知识增强、可验证性分流、确定性验证。证据充分（v0.1.1、v0.2、v0.3）。
- **P2（候选 — Runtime）**：编码规划与模型路由。商业核心竞争力所在，建议优先准备。**技术细节严禁公开披露。**
- **P3（候选 — 上下文缺口）**：多源空间上下文缺口识别。需多源数据集成基础设施。**技术细节严禁公开披露。**
- **P4（候选 — Domain Pack）**：行业规则包与人工复核反馈优化。需至少一个行业包实现。**技术细节严禁公开披露。**
- **P5（候选 — 低空垂直应用）**：低空场景空间约束验证。依赖 P4 行业包框架。Mock MVP 证据已就绪。**技术细节严禁公开披露。**

### 建议提交顺序

P1（已完成）→ P2（下一优先级）→ P3 → P4 → P5
