# GeoTask Public Roadmap

[简体中文](#中文路线图) | [English](#english-roadmap)

> **Current positioning: GeoTask is a domain-neutral spatiotemporal Task Context Engine for AI agents.**
>
> The roadmap now follows the Task Context problem space. Earlier World-State / Verification milestones remain part of the released compatibility history, but they no longer define GeoTask's long-term semantic ownership.

This roadmap describes public research and Core evolution directions. It is **not** a delivery-date commitment.

---

## 中文路线图

### 1. 当前 North Star

> **Task Sufficiency at Minimum Context Cost**

GeoTask 的目标不是最大化 Context 数量，而是在不增加关键遗漏的前提下，让当前任务获得真正需要、适用且足够的信息。

核心反指标：

> **Critical Context Miss Rate**

同时关注：

- False Sufficiency Rate；
- Irrelevant / Inapplicable Context Rate；
- Unnecessary Context Rebuild；
- Provider / carried-context / token / latency / human-recovery cost。

### 2. 当前公共基线 ✅

当前 GitHub Public Core 已发布：

- `TaskFrame`；
- `ContextRequirement`；
- `ContextCandidate`；
- Relevance / Applicability contracts；
- `ResolutionRequirement` / `ResolutionAdequacyResult`；
- `ContextAssessment` / `ContextGap`；
- `SufficiencyAssessment`；
- `TaskContext` / `ContextConstructionTrace`；
- Requirement-level assessment composition；
- deterministic context construction；
- context minimality / `MinimumSufficientTaskContext`；
- temporal reassessment / continuity contracts；
- provider-neutral composition seams。

已经公开一个独立消费者：

- `examples/independent_consumers/warehouse_robot_picking/`
  - indoor GIS / topology；
  - inventory API；
  - aisle-clearance sensor；
  - Task → Requirement → Relevance / Applicability / Resolution → Sufficiency → Minimum Context → bounded Temporal Reassessment；
  - 不依赖官方 WorldState；
  - 不把 Context Sufficiency 误当成机器人动作授权。

### 3. GT-C1 — Requirement Derivation

**问题：** 如何从 Task 稳定地得到它真正需要的 Requirement，而不是让调用方手写一份不可解释的上下文清单？

研究重点：

- critical vs optional；
- spatial / temporal / semantic requirement；
- resolution need；
- validity / freshness need；
- evidence / source constraints；
- task-dependent derivation trace；
- domain profile 留在 consumer，不污染 Core。

成功标准：

```text
same Task + same explicit method + same inputs
→ stable, inspectable requirements
```

### 4. GT-C2 — Relevance / Applicability Separation

**问题：** 为什么“相关”不能直接等同于“适用”？

需要持续证明：

```text
same candidate fact
+ different task / scope / time / condition
→ different applicability
```

方向：

- relevance 与 applicability 独立证据；
- explicit method / policy seam；
- cross-domain holdout；
- 误纳无关/不适用 Context 的反指标。

### 5. GT-C3 — Resolution Adequacy & Sufficiency

**问题：** “有数据”什么时候才足以支持任务？

至少考虑：

- spatial resolution；
- temporal resolution / freshness；
- precision / uncertainty；
- semantic resolution；
- coverage / scope；
- critical requirement closure。

核心原则：

```text
Available ≠ Adequate
Applicable ≠ Sufficient
High confidence ≠ Sufficient
```

### 6. GT-C4 — Minimum Context Cost

**问题：** 如何减少 Context，而不是通过“漏掉关键事实”获得漂亮的成本数字？

目标：

```text
Context Cost ↓
while
Critical Context Miss does not ↑
```

成本至少区分：

- network acquisition cost；
- carried-context bytes；
- token/context cost；
- provider latency；
- human recovery cost。

研究重点：

- requirement-level contribution；
- optional context pruning；
- minimum sufficient proof；
- payload reduction 与 upstream acquisition cost 的边界区分。

### 7. GT-C5 — Temporal Reassessment

**问题：** 现实或 Provider 变化后，为什么不应该重建全部 Context？

目标链路：

```text
Changed facts / provider state
        ↓
Affected ContextRequirements
        ↓
Reassess applicability / resolution / sufficiency
        ↓
ContextGap delta
        ↓
Minimal rebuild only when needed
```

主要度量：

- affected-requirement precision / recall；
- Context Rebuild Locality；
- unnecessary rebuild；
- stale-context exposure；
- unaffected-context reuse correctness。

### 8. GT-C6 — Independent Consumers

**问题：** GeoTask 是否真的独立于某一个业务、某一种 Provider 或官方 WorldState？

当前：

- Warehouse Robot Picking 独立消费者 ✅

下一步：

- 第二、第三独立领域；
- 不要求 Core Fork；
- 不引入 domain-specific Core branch；
- 使用 GIS / API / Sensor / Database / other provider 直接完成 Task → Context；
- 用相同公共语义度量 Task Sufficiency 与 Context Cost。

### 9. 下一条动态主线 — Reality Change → Context Reassessment

GeoTask 只拥有其中的 Context 部分：

```text
Reality / Provider Change
        ↓
Affected Requirements
        ↓
Applicability / Resolution / Sufficiency Reassessment
        ↓
TaskContext / ContextGap Delta
        ↓
Downstream grounding / domain decision
```

GeoTask 不因此接管：

- world truth resolution；
- Agent runtime lifecycle；
- domain decision；
- business authorization；
- physical action execution。

### 10. Open Strategy

GeoTask 的长期公共资产是：

> **Task Context Method / Engine / Benchmark / Open Protocol**

Provider 必须保持开放：

```text
WorldState
GIS
API
Sensor
Database
Other Provider
```

只要能够映射到 GeoTask 的 ContextCandidate / assessment contracts，就不要求采用官方 WorldState 实现。

### 11. Legacy / Compatibility

v0.1–v0.6 阶段已经发布的以下资产继续保留：

- Verifiable Task Protocol；
- deterministic operators；
- Artifact Registry；
- Verification / Control contracts；
- World-State Cycle；
- Runtime / Verification Provider profiles；
- Reference Agent；
- GT01–GT42 examples；
- historical white paper / cookbook / release notes。

它们是已发布公共兼容资产与项目历史，不静默删除。

但从本 Roadmap 起：

```text
GeoTask long-term target
≠ Trusted World-State Runtime
≠ Verifiable World Model

GeoTask long-term target
= Task Context Engine
```

---

## English roadmap

### 1. North Star

> **Task Sufficiency at Minimum Context Cost**

GeoTask does not optimize for maximum context volume. It aims to provide the context the current task actually needs while keeping critical misses visible.

Primary counter-metric:

> **Critical Context Miss Rate**

Also track false sufficiency, irrelevant/inapplicable context, unnecessary rebuilds, provider latency, carried bytes, token cost, and human recovery cost.

### 2. Current public baseline ✅

The GitHub Public Core now includes:

- `TaskFrame`;
- `ContextRequirement`;
- `ContextCandidate`;
- relevance / applicability contracts;
- resolution requirements and adequacy results;
- `ContextAssessment` / `ContextGap`;
- `SufficiencyAssessment`;
- `TaskContext` / `ContextConstructionTrace`;
- explicit requirement-assessment composition;
- deterministic context construction;
- context minimality / `MinimumSufficientTaskContext`;
- temporal reassessment / continuity contracts;
- provider-neutral composition seams.

A public independent consumer is available at:

- `examples/independent_consumers/warehouse_robot_picking/`

It composes indoor GIS, an inventory API, and an aisle-clearance sensor without requiring the official WorldState implementation and keeps context sufficiency separate from robot action authorization.

### 3. GT-C1 — Requirement Derivation

Develop stable, inspectable Task → Requirement methods, including criticality, spatial/temporal/semantic needs, resolution, validity, freshness, and source constraints.

### 4. GT-C2 — Relevance / Applicability Separation

Prove that the same candidate fact can have different applicability under different task scopes, times, objects, and conditions. Keep relevance and applicability evidence independent.

### 5. GT-C3 — Resolution Adequacy & Sufficiency

Move beyond “data exists” toward explicit spatial, temporal, precision, semantic, coverage, and critical-requirement adequacy.

```text
Available ≠ Adequate
Applicable ≠ Sufficient
High confidence ≠ Sufficient
```

### 6. GT-C4 — Minimum Context Cost

Reduce context cost only while critical misses do not increase.

```text
Context Cost ↓
while
Critical Context Miss does not ↑
```

Separate network acquisition, carried bytes, token cost, provider latency, and human recovery cost.

### 7. GT-C5 — Temporal Reassessment

Map provider/reality changes to affected requirements, reassess only what changed, and rebuild only what is necessary.

```text
Change
→ affected requirements
→ reassessment
→ context/gap delta
→ minimal rebuild
```

### 8. GT-C6 — Independent Consumers

Continue validating Task → Context outside any one domain, provider family, or official WorldState implementation, without Core forks or domain-specific Core branches.

### 9. Dynamic frontier — Reality Change → Context Reassessment

GeoTask owns the context-reassessment portion only. It does not take ownership of world truth, agent runtime lifecycle, domain judgment, business authorization, or physical execution.

### 10. Open strategy

The durable public assets are:

> **Task Context Method / Engine / Benchmark / Open Protocol**

Providers remain open and implementation-neutral: WorldState, GIS, APIs, sensors, databases, and other providers can participate when they map cleanly to GeoTask contracts.

### 11. Legacy / compatibility

Previously released Verifiable Task Protocol, World-State Cycle, Verification, Runtime/Provider, Reference Agent, GT examples, and historical documentation remain public compatibility assets and project history.

They no longer define the long-term positioning:

```text
GeoTask long-term target
= Task Context Engine
```
