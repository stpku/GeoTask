# P1 Coverage Audit and P2 Non-overlap Analysis

> **CONFIDENTIAL — PRIVATE REPOSITORY — DO NOT MAKE PUBLIC**
> **机密 — 私有仓库 — 禁止公开**

> This document contains an internal preliminary assessment of P1 patent coverage
> across all identified invention points. **No formal P1 claim text was found in
> this repository. All coverage assessments are based on internal evidence files
> and invention story documents, NOT on verified attorney-confirmed claim language.**
>
> 本文档为 P1 专利覆盖范围的内部初步评估。仓库中未找到正式 P1 权利要求文本。所有覆盖
> 评估均基于内部证据文件和发明故事文档，并非基于经代理人确认的正式权利要求书。

---

## 1. Audit Purpose

This audit systematically reviews all 10 invention points (INV-001 through INV-010) from the invention ledger to determine:

- Which invention points are **likely covered** by the filed P1 patent.
- Which are **partially covered** or in an uncertain boundary zone.
- Which are **likely uncovered** and therefore candidates for separate patent filings (P2, P3, P4, P5).
- The **P2 overlap risk** for each invention point — i.e., whether a future P2 filing might inadvertently duplicate P1 scope.

The audit is conducted to support P2 candidate patent boundary design and to generate targeted attorney confirmation questions.

---

## 2. Evidence Sources Reviewed

| Source | Path | Description |
|--------|------|-------------|
| Invention Ledger | `patent_evidence/09_product_architecture_v0_1/invention_ledger.md` | Master inventory of INV-001 through INV-010 |
| Invention Story | `patent_evidence/05_invention_story/technical_problem_solution_effect.md` | P1 technical problem, solution, and effect narrative |
| Claim Mapping | `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` | Patent feature-to-evidence mapping for P1 |
| Attorney Brief | `patent_evidence/00_attorney_brief/attorney_one_page_summary.md` | One-page summary for patent prosecution |
| Benchmark v0.1 | `patent_evidence/03_benchmark/encoding_benchmark_v0_1_summary.md` | Token cost and verification evidence |
| Benchmark v0.2 | `patent_evidence/07_benchmark_v0_2/` | Expanded 24-case benchmark evidence |
| Core v0.3 | `patent_evidence/08_core_v0_3/` | Production normalizer/verifier evidence |
| Patent Portfolio Roadmap | `patent_evidence/09_product_architecture_v0_1/patent_portfolio_roadmap.md` | P1–P5 filing roadmap |
| Product-to-Patent Mapping | `patent_evidence/09_product_architecture_v0_1/product_to_patent_mapping.md` | Module-to-patent direction mapping |
| Code Evidence | `patent_evidence/02_code_evidence/geotask_version_snapshot.md` | Code version snapshot |

---

## 3. Audit Confidence Level

| Level | Definition |
|-------|-----------|
| **High** | Multiple independent evidence sources support the coverage assessment; internal narrative and code evidence are consistent |
| **Medium-High** | Strong evidence from invention story and claim mapping; minor gaps in code-level evidence |
| **Medium** | Evidence supports the assessment directionally but formal claim language is not available for confirmation |
| **Low-Medium** | Limited evidence; coverage assessment is extrapolated from general P1 scope descriptions |
| **Low** | Minimal evidence; coverage assessment is speculative based on P1's stated focus areas |

**Overall audit limitation**: No formal P1 claim text (independent claims, dependent claims) was found in this repository. All assessments are based on internal evidence files. **Attorney confirmation is required for every row.**

> **整体审计局限**：仓库中未找到正式 P1 权利要求文本（独立权利要求、从属权利要求）。所有评估均基于内部证据文件。**每一行均需代理人确认。**

---

## 4. Invention Point Coverage Table

> **Preliminary internal assessment — attorney confirmation required.**
> **内部初步判断，需代理人依据正式提交文本核对确认。**

