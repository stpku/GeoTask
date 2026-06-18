# Patent Evidence Guide

## 概述

本指南说明如何使用 GeoTask Encoding Benchmark 和专利证据包支撑专利申请。

## 专利证据包 (`patent_evidence/`)

### 用途

- 内部技术证据归档，**不是公开材料**
- 用于后续专利审查意见答复支撑
- 用于证明 GeoTask 技术效果
- 不应提交真实申请号、真实通知书、代理材料、客户数据

### 可以提交的文件

| 文件 | 说明 |
|------|------|
| `README.md` | 证据包说明 |
| `EVIDENCE_MANIFEST.md` | 证据清单和完整性检查 |
| `00_attorney_brief/` | 代理人版一页摘要 |
| `01_filing/filing_checklist.md` | 提交清单模板（不含真实数据） |
| `01_filing/placeholder_do_not_commit_real_documents.md` | 提醒不要误提交 |
| `02_code_evidence/` | 代码版本快照、测试快照、CLI 快照 |
| `03_benchmark/` | Benchmark 结果（CSV、JSON、Markdown） |
| `04_prior_art_review/` | 新颖性/创造性定位分析 |
| `05_invention_story/` | 技术问题→方案→效果 |
| `06_claim_mapping/` | 权利要求—证据映射矩阵 |

### 不要提交的文件

- ❌ 真实受理通知书（CNIPA filing receipts）
- ❌ 真实申请号（application numbers）
- ❌ 代理沟通记录（attorney correspondence）
- ❌ 客户数据（customer data）
- ❌ 第三方保密材料（third-party confidential materials）
- ❌ 缴费凭证（fee payment receipts）

## Encoding Benchmark 如何支撑专利

### 核心主张

> 任务相关空间编码能够在更少 token 下，提高大模型空间任务输出的稳定性、可归一化性和可验证性。

### Benchmark 证据映射

| 专利主张要素 | Benchmark 证据 |
|------------|---------------|
| 降低 token 输入成本 | Compact DSL avg tokens << Natural Language avg tokens |
| 提高归一化成功率 | GeoTask YAML 和 Compact DSL 归一化成功率更高 |
| 对象-算子-命题绑定 | 结构化编码使每个测量可被确定性验证 |
| 本地确定性验证检出模型错误 | 错误距离和错误布尔值被标记为 contradicted |
| 缺失信息转为 need_review | operator_reference_missing 在所有编码中被检出 |
| 编码模板优化 | Benchmark Score 同时考虑 token 效率和验证成功率 |

### 向代理人解释技术效果

当需要向专利代理人说明技术效果时，可以引用以下材料：

1. **代码证据**（`02_code_evidence/`）：
   - 证明 GeoTask Core 已实现并经过测试
   - 展示 Normalizer 和 Verifier 的实际功能

2. **Benchmark 数据**（`03_benchmark/`）：
   - CSV 表格展示各编码格式的 token 成本对比
   - 图表直观展示 token 成本、验证成功率、归一化成功率
   - Markdown 报告提供完整的实验方法和结论

3. **现有技术对比**（`04_prior_art_review/`）：
   - 说明本案不是简单的 prompt 压缩、LLM-GIS agent 或格式转换
   - 强调对象-算子-命题绑定和本地确定性验证的创新点

4. **技术问题-方案-效果**（`05_invention_story/`）：
   - 三段式结构清晰说明技术创新点
   - 与技术效果一一对应

5. **代理人摘要**（`00_attorney_brief/`）：
   - 一页摘要，适合直接提供给专利代理人
   - 包含关键实验数据、专利主张支撑、限制说明
   - 推荐用语可直接用于审查意见答复

6. **权利要求映射**（`06_claim_mapping/`）：
   - 权利要求—证据映射矩阵
   - 每个专利技术特征对应具体证据文件和 benchmark 结果
   - 包含证据文件路径和解释说明

7. **证据清单**（`EVIDENCE_MANIFEST.md`）：
   - 完整证据包目录和说明
   - 仓库状态、保密性说明、可复现命令
   - 完整性检查清单

## Delivery Workflow for Attorney Review

建议交付流程（按顺序）：

