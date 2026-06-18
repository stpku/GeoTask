# 10 — P1 Coverage Audit and P2 Non-overlap Boundary Design

> **CONFIDENTIAL — PRIVATE REPOSITORY — DO NOT MAKE PUBLIC**
> **机密 — 私有仓库 — 禁止公开**

> This directory contains internal patent boundary analysis for P1 (filed) and P2 (candidate).
> All P2 mechanisms are **CANDIDATE patent mechanisms — DO NOT DISCLOSE** before filing.
> 所有 P2 机制为**候选专利机制——提交申请前禁止披露**。

---

## Purpose

This directory provides:

1. **P1 coverage audit** — systematic review of which invention points are covered by the filed P1 patent, which are partially covered, and which are uncovered.
2. **P2 non-overlap design** — articulation of the P2 candidate patent scope, explicitly differentiating it from P1 to avoid double-coverage and ensure independent patentability.
3. **Attorney confirmation questions** — specific questions for patent counsel to confirm P1 scope and validate P2 boundary.
4. **Disclosure boundary note** — explicit non-disclosure rules for P2-specific mechanisms.

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `README.md` | This file — overview, security warnings, file index |
| `p1_coverage_audit.md` | Systematic audit of all 10 invention points against P1 likely coverage; confidence levels; P2 overlap risk assessment |
| `p2_non_overlap_design.md` | P2 candidate patent technical scope, inventive concept, technical chain, and explicit differentiation from P1 |
| `attorney_questions_for_p1_p2.md` | Specific questions for patent counsel regarding P1 claim scope and P2 filing strategy |
| `disclosure_boundary_note.md` | Non-disclosure rules for P2-specific mechanisms; supersedes general open-source boundary statements for P2 content |

---

## Cross-References to Other Evidence Directories

| Evidence Directory | Relationship |
|-------------------|-------------|
| `patent_evidence/02_code_evidence/` | Code version snapshots — supports INV-001 through INV-005 |
| `patent_evidence/03_benchmark/` | Encoding benchmark v0.1 — supports INV-001, INV-004 |
| `patent_evidence/05_invention_story/` | Technical problem/solution/effect — supports P1 invention story |
| `patent_evidence/06_claim_mapping/` | Claim-to-evidence matrix — primary basis for P1 coverage audit |
| `patent_evidence/07_benchmark_v0_2/` | Expanded benchmark — supports INV-001, INV-002, INV-004 |
| `patent_evidence/08_core_v0_3/` | Production Core v0.3 — supports INV-002, INV-005 |
| `patent_evidence/09_product_architecture_v0_1/` | Invention ledger, patent portfolio roadmap — source of INV-001 through INV-010 |

---

## Security Warning

1. This repository is **private**. Do not make it public without explicit authorization.
2. P2 candidate mechanisms (INV-006, INV-007) and P3/P4 candidates (INV-008, INV-009, INV-010) describe **unpatented inventions**. Their technical details, decision rules, parameter designs, optimization objectives, and implementation strategies MUST NOT appear in public materials.
3. No real application numbers, attorney names, or filing receipts are stored in this directory.
4. When sharing with patent counsel, reference specific files. Do not share the entire repository unless access policy allows it.

> **安全提醒**：P2 候选机制（INV-006、INV-007）及 P3/P4 候选（INV-008、INV-009、INV-010）描述的是未申请专利的发明。其技术细节、决策规则、参数设计、优化目标和实现策略**严禁**出现在任何公开材料中。

---

## Evidence Version

- **Audit version**: `p1-p2-boundary-audit-v0.1`
- **Date**: 2025-06
- **Source**: `patent_evidence/09_product_architecture_v0_1/invention_ledger.md` (v0.1)
- **Invention points audited**: 10 (INV-001 through INV-010)
