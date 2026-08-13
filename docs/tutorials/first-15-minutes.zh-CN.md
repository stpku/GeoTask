# GeoTask 第一次体验：15 分钟理解一个会变化的世界

本页只回答一个问题：**GeoTask 到底帮助 Agent 解决什么问题？**

第一次接触 GeoTask 时，不需要先学习 GT01—GT42，也不需要先理解 Discrepancy、Correction、Impact Graph、Materialization 等正式 Artifact。先跑通一个完整故事，再决定是否继续深入协议细节。

> **一句话理解 GeoTask：** 当现实发生变化时，GeoTask 让 Agent 知道“什么变了、影响什么、哪些结论需要更新，以及当前是否真的允许行动”。

本教程全部使用虚构数据，只运行公共 Core 和本地 Reference Agent，不访问生产数据库，不读取真实监管数据，也不会执行现实动作。

---

## 0—5 分钟：先看懂故事，不背术语

场景里有一个虚构设施和一个障碍物。

原来的系统状态认为：

```text
障碍物距离 = 80m
安全阈值     = 50m
旧评估       = 通过
```

随后出现一条新的地图 Observation：

```text
障碍物距离变成 70m
```

一个普通脚本最容易做的是：直接把 80 改成 70，然后重新输出“通过”。

GeoTask 不这样做。它保留旧状态，并把变化拆成一个受控过程：

```text
现实出现新信息
      ↓
记录新的 Observation
      ↓
更新当前 World State 中的事实
      ↓
识别旧结论中哪些部分因此变旧
      ↓
只重新计算受影响的部分
      ↓
判断下一步是否具备条件
      ↓
但不擅自执行现实动作
```

因此，第一次体验时只需要记住四个词：

| 概念 | 先这样理解 |
|---|---|
| **Observe** | 我新知道了什么？ |
| **State** | 现在世界是什么样？ |
| **Verify** | 原来的判断还成立吗，哪些地方要更新？ |
| **Act** | 当前是否具备进入下一步的条件？真的执行了吗？ |

此时不用记任何 Artifact 名称。

---

## 5—10 分钟：运行一次完整变化

建议在新的虚拟环境里安装当前发布版：

```bash
python -m pip install --no-cache-dir geotask-core==0.4.1
geotask agent demo --output ./geotask-reference-agent
cd geotask-reference-agent
```

`geotask agent demo` 会生成一个可修改的本地 Reference Agent 工作目录，并立即重放固定成功场景。它不会访问网络事实源、生产数据库或真实业务系统。

如果需要再次运行：

```bash
python replay.py --scenario success --check-expected
```

第一次不要试图读懂全部 JSON。只找下面几类结果：

```text
distance_m = 70.0
obstacle_clearance_pass = true
report_update_eligible = true
production_report_refreshed = false
action_authorized = false
action_executed = false
```

它们共同表达的是：

> 新事实已经被接受；受影响的判断已经重新计算；当前条件允许外部系统继续考虑报告更新；**但 GeoTask 没有替你刷新生产报告，也没有获得现实动作授权。**

这就是 GeoTask 最重要的边界之一：

```text
eligible != authorized != executed
```

---

## 10—15 分钟：自己改一个输入

现在把障碍物再向设施移动 10 米。

复制固定成功场景：

```bash
cp scenarios/success.json /tmp/geotask-reference-60m.json
```

只做三件事：

1. 把 `scenario.id` 从 `success` 改成 `developer-60m`；
2. 把障碍物坐标从 `[70, 0]` 改成 `[60, 0]`；
3. 删除可选的固定 `expected` 区块。

然后运行：

```bash
python replay.py --scenario-file /tmp/geotask-reference-60m.json
```

你应该看到：

```text
distance_m = 60.0
report_update_eligible = true
production_report_refreshed = false
```

如果你已经能解释下面三句话，就完成了第一次 GeoTask 体验：

1. **输入事实变了，所以世界状态也必须留下变化记录；**
2. **不是所有旧结论都要重算，只更新被这个变化影响的部分；**
3. **技术上具备下一步条件，不等于现实动作已经被授权或执行。**

到这里，不要求你准确说出 revision 1、2、3，也不要求记住所有注册 Artifact。

---

## 15—30 分钟：再把直觉映射到正式机制

如果你想继续深入，再阅读完整 Reference Agent 教程。此时可以把刚才的直觉映射到正式术语：

| 直觉 | GeoTask 正式机制 |
|---|---|
| 新信息到来 | Observation |
| 当前可追踪的现实状态 | World State |
| 旧结论与新事实不一致 | Discrepancy |
| 明确哪些路径允许被修正 | Correction Request |
| 明确变化会影响哪些后续判断 | Impact Graph |
| 只重算受影响的值 | Recompute / Reevaluation |
| 形成新的后继状态 | World State Materialization |
| 判断下一步是否具备条件 | Control / Eligibility |
| 不越过现实权限边界 | Authorization / Execution boundary |

完整的 `rev1 → rev2 → rev3` 生命周期也在这个阶段再学习：它用于解释为什么 GeoTask 不原地覆盖历史状态，以及为什么“事实已经变化”和“旧评估已经重算”是两个不同事件。

继续阅读：

- [Reference Agent 从头到尾教程](reference-agent.zh-CN.md)
- [证据、冲突、阻断与恢复](../reference/evidence-and-recovery.md)
- [GeoTask Architecture Series](../articles/architecture-series/README.zh-CN.md)

---

## 第一次体验的成功标准

第一次体验不是架构考试。

一个不了解 GeoTask 的开发者，如果能够在 15 分钟左右做到以下三件事，就已经完成了有效激活：

- 找到并成功运行 Reference Agent；
- 修改一个真实输入并看到确定性结果变化；
- 正确解释“事实变化 → 有限影响 → 受控下一步”，并明确 `eligible != executed`。

准确解释所有 Artifact、revision 生命周期和内部协议关系，应该属于后续的 **Advanced Comprehension**，而不是第一次使用 GeoTask 的前置条件。