1. **先看 `DELIVERY_NOTE_v0_1_1.md`** — 了解证据包用途、关键发现、推荐用语和限制。
2. **再看 `attorney_one_page_summary.md`** — 一页摘要，含关键指标和专利支撑说明。
3. **再看 `claim_to_evidence_matrix.md`** — 每个专利技术特征对应具体证据文件。
4. **需要复现实验时运行 benchmark**：
   ```bash
   python benchmarks/encoding_v0_1/run_benchmark.py
   ```
5. **不要将 simulated benchmark 解释为真实 LLM 评测** — 所有报告均包含明确边界声明。

### 向代理人交付时的注意事项

- 明确指出：本 benchmark 使用**确定性模拟输出**，不声明真实 LLM API 准确率。
- 提供 token reduction 和 compression ratio 的量化数据（基于 JSON 实际值）。
- 说明 evidence package 文件之间的引用关系（manifest → brief → claim mapping → report）。
- 提醒代理人不要将 benchmark 结果等同于真实 LLM 性能评测。

## Simulated Benchmark 边界说明

**重要**：本 benchmark 使用确定性模拟模型输出，目的是保证实验可复现。该 benchmark 评估不同空间任务编码在 token 成本、归一化行为、验证行为、矛盾检出和复核原因生成方面的**工程差异**，不声明真实大模型 API 的准确率。

> Model outputs are deterministic simulated outputs for benchmark reproducibility. This benchmark evaluates encoding cost, normalization behavior, verification behavior, contradiction detection, and review-reason generation. It does not claim live LLM accuracy.

## 向代理人解释时推荐用语

**英文**:

> "The benchmark does not prove general LLM superiority. It supports the engineering claim that task-related spatial encodings can reduce token cost while preserving normalizable and verifiable output structure under deterministic simulated conditions."

**中文**:

> "该 benchmark 不证明大模型通用准确率提升，而是支撑一个工程性主张：在确定性模拟条件下，任务相关空间编码能够降低 token 成本，同时保持可归一化、可验证的输出结构。"

## 运行 Benchmark

```bash
# 安装依赖（含 matplotlib 用于图表）
pip install -e ".[dev]"

# 运行 benchmark
python benchmarks/encoding_v0_1/run_benchmark.py

# 运行所有测试
pytest
```

## 限制与注意事项

- Benchmark 使用模拟模型输出，非真实 LLM 推理结果
- Token 估算是近似值，不精确对应任何特定模型的 tokenizer
- v0.1.1 覆盖 4 个 case、2 类算子；v0.2 覆盖 24 个 case、6 类算子；v0.3 将 6 类算子回灌到生产级 Core

## Evidence Version Summary

### Evidence layering

When explaining to an attorney or examiner, distinguish between:

| Version | What It Is | What It Is NOT |
|---------|-----------|----------------|
| **v0.1.1** | End-to-end Core Normalizer + Verifier loop evidence (2 ops) | Does not cover all operators |
| **v0.2** | Multi-scenario structural encoding evidence (6 ops, 24 cases) | Does not prove Core Normalizer handles all 6 operators |
| **v0.3** | **Production Core backfill** — Core Normalizer/Verifier handle all 6 operators | Does not include real LLM evaluation |

### v0.3 Production Core Evidence

**v0.3 closes the gap between v0.2 benchmark and production code.** All 6 operators, 8 error types, invalid operator/reference detection, unit mismatch detection, and Chinese negation are now in the production `src/geotask_core/normalizer.py` and `verifier.py`.

| Evidence | Location |
|----------|----------|
| Production end-to-end tests | `tests/test_core_normalizer_verifier_v0_3.py` |
| Ops unit tests (6 operators) | `tests/test_ops_v0_3.py` |
| Evidence integrity tests | `tests/test_core_v0_3_evidence.py` |
| Evidence package | `patent_evidence/08_core_v0_3/` |
| Technical documentation | `docs/core_normalizer_verifier_v0_3.md` |

Key capabilities in v0.3 production Core:
- Unified status hierarchy: `invalid_operator` > `invalid_reference` > `contradicted` > `need_review` > `verified`
- Invalid operator detection (e.g., "haversine" rejected)
- Invalid reference detection (object not in geotask_data)
- Unit mismatch detection (km vs meter)
- Chinese negation for contains and intersection

