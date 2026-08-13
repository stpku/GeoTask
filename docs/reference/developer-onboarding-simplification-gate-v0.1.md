# GeoTask P1 Developer Onboarding Simplification Gate v0.1

**Status:** candidate gate; implementation in progress; no external validation claim  
**Date:** 2026-08-13  
**Scope:** developer onboarding and Product Track activation only

## 1. Problem

GeoTask 的 Core 语义、证据治理和行动边界需要保持严格，但第一次接触产品的开发者不应该在理解产品价值之前，被要求同时掌握全部 Artifact 名称和 revision 生命周期。

当前已发布的 `developer-activation-protocol-v0.1.md` 把两类问题放在同一个 30 分钟 Gate 中：

1. **Product Activation：**开发者能否发现入口、运行 Reference Agent、修改一个真实输入，并理解系统为什么受控更新；
2. **Architecture Comprehension：**开发者能否进一步解释 `rev1 → rev2 → rev3`、Discrepancy、Correction、Impact 和 Reevaluation 等正式机制。

这会把“能不能开始使用 GeoTask”与“能不能已经读懂 GeoTask 的内部架构”混为一个门槛。

本 Gate 的目标不是降低正确性要求，而是把学习顺序改为：

> **先理解价值 → 再跑通闭环 → 再学习正式机制。**

## 2. Non-goals

本 Gate **不做**以下事情：

- 不修改任何 Core Schema、Operator、Artifact 或执行语义；
- 不把 Unknown、Conflict、Stale 或 Contradicted 降级为方便的 Boolean；
- 不放宽 `eligible != authorized != executed`；
- 不赋予 Reference Agent 生产写入、外部事实获取或现实动作权限；
- 不把作者、CI、实现 Agent 或 scripted demo 算作外部开发者；
- 不宣称 P1 external developer activation 已经通过。

降低的是**认知入口成本**，不是验证和控制标准。

## 3. Three-layer onboarding model

### L1 — 0–5 分钟：Value Comprehension

开发者只需要回答：

> GeoTask 为什么存在？

建议通过一个会变化的虚构世界说明：旧事实被新 Observation 更新以后，系统不会静默覆盖历史结论，而会保留变化、识别有限影响、重新验证受影响部分，并保持现实动作边界。

首次只引入四个直觉概念：

```text
Observe → State → Verify → Act
```

合格的自然语言理解是：

> **现实事实变了，GeoTask 帮 Agent 知道什么变了、影响什么、哪些判断需要更新，以及下一步是否具备条件。**

这一阶段不要求记住正式 Artifact 名称。

### L2 — 5–15 分钟：Product Activation

开发者应能独立完成：

1. 找到并运行安装包中的 Reference Agent；
2. 成功重放固定 `success` 场景；
3. 修改一个输入，例如把障碍物坐标从 `[70, 0]` 改为 `[60, 0]`；
4. 再次运行并确认确定性结果随输入变化；
5. 明确 `report_update_eligible=true` 不表示生产报告已经刷新。

这一阶段的核心不是背输出字段，而是证明项目是**可发现、可运行、可修改**的。

### L3 — 15–30 分钟：Boundary and Bounded-impact Comprehension

开发者应能用自己的语言解释：

- 新事实进入以后，旧结论不能静默原地覆盖；
- 变化应该只影响有依赖关系的部分，而不是无差别重算整个世界；
- `eligible` 只表示具备进入下一步的条件，不等于 `authorized`，更不等于 `executed`；
- 缺证据、证据冲突、过期或被反证时，系统应保持 fail-closed，而不是为了给出答案强行返回方便的 Boolean。

这构成 **Core Activation Comprehension**。

## 4. Advanced Comprehension

以下内容仍然重要，但从第一次激活硬门槛移动到后续 Advanced Comprehension：

- `rev1 → rev2 → rev3` 的精确生命周期；
- Observation Merge Result；
- Discrepancy Report；
- Correction Request；
- Impact Graph；
- Recompute Derivation Result；
- World State Materialization Result；
- Incremental Reevaluation Result；
- 更完整的 Artifact 依赖与审计关系。

移动学习阶段不代表这些机制可以被删除或弱化。它们仍然是 GeoTask 正式实现和审计语义的一部分。

## 5. Proposed future external activation gate

在后续 `developer-activation-protocol-v0.2` 中，建议把首次 Product Activation 的核心通过条件调整为：

- 至少 3 名没有跟随 GT01—GT42 详细实现历史的开发者真实参加；
- 所有人都能运行固定 Reference Agent，或者每个失败都有明确记录的 repository defect；
- 至少 2/3 能在不修改 Core 源码的情况下修改并运行一个自定义场景；
- 至少 2/3 能同时解释 **bounded impact** 与 **`eligible != executed`**；
- `rev1 → rev2 → rev3` 继续记录为 Advanced Comprehension 指标，但不单独阻断第一次 Product Activation；
- 重复 confusion point、repository defect 或 documentation gap 仍必须进入 follow-up，不能为了得到绿色结论而删除或改写证据。

这个建议仍保持 fail-closed：降低术语考试门槛，不降低真实运行、可修改性、有限影响和行动边界要求。

## 6. Transition rule

当前已经发布的以下 v0.1 制品保持原样，并继续作为现有基线：

- `developer-activation-protocol-v0.1.md`；
- `developer-activation-result-template.yaml`；
- `developer-activation-observer-runbook-v0.1.md`；
- `tools/summarize_developer_activation.py` 的 v0.1 记录与判定语义。

**不得只修改其中一个文件就悄悄改变 Gate。**

如果正式进入 v0.2，必须把以下内容作为一个原子升级包一起实现和测试：

1. protocol v0.2；
2. result schema/template v0.2；
3. observer runbook v0.2；
4. aggregator 对 v0.2 的明确处理；
5. 自动化测试；
6. 文档入口和迁移说明。

在这个原子升级包完成之前，v0.1 的历史结果和判断含义不得被重新解释。

## 7. Evidence required to close this Gate

本 Simplification Gate 的工程闭环需要证明：

- 首次体验路径能够从公开 Quickstart 自然发现，并直接在该公开文档内完成，不依赖额外未导出的教程文件；
- 首次体验不要求先理解 GT01—GT42；
- 15 分钟路径只依赖公开安装包和 materialized Reference Agent；
- 文档中的版本、命令和预期输出与当前发布版一致；
- Core 语义和权限边界没有变化；
- 后续真实盲测仍使用匿名、可审计、不可伪造的参与者记录。

完成这些工程条件，只能得到：

> **Developer onboarding simplification implementation ready for external trial.**

不能得到：

> **P1 external developer activation validated.**

后者仍然需要真实外部参与者证据。

## 8. Decision boundary

本 Gate 采用以下责任分离：

```text
Onboarding simplified
        !=
External activation validated
        !=
Core architecture changed
        !=
Production authorization
```

因此，本轮最重要的产品判断是：

> **让第一次使用更简单，但让真实世界的验证、证据和行动边界继续保持严格。**
