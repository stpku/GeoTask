# Patent Evidence Package

This directory contains **private patent evidence** for the GeoTask project.

## Purpose

- Not public material.
- Used for internal technical evidence archiving.
- Used to support subsequent patent examination responses.
- Used to demonstrate GeoTask technical effects.
- Should **NOT** contain real application numbers, filing receipts, attorney documents, agent materials, or customer data.

## Warning

> This directory is for private patent evidence only. Do not commit real filing receipts, application numbers, attorney documents, customer data, or confidential third-party materials unless the repository access policy explicitly allows it.

> 本目录仅用于私有专利证据归档。未经确认，不要提交真实受理通知书、申请号、代理文件、客户数据或第三方保密材料。

## Directory Structure

```
patent_evidence/
├── README.md                          ← This file
├── EVIDENCE_MANIFEST.md               ← Evidence inventory and integrity checklist
├── 00_attorney_brief/                 ← One-page summary for patent prosecution
│   └── attorney_one_page_summary.md
├── 01_filing/                         ← Filing checklist (no real documents)
│   ├── filing_checklist.md
│   └── placeholder_do_not_commit_real_documents.md
├── 02_code_evidence/                  ← Code version and test snapshots
│   ├── geotask_version_snapshot.md
│   ├── test_snapshot.md
│   └── cli_snapshot.md
├── 03_benchmark/                      ← Benchmark results (auto-generated)
│   ├── encoding_benchmark_v0_1_results.csv
│   ├── encoding_benchmark_v0_1_results.json
│   └── encoding_benchmark_v0_1_summary.md
├── 04_prior_art_review/               ← Novelty and creativity positioning
│   └── novelty_creativity_positioning.md
├── 05_invention_story/                ← Technical problem → solution → effect
│   └── technical_problem_solution_effect.md
└── 06_claim_mapping/                  ← Patent features → evidence mapping
    └── claim_to_evidence_matrix.md
```

## Simulated Benchmark Boundary

Model outputs are deterministic simulated outputs for benchmark reproducibility. This benchmark evaluates encoding cost, normalization behavior, verification behavior, contradiction detection, and review-reason generation. It does **not** claim live LLM accuracy.

> 本 benchmark 使用确定性模拟模型输出，目的是保证实验可复现。该 benchmark 评估不同空间任务编码在 token 成本、归一化行为、验证行为、矛盾检出和复核原因生成方面的工程差异，不声明真实大模型 API 的准确率。
