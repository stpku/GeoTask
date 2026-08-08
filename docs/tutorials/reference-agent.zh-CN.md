# 从头到尾运行 GeoTask Reference Agent

[English](reference-agent.md) | **简体中文**

本教程面向第一次接触 GeoTask 完整生命周期的开发者。你不需要先阅读 GT01—GT42；目标是在一个虚构的低空设施评估更新场景中，看清一条新证据如何经过 World State、Discrepancy、Correction、Impact 和 Control，最终只得到“报告具备更新条件”，而不是把它误写成“报告已经发布”。

> **边界：** 本教程全部使用虚构数据，只运行公共 Core 和本地参考代码，不访问 Lowa-GT 生产数据库，不调用真实监管数据，不自动写库、发布报告或执行现实动作。

## 1. 准备源码环境

Reference Agent 的固定场景、脚本和体验材料属于公共仓库示例，因此本教程从源码仓库运行：

```bash
git clone https://github.com/stpku/GeoTask.git
cd GeoTask
python -m pip install -e .
```

如果你已经处于 GeoTask 源码工作区，也可以直接继续。`replay.py` 同时兼容源码 checkout 和已安装的 `geotask-core` 包。

## 2. 先运行成功场景

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario success \
  --check-expected
```

固定成功场景描述：

- 基线设施 `FAC-001`；
- 旧障碍物距离为 80 米；
- 最小障碍物距离阈值为 50 米；
- 新地图 Observation 将障碍物位置更新为距离设施 70 米；
- 新证据在声明的有效期内；
- 人工复核条件显式为 `true`。

重点不要只看最终 `satisfied`，而要看状态为什么分三步变化。

## 3. 看懂 rev1 → rev2 → rev3

### rev1：基线 World State

`world_state_before.json` 保存旧业务状态：

```text
obstacle_distance_m = 80
obstacle_clearance_pass = true
accessibility_score = 84
service_capability_score = 78
report_version = report-v4
```

这是不可变基线。Replay 会记录它的 `semantic_fingerprint`，后续不会原地覆盖。

### rev2：只吸收新 Observation

新地图证据被接受后，Reference Agent 先产生 observation-state：

```text
mapped-obstacle-01.position_xy: 80m → 70m
obstacle_distance_m: 仍然是 80
obstacle_clearance_pass: 仍然是 true
```

这一步故意不把评估结果一起改掉。否则系统会失去一个非常重要的事实：**现实输入已经变化，但旧结论尚未重新计算。**

在输出中查看：

```text
reference_agent.world_state_update.observation_state_revision = 2
```

## 4. Discrepancy：明确指出“当前哪里已经不一致”

GeoTask 使用注册的 `geotask.discrepancy-report` 表达：

```text
current observed value = 80m
expected recomputed value = 70m
```

这里 `observed` 是 rev2 当前 World State 中仍存在的旧值，`expected` 才是新证据驱动的确定性重算目标。

这个方向不能反过来。GeoTask 先描述当前状态为什么已经 stale，再请求纠偏，而不是把未来结果冒充当前事实。

查看：

```text
reference_agent.registered_impact_bundle.discrepancy_report
```

## 5. Correction：只允许改两个路径

注册的 `geotask.correction-request` 只允许：

```text
recompute obstacle_distance_m
recompute obstacle_clearance_pass
```

同时显式保护：

```text
accessibility_score
service_capability_score
```

因此一次障碍物证据变化不会自动变成“整站重新评分”。

查看：

```text
reference_agent.registered_impact_bundle.correction_request
```

## 6. Impact：影响必须沿显式依赖链传播

注册的 `geotask.impact-graph` 将有限依赖表示为有向图：

```text
Discrepancy
  → recompute obstacle distance
  → obstacle_distance_m path
  → distance_2d assertion recheck
  → obstacle clearance path
  → assessment_refresh
  → report_refresh
