# P2 Candidate Patent: Encoding Planning, Model Routing and Verification-cost Joint Scheduling

> **CONFIDENTIAL — PRIVATE REPOSITORY — DO NOT MAKE PUBLIC**
> **机密 — 私有仓库 — 禁止公开**

> **DO NOT DISCLOSE**: This document describes a **candidate patent mechanism** that has
> NOT been filed. All technical details herein — including decision rules, parameter
> designs, optimization objectives, cost models, and implementation strategies — MUST
> NOT appear in any public material before filing.
>
> **禁止披露**：本文档描述的是**尚未提交申请的候选专利机制**。文中所有技术细节——包括
> 决策规则、参数设计、优化目标、成本模型和实现策略——在申请提交之前**严禁**出现在任何
> 公开材料中。

---

## 1. Technical Problem

Current spatial task LLM systems face a **joint optimization gap**: after encoding a spatial task and sending it to an LLM, there is no systematic method to jointly plan the encoding form, model invocation method, local verification approach, and human review path under multi-dimensional constraints (task complexity, token budget, model capability, invocation cost, local operator availability, verification cost, and human review cost).

P1 addresses the encoding and verification pipeline but does not address the **planning and scheduling** of that pipeline under cost and resource constraints.

Specific sub-problems P2 addresses:

1. Different spatial tasks have different complexity levels, but the encoding form is currently chosen without considering the model's token budget or capability profile.
2. Different LLMs have different capabilities and costs, but model routing is currently not informed by verification attainability or local operator availability.
3. Deterministic verification and human review both have costs, but there is no joint cost model that optimizes total verification coverage under a budget constraint.
4. The encoding form, model selection, verification method, and review path are currently treated as independent decisions rather than jointly optimized.

---

## 2. P2 Core Inventive Concept

> Under spatial task verifiability constraints, jointly model task complexity, token budget, model capability, model invocation cost, local operator availability, deterministic verification cost, and human review cost; based on this joint model, plan and schedule the spatial task encoding form, model invocation method, local verification method, and review path.

> 在空间任务可验证性约束下，对任务复杂度、令牌预算、模型能力、模型调用成本、本地算子可用性、确定性验证成本和人工复核成本进行联合建模，并据此对空间任务编码形式、模型调用方式、本地验证方式和复核路径进行联合规划与调度。

**P2 MUST NOT be reduced to "selecting DSL or YAML under token budget."** P2 is NOT merely encoding selection. P2 is a joint optimization of encoding form, model routing, verification path, and review path under multi-dimensional constraints including verifiability coverage, cost budget, and resource availability.

> **P2 绝不能被矮化为"在令牌预算下选择 DSL 还是 YAML"。** P2 不仅仅是编码选择。P2 是在可验证性覆盖、成本预算和资源可用性等多维约束下，对编码形式、模型路由、验证路径和复核路径的联合优化。

---

## 3. Difference from P1

```
P1 focus: Task-related spatial encoding, model knowledge augmentation,
          verifiability-based triage, and deterministic verification.

P2 focus: Joint planning and scheduling of encoding, model routing, and
          verification under verifiability, cost, and resource constraints.
```

| Dimension | P1 Scope | P2 Scope |
|-----------|---------|---------|
| Encoding | Defines structured encoding formats (YAML, Compact DSL) for spatial tasks | Plans which encoding form to use based on task complexity, token budget, and model capability |
| Model invocation | Assumes a model is invoked; focuses on what happens after output | Routes tasks to specific models based on capability profile, cost, and verification attainability |
| Verification | Normalizer + Verifier pipeline; triage into verified/contradicted/need_review | Schedules verification method (deterministic vs. human review) based on cost and coverage constraints |
| Review | Identifies need_review cases | Plans the review path (which items to human-review, at what cost, under what coverage target) |
| Optimization | Not addressed — each stage is independent | Joint optimization of encoding + routing + verification + review under a unified cost/coverage model |
| Cost modeling | Not addressed | Models token cost, model invocation cost, verification cost, and human review cost jointly |

**Key differentiator**: P1 is the *pipeline* (encode → invoke → normalize → verify → triage). P2 is the *planner and scheduler* that optimizes how that pipeline is configured for each task under constraints.

---

## 4. Candidate Technical Chain

> **DO NOT DISCLOSE** — The following technical chain describes candidate patent mechanisms.
> **禁止披露** — 以下技术链描述的是候选专利机制。

