# 02｜GeoTask 不是 Agent Framework，而是可信状态与控制层

很多人第一次看到 GeoTask，会把它和 Agent Framework、Workflow Engine、Memory、Tool Router 放在一起比较。这个比较很自然，但如果把 GeoTask 也做成“另一个 Agent 框架”，它最有价值的边界反而会消失。

## 1. Agent Framework 主要解决“怎么做事”

典型 Agent Framework 关注的是：

- 如何组织 Prompt 和 Context；
- 如何选择和调用 Tool；
- 如何拆解任务与规划步骤；
- 如何管理多轮 Memory；
- 如何编排多个 Agent；
- 如何处理失败重试和流程状态。

这些能力回答的是：**Agent 如何完成一项工作。**

GeoTask 要回答的是另一个问题：

> Agent 在做决定之前，依赖的现实状态是否可验证？决定形成之后，它是否真的具备进入下一行动阶段的条件？

## 2. GeoTask 更像 Agent 与现实世界之间的 Trust Control Plane

可以把软件栈简化为：

```text
LLM / Multimodal Model
        ↓
Agent reasoning / planning / workflow
        ↓
GeoTask Core
  - World State
  - Evidence
  - Verification
  - Impact
  - Control
  - Artifact / Replay
        ↓
Runtime / Provider / Industry System
        ↓
Database / API / Device / Human workflow
```

GeoTask 不替 Agent 决定“该调用哪个工具”，也不拥有行业系统的业务真相。它提供一组稳定机器契约，让 Agent 和外部系统能够明确知道：

- 当前判断依赖什么状态；
- 这些状态由什么证据支持；
- 哪些地方未知或冲突；
- 上游变化会影响哪些结论；
- 哪些输出只是 `eligible`；
- 哪些动作仍然没有被 `authorized`；
- 哪些执行事实上没有发生。

## 3. 为什么不能把行业数据库直接塞进 GeoTask

如果 GeoTask 为每个行业复制一套对象库、规则库、审批库和生产数据库，它会迅速变成一个大而全的行业平台，而不是通用可信层。

更稳健的方式是：

```text
Industry System of Record
        ↓ bounded snapshot / reference
GeoTask verification and control artifacts
        ↓
Industry System decides next business action
```

权威业务系统继续拥有：真实对象、业务数据、领域规则、人工审批、报告和生产写入。GeoTask 只接收任务所需的受限状态投影和引用，并输出可验证制品。

这也是为什么同一个仓库里出现 Integration 代码，并不意味着 Integration 能力自动属于 Core。能力所有权变化必须经过显式 Promotion Gate。

## 4. 为什么也不应该把 GeoTask 做成自动执行平台

GeoTask 的强项是把“事实是否成立”“证据是否充分”“控制条件是否满足”拆开。若 Core 自己直接执行生产动作，就会把判断层与执行权限重新耦合。

因此应长期保留至少三层：

```text
eligible   = 技术/证据条件允许进入下一阶段判断
authorized = 外部权威明确授予执行权限
executed   = 现实动作确实发生并有可审计记录
```

三者可以全部为 false，也可以 `eligible=true` 而后两者仍为 false。这个差别不是文案问题，而是高风险 Agent 的架构边界。

## 5. GeoTask 与 Memory 有什么不同

Memory 解决“之前发生过什么、模型以后还要记住什么”。World State 解决“当前任务依赖的现实状态是什么，以及为什么可以相信它”。

一个 Memory 条目可以说：“昨天地图显示障碍物距离 80 米。”

一个可信 World State 还需要知道：

- 该记录的来源和版本；
- 当前有效时间；
- 对应哪个对象；
- 是否已有更新 Observation；
- 更新后哪些评估已经 stale；
- 哪些结论需要重算。

Memory 可以成为 Observation 的来源，但 Memory 本身不自动等于当前 World State。

## 6. 当前产品边界

当前公共 GeoTask Core 已经形成可验证任务协议、世界状态与证据制品、确定性验证、影响与有限重算、控制评估、Artifact Registry 和 Reference Agent 教材闭环。

它没有宣称替代完整 Agent Framework，也没有提供企业级 World State Store、生产审批中心或现实执行控制器。这样的边界是刻意设计，而不是“功能还没堆够”。

下一篇进一步拆开三个经常被混为一谈的对象：**Context、Tool Result 和 World State。**

[上一篇：为什么 Agent 需要可信世界状态](01-why-agents-need-trusted-world-state.zh-CN.md) ｜ [下一篇：Context、Tool Result 与 World State](03-context-tool-result-world-state.zh-CN.md)