| ID | Invention Point | Likely P1 Coverage | Confidence | Basis | P2 Overlap Risk | Recommended Action |
|---|---|---|---|---|---|---|
| INV-001 | Task-related spatial encoding | Likely covered | High | Core function of P1, evidence in `patent_evidence/03_benchmark/`, `patent_evidence/05_invention_story/technical_problem_solution_effect.md` (S1, S2), and `benchmarks/encoding_v0_1/inputs/` | Low | Verify with attorney |
| INV-002 | Object-operator-proposition binding | Likely covered | High | Claimed as core mechanism in P1; evidence in `patent_evidence/02_code_evidence/geotask_version_snapshot.md`, `src/geotask_core/models.py`, `src/geotask_core/ops.py`, `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` (row 3) | Low | Verify with attorney |
| INV-003 | Model knowledge augmentation candidate task generation | Likely covered | Medium-High | P1 covers model knowledge augmentation; evidence in `patent_evidence/05_invention_story/technical_problem_solution_effect.md` (S3, S4), `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` (row 9) | Low | Attorney confirmation |
| INV-004 | Verifiability-based triage | Likely covered | High | Central to P1 claims; evidence in `patent_evidence/03_benchmark/encoding_benchmark_v0_1_results.json`, `patent_evidence/06_claim_mapping/claim_to_evidence_matrix.md` (row 6), `src/geotask_core/result_schema.py` | Low | Verify with attorney |
| INV-005 | Model output normalization and deterministic verification | Likely covered | High | Both normalizer and verifier are P1 core; evidence in `patent_evidence/02_code_evidence/test_snapshot.md`, `src/geotask_core/normalizer.py`, `src/geotask_core/verifier.py`, `patent_evidence/08_core_v0_3/core_v0_3_capability_summary.md` | Low | Verify with attorney |
| INV-006 | Encoding template selection under token budget constraints | Partially covered | Medium | P1 may cover encoding generally but not specifically token-budget-aware selection; partial token cost evidence in `benchmarks/encoding_v0_1/outputs/`, `benchmarks/encoding_v0_2/outputs/` | Medium-High | Attorney MUST confirm; likely candidate for P2 |
| INV-007 | Model routing and verification cost joint scheduling | Likely uncovered | Medium | P1 focuses on encoding/verification, not on model-cost-verification joint optimization; no prototype evidence exists | High | Candidate for P2; **DO NOT DISCLOSE** |
| INV-008 | Multi-source spatial context gap identification | Partially covered | Low-Medium | P1 may reference context but not multi-source gap identification specifically; no prototype evidence exists | Medium-High | Candidate for P2 or P3; **DO NOT DISCLOSE** |
| INV-009 | Industry Domain Pack rule mapping | Likely uncovered | Low | P1 is general-purpose; industry rule mapping is a P4/P5 candidate; no domain pack implementation exists | High | Candidate for P4/P5; **DO NOT DISCLOSE** |
| INV-010 | Human review feedback-driven template optimization | Likely uncovered | Low-Medium | P1 may reference review but not feedback-driven optimization specifically; no feedback loop prototype exists | High | Candidate for P4; **DO NOT DISCLOSE** |

> **Preliminary internal assessment — attorney confirmation required.**
> **内部初步判断，需代理人依据正式提交文本核对确认。**

---

## 5. P1 Likely Covered Scope

Based on the evidence reviewed, P1 likely covers the following technical scope:

1. **Task-related spatial encoding** (INV-001) — structured lightweight encoding (YAML / Compact DSL) replacing natural language for spatial tasks sent to LLMs. Evidence: encoding benchmark v0.1 and v0.2; invention story S1/S2.
2. **Object-operator-proposition binding** (INV-002) — three-way binding of spatial objects, deterministic operators, and verifiable propositions. Evidence: production code in `src/geotask_core/models.py` and `ops.py`; claim mapping row 3.
3. **Model knowledge augmentation** (INV-003) — candidate task generation where the LLM fills context gaps within a constrained task structure. Evidence: invention story S3/S4; claim mapping row 9.
4. **Verifiability-based triage** (INV-004) — classifying each measurement as verified / contradicted / need_review based on deterministic verification feasibility. Evidence: benchmark results; `result_schema.py`; claim mapping row 6.
5. **Model output normalization and deterministic verification** (INV-005) — Normalizer extracts structured measurements from unstructured LLM text; Verifier cross-checks against local operator results. Evidence: v0.3 production code; 407 tests; core v0.3 capability summary.

**P1 core technical chain** (as understood from evidence):
```
Spatial task → Structured encoding → LLM invocation → Model output →
Normalizer (extraction) → Verifier (deterministic cross-check) →
Triage (verified / contradicted / need_review)
```

