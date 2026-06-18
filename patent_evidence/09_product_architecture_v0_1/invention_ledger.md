# Invention Ledger — GeoTask Patent Portfolio

> **CONFIDENTIAL — PRIVATE REPOSITORY**
> This document tracks all invention points in the GeoTask system.
> Invention points marked "Candidate — DO NOT DISCLOSE" contain unpatented mechanisms.
> Their technical details MUST NOT appear in any public material.

> **机密 — 私有仓库**
> 本文档追踪 GeoTask 系统的所有发明点。
> 标记为"候选——禁止披露"的发明点包含未申请专利的机制，其技术细节不得出现在任何公开材料中。

---

## Ledger Version

- **Version**: v0.1
- **Date**: 2025-06
- **Production test count**: 460 passing tests
- **Core operators**: 6

---

## Invention Point Registry

| ID | Invention Point | Current Status | Included in P1? | Should File Separately? | Disclosure Risk | Evidence Files | Recommended Action |
|----|----------------|----------------|-----------------|------------------------|----------------|----------------|-------------------|
| INV-001 | Task-related spatial encoding — structured lightweight encoding (YAML / Compact DSL) replacing natural language for spatial tasks sent to LLMs | **Filed in P1** | Yes | No — covered by P1 | Low (publicly safe as open-source format) | `patent_evidence/03_benchmark/encoding_benchmark_v0_1_summary.md`, `patent_evidence/05_invention_story/technical_problem_solution_effect.md` (S1, S2), `benchmarks/encoding_v0_1/inputs/`, `benchmarks/encoding_v0_2/cases.yaml` | Maintain evidence; extend benchmark coverage as operators grow |
| INV-002 | Object-operator-proposition binding — three-way binding of spatial objects, deterministic operators, and verifiable propositions | **Filed in P1** | Yes | No — covered by P1 | Low (binding concept disclosed in P1 filing and open-source code) | `patent_evidence/02_code_evidence/geotask_version_snapshot.md`, `src/geotask_core/models.py`, `src/geotask_core/ops.py`, `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` (row 3) | Maintain evidence; v0.3 production code strengthens this claim |
| INV-003 | Model knowledge augmentation — candidate task generation where the LLM fills context gaps within a constrained task structure | **Filed in P1** | Yes | No — covered by P1 | Low (concept disclosed in P1 filing) | `patent_evidence/05_invention_story/technical_problem_solution_effect.md` (S3, S4), `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` (row 9) | Maintain evidence; consider adding live LLM evaluation evidence in future |
| INV-004 | Verifiability-based triage — classifying each measurement as verified / contradicted / need_review based on deterministic verification feasibility | **Filed in P1** | Yes | No — covered by P1 | Low (triage concept disclosed in P1 filing) | `patent_evidence/03_benchmark/encoding_benchmark_v0_1_results.json`, `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` (row 6), `src/geotask_core/result_schema.py` | Maintain evidence; v0.3 unified status hierarchy strengthens this |
| INV-005 | Model output normalization and deterministic verification — Normalizer extracts structured measurements from unstructured LLM text; Verifier cross-checks against local operator results | **Filed in P1** | Yes | No — covered by P1 | Low (mechanism disclosed in P1 filing and open-source code) | `patent_evidence/02_code_evidence/test_snapshot.md`, `src/geotask_core/normalizer.py`, `src/geotask_core/verifier.py`, `patent_evidence/08_core_v0_3/core_v0_3_capability_summary.md`, `patent_evidence/08_core_v0_3/core_v0_3_end_to_end_cases.md` | Maintain evidence; v0.3 production backfill closes the evidence boundary |
| INV-006 | Encoding template selection under token budget constraints — the system selects the optimal encoding template based on task complexity, model context window, and cost constraints | **Candidate P2 — DO NOT DISCLOSE** | No | Yes — file as part of P2 | **HIGH** — mechanism not yet protected; premature disclosure would destroy novelty | `benchmarks/encoding_v0_1/outputs/` (token cost comparison provides partial evidence), `benchmarks/encoding_v0_2/outputs/` (expanded token data). See `patent_evidence/10_p1_p2_boundary_audit/p1_coverage_audit.md` for P1 coverage assessment | Develop internal prototype; prepare evidence before filing; DO NOT describe selection logic in public materials |
| INV-007 | Model routing and verification cost joint scheduling — the system jointly optimizes which model to route spatial tasks to and the expected verification cost | **Candidate P2 — DO NOT DISCLOSE** — See `patent_evidence/10_p1_p2_boundary_audit/p2_non_overlap_design.md` | No | Yes — file as part of P2 | **HIGH** — mechanism not yet protected; no public evidence exists | Evidence needed: internal routing prototype, cost model benchmarks | Design and implement internal prototype; prepare benchmark evidence; DO NOT describe routing strategies in public materials |
| INV-008 | Multi-source spatial context gap identification — the system identifies missing spatial data across heterogeneous sources before encoding and orchestrates data supplement | **Candidate P3 — DO NOT DISCLOSE** | No | Yes — file as part of P3 | **HIGH** — mechanism not yet protected | Evidence needed: gap identification prototype, multi-source integration tests. See also `patent_evidence/10_p1_p2_boundary_audit/` for P1/P2 boundary context | Design internal prototype; prepare evidence before filing; DO NOT describe gap identification logic in public materials |
| INV-009 | Industry Domain Pack rule mapping — the system maps industry-specific rules (e.g., aviation regulations, construction codes) to spatial task templates and constraint verification operators | **Candidate P4 — DO NOT DISCLOSE** | No | Yes — file as part of P4 | **MEDIUM** — concept is known in domain but specific mapping mechanism is novel | Evidence needed: at least one domain pack implementation (e.g., UAV rule pack), rule-to-template mapping tests | Implement first domain pack (UAV); gather constraint verification evidence; DO NOT describe rule mapping mechanisms in public materials |
| INV-010 | Human review feedback-driven template optimization — the system uses human review outcomes (confirmed, corrected, rejected) to optimize encoding templates and verification thresholds over time | **Candidate P4 — DO NOT DISCLOSE** | No | Yes — file as part of P4 | **MEDIUM** — feedback loop concept is general but spatial task-specific application may be novel | Evidence needed: feedback loop prototype, before/after template quality comparison | Design feedback loop; collect initial review data; DO NOT describe optimization mechanisms in public materials |
| INV-011 | Low-altitude site precheck task template and constraint verification — the system composes Core spatial operators into domain-specific precheck workflows for low-altitude flight site evaluation | **Candidate P5 — DO NOT DISCLOSE** | No | Yes — file as part of P5 | **MEDIUM** — low-altitude precheck concept exists but specific task template composition and constraint verification orchestration are novel | `src/geotask_domain_packs/lowalt_site_precheck/`, `tests/test_lowalt_site_precheck_v0_1.py`, `docs/lowalt_site_precheck_pack_v0_1.md`. See `patent_evidence/11_lowalt_site_precheck_v0_1/` | Extend mock MVP to production; gather real domain evidence; DO NOT describe precheck orchestration mechanisms in public materials |

