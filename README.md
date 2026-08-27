# GeoTask

**简体中文** | [English](README.en.md)

> **GeoTask 是面向 AI Agent 的时空任务上下文引擎（Spatiotemporal Task Context Engine）。**
>
> 它不试图把“整个世界”塞进 Agent 的上下文，而是围绕当前任务，构造**真正需要、适用、分辨率足够且可明确判断充分性**的最小上下文。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![CI](https://github.com/stpku/GeoTask/actions/workflows/ci.yml/badge.svg)](https://github.com/stpku/GeoTask/actions/workflows/ci.yml)
[![Pages](https://github.com/stpku/GeoTask/actions/workflows/pages.yml/badge.svg)](https://stpku.github.io/GeoTask/)
[![Release](https://img.shields.io/github/v/release/stpku/GeoTask?include_prereleases&label=release)](https://github.com/stpku/GeoTask/releases)
[![PyPI](https://img.shields.io/pypi/v/geotask-core)](https://pypi.org/project/geotask-core/)

## 为什么是 Task Context，而不是“更多上下文”

Agent 进入真实任务后，问题通常不是“有没有数据”，而是：

- **这个任务到底需要知道什么？**
- **某条信息虽然相关，但对当前对象、空间、时间和条件真的适用吗？**
- **它的空间/时间/语义分辨率足够支持当前任务吗？**
- **已有上下文是否足够，还是仍存在关键缺口？**
- **能否减少无关上下文，同时不漏掉关键上下文？**
- **现实发生变化后，哪些 Requirement 需要重评，哪些上下文可以继续复用？**

GeoTask 将这些问题变成显式、可组合、可测试的 Task Context 合同与方法。

```text
Task
  ↓
derive requirements
  ↓
discover candidates
  ↓
Relevance
  ↓
Applicability
  ↓
Resolution Adequacy
  ↓
Sufficiency
  ↓
Minimum Sufficient TaskContext
  ↓
Explicit Gaps / Trace / Cost
```

## 核心语义

当前公共 Core 已提供面向 Task Context 的一组稳定原语与组合接口，包括：

- `TaskFrame`
- `ContextRequirement`
- `ContextCandidate`
- `RelevanceResult`
- `ApplicabilityResult`
- `ResolutionRequirement` / `ResolutionAdequacyResult`
- `ContextAssessment`
- `ContextGap`
- `SufficiencyAssessment`
- `TaskContext`
- `ContextConstructionTrace`
- `ContextMinimalityAssessment`
- `MinimumSufficientTaskContext`
- Temporal Reassessment / Continuity contracts

这些对象刻意保持几个边界：

```text
Context ≠ World State
Relevant ≠ Applicable
Applicable ≠ Sufficient
Candidate exists ≠ Requirement satisfied
Large payload ≠ Sufficient context
Provider returned a value ≠ Valid task context
Context sufficient ≠ Domain decision
Context sufficient ≠ Action authorization
```

## GeoTask 负责什么

GeoTask 负责 **Task-relative Context**：

1. 用 `TaskFrame` 明确当前任务、目标与作用域；
2. 从任务导出或接收 `ContextRequirement`；
3. 从 GIS、API、Sensor、Database、WorldState 或其他 Provider 获取 `ContextCandidate`；
4. 分别评估 Relevance、Applicability 与 Resolution Adequacy；
5. 显式形成 Requirement-level Assessment 与 Gap；
6. 由明确方法组合 `SufficiencyAssessment`；
7. 构造 `TaskContext`，并在不增加 Critical Context Miss 的前提下寻找 Minimum Sufficient Context；
8. 当 Provider / Reality 变化时，仅重评受影响 Requirement，并尽量复用未受影响 Context。

GeoTask **不拥有世界真值**，也不替代 Agent Harness、GIS、数据库、知识图谱、RAG 系统或领域决策系统。

```text
World / Data Providers
WorldState · GIS · API · Sensor · Database · Other Provider
                    │
                    ▼
              ┌─────────┐
              │ GeoTask │
              │  Task   │
              │ Context │
              └────┬────┘
                   │
                   ▼
             Agent / Harness
                   │
                   ▼
           Domain Decision / Action
```

**Provider 可以告诉 GeoTask“候选事实是什么”；GeoTask 判断的是“它对当前任务是否需要、适用、足够”。**

## North Star：充分，而不是堆积

GeoTask 的长期目标是：

> **Task Sufficiency at Minimum Context Cost**

也就是在保证关键 Requirement 不被遗漏的前提下，用尽可能少、尽可能局部的上下文支撑任务。

建议同时观察正指标与反指标：

| 目标 | Counter Metric |
|---|---|
| Critical Requirement Coverage ↑ | **Critical Context Miss Rate** |
| Sufficiency Accuracy ↑ | **False Sufficiency Rate** |
| Context Reduction ↑ | **Critical Context Miss Rate** |
| Applicability Accuracy ↑ | **Irrelevant / Inapplicable Context Rate** |
| Local Rebuild ↑ | **Unnecessary Context Rebuild** |

上下文成本不只等于 Token，可以包括网络获取、携带字节、Provider 延迟、人类恢复成本等。

## 已公开的独立消费者：Warehouse Robot Picking

GeoTask 已提供一个**不依赖官方 WorldState、也不依赖低空领域**的独立消费者示例：

```text
Indoor GIS / topology
Inventory API
Aisle-clearance sensor
        ↓
TaskFrame
        ↓
ContextRequirement[]
        ↓
ContextCandidate[]
        ↓
Relevance / Applicability / Resolution Adequacy
        ↓
SufficiencyAssessment
        ↓
Minimum Sufficient TaskContext
        ↓
Sensor change
        ↓
Bounded Temporal Reassessment
```

示例中特意保留一个关键语义：**即使测得通道比机器人更窄，只要这个测量本身相关、适用、新鲜且分辨率足够，GeoTask 仍可以判断“上下文充分”；但它不会因此判断“机器人可以通行”。** 领域安全判断与动作授权仍属于下游系统。

- [Warehouse Robot Picking 示例](examples/independent_consumers/warehouse_robot_picking/README.md)

## 安装与现有工具

```bash
pip install geotask-core
geotask inspect capabilities
geotask inspect health
```

当前公共包同时保留既有确定性算子、Artifact、Verification、Runtime/Provider、Reference Agent 与 Benchmark 能力。它们是 GeoTask 演化过程中已经发布的公共兼容资产；**新的长期语义所有权以 Task Context Engine 为主线**。

如果想直接查看 Task Context Engine 的组合方式，优先从独立消费者开始：

```bash
python - <<'PY'
from examples.independent_consumers.warehouse_robot_picking.consumer import (
    build_warehouse_pick_context,
)

run = build_warehouse_pick_context()
print(run.construction.sufficiency.status)
print(len(run.construction.context.values), len(run.minimum.context.values))
PY
```

预期高层结果：

```text
sufficient
4 3
```

该示例是确定性参考实现，不代表真实仓储集成或机器人安全认证。

## Reality Change：下一条重要主线

Task Context 不是一次性 Prompt 组装。对长任务，现实会变化：状态过期、Provider 更新、冲突出现、Unknown 被解决。

GeoTask 的变化响应边界是：

```text
Changed facts / provider state
        ↓
Affected ContextRequirements
        ↓
Reassess Applicability / Resolution / Sufficiency
        ↓
ContextGap delta
        ↓
Minimal rebuild only when needed
```

目标不是每次变化都重建全部上下文，而是让 **Context Rebuild Locality** 可解释、可测量。

## 公开路线

当前 Task Context 主线按以下研究问题持续推进：

- **Requirement Derivation** — Task → Requirement 的稳定方法；
- **Relevance / Applicability Separation** — 同一事实对不同任务可以有不同适用性；
- **Resolution Adequacy & Sufficiency** — “有数据”不等于“足够支持任务”；
- **Minimum Context Cost** — 在 Critical Miss 不上升的前提下降低上下文成本；
- **Temporal Reassessment** — 变化只触发有界重评与最小重建；
- **Independent Consumers** — 用第二、第三领域验证 Core 不被单一业务塑形。

路线图描述研究方向和公共能力演化，不构成交付日期承诺。

## Legacy / Compatibility

GeoTask 早期公开版本以“可验证时空任务协议 / World-State Cycle / Verification”为主线，已经形成大量可验证 Artifact、案例和文档。这些资产继续保留，用于兼容、可追溯历史和已发布能力维护，但**不再定义 GeoTask 的长期产品定位**。

需要理解旧资产时，可从以下入口进入：

- [中文文档导航](docs/README.md)
- [GT01—GT20 Cookbook](docs/cookbook/gt01-gt20.zh-CN.md)
- [GT21—GT28 World-State Cycle](docs/cookbook/gt21-gt28.zh-CN.md)
- [Reference Agent](docs/reference/reference-agent-v0.1.md)
- [Verification Quality Benchmark](docs/reference/verification-quality-benchmark-v0.2.md)
- [历史白皮书 v0.1](docs/whitepaper/GeoTask_White_Paper_v0.1.md)

> 历史文档中的 “GeoTask = World-State Runtime / Verifiable World Model” 应按其发布时的版本语境理解；当前定位以 **Task Context Engine** 为准。

## 开始使用

- [GeoTask 项目主页](https://stpku.github.io/GeoTask/)
- [Warehouse Robot Picking 独立消费者](examples/independent_consumers/warehouse_robot_picking/README.md)
- [5 分钟中文入门](docs/tutorials/quickstart.zh-CN.md)
- [公共 API](src/geotask_core/v1/)
- [Examples](examples/)
- [Issues](https://github.com/stpku/GeoTask/issues)
- [Releases](https://github.com/stpku/GeoTask/releases)

## License

GeoTask Core 使用 [MIT License](LICENSE)。

---

**一句话：GeoTask 不负责“知道整个世界”，而负责让 Agent 在当前任务中，只拿到真正需要、适用且足够的时空上下文。**
