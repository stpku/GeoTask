# 03｜Context、Tool Result 与 World State 为什么必须分开

在很多 Agent 系统里，下面三句话经常被当成同一件事：

1. 模型上下文里出现了一个信息；
2. 某个工具返回了一个结果；
3. 系统认为某个现实事实当前成立。

这三者如果不分开，Agent 的“知道”就会和现实的“成立”混在一起。

## 1. Context：模型当前可见的信息集合

Context 适合承载：

- 用户要求；
- 历史对话；
- 检索片段；
- 工具结果；
- 中间推理所需的摘要；
- 当前计划和约束。

它的核心问题是“模型能否看见”。Context 本身通常不要求每条信息都有稳定对象身份、版本、有效期和证据链。

因此：

```text
in context ≠ verified world fact
```

## 2. Tool Result：一次外部调用的返回值

Tool Result 比 Context 更接近现实，因为它往往来自数据库、地图、传感器、API 或模型服务。但它仍然只回答：

> 在这次调用、这个时间、这个版本和这些输入条件下，外部能力返回了什么？

Tool Result 可能存在：

- 数据版本落后；
- 来源不明；
- 缺少有效期；
- 单位或坐标基准不一致；
- 多来源冲突；
- 调用成功但语义不适用于当前对象；
- 模型输出仅是预测而非事实。

所以更安全的默认路径是：

```text
Tool Result
    ↓
Observation / Candidate Claim
    ↓ verification / source / time / scope checks
World State
```

## 3. World State：被明确纳入当前任务现实表达的版本化状态

GeoTask 的 World State 关注“当前任务依赖什么现实状态”。它要求状态能够被稳定引用、检查和演化。

一个状态进入 World State 后，仍不意味着它永远正确。它意味着：

- 系统知道它属于哪个对象；
- 知道它来自哪些 Observation / Evidence；
- 知道它在什么时间和版本下成立；
- 知道当前验证状态；
- 后续变化可以产生新 revision，而不是原地覆盖历史。

这使得“现实变化”可以被表达成状态迁移，而不是 Prompt 里的句子被悄悄替换。

## 4. 为什么 revision 很重要

Reference Agent 用一个很简单的三版本过程证明这件事：

```text
rev1：旧世界状态，障碍物距离评估为 80m
rev2：新 Observation 已进入，但旧评估仍然是 80m
rev3：完成受限重算后，评估更新为 70m
```

rev2 是整个可信链条最关键的一步之一。

如果一收到新 Observation 就直接把所有派生结果改掉，系统就无法区分：

- “现实输入已经变化”；
- “旧结论已经 stale”；
- “新结论已经完成验证和重算”。

这三个时刻在高风险系统里不能合并。

## 5. 状态更新必须是显式的

GeoTask 当前公共 Core 提供 Observation Merge、State Transition、Discrepancy Report、Correction Request、Recompute Derivation 和 World State Materialization 等契约，目的不是让每一次更新更复杂，而是让更新过程变成可验证机器事实。

理想状态不是：

```text
模型说“我已经更新了”
```

而是：

```text
旧状态指纹
+ 精确输入 Observation
+ 显式允许变更路径
+ 确定性重算值
→ 新状态指纹
```

## 6. 这对 Agent 工程意味着什么

Agent 可以继续自由使用 Context、Memory 和 Tool Calling，但在进入重要判断前，应把真正依赖的现实信息投影到正式状态与证据契约中。

换句话说：

- Context 用于思考；
- Tool Result 用于观察；
- World State 用于承担可验证现实依赖。

下一篇讨论由此自然产生的另一个问题：**如果关键事实没有足够证据，Agent 应该怎么办？**

[上一篇：GeoTask 不是 Agent Framework](02-geotask-is-not-an-agent-framework.zh-CN.md) ｜ [下一篇：AI 知道自己不知道之后，下一步做什么](04-unknown-evidence-and-recovery.zh-CN.md)