> **Note**: This is an internal reconstruction of P1 scope based on evidence files. Formal P1 claim text was not found in the repository. Attorney confirmation required.
>
> **注意**：以上为基于证据文件的 P1 范围内部重建。仓库中未找到正式 P1 权利要求文本。需代理人确认。

---

## 6. P1 Partially Covered or Uncertain Scope

| ID | Invention Point | Uncertainty |
|---|---|---|
| INV-006 | Encoding template selection under token budget constraints | P1 covers "encoding" broadly but may not specifically claim the mechanism of selecting encoding templates based on token budget, task complexity, and model context window. The benchmark evidence shows token cost comparison across encodings, which could be interpreted as supporting evidence for encoding selection — but the selection algorithm itself may not be in P1 scope. |
| INV-008 | Multi-source spatial context gap identification | P1 may reference "context" in the model knowledge augmentation claims, but multi-source gap identification and data supplement orchestration are likely beyond P1's specific technical scope. |

**These are the highest-priority items for attorney confirmation.** If P1 already covers INV-006 in its dependent claims, P2 must be redesigned to exclude encoding selection and focus purely on model routing + verification cost scheduling.

---

## 7. P1 Likely Uncovered Candidate Scope

| ID | Invention Point | Why Likely Uncovered | Filing Candidate |
|---|---|---|---|
| INV-007 | Model routing and verification cost joint scheduling | P1 focuses on encoding and verification, not on which model to route tasks to or how to jointly optimize model cost and verification cost | **P2** |
| INV-009 | Industry Domain Pack rule mapping | P1 is general-purpose spatial task encoding; industry-specific rule mapping is an extension layer | **P4/P5** |
| INV-010 | Human review feedback-driven template optimization | P1 covers single-pass verification; feedback-driven iterative optimization of templates and thresholds is a separate inventive concept | **P4** |

> **DO NOT DISCLOSE**: The technical details of INV-007, INV-009, and INV-010 MUST NOT appear in any public material before their respective patent filings.
>
> **禁止披露**：INV-007、INV-009 和 INV-010 的技术细节在各自专利申请之前**严禁**出现在任何公开材料中。

---

## 8. Required Attorney Confirmation

The following items require confirmation from patent counsel against the formal P1 submission text:

1. **INV-006 boundary**: Does P1's independent claim or any dependent claim already cover "selecting encoding template form based on token budget constraints and task complexity"? If yes, P2 must exclude encoding selection. If no, INV-006 should be included in P2.

2. **INV-003 scope**: Does P1's model knowledge augmentation claim extend to "context gap identification across multiple data sources," or is it limited to "LLM fills gaps within a given task structure"? This determines whether INV-008 overlaps with P1.

3. **INV-010 boundary**: Does P1 reference "human review feedback" in any claim? If P1's triage (verified / contradicted / need_review) implicitly covers review-driven optimization, INV-010's novelty may be weaker.

4. **Overall P1 independent claim scope**: Without formal claim text in the repository, all coverage assessments above are preliminary. Attorney MUST confirm the actual scope of P1's independent claim(s) and key dependent claims.

> **Attorney confirmation required for all rows in the coverage table.**
> **覆盖表中每一行均需代理人确认。**

---

## 9. Disclosure Control

| Category | Invention IDs | Disclosure Rule |
|----------|---------------|-----------------|
| **Filed in P1 — safe to reference** | INV-001, INV-002, INV-003, INV-004, INV-005 | May be referenced in public materials; core open-source code implements these |
| **Candidate P2 — DO NOT DISCLOSE** | INV-006, INV-007 | Technical details, decision rules, parameter designs, and optimization strategies MUST NOT appear in public README, API docs, papers, demos, or open-source code before filing |
| **Candidate P3 — DO NOT DISCLOSE** | INV-008 | Same non-disclosure rules as P2 |
| **Candidate P4/P5 — DO NOT DISCLOSE** | INV-009, INV-010 | Same non-disclosure rules as P2; general concept references are acceptable but specific mechanisms are not |

> See `patent_evidence/10_p1_p2_boundary_audit/disclosure_boundary_note.md` for detailed non-disclosure rules.
>
> 详见 `patent_evidence/10_p1_p2_boundary_audit/disclosure_boundary_note.md` 中的详细非披露规则。