---

## Summary by Filing Status

| Status | Count | Invention IDs |
|--------|-------|---------------|
| Filed in P1 | 5 | INV-001, INV-002, INV-003, INV-004, INV-005 |
| Candidate P2 (Runtime) | 2 | INV-006, INV-007 |
| Candidate P3 (Context Gap) | 1 | INV-008 |
| Candidate P4 (Domain Pack) | 2 | INV-009, INV-010 |
| Candidate P5 (Low-Altitude) | 1 | INV-011 |

---

## Disclosure Risk Matrix

| Risk Level | Invention IDs | Guidance |
|------------|---------------|----------|
| **LOW** — Already filed or publicly disclosed | INV-001, INV-002, INV-003, INV-004, INV-005 | Safe to reference in public materials; core open-source code implements these |
| **HIGH** — Not filed; disclosure destroys novelty | INV-006, INV-007, INV-008 | Strict non-disclosure; no public description of mechanism details |
| **MEDIUM** — Not filed; concept partially public but mechanism novel | INV-009, INV-010, INV-011 | Avoid describing specific mechanism; general concept references are acceptable |

---

## Evidence Gap Analysis

| Invention ID | Evidence Status | Missing Evidence |
|-------------|----------------|-----------------|
| INV-001 | Complete — benchmark v0.1, v0.2, v0.3 evidence | None |
| INV-002 | Complete — code evidence, claim mapping | None |
| INV-003 | Partial — invention story covers concept; no live LLM evaluation | Live LLM candidate generation evaluation |
| INV-004 | Complete — benchmark triage evidence | None |
| INV-005 | Complete — v0.3 production code + 407 tests | None |
| INV-006 | Partial — token cost data exists; no selection algorithm evidence | Encoding selection prototype, selection benchmark |
| INV-007 | Missing — no prototype or evidence | Routing prototype, cost model, routing benchmark |
| INV-008 | Missing — no prototype or evidence | Gap identification prototype, multi-source test suite |
| INV-009 | Missing — no domain pack implementation | First domain pack (UAV), rule mapping tests |
| INV-010 | Missing — no feedback loop prototype | Feedback loop prototype, before/after comparison data |
| INV-011 | Partial — mock MVP exists (domain pack + 14 tests); no real data | Production domain pack with real regulatory rules, real spatial data |

---

## 中文摘要

本发明台账追踪 GeoTask 系统中所有已识别的发明点。INV-001 至 INV-005 已包含在第一件专利（P1）中，证据充分。INV-006 至 INV-011 为候选专利机制，尚未提交申请，其技术细节**严禁**在公开材料中披露。每个发明点均标注了证据文件路径和证据缺口，以指导后续专利申请准备工作。P1/P2 边界审计见 `patent_evidence/10_p1_p2_boundary_audit/`。P5 低空选址预检证据见 `patent_evidence/11_lowalt_site_precheck_v0_1/`。