```
Step 1:  Task complexity assessment
         → Analyze spatial task structure to determine complexity level

Step 2:  Token budget estimation
         → Estimate token consumption for each candidate encoding form

Step 3:  Model capability profiling
         → Profile available models for spatial reasoning capability and context window

Step 4:  Local operator availability assessment
         → Determine which deterministic operators are available for the task's spatial types

Step 5:  Verification attainability assessment
         → For each measurement in the task, assess whether deterministic verification
           is attainable given available operators

Step 6:  Model invocation cost estimation
         → Estimate invocation cost for each candidate model given the encoding and task

Step 7:  Deterministic verification cost estimation
         → Estimate computational cost of running local operators for verification

Step 8:  Human review cost estimation
         → Estimate cost of human review for measurements that cannot be deterministically verified

Step 9:  Encoding form selection
         → Select encoding form (natural language / YAML / Compact DSL / hybrid) based on
           task complexity, token budget, and model capability

Step 10: Model routing selection
         → Route the task to the optimal model based on capability, cost, and verification
           attainability

Step 11: Local verification and review path selection
         → Assign each measurement to deterministic verification or human review based on
           operator availability and cost

Step 12: Joint optimization result under verification coverage constraints
         → Produce the jointly optimized plan: encoding form + model routing + verification
           path + review path, satisfying the verification coverage target within the cost
           budget
```

---

## 5. Candidate Independent Claim Direction

> **DO NOT DISCLOSE** — Claim direction is a candidate; attorney must draft formal claim language.
> **禁止披露** — 以下为权利要求方向草案；正式权利要求书须由代理人撰写。

**Direction**: A method/system for jointly planning spatial task encoding, model routing, and verification scheduling, comprising:

- Receiving a spatial task with one or more spatial objects and operations;
- Assessing task complexity and estimating token budget for candidate encoding forms;
- Profiling available model capabilities and invocation costs;
- Assessing local operator availability and verification attainability for each measurement;
- Estimating deterministic verification cost and human review cost;
- Jointly selecting, under a verification coverage constraint and a cost budget constraint, the encoding form, model routing, local verification method, and human review path;
- Outputting the jointly optimized plan for execution.

---

## 6. Candidate Dependent Claim Directions

> **DO NOT DISCLOSE** — These are candidate directions; attorney must confirm and draft.
> **禁止披露** — 以下为候选从属权利要求方向；代理人须确认并撰写。

1. The method of claim 1, wherein task complexity assessment uses spatial object type count, operator count, and inter-object relationship complexity.
2. The method of claim 1, wherein token budget estimation computes approximate token counts for each encoding form and compares against the selected model's context window.
3. The method of claim 1, wherein model capability profiling includes spatial reasoning accuracy, hallucination rate on spatial tasks, and supported context window size.
4. The method of claim 1, wherein verification attainability is determined by matching each measurement's required operator against the set of locally available deterministic operators.
5. The method of claim 1, wherein the joint optimization minimizes total cost (model invocation + verification + review) subject to a minimum verification coverage ratio.
6. The method of claim 1, further comprising re-planning when a verification result triggers a need_review status, by re-routing the measurement to human review and updating the cost model.
7. The method of claim 1, wherein the encoding form selection includes a hybrid encoding that uses structured encoding for verifiable measurements and natural language for non-verifiable context.
8. The method of claim 1, wherein model routing considers historical verification pass rates for each model on similar spatial task types.

---

## 7. Required Implementation Evidence

Before P2 filing, the following evidence should be prepared:

| Evidence Item | Status | Path (when available) |
|---------------|--------|----------------------|
| Encoding selection prototype demonstrating token-budget-aware selection | Not started | — |
| Model routing prototype with at least 2 model profiles | Not started | — |
| Verification cost model benchmark | Not started | — |
| Human review cost estimation prototype | Not started | — |
| Joint optimization prototype producing a combined plan | Not started | — |
| End-to-end test: task → plan → execution → verification → coverage report | Not started | — |
| Comparative benchmark: joint optimization vs. independent decisions | Not started | — |
| Token cost data from v0.1/v0.2 benchmarks (partial evidence) | Available | `benchmarks/encoding_v0_1/outputs/`, `benchmarks/encoding_v0_2/outputs/` |

---

## 8. Non-disclosure Boundary

The following P2-specific mechanisms MUST NOT be disclosed before filing:

- Joint cost model formulation (how token cost, invocation cost, verification cost, and review cost are combined)
- Optimization objective and constraint formulation
- Encoding selection decision rules and parameters
- Model routing decision rules and capability profiling method
- Verification path assignment algorithm
- Human review cost estimation method
- Re-planning and fallback strategies
- Any weights, thresholds, or scoring functions used in the joint optimization

> See `patent_evidence/10_p1_p2_boundary_audit/disclosure_boundary_note.md` for the full non-disclosure statement.

---

## 9. Attorney Confirmation Questions

1. Does P1 already cover any aspect of "encoding template selection under token budget constraints" (INV-006)? If so, how should P2's encoding selection component be scoped to avoid overlap?
2. Is the "joint optimization of encoding + routing + verification + review" sufficiently distinct from P1's "encoding + verification pipeline" to support an independent P2 filing?
3. Should P2 be filed as a single application covering the full joint optimization, or should "encoding planning" and "model routing + verification scheduling" be split into two separate applications?
4. What is the recommended timeline for P2 filing relative to P1?
5. Are the 12 steps in the technical chain sufficient to support an independent claim, or should certain steps be merged or split?

> See `patent_evidence/10_p1_p2_boundary_audit/attorney_questions_for_p1_p2.md` for the complete list of attorney questions.
