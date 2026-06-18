# Product Architecture Patent Positioning

> **CONFIDENTIAL — PRIVATE REPOSITORY**
> This document contains patent strategy information. Do NOT make public.
> Candidate patent mechanisms (P2–P5) MUST NOT be disclosed in any public material.

> **机密 — 私有仓库**
> 本文档包含专利策略信息。请勿公开。
> 候选专利机制（P2–P5）不得在任何公开材料中披露。

---

## 1. P1 — First Patent (Filed)

### Scope

The first patent covers the following four technical pillars:

| Pillar | Description | Core Evidence |
|--------|-------------|---------------|
| Task-Related Spatial Encoding | Lightweight structured encoding (GeoTask YAML / Compact DSL) that represents spatial objects, operators, and tasks for LLM consumption, replacing verbose natural language | `patent_evidence/03_benchmark/`, `benchmarks/encoding_v0_1/` |
| Model Knowledge Augmentation | The system defines a context boundary; the LLM fills candidate spatial content from its training knowledge within the constrained task structure | `patent_evidence/05_invention_story/technical_problem_solution_effect.md` (S3, S4) |
| Verifiability-Based Triage | The system classifies each measurement as `verified`, `contradicted`, or `need_review` based on whether deterministic local verification is possible | `patent_evidence/03_benchmark/encoding_benchmark_v0_1_results.json`, `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` |
| Deterministic Verification | Local operators (distance_2d, line_intersects_rect, etc.) compute ground truth and cross-check against normalized model output | `src/geotask_core/verifier.py`, `src/geotask_core/ops.py`, `patent_evidence/08_core_v0_3/` |

### Key Metrics Supporting P1

- 6 spatial operators in production Core (`src/geotask_core/ops.py`)
- 407 passing tests across the test suite
- 77.7% token reduction (Compact DSL vs. natural language)
- 100% normalization success rate across all benchmark encodings
- Contradiction detection for wrong distances and incorrect boolean judgments

---

## 2. Runtime — Engineering Carrier for P1

The GeoTask Runtime is the **engineering carrier** that implements the P1 patent claims in a deployable system. The Runtime is NOT a "generic model calling platform" or "LLM API wrapper."

### What the Runtime Implements

| Runtime Component | Patent Relationship |
|-------------------|---------------------|
| Encoding Planner | Implements task-related spatial encoding generation (P1 Pillar 1) |
| Model Adapter | Implements model knowledge augmentation by constraining LLM input/output within the encoding structure (P1 Pillar 2) |
| Result Governor | Implements verifiability-based triage and deterministic verification (P1 Pillars 3–4) |

### Why This Distinction Matters

- Patent claims should describe the **system and method** — the technical mechanism — not the product brand.
- The Runtime is the **concrete implementation** of the patent claims. Describing the Runtime as a "generic model calling platform" would weaken patent scope by conflating it with commodity API orchestration tools.
- Patent-neutral terminology: "spatial task intermediate representation system" rather than "GeoTask Runtime."

---

## 3. Candidate Future Patents

> **WARNING**: The technical mechanisms described below are NOT yet patented.
> At minimum, before the technical solution is finalized and the patent application is prepared:
> - DO NOT disclose key mechanism details in public repositories
> - DO NOT describe these mechanisms in public README or documentation
> - DO NOT include these mechanisms in public papers or presentations
> - DO NOT discuss these mechanisms in public issues or pull requests

### P2 Candidate — Runtime Encoding & Routing

**Technical problems addressed**: Encoding selection under token budget constraints; model routing with verification cost optimization.

**Relationship to P1**: P1 defines the encoding format and verification method. P2 extends to the **runtime decision layer** — how to select the optimal encoding template and which model to route to based on task complexity and cost constraints.

### P3 Candidate — Context Gap Identification

**Technical problem addressed**: Multi-source spatial context gap identification — the system identifies what spatial data is missing before encoding and orchestrates data supplement from heterogeneous sources.

**Relationship to P1**: P1 defines context gap generation within a single encoding. P3 extends to **pre-encoding analysis** across multiple data sources.

### P4 Candidate — Domain Pack & Human Feedback

**Technical problems addressed**: Industry rule pack and spatial task template synergy; human review feedback-driven encoding optimization.

**Relationship to P1**: P1 provides the general verification mechanism. P4 extends to **domain-specific constraint verification** and **closed-loop template improvement** from human review outcomes.

### P5 Candidate — Low-Altitude Spatial Verification

**Technical problem addressed**: Model-enhanced spatial constraint verification for low-altitude site precheck or flight mission precheck.

**Relationship to P1**: P1 provides general spatial verification. P5 extends to a **specific vertical application** with regulatory and safety constraints.

---

## 4. Product Layer → Patent Claim Mapping

```
┌─────────────────────────────────────────────────────────────┐
│  Domain Pack (Industry Rules, Templates, Workflows)         │  ← P4 candidate claims
│  商业交付资产 — 行业规则、模板、工作流                          │
├─────────────────────────────────────────────────────────────┤
│  Runtime (Encoding Planner, Model Router, Result Governor)  │  ← P2 candidate claims
│  商业核心 — 编码规划、模型路由、结果治理                        │
├─────────────────────────────────────────────────────────────┤
│  GeoTask Core (Format, Operators, Normalizer, Verifier)     │  ← P1 filed claims
│  轻量基础 — 格式定义、确定性算子、归一化、验证                   │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Patent Direction | Claim Type | Filing Status |
|-------|-----------------|------------|---------------|
| GeoTask Core | P1 — Encoding format, object-operator binding, normalization, verification | System and method claims | **Filed** |
| Runtime | P2 — Encoding planning, model routing, cost optimization | Orchestration and routing claims | **Candidate — NOT filed** |
| Context Gap Analyzer | P3 — Multi-source gap identification, data supplement | Data orchestration claims | **Candidate — NOT filed** |
| Domain Pack | P4 — Industry rules, templates, human feedback loop | Industry rule and template claims | **Candidate — NOT filed** |
| Low-Altitude Vertical | P5 — Spatial constraint verification for low-altitude operations | Vertical application claims | **Candidate — NOT filed** |

---

## 5. Disclosure Risk Summary

| Layer | Public-Safe Content | Must-Not-Disclose Content |
|-------|--------------------|-----------------------------|
| GeoTask Core | Format specification, YAML examples, basic operator definitions, open-source code under MIT | Detailed normalizer/verifier internal logic specific to patent claims (already disclosed in P1 filing) |
| Runtime | General architecture diagram (3-layer stack) | Encoding selection logic, model routing strategies, cost optimization mechanisms |
| Domain Pack | Existence of domain pack concept | Specific rule mapping mechanisms, template synergy algorithms, feedback loop implementation |

---

## 6. 中文摘要

### P1（已提交）

第一件专利覆盖四大技术支柱：任务相关空间编码、模型知识增强、可验证性分流、确定性验证。Core 层的格式定义和验证机制是 P1 权利要求的技术载体。

### Runtime 定位

Runtime 是 P1 专利权利要求的工程实现载体，不应被描述为"通用模型调用平台"。

### 候选专利（P2–P5）

P2–P5 覆盖编码规划与模型路由（P2）、多源上下文缺口识别（P3）、行业规则包与模板协同（P4）、低空垂直应用（P5）。这些候选机制的技术细节在专利申请准备完成前，**严禁**在公开仓库、公开文档、公开论文或公开演示材料中披露。
