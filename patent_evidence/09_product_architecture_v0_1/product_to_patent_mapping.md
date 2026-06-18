# Product Module → Patent Direction Mapping

> **CONFIDENTIAL — PRIVATE REPOSITORY**
> This document maps product modules to patent directions.
> Modules marked "NOT public-safe" contain unpatented mechanisms. Do NOT disclose details publicly.

> **机密 — 私有仓库**
> 本文档将产品模块映射到专利方向。
> 标记为"不可公开"的模块包含未申请专利的机制，请勿公开披露细节。

---

## Mapping Table

| Product Module | Technical Capability | Corresponding Patent Direction | Current Evidence | Public-Safe? |
|---------------|---------------------|-------------------------------|-----------------|-------------|
| **GeoTask Core** | Structured spatial task encoding (YAML / Compact DSL); object type definitions (point, line, rect); 6 deterministic operators (distance_2d, line_intersects_rect, point_to_line_distance_2d, rect_contains_point, time_overlap, altitude_overlap) | **P1 (Filed)** — Task-related spatial encoding, object-operator-proposition binding | `src/geotask_core/ops.py`, `src/geotask_core/models.py`, `src/geotask_core/parser.py`, `patent_evidence/03_benchmark/`, `patent_evidence/07_benchmark_v0_2/` | **Yes** — Open-source under MIT; format and operators are publicly disclosed |
| **GeoTask Core — Normalizer** | Extracts structured measurements from unstructured LLM text output; supports multi-operator extraction, unit detection, Chinese negation, Markdown/YAML format handling | **P1 (Filed)** — Model output normalization | `src/geotask_core/normalizer.py`, `patent_evidence/08_core_v0_3/core_v0_3_capability_summary.md`, `patent_evidence/02_code_evidence/test_snapshot.md` | **Yes** — Open-source under MIT; normalizer code is public |
| **GeoTask Core — Verifier** | Cross-checks normalized model output against deterministic local operator results; produces unified status (verified / contradicted / need_review); supports invalid_operator and invalid_reference detection | **P1 (Filed)** — Deterministic verification, verifiability-based triage | `src/geotask_core/verifier.py`, `src/geotask_core/result_schema.py`, `patent_evidence/08_core_v0_3/core_v0_3_end_to_end_cases.md` | **Yes** — Open-source under MIT; verifier code is public |
| **Encoding Planner** | Selects optimal encoding template based on task complexity, model context window, and token budget constraints | **P2 (Candidate — DO NOT DISCLOSE)** — Encoding planning under token budget constraints | Partial: `benchmarks/encoding_v0_1/outputs/` (token cost comparison across encodings); encoding selection algorithm evidence NOT yet available | **NO** — Selection logic is unpatented; disclosure destroys novelty |
| **Model Router** | Routes spatial tasks to optimal model considering inference cost, expected verification cost, and model spatial reasoning capability | **P2 (Candidate — DO NOT DISCLOSE)** — Model routing and verification cost joint scheduling | Evidence NOT yet available; no routing prototype exists | **NO** — Routing strategy is unpatented; disclosure destroys novelty |
| **Result Governor** | Orchestrates the normalization → verification → triage pipeline; enforces status hierarchy; generates review reasons; computes overall task status | **P1 (Filed)** — Verifiability triage and status-aware output | `src/geotask_core/result_schema.py`, `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` (rows 6, 7) | **Partially** — General pipeline is public; governance policies and escalation logic for Runtime are not |
| **Context Gap Analyzer** | Identifies missing spatial data across heterogeneous sources before encoding; orchestrates data supplement from external sources | **P3 (Candidate — DO NOT DISCLOSE)** — Multi-source spatial context gap identification | Evidence NOT yet available; no gap identification prototype exists | **NO** — Gap identification logic is unpatented; disclosure destroys novelty |
| **Domain Pack** | Maps industry-specific rules (aviation, construction, environmental) to spatial task templates and constraint verification operators; provides industry-specific object libraries and scoring logic | **P4 (Candidate — DO NOT DISCLOSE)** — Industry rule pack and spatial task template synergy | Evidence NOT yet available; GeoTask UAV is planned but not implemented | **NO** — Rule mapping mechanisms are unpatented; high-level concept (existence of domain packs) is public but mechanism details are not |
| **Human Review Feedback Loop** | Collects human review outcomes (confirmed, corrected, rejected) and uses them to optimize encoding templates, verification thresholds, and triage policies over time | **P4 (Candidate — DO NOT DISCLOSE)** — Human review feedback-driven template optimization | Evidence NOT yet available; no feedback loop prototype exists | **NO** — Feedback optimization mechanism is unpatented; disclosure destroys novelty |
| **LowAlt Site Precheck Pack** | Low-altitude site precheck constraint verification — composes Core operators into domain-specific precheck workflows for flight site evaluation | **P5 (Candidate — DO NOT DISCLOSE)** — Model-enhanced spatial constraint verification for low-altitude site precheck | `src/geotask_domain_packs/lowalt_site_precheck/`, `tests/test_lowalt_site_precheck_v0_1.py`, `patent_evidence/11_lowalt_site_precheck_v0_1/` | **NO** — DO NOT DISCLOSE — precheck orchestration mechanism is unpatented |

---

## Evidence Status Summary

| Patent Direction | Modules with Complete Evidence | Modules with Partial Evidence | Modules with No Evidence |
|-----------------|-------------------------------|------------------------------|--------------------------|
| P1 (Filed) | GeoTask Core, Normalizer, Verifier, Result Governor | — | — |
| P2 (Candidate) | — | Encoding Planner (token data exists) | Model Router |
| P3 (Candidate) | — | — | Context Gap Analyzer |
| P4 (Candidate) | — | — | Domain Pack, Human Review Feedback Loop |
| P5 (Candidate) | — | LowAlt Site Precheck Pack (mock MVP) | — |

---

## Public Disclosure Boundary

```
┌──────────────────────────────────────────────────────────────────┐
│  PUBLIC-SAFE (open-source, P1 filed)                            │
│                                                                  │
│  GeoTask Core: format spec, operators, normalizer, verifier     │
│  Examples, benchmarks, test results, CLI                        │
│  General architecture diagram (3-layer stack)                   │
├──────────────────────────────────────────────────────────────────┤
│  MUST NOT DISCLOSE (unpatented, candidates P2–P4)               │
│                                                                  │
│  Encoding selection logic (P2)                                  │
│  Model routing strategies (P2)                                  │
│  Cost optimization mechanisms (P2)                              │
│  Gap identification algorithms (P3)                             │
│  Rule mapping mechanisms (P4)                                   │
│  Template synergy algorithms (P4)                               │
│  Feedback loop optimization (P4)                                │
│  LowAlt precheck orchestration (P5)                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 中文摘要

本映射表将 GeoTask 产品模块映射到对应的专利方向。

- **GeoTask Core**（格式、算子、归一化器、验证器）→ P1（已提交），可公开。
- **编码规划器、模型路由器** → P2（候选），不可公开。
- **上下文缺口分析器** → P3（候选），不可公开。
- **行业规则包、人工复核反馈环** → P4（候选），不可公开。
- **低空选址预检 Domain Pack** → P5（候选），不可公开。

对于 P2–P5 候选专利方向涉及的模块，其技术机制细节在专利申请准备完成前**严禁**在公开材料中披露。
