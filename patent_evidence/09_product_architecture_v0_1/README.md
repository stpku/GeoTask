# 09 — Product Architecture Patent Positioning (v0.1)

> **CONFIDENTIAL — PRIVATE REPOSITORY**
> This directory is part of the GeoTask private patent evidence archive.
> Do NOT make this directory or its contents public.
> Do NOT share outside authorized patent counsel and internal team.

> **机密 — 私有仓库**
> 本目录属于 GeoTask 私有专利证据档案。
> 请勿公开本目录及其内容。
> 请勿在授权专利代理人和内部团队之外分享。

---

## Purpose

This evidence directory provides **product architecture patent positioning** and an **invention ledger** for the GeoTask patent portfolio. It serves three functions:

1. **Map product architecture layers to patent claim coverage** — clarify which product modules correspond to which patent filings and which are candidates for future filings.
2. **Track all invention points** — maintain a single-source inventory of what has been filed, what is a candidate for future filing, and what the disclosure risk is for each.
3. **Define the patent portfolio roadmap** — recommend filing priorities and sequencing across P1 (filed) through P5 (candidate).

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `README.md` | This file — overview, security warnings, file index |
| `product_architecture_patent_positioning.md` | Product layer → patent claim mapping; P1 scope vs. candidate patents |
| `invention_ledger.md` | Master inventory of all invention points (INV-001 through INV-010+) with filing status, evidence links, and disclosure risk |
| `patent_portfolio_roadmap.md` | Recommended patent portfolio: P1 (filed) through P5 (candidate) with technical scope, evidence requirements, and filing readiness |
| `product_to_patent_mapping.md` | Product module → technical capability → patent direction mapping table |
| `commercial_boundary_note.md` | Commercial boundary statement: what is open-sourceable vs. commercial core vs. must-not-disclose |

---

## Cross-References to Other Evidence Directories

| Evidence Directory | Relationship to This Directory |
|-------------------|-------------------------------|
| `00_attorney_brief/` | One-page summary for patent prosecution — P1 scope |
| `01_filing/` | Filing checklist (no real documents stored) |
| `02_code_evidence/` | Code version and test snapshots — supports INV-002, INV-005 |
| `03_benchmark/` | Encoding benchmark v0.1 results — supports INV-001, INV-004, INV-006 |
| `04_prior_art_review/` | Novelty and creativity positioning — supports P1 differentiation |
| `05_invention_story/` | Technical Problem → Solution → Effect — supports INV-001 through INV-005 |
| `06_claim_mapping/` | Patent feature → evidence mapping matrix — supports P1 claims |
| `07_benchmark_v0_2/` | Expanded 24-case benchmark — supports INV-001, INV-002, INV-004 |
| `08_core_v0_3/` | Production Core backfill — supports INV-002, INV-005 |

---

## Related Documentation

| Document | Path |
|----------|------|
| Patent Boundary | `docs/patent_boundary.md` |
| Open Source Boundary | `docs/open_source_boundary.md` |
| Design Principles | `docs/design_principles.md` |

---

## Evidence Version

- **Evidence version**: `product-architecture-v0.1`
- **Recommended tag**: `patent-portfolio-v0.1`
- **Production test count**: 407 passing tests
- **Core operators**: 6 (distance_2d, line_intersects_rect, point_to_line_distance_2d, rect_contains_point, time_overlap, altitude_overlap)

---

## Confidentiality Reminder

1. This repository is **private**. Do not make it public without explicit authorization.
2. Invention points INV-006 through INV-010 describe **unpatented candidate mechanisms**. Their technical details MUST NOT appear in public materials, public README, public documentation, public papers, or public presentations.
3. No real application numbers, filing receipts, attorney names, or customer data are stored in this directory.
4. When sharing with patent counsel, reference specific files from this manifest. Do not share the entire repository.
