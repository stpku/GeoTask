# Commercial Boundary Note — GeoTask

> **CONFIDENTIAL — PRIVATE REPOSITORY**
> This document defines the commercial boundary of the GeoTask product architecture.
> Do NOT make this document public.

> **机密 — 私有仓库**
> 本文档定义 GeoTask 产品架构的商业边界。请勿公开本文档。

---

## English Version

### GeoTask Core — Lightweight Basic Capability / Open-Source Entry Point

GeoTask Core CAN serve as a lightweight basic capability or open-source entry point:

- **Format specification**: GeoTask YAML and Compact DSL encoding formats are open-source under MIT License.
- **Deterministic operators**: The 6 spatial operators (distance_2d, line_intersects_rect, point_to_line_distance_2d, rect_contains_point, time_overlap, altitude_overlap) are open-source.
- **Normalizer and Verifier**: The production normalizer and verifier are open-source.
- **CLI and examples**: The command-line interface and example files are open-source.
- **Tests and benchmarks**: Test suites and benchmark infrastructure are open-source.

The open-source Core establishes the GeoTask format as a standard for spatial task representation, enables community adoption, and provides patent evidence for the P1 filing.

### GeoTask Runtime — Commercial Core

The following Runtime capabilities ARE commercial core and MUST NOT be open-sourced:

| Capability | Description | Patent Status |
|-----------|-------------|---------------|
| Encoding Planning | Selection of optimal encoding template based on task complexity, model context window, and token budget constraints | Candidate P2 — unpatented |
| Model Adaptation | Routing spatial tasks to optimal model considering inference cost and verification cost | Candidate P2 — unpatented |
| Cost Control | Joint optimization of encoding cost, inference cost, and verification cost | Candidate P2 — unpatented |
| Audit Governance | Production audit trail, compliance verification, output contract enforcement | Commercial implementation |
| Strategy Library | Accumulated encoding strategies, model performance profiles, and optimization heuristics | Commercial trade secret |

### GeoTask Domain Pack — Commercial Delivery Assets

The following Domain Pack capabilities ARE commercial delivery assets and MUST NOT be open-sourced:

| Capability | Description | Patent Status |
|-----------|-------------|---------------|
| Industry Rules | Domain-specific spatial constraint rules (aviation, construction, environmental) | Candidate P4 — unpatented |
| Data Connectors | Connectors to industry-specific spatial data sources | Commercial implementation |
| Workflows | Industry-specific spatial task workflows and approval processes | Commercial implementation |
| Scoring Logic | Domain-specific scoring and ranking of spatial verification results | Commercial implementation |
| Customer Templates | Customer-specific encoding templates and verification configurations | Commercial delivery asset |

### Non-Disclosure Requirement

Mechanisms not yet patented MUST NOT be disclosed in public materials:

1. **Public README**: May describe GeoTask Core format, operators, and general architecture. MUST NOT describe encoding selection logic, model routing strategies, or cost optimization mechanisms.
2. **Public documentation**: May include format specifications, API references, and usage examples for the open-source Core. MUST NOT include Runtime decision logic or Domain Pack mechanisms.
3. **Public papers and presentations**: May reference GeoTask as a spatial task representation system with deterministic verification. MUST NOT disclose candidate patent mechanisms (P2–P5).
4. **Public issues and pull requests**: May discuss Core bugs, feature requests, and contributions. MUST NOT discuss Runtime or Domain Pack implementation details.
5. **Customer-facing materials**: May demonstrate Core capabilities. Runtime and Domain Pack capabilities should be demonstrated under NDA only.

---

## 中文版本

### GeoTask Core — 轻量基础能力 / 开源入口

GeoTask Core 可以作为轻量基础能力或开源入口：

- **格式规范**：GeoTask YAML 和 Compact DSL 编码格式在 MIT 许可证下开源。
- **确定性算子**：6 个空间算子（distance_2d、line_intersects_rect、point_to_line_distance_2d、rect_contains_point、time_overlap、altitude_overlap）已开源。
- **归一化器和验证器**：生产级归一化器和验证器已开源。
- **CLI 和示例**：命令行工具和示例文件已开源。
- **测试和基准**：测试套件和基准测试基础设施已开源。

开源 Core 确立 GeoTask 格式作为空间任务表达标准，促进社区采纳，并为 P1 专利申请提供证据支撑。

### GeoTask Runtime — 商业核心

以下 Runtime 能力属于**商业核心**，**不得**开源：

| 能力 | 描述 | 专利状态 |
|-----|------|---------|
| 编码规划 | 基于任务复杂度、模型上下文窗口和令牌预算约束选择最优编码模板 | 候选 P2 — 未申请专利 |
| 模型适配 | 综合考虑推理成本和验证成本将空间任务路由到最优模型 | 候选 P2 — 未申请专利 |
| 成本控制 | 编码成本、推理成本和验证成本的联合优化 | 候选 P2 — 未申请专利 |
| 审计治理 | 生产级审计追踪、合规验证、输出合约执行 | 商业实现 |
| 策略库 | 积累的编码策略、模型性能画像和优化启发式规则 | 商业秘密 |

### GeoTask Domain Pack — 商业交付资产

以下 Domain Pack 能力属于**商业交付资产**，**不得**开源：

| 能力 | 描述 | 专利状态 |
|-----|------|---------|
| 行业规则 | 领域特定的空间约束规则（航空、建筑、环境监测） | 候选 P4 — 未申请专利 |
| 数据连接器 | 行业特定空间数据源的连接器 | 商业实现 |
| 工作流 | 行业特定的空间任务工作流和审批流程 | 商业实现 |
| 评分逻辑 | 领域特定的空间验证结果评分和排序 | 商业实现 |
| 客户模板 | 客户特定的编码模板和验证配置 | 商业交付资产 |

### 禁止披露要求

尚未获得专利保护的机制**不得**在公开材料中披露：

1. **公开 README**：可描述 GeoTask Core 格式、算子和总体架构。**不得**描述编码选择逻辑、模型路由策略或成本优化机制。
2. **公开文档**：可包含开源 Core 的格式规范、API 参考和使用示例。**不得**包含 Runtime 决策逻辑或 Domain Pack 机制。
3. **公开论文和演示**：可将 GeoTask 介绍为具备确定性验证的空间任务表达系统。**不得**披露候选专利机制（P2–P5）。
4. **公开 Issue 和 Pull Request**：可讨论 Core 的 bug、功能需求和贡献。**不得**讨论 Runtime 或 Domain Pack 的实现细节。
5. **客户资料**：可展示 Core 能力。Runtime 和 Domain Pack 能力应仅在保密协议（NDA）下展示。

---

## Summary / 总结

| Layer / 层级 | Open-Source? / 是否开源 | Commercial? / 是否商业 | Patent Status / 专利状态 |
|-------------|----------------------|----------------------|-------------------------|
| GeoTask Core | Yes / 是 | Basic capability / 基础能力 | P1 Filed / P1 已提交 |
| GeoTask Runtime | No / 否 | Commercial core / 商业核心 | P2 Candidate / P2 候选 |
| GeoTask Domain Pack | No / 否 | Delivery asset / 交付资产 | P4 Candidate / P4 候选 |
