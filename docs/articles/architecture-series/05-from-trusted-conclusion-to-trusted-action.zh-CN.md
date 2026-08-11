# 05｜从可信结论到可信行动：Eligibility、Authority 与 Execution

很多 AI 系统最危险的语义跳跃，不发生在“事实判断”阶段，而发生在最后一步：

> 条件满足了，所以系统就可以执行。

这句话经常把三种完全不同的状态压成一个 Boolean。

## 1. Eligibility 只回答“是否具备进入下一阶段的条件”

例如，一个评估流程经过验证后可能得到：

```text
report_update_eligible = true
```

这意味着：当前证据、重算结果和控制条件已经满足“可以考虑更新报告”的技术门槛。

它不意味着：

- 已经获得业务负责人批准；
- 已经获得生产写权限；
- 已经发布报告；
- 已经修改数据库；
- 已经执行现实动作。

因此：

```text
eligible ≠ authorized
```

## 2. Authority 必须来自明确的外部权威

GeoTask Core 不应该凭技术条件自行创造现实权限。

真正的授权可能来自：

- 人工审批；
- 外部业务系统；
- 权限与策略服务；
- 法定或组织流程；
- 已签发且仍有效的授权记录。

Core 可以验证调用方提供的授权材料是否结构闭合、版本一致、是否满足已声明控制条件，但不能因为“算法觉得可以”就把 `authorized` 从 false 改成 true。

因此：

```text
technical condition satisfied
        ↓
eligible = true
        ↓
external authority decision
        ↓
authorized = true / false / unverifiable
```

## 3. Authorized 也不等于 Executed

即使一个动作已经获得批准，它仍可能因为网络错误、人工取消、设备故障、幂等保护或执行窗口关闭而没有实际发生。

因此必须继续区分：

```text
authorized ≠ sent ≠ executed
```

一个可信系统应能够明确记录：

- 是否允许执行；
- 是否已经形成指令；
- 指令是否发送；
- 外部系统是否接受；
- 现实动作是否真正完成；
- 完成后有什么可审计证据。

## 4. 为什么这不是“多几个字段”

如果把这些状态混在一起，LLM 很容易生成类似：

> “验证通过，报告已更新。”

但底层事实可能只是：

```text
report_update_eligible = true
action_authorized = false
production_write_performed = false
production_report_refreshed = false
action_executed = false
```

在普通聊天里，这可能只是表述不严谨；在高风险物理世界 Agent 中，它会直接变成责任边界错误。

## 5. Batch 场景更容易暴露这个问题

单条候选的边界已经重要，批量流程更容易出现另一种错误：

> “这批候选都通过技术筛选，所以可以批量执行。”

但正确的通用原则仍然是：

```text
Batch Eligibility ≠ Batch Authority ≠ Execution
```

GeoTask 已经建立公开的 Cross-Line Promotion Gate 与第二系统验证协议：任何准备进入 Core 的通用抽象，都必须有独立第二系统/行业复用证据，并经过显式 Gate 决定。仅凭一个行业中的批量流程经验，不能把类似原则直接写成新的 Core 所有权事实。这体现了同一个原则：**技术上看起来合理，不等于架构所有权已经获准迁移。**

## 6. GeoTask 的责任边界

GeoTask Core 长期应该擅长：

- 判断哪些前提已经满足；
- 暴露哪些条件仍未知或冲突；
- 绑定授权所需的证据和控制条件；
- 生成可审计的 Control Evaluation；
- 保持 `action_executed=false`，除非调用方/runtime 边界明确提供真实执行事实。

GeoTask Core 不应该：

- 自动拥有行业生产写权限；
- 从 eligibility 推断 approval；
- 从 approval 推断现实执行；
- 把验证制品包装成已经发生的现实动作。

下一篇把前五篇全部串起来，直接从安装开始，做一个可以运行、修改、失败关闭和重放的 Reference Agent。

[上一篇：AI 知道自己不知道之后](04-unknown-evidence-and-recovery.zh-CN.md) ｜ [下一篇：从头到尾做一个 GeoTask Reference Agent](06-reference-agent-end-to-end.zh-CN.md)