```

它不会自动发现全世界的依赖，也不会把无关设施、无关评分项或整份报告全部纳入重算。

查看：

```text
reference_agent.registered_impact_bundle.impact_graph
```

另外，`reference_agent.impact_scope` 是面向开发者阅读的业务摘要；真正通过 Core 严格校验的规范制品位于 `registered_impact_bundle`。

## 7. rev3：只物化受影响的评估结果

确定性 `distance_2d` 执行后，最终 successor World State 为 revision 3：

```text
obstacle_distance_m = 70
obstacle_clearance_pass = true
accessibility_score = 84       # reuse
service_capability_score = 78  # reuse
```

查看：

```text
reference_agent.world_state_update.successor_revision = 3
```

## 8. Control：具备条件不等于已经执行

Reference Agent 的报告更新门禁要求：

```text
obstacle_distance_m >= min_obstacle_distance_m
AND evidence_verified == true
AND human_review_approved == true
```

成功场景中这些条件全部满足，因此：

```text
assessment_refresh_eligible = true
report_update_eligible = true
```

但必须同时看到：

```text
production_write_performed = false
production_report_refreshed = false
action_authorized = false
action_executed = false
```

GeoTask 只证明外部业务系统**现在具备执行下一步的条件**；真正的 Lowa-GT 或其他行业系统仍必须通过自己的服务边界完成写库、审批和发布，并产生新的权威记录。

## 9. 运行四个失败关闭场景

### 缺少证据

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario missing_evidence \
  --check-expected
```

结果应保持 `unverifiable`，并产生 Evidence Request。

### 新鲜证据互相冲突

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario conflicting_evidence \
  --check-expected
```

70 米与 30 米两个新鲜独立来源同时存在，但未声明来源优先级或仲裁策略，因此保持 `conflicted`。GeoTask 不按到达顺序覆盖，也不自行投票。

### 证据已经过期

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario stale_evidence \
  --check-expected
```

有数据不等于有当前有效证据。结果保持 `unverifiable`。

### 新证据明确否定安全条件

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario contradicted \
  --check-expected
```

障碍物距离变为 30 米，确定性事实可以进入 successor World State，但 `obstacle_clearance_pass=false`，报告刷新保持 blocked。

## 10. 自己修改一个输入

现在不要改 Core 代码。复制成功场景：

```bash
cp examples/reference_agent/facility_assessment_update/scenarios/success.json /tmp/geotask-reference-60m.json
```

编辑 `/tmp/geotask-reference-60m.json`：

```json
{
  "scenario": {
    "id": "developer-60m",
    "evidence": [
      {
        "coordinates": [60, 0]
      }
    ]
  }
}
```

实际文件还需要保留原场景中的时间、来源、生产者、版本和其他字段；只需要把：

```text
scenario.id: success → developer-60m
coordinates: [70, 0] → [60, 0]
```

并删除可选的固定 `expected` 区块即可。

运行：

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py \
  --scenario-file /tmp/geotask-reference-60m.json
```

你应该看到：

```text
distance_m = 60.0
observation_state_revision = 2
successor_revision = 3
report_update_eligible = true
production_report_refreshed = false
```

这一步是 Reference Agent 与 GT 单项案例的重要区别：开发者可以修改真实输入状态，而不是只能观看固定演示。

## 11. 检查确定性重放

同一个固定场景重复运行时，`replay_fingerprint` 应保持一致：

```bash
python3 examples/reference_agent/facility_assessment_update/replay.py --scenario success
python3 examples/reference_agent/facility_assessment_update/replay.py --scenario success
```

测试也会自动验证这一点。

## 12. 运行 Reference Agent 专项测试

```bash
python3 -m pytest \
  tests/test_reference_agent_facility_assessment_update.py \
  tests/test_reference_agent_experience_page.py
```

这些测试覆盖：

- 五类固定场景；
- Unknown / Conflict 失败关闭；
- rev1 / rev2 / rev3 状态分离；
- 注册 Discrepancy / Correction / Impact 制品与 SHA-256 绑定；
- 影响范围与无关结果复用；
- 自定义场景文件；
- 确定性重放；
- `eligible != executed`；
- 公共体验页与项目入口。

## 13. 下一步：映射到 Lowa-GT，而不是复制低空数据库

公开 Reference Agent 只证明通用机制。首个真实行业验证将按照 `GeoTask ↔ Lowa-GT Integration Contract v0.1` 进入只读/影子模式：

```text
Lowa-GT authoritative facility/evidence/assessment/report state
→ bounded Trusted State Snapshot
→ GeoTask Verification / Impact / Control
→ human-readable recommendation
→ Lowa-GT decides whether to rescore or refresh
```

GeoTask 不成为第二个低空 System of Record，也不会直接替 Lowa-GT 写数据库。
