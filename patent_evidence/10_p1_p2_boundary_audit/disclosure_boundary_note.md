# Disclosure Boundary Note — P2 Candidate Patent Mechanisms

> **CONFIDENTIAL — PRIVATE REPOSITORY — DO NOT MAKE PUBLIC**
> **机密 — 私有仓库 — 禁止公开**

---

## Non-disclosure Statement

P2's joint planning, model routing, cost estimation, verification coverage constraints, and optimization strategies are **CANDIDATE patent mechanisms** before filing. They **MUST NOT** be disclosed in public README, public API documentation, public examples, public papers, public demonstrations, or public repositories — including their detailed decision rules, parameter designs, optimization objectives, weights, or implementation strategies.

P2 的联合规划、模型路由、成本估算、验证覆盖约束和优化策略在申请提交之前属于**候选专利机制**。其详细决策规则、参数设计、优化目标、权重或实现策略**严禁**在公开 README、公开 API 文档、公开示例、公开论文、公开演示或公开代码仓库中披露。

---

## Scope of This Note

This note applies to the following invention points and their associated technical details:

| ID | Invention Point | Filing Candidate | Disclosure Status |
|---|---|---|---|
| INV-006 | Encoding template selection under token budget constraints | P2 | **DO NOT DISCLOSE** |
| INV-007 | Model routing and verification cost joint scheduling | P2 | **DO NOT DISCLOSE** |
| INV-008 | Multi-source spatial context gap identification | P2 or P3 | **DO NOT DISCLOSE** |
| INV-009 | Industry Domain Pack rule mapping | P4/P5 | **DO NOT DISCLOSE** |
| INV-010 | Human review feedback-driven template optimization | P4 | **DO NOT DISCLOSE** |

---

## Supersession Clause

**This note supersedes any general open-source boundary statements for P2-specific mechanisms.**

The general open-source boundary documented in `docs/open_source_boundary.md` and `docs/open_core_commercial_runtime_boundary.md` applies to the overall GeoTask project. However, for the specific mechanisms listed above (INV-006 through INV-010), this disclosure boundary note provides **stricter and more specific** non-disclosure rules that take precedence.

**本说明针对 P2 特定机制的非披露规则，优先于任何通用的开源边界声明。**

`docs/open_source_boundary.md` 和 `docs/open_core_commercial_runtime_boundary.md` 中的通用开源边界声明适用于 GeoTask 项目整体。但对于上述特定机制（INV-006 至 INV-010），本非披露说明提供**更严格、更具体**的非披露规则，且优先级更高。

---

## Prohibited Disclosure Channels

The following channels MUST NOT contain technical details of P2 candidate mechanisms before filing:

| Channel | Rule |
|---------|------|
| Public README (`README.md`) | No P2 mechanism details; general product capability descriptions are acceptable |
| Public API documentation | No P2 decision rules, parameters, or optimization logic |
| Public examples (`examples/` directory) | No examples that demonstrate P2 joint optimization behavior |
| Public papers or preprints | No P2 technical problem statement, solution, or evaluation |
| Public conference presentations or talks | No P2 mechanism descriptions |
| Public demonstrations or screenshots | No screenshots showing P2 planning/scheduling UI or output |
| Open-source code in public repositories | No P2 implementation code; mock interfaces in `src/geotask_runtime/` are acceptable only if they do not expose P2 decision logic |
| Issue trackers on public platforms | No P2 mechanism discussion in public issues or PRs |
| Social media or blog posts | No P2 technical details |

---

## What MAY Be Disclosed

The following general concepts may be referenced in public materials **without** disclosing P2-specific mechanisms:

- GeoTask supports multiple encoding forms (YAML, Compact DSL, natural language) — this is already public in P1 and open-source code.
- GeoTask is designed to work with multiple LLMs — general concept, no routing logic details.
- GeoTask includes deterministic verification — already public in P1.
- GeoTask may include human review for non-verifiable measurements — general concept in P1's triage.
- Future versions will support cost-aware planning — acceptable as a general roadmap statement, as long as no mechanism details are given.

---

## Specific Mechanisms That MUST NOT Be Disclosed

The following are examples of P2-specific technical details that MUST NOT appear in any public material:

1. How task complexity is assessed and scored
2. How token budget is estimated for each encoding form
3. How model capability is profiled for spatial reasoning tasks
4. How local operator availability affects encoding or routing decisions
5. How verification attainability is assessed per measurement
6. How model invocation cost is estimated or compared
7. How deterministic verification cost is estimated
8. How human review cost is estimated
9. How encoding form is selected based on the above factors
10. How model routing is decided based on the above factors
11. How verification and review paths are assigned
12. How the joint optimization balances cost, coverage, and resource constraints
13. Any weights, thresholds, scoring functions, or optimization objectives
14. Any re-planning or fallback strategies when verification fails

---

## Duration

This non-disclosure boundary remains in effect until:

- P2 is filed and the filing is confirmed by patent counsel, **OR**
- Patent counsel explicitly advises that specific mechanisms may be disclosed, **OR**
- The decision is made to abandon the P2 filing (in which case, disclosure review must still be conducted to protect remaining candidate patents P3–P5).

---

## Responsible Parties

- **Internal team**: Must review all public-facing materials (README updates, documentation changes, example additions, blog posts) for P2 mechanism leaks before publication.
- **Patent counsel**: Should be consulted before any public disclosure that touches on encoding selection, model routing, cost optimization, or verification scheduling.

---

## Cross-references

| Document | Path |
|----------|------|
| P1 Coverage Audit | `patent_evidence/10_p1_p2_boundary_audit/p1_coverage_audit.md` |
| P2 Non-overlap Design | `patent_evidence/10_p1_p2_boundary_audit/p2_non_overlap_design.md` |
| Attorney Questions | `patent_evidence/10_p1_p2_boundary_audit/attorney_questions_for_p1_p2.md` |
| Invention Ledger | `patent_evidence/09_product_architecture_v0_1/invention_ledger.md` |
| Open Source Boundary | `docs/open_source_boundary.md` |
| Commercial Runtime Boundary | `docs/open_core_commercial_runtime_boundary.md` |
| Patent Boundary | `docs/patent_boundary.md` |
