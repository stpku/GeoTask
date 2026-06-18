# Attorney Confirmation Questions for P1/P2 Boundary

> **CONFIDENTIAL — PRIVATE REPOSITORY — DO NOT MAKE PUBLIC**
> **机密 — 私有仓库 — 禁止公开**

> These questions should be reviewed by patent counsel against the formal P1
> submission text to confirm coverage scope and validate P2 boundary design.
> No formal P1 claim text was found in this repository; all coverage
> assessments are preliminary internal assessments.
>
> 以下问题需由代理人依据正式 P1 提交文本审核，以确认覆盖范围并验证 P2 边界设计。
> 仓库中未找到正式 P1 权利要求文本；所有覆盖评估均为内部初步判断。

---

## Context for Attorney

- **P1 status**: Filed (no formal claim text stored in this repository)
- **P1 evidence sources**: `patent_evidence/05_invention_story/`, `patent_evidence/06_claim_mapping/`, `patent_evidence/00_attorney_brief/`
- **P2 status**: Candidate — not filed
- **P2 design document**: `patent_evidence/10_p1_p2_boundary_audit/p2_non_overlap_design.md`
- **Invention ledger**: `patent_evidence/09_product_architecture_v0_1/invention_ledger.md`
- **Invention points in question**: INV-006 through INV-010

---

## Questions

### Q1. P1 Independent Claim — Encoding Selection Coverage

Does P1's independent claim already cover **"encoding template selection under token budget constraints"** (INV-006)?

Specifically: does the P1 independent claim or any dependent claim describe a step of choosing between different encoding forms (e.g., natural language, structured YAML, compact DSL) based on token budget, task complexity, or model context window?

**Why this matters**: If P1 covers encoding selection, P2 must exclude it and focus purely on model routing and verification cost scheduling. If P1 does NOT cover encoding selection, INV-006 should be included in P2's scope.

---

### Q2. P1 Dependent Claims — Template Optimization by Verification Pass Rate

Do P1's dependent claims cover **"encoding template optimization based on verification pass rate and token consumption"**?

Specifically: does any P1 dependent claim describe adjusting or optimizing encoding templates based on observed verification success rates and token efficiency metrics?

**Why this matters**: The v0.1 and v0.2 benchmarks (`patent_evidence/03_benchmark/`, `patent_evidence/07_benchmark_v0_2/`) show token cost and verification pass rate comparisons across encoding forms. If P1 already claims optimization based on these metrics, P2 must be careful not to re-claim this as a joint optimization input.

---

### Q3. P1 Coverage — Model Routing and Verification Cost Joint Scheduling

Does P1 cover **"joint scheduling of model routing and local operator verification cost"** (INV-007)?

Specifically: does P1 describe or claim any mechanism for selecting which LLM to invoke based on the expected verification cost, local operator availability, or model invocation cost?

**Why this matters**: INV-007 is a core component of the proposed P2. If P1 already covers model routing or verification cost scheduling in any form, P2's scope must be narrowed accordingly.

---

### Q4. P1 Coverage — Multi-source Context Gap Identification

Does P1 cover **"multi-source context gap identification and data supplement orchestration"** (INV-008)?

Specifically: does P1's "model knowledge augmentation" claim extend to identifying missing spatial data across multiple heterogeneous sources and orchestrating data retrieval before encoding? Or is P1 limited to "the LLM fills gaps within a given task structure"?

**Why this matters**: INV-008 is a candidate for P3. If P1's model knowledge augmentation claims are broad enough to cover multi-source gap identification, INV-008's independent patentability may be weakened.

---

### Q5. P2 Filing Timing

Should P2 be filed separately **as soon as possible after P1**?

Considerations:
- P2 mechanisms are not yet implemented (no prototype evidence).
- However, the conceptual design is documented internally.
- Premature public disclosure (e.g., in README updates, conference talks, or open-source code) could destroy P2 novelty.
- Is there a recommended window for P2 filing relative to P1's filing date?

---

### Q6. P2 Filing Structure — Split or Combined

Should P2 be split into **two separate applications**:
- **P2a**: Encoding planning + model routing under cost and capability constraints
- **P2b**: Context gap identification + data supplement orchestration (currently INV-008, candidate P3)

Or should P2 remain a single application covering the full joint optimization (encoding + routing + verification + review path)?

**Trade-offs**:
- Single application: stronger joint inventive step; simpler portfolio management.
- Split applications: each is more focused; easier to prosecute; one can proceed even if the other faces prior art issues.

---

### Q7. Pre-filing Non-disclosure Scope

Which P2 mechanisms **must NOT appear** in the following before filing:
- Public README (`README.md`)
- Public API documentation
- Public examples (`examples/` directory)
- Public papers or presentations
- Public demonstrations or screenshots
- Open-source code contributions

Specifically: is it safe to mention "model routing" or "encoding selection" as general concepts in public materials, as long as the specific decision rules, cost models, optimization objectives, and parameter designs are not disclosed? Or should even the general concept be avoided?

---

### Q8. P5 (LowAlt Industry Case) Boundary

How should the boundary between **P5** (LowAlt industry-specific spatial task processing) and **P1/P2** be set?

Context:
- P1 is general-purpose spatial task encoding and verification.
- P2 is joint planning/scheduling of encoding, routing, and verification.
- P5 would cover industry-specific rule mapping and domain-specific spatial task templates (INV-009).
- There is also `patent_evidence/11_lowalt_site_precheck_v0_1/` which contains evidence for a specific industry application.

Should P5 be structured as a "method of applying P1/P2 to a specific industry domain," or should it claim independent technical features specific to the domain (e.g., aviation regulation mapping, construction code verification)?

---

## Additional Questions

### Q9. P1 Formal Claim Text Availability

Can the formal P1 submission text (at minimum, the independent claim and key dependent claims) be provided for internal reference? This would significantly improve the accuracy of all P2 boundary assessments.

**Current limitation**: All coverage assessments in `p1_coverage_audit.md` are based on internal evidence files, not on verified claim language.

---

### Q10. Continuation or Divisional Filing Options

If P1's claims are found to be narrower than expected (e.g., P1 does not cover INV-006), is it preferable to:
- (a) File P2 as a completely independent application, or
- (b) File a continuation or divisional application from P1 that extends into encoding selection territory, while filing P2 for the remaining model routing and verification scheduling mechanisms?

---

### Q11. International Filing Strategy

If P2 is filed domestically (CNIPA), should PCT or direct foreign filings (e.g., USPTO) be considered for P2? Does the P1 filing establish any priority date that P2 could benefit from via continuation?

---

## Summary for Attorney Review

| Question | Core Issue | Priority |
|----------|-----------|----------|
| Q1 | Does P1 cover encoding selection under token budget? | **Critical** — determines P2 scope |
| Q2 | Does P1 cover template optimization by pass rate? | **High** — affects P2 overlap risk |
| Q3 | Does P1 cover model routing + verification cost scheduling? | **Critical** — core P2 component |
| Q4 | Does P1 cover multi-source context gap identification? | **Medium** — affects P3 scope |
| Q5 | P2 filing timing | **High** — urgency assessment |
| Q6 | P2 split or combined filing | **Medium** — portfolio strategy |
| Q7 | Pre-filing non-disclosure scope | **High** — operational guidance |
| Q8 | P5 / P1 / P2 boundary | **Medium** — long-term portfolio |
| Q9 | P1 formal claim text availability | **High** — improves all assessments |
| Q10 | Continuation vs. independent filing | **Medium** — filing strategy |
| Q11 | International filing strategy | **Low** — longer-term |
