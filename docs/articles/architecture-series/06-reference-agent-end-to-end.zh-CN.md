# 06｜从头到尾做一个 GeoTask Reference Agent

前五篇讲的是思想。最后一篇把这些原则压缩成一个开发者真正能运行、修改、失败关闭和重放的 Agent 闭环。

这个 Reference Agent 使用的是**虚构低空设施评估更新**场景。它不是低空产品，也不接真实行业数据库；它只是用一个足够具体的场景证明 GeoTask 的通用生命周期。

## 1. 先安装并生成教材工作区

```bash
pip install geotask-core
geotask agent demo --output ./geotask-reference-agent
cd geotask-reference-agent
```

`agent demo` 会先验证安装包中的 Reference Agent bundle，再生成一份开发者可修改的本地工作区，并执行一次 `success` 场景重放。

这个动作本身仍是本地、离线、无副作用的：

```text
external_truth_fetched = false
production_write_performed = false
action_authorized = false
action_executed = false
```

## 2. 用户任务不是“算一个距离”，而是维护一个可信决定

场景中的用户要求大意是：

> 一个虚构设施收到新的障碍物地图 Observation。只重新评估依赖障碍物净空的结论，保留无关评估项，说明仍然未知或冲突的部分，并判断报告是否具备刷新条件。不要发布报告，也不要执行现实动作。

这里真正的任务不是 `distance_2d`。距离只是一个确定性算子。完整任务需要回答：

- 新证据能否进入当前世界状态；
- 旧评估是否已经 stale；
- 哪些路径允许修改；
- 哪些结论需要重算；
- 哪些结果必须复用而不能跟着全量刷新；
- 最终只是 `eligible`，还是已经发生写入。

## 3. rev1：先冻结旧世界状态

初始状态里：

```text
obstacle_distance_m = 80
obstacle_clearance_pass = true
accessibility_score = 84
service_capability_score = 78
```

Reference Agent 先记录 revision 1 的状态和语义指纹。它不会在原对象上直接改值。

## 4. rev2：新 Observation 进入，但旧结论暂时不改

新地图 Observation 表示障碍物位置变化，对应距离变成 70m。

此时系统首先形成 revision 2：

```text
obstacle position = new observation
obstacle_distance_m = still 80
obstacle_clearance_pass = still true
```

这不是错误，而是刻意保留一个关键事实：**现实输入已经变化，旧评估尚未重算。**

## 5. Discrepancy：明确指出哪里已经 stale

系统现在可以生成 Discrepancy Report：

```text
current stored assessment = 80m
expected recomputed value = 70m
```

Discrepancy 不负责修复。它只把“当前状态哪里不一致、为什么不一致、影响什么”变成正式制品。

## 6. Correction：限制允许修改的范围

Correction Request 只允许重新计算：

```text
obstacle_distance_m
obstacle_clearance_pass
```

同时显式保护：

```text
accessibility_score
service_capability_score
```

这样一次局部地图更新不会被放大成整站重评分。

## 7. Impact：把变化沿显式依赖传播

Impact Graph 表达有限依赖链：

```text
new obstacle evidence
→ obstacle distance discrepancy
→ distance recomputation
→ clearance reassessment
→ assessment refresh gate
→ report refresh gate
```

GeoTask Core 不自动发现“所有可能依赖”，也不因为存在一条变化就触发全局重算。

## 8. rev3：只物化受影响的后继状态

完成确定性重算后，revision 3 变为：

```text
obstacle_distance_m = 70
obstacle_clearance_pass = true
accessibility_score = 84       # reused
service_capability_score = 78  # reused
```

现在旧状态、Observation-state 和重算后的 successor state 三个阶段都可以独立重放和审计。

## 9. Control：条件满足仍然不是现实执行

成功场景最终得到：

```text
assessment_refresh_eligible = true
report_update_eligible = true
```

同时必须继续保持：

```text
production_write_performed = false
production_report_refreshed = false
action_authorized = false
action_executed = false
```

这正是整个 Reference Agent 最重要的结论之一：**Answers are cheap; decisions need evidence; actions need authority.**

## 10. 运行失败关闭场景

教材包同时包含四类失败路径：

```bash
python replay.py --scenario missing_evidence --check-expected
python replay.py --scenario conflicting_evidence --check-expected
python replay.py --scenario stale_evidence --check-expected
python replay.py --scenario contradicted --check-expected
```

分别用于证明：

- 没证据时保持 `unverifiable`；
- 证据冲突且无显式仲裁策略时保持 `conflicted`；
- 有数据但过期时不能当作当前事实；
- 新鲜证据明确否定条件时可以得到 `contradicted`，但仍不自动执行动作。

## 11. 自己修改一个真实输入

复制成功场景：

```bash
cp scenarios/success.json ./developer-60m.json
```

只修改场景 id，把障碍物坐标从 `[70, 0]` 改成 `[60, 0]`，并删除固定 `expected` 区块，然后运行：

```bash
python replay.py --scenario-file ./developer-60m.json
```

你应该看到：

```text
distance_m = 60.0
observation_state_revision = 2
successor_revision = 3
report_update_eligible = true
production_report_refreshed = false
```

这一步很重要：Reference Agent 不是只能观看的演示，而是可以修改输入并观察整个可信生命周期如何变化的教材产品。

## 12. 从这个 Agent 学到的不是低空规则，而是一种 Agent 结构

完整模式可以抽象为：

```text
User Task
   ↓
Agent Proposal
   ↓
World State Snapshot
   ↓
Verification
   ↓
Unknown / Conflict / Discrepancy
   ↓
Evidence Request / Correction
   ↓
Impact + bounded recomputation
   ↓
Successor World State
   ↓
Control Evaluation
   ↓
eligible / authorized / executed explicitly separated
```

换成物流、机器人、网络规划、民航、工业运维或其他高风险场景时，行业对象和规则应该留在各自系统或 Pack / Provider 中；GeoTask 复用的是上面的可信生命周期，而不是复制一套低空数据库。

## 13. 下一步

想看完整命令、五类场景和字段解释，可以继续阅读：

- [Reference Agent 从零教程](../../tutorials/reference-agent.zh-CN.md)
- [Reference Agent v0.1 规格](../../reference/reference-agent-v0.1.md)
- [P1 陌生开发者激活协议](../../reference/developer-activation-protocol-v0.1.md)

Architecture Series 到这里完成第一版闭环：从“为什么需要可信世界状态”一直走到“怎样把它做成一个真正可运行的 Agent”。

[上一篇：从可信结论到可信行动](05-from-trusted-conclusion-to-trusted-action.zh-CN.md) ｜ [返回系列目录](README.zh-CN.md)
