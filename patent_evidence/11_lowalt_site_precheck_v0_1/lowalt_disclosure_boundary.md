# LowAlt Site Precheck — Disclosure Boundary

> **CONFIDENTIAL — PRIVATE REPOSITORY — DO NOT DISCLOSE**
> This document defines the disclosure boundary for the LowAlt Site Precheck domain pack.
> P5 candidate patent mechanisms MUST NOT be disclosed in any public material.

> **机密 — 私有仓库 — 禁止披露**
> 本文档定义低空选址预检 Domain Pack 的披露边界。
> P5 候选专利机制不得在任何公开材料中披露。

---

## Disclosure Boundary

| Layer | Disclosure Status | Notes |
|-------|-------------------|-------|
| GeoTask Core operators (distance_2d, line_intersects_rect, etc.) | **Public** — Open source (MIT) | Safe to reference |
| Domain Pack protocol interface | **Public** — Reference interface in `geotask_runtime/domain_pack.py` | Safe to reference |
| LowAlt precheck task template and constraint verification workflow | **NOT public — Candidate P5 — DO NOT DISCLOSE** | Verification workflow composition is novel |
| LowAlt precheck rules and risk evaluation logic | **NOT public — Candidate P5 — DO NOT DISCLOSE** | Rule composition mechanism is novel |
| Mock data and fictional coordinates | **Private** — Part of this pack | No real data |
| Real data adapters and regulatory integrations | **Not implemented** — Future, private | N/A |

---

## What May Be Referenced Publicly

1. The **existence** of domain packs as an extension mechanism (already in README architecture diagram)
2. The **existence** of low-altitude as an example domain (generic concept)
3. GeoTask Core operators used by the pack (already open source)

## What MUST NOT Be Disclosed

1. The specific **task template composition** for site precheck workflows
2. The **constraint verification orchestration** pattern (enrich_context → build_verification_plan → run_precheck)
3. The **risk evaluation and data gap identification** mechanisms
4. Any **scoring, ranking, or decision logic** for site evaluation
5. The specific **mapping from aviation/regulatory rules to spatial operators**

---

## Relationship to Patent Portfolio

| Patent | Relationship |
|--------|-------------|
| P1 (Filed) | Core operators used by this pack are covered by P1 |
| P4 (Candidate) | Domain Pack framework and rule mapping — P5 builds on P4 |
| P5 (Candidate) | This pack is the primary evidence for P5 |

---

## Evidence Files

| File | Location |
|------|----------|
| Domain pack documentation | `docs/lowalt_site_precheck_pack_v0_1.md` |
| Domain pack source code | `src/geotask_domain_packs/lowalt_site_precheck/` |
| Domain pack tests | `tests/test_lowalt_site_precheck_v0_1.py` |
| Example YAML files | `examples/domain_packs/lowalt_site_precheck/` |
| This disclosure boundary | `patent_evidence/11_lowalt_site_precheck_v0_1/lowalt_disclosure_boundary.md` |

---

## 中文摘要

本文档定义低空选址预检 Domain Pack 的披露边界。GeoTask Core 算子和 Domain Pack 协议接口已公开，但低空预检的任务模板组合、约束验证编排、风险评估和数据缺口识别机制属于 P5 候选专利范畴，**严禁**在公开材料中披露。
