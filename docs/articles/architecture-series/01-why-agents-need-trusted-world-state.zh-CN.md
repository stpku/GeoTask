# 01｜为什么 Agent 需要可信世界状态

今天的大模型 Agent 已经很擅长理解语言、规划步骤、调用工具和生成建议。问题在于：**会推理，不等于知道现实世界现在到底是什么状态。**

一个 Agent 可以同时看到聊天上下文、搜索结果、传感器数据、数据库查询、模型预测和人工输入。这些内容都可能有价值，但它们天然具有不同的来源、时间、版本、适用范围和可信程度。如果系统把“当前看见的信息”直接当成“当前真实世界”，很多高风险错误会在软件边界里被悄悄吞掉。

## 1. Context 不是现实

LLM Context 的作用是让模型在一次推理中看到信息。它适合表达“模型现在知道了什么”，却不天然回答：

- 这个事实是谁提供的？
- 它什么时候成立？
- 现在是否仍然有效？
- 它适用于哪个对象和空间范围？
- 是否有另一份证据与它冲突？
- 这个结论是否已经因为上游事实变化而失效？

这些问题不是 Prompt 写得更长就能彻底解决的。它们需要一个外显、版本化、可验证的状态层。

## 2. Tool Result 也不是自动成立的事实

工具调用返回成功，只能证明“工具返回了一个结果”。它不能自动证明结果代表当前现实。

地图服务可能过期，传感器可能漂移，数据库记录可能滞后，模型输出可能只是候选判断。GeoTask 因此把外部输入优先视为 Observation、Candidate Claim 或 Evidence，而不是让调用成功直接升级为 World State 真值。

## 3. World State 要回答的是“此刻我们凭什么这么认为”

GeoTask 所追求的 World State 不是把整个世界复制进数据库，而是把一个任务真正依赖的现实状态明确表达出来。一个可验证状态至少需要能够绑定：

- 对象身份；
- 空间与时间；
- 属性与关系；
- 来源与证据；
- 版本与有效期；
- 验证状态；
- 与后续判断之间的依赖。

这样，Agent 做决策时依赖的就不再只是“上下文里有一句话”，而是一个可以检查、比较、重放和更新的机器对象。

## 4. 可信不是“永远正确”，而是“不掩盖不确定性”

一个可信系统不应该因为必须给出答案，就把未知压成 false，也不应该在证据冲突时偷偷选一个来源。

GeoTask 长期保留的关键状态包括：

- `SATISFIED`：当前证据支持条件成立；
- `CONTRADICTED`：当前证据明确否定条件；
- `UNVERIFIABLE`：缺少足够证据，无法判断；
- `CONFLICTED`：存在无法按已声明规则消解的冲突。

这里最重要的能力不是“多一个状态枚举”，而是让系统在不知道时能够**停下来，并说明缺什么**。

## 5. 世界状态真正有价值的地方是“变化之后怎么办”

静态校验只能回答“现在这个结论对不对”。现实系统更难的问题是：

> 上游事实改变以后，哪些已有结论、报告、控制条件必须失效、复核或重算？

因此 GeoTask 的长期核心不只是状态本身，还包括 Dependency / Impact：把“事实变化”沿着显式依赖传播到受影响的判断，同时避免全局无边界重算。

这也是为什么 GeoTask 的演进主轴逐渐从任务规则扩展到：

```text
Observation / Evidence
        ↓
World State
        ↓
Verification
        ↓
Discrepancy / Evidence Request
        ↓
Impact / bounded recomputation
        ↓
Control Evaluation
```

## 6. GeoTask 当前做到了哪里

当前公共 Core 已经提供 Observation、World State、State Transition、Verification Session、Discrepancy Report、Correction Request、Impact Graph、受限重算、后继状态物化、增量复核和 Control Evaluation 等公开契约与确定性实现。

这已经能证明“可信世界状态运行时”的关键机制，但仍不意味着 GeoTask 已经成为一个完整生产级 World-State Runtime。生产存储、真实数据接入、企业权限、审批编排和现实动作执行仍属于外部 Runtime、行业系统或未来企业能力边界。

下一篇继续回答一个容易混淆的问题：**既然 Agent 已经有 Workflow、Memory 和 Tool Calling，为什么还需要 GeoTask？**

[下一篇：GeoTask 不是 Agent Framework，而是可信状态与控制层](02-geotask-is-not-an-agent-framework.zh-CN.md)