### Recommended attorney statement for v0.3

> "v0.3 backfills stable capabilities from benchmark v0.2 into the production GeoTask Core Normalizer and Verifier. All 6 operators are now supported in production code. The unified status hierarchy (invalid_operator > invalid_reference > contradicted > need_review > verified) enables production-grade error classification. Evidence is based on deterministic end-to-end tests using `normalize_model_output` + `verify_normalized_result`."

> "v0.3 将 benchmark v0.2 中能力回灌到生产级 GeoTask Core Normalizer 和 Verifier。全部 6 类算子已在生产代码中支持，统一的状态层级（invalid_operator > invalid_reference > contradicted > need_review > verified）提供生产级错误分类。证据基于确定性端到端测试。"

### Key points when discussing v0.2

1. **v0.1.1 is the end-to-end loop evidence** — the production GeoTask Core Normalizer extracts, normalizes, and verifies 2 core operators (distance_2d, line_intersects_rect) from model outputs.

2. **v0.2 is extended coverage evidence** — it demonstrates that the encoding structure (object references, operator references, propositions, expected outputs) is extensible to 6 operators and 24 cases. It uses a benchmark-local verifier, not the production normalizer, for the 4 new operators.

3. **v0.3 is the production Core backfill** — it takes v0.2's proven capabilities and integrates them into the production normalizer and verifier.

4. **Do not present v0.2 as proof that Core Normalizer fully supports all new operators** — that is v0.3's role.

5. **Do not present v0.2 as a live LLM accuracy evaluation** — all outputs are deterministic simulations. The benchmark evaluates encoding structure, not model performance.

## 下一步

- ~~将 v0.2 中稳定算子回灌 Core Normalizer（v0.3）~~ ✅ 已完成
- 加入真实 LLM 评估（v0.4）
- 运行统计显著性检验（v0.4）

## How to Explain Core v0.3

### Evidence layer positioning

| Version | Role | When to cite |
|---------|------|-------------|
| **v0.1.1** | Initial end-to-end Core loop (2 ops) | Examiner questions whether Core has any end-to-end loop |
| **v0.2** | Structural extensibility (6 ops, 24 cases) | Examiner questions whether encoding structure scales |
| **v0.3** | Production Core backfill (6 ops in Core) | Examiner questions whether scalable structure is production-grade |

### Key points when discussing v0.3

1. **v0.1.1 is the initial end-to-end evidence** — proves the Core loop works for 2 core operators.

2. **v0.2 is structural coverage evidence** — proves the encoding structure scales to 6 operators and 24 cases via a benchmark-local verifier.

3. **v0.3 is the production Core backfill** — closes the v0.2 local-verifier boundary by integrating stable multi-operator capabilities into production `normalizer.py` and `verifier.py`.

4. **Do not present v0.3 as live LLM accuracy** — all tests use deterministic simulated outputs. v0.4 will address real LLM evaluation.

5. **Do not present v0.3 as replacing v0.2** — v0.2 provides broader structural coverage (24 cases). v0.3 provides production Core evidence.

### Recommended attorney statement for v0.3

> "Core v0.3 closes the Benchmark v0.2 local-verifier boundary by moving stable multi-operator capabilities into the production GeoTask Core Normalizer and Verifier. This strengthens the evidence for the claimed task-related spatial encoding, model-output normalization, deterministic verification, and verifiability-based status routing mechanisms."

> "Core v0.3 通过将稳定的多算子能力迁移至生产级 GeoTask Core Normalizer 和 Verifier，关闭了 Benchmark v0.2 中本地 benchmark 验证器的边界问题。"

### v0.3 delivery files

For attorney review, prioritize:

- `patent_evidence/08_core_v0_3/core_v0_3_attorney_addendum.md` — complete evidence summary
- `patent_evidence/08_core_v0_3/core_v0_3_delivery_note.md` — delivery instructions
- `patent_evidence/08_core_v0_3/core_v0_3_claim_support_update.md` — claim mapping
