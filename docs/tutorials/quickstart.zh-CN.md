# GeoTask 中文快速入门

[English](quickstart.md) | **简体中文**

第一次接触 GeoTask 时，不需要先读完规范、Artifact 或 GT01—GT42。先根据你的目标选择一条路径：

- **想先知道 GeoTask 解决什么问题：**直接跳到本页的 [15 分钟第一次体验](#4-15-分钟第一次体验一个会变化的世界)，用一个会变化的 Reference Agent 场景理解“事实变化 → 有限影响 → 受控下一步”。
- **想先学习 GeoTask Core 文件和 CLI：**从第 1 节开始，用一个最小距离任务完成安装、验证和确定性执行。

公共 GeoTask Core 可以完全离线运行；本页不调用大模型，不需要模型密钥，也不会访问生产系统。

## 1. 安装并自检

要求 Python 3.10 及以上。推荐在独立虚拟环境中验证当前发布版：

```bash
python -m venv .venv
```

Linux 或 macOS：

```bash
source .venv/bin/activate
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

安装固定版本：

```bash
python -m pip install --no-cache-dir geotask-core==0.4.1
```

检查实际安装版本和 CLI：

```bash
python -c "from importlib.metadata import version; print(version('geotask-core'))"
geotask --help
```

预期安装版本：

```text
0.4.1
```

然后运行一次安装自检：

```bash
geotask inspect health
```

`inspect health` 检查已安装包身份、Schema、Artifact、Operator、Capability、Reference Agent 和离线 benchmark 等公共能力。它不会访问网络事实源、调用模型、写入生产状态或授权现实动作。

## 2. 创建一个最小 GeoTask

新建 `my_distance.yaml`：

```yaml
geotask:
  id: my-distance
  schema_version: "1.0"

space:
  crs:
    type: local_cartesian
    identifier: local_xy_m
  horizontal_unit: meter
  coordinate_order: [x, y]

objects:
  start:
    type: point
    coordinates: [0, 0]
  end:
    type: point
    coordinates: [6, 8]

operator_set:
  - distance_2d

tasks:
  - id: calculate-distance
    family: measurement
    goal: 计算 start 与 end 之间的二维欧氏距离
    assertions:
      - id: route_distance
        operator: distance_2d
        object_refs: [start, end]
        unit: meter

execution:
  mode: local_only

output_contract:
  format: structured
  required_fields:
    - route_distance
```

先验证结构和引用：

```bash
geotask validate my_distance.yaml
```

再执行：

```bash
geotask run my_distance.yaml
```

预期距离为 **10 米**。

这一小步已经体现了 GeoTask Core 的基本原则：对象、空间基准、算子和输出契约都是显式的，确定性结果可以被重新计算，而不是只相信一段模型生成文本。

## 3. 查看当前能力，不背静态清单

首次使用时不需要记住当前有多少个 Operator、Artifact 或 Schema。安装包中的 Registry 才是当前能力的机器可读来源：

```bash
geotask inspect operators
geotask inspect capabilities
geotask inspect schemas --format json
```

公共 v1 GeoTask 文档的 JSON Schema 文件位于：

```text
schemas/geotask-v1.0.schema.json
```

仓库同时提供可直接复用的本地 IDE Schema 配置 `.vscode/settings.json`。核心映射是：

```json
{
  "yaml.schemas": {
    "./schemas/geotask-v1.0.schema.json": [
      "**/*.geotask.yaml",
      "**/*.geotask.yml",
      "examples/core/v1_*.yaml"
    ]
  }
}
```

该配置只引用仓库内的本地 Schema，不依赖远程 Schema 服务。

文档中的示例用于帮助理解，不应代替 Registry 充当静态能力清单。这样可以避免版本升级后，教程里的数量或名称与实际安装包漂移。

如果你只想看看一个算子的输入、输出和边界语义，可以从 `geotask inspect operators` 的结果开始，而不必先阅读全部语言规范。

## 4. 15 分钟第一次体验：一个会变化的世界

这一段只回答一个问题：**GeoTask 到底帮助 Agent 解决什么问题？**

> **一句话理解 GeoTask：** 当现实发生变化时，GeoTask 让 Agent 知道“什么变了、影响什么、哪些结论需要更新，以及当前是否真的允许行动”。

### 0—5 分钟：先看懂故事，不背术语

场景里有一个虚构设施和一个障碍物。原来的系统状态认为：

```text
障碍物距离 = 80m
安全阈值     = 50m
旧评估       = 通过
```

随后出现一条新的地图 Observation：

```text
障碍物距离变成 70m
```

GeoTask 不把 80 静默覆盖成 70 后直接给出一个新结论，而是保留变化并进入受控更新：

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

第一次只需要记住四个直觉：

| 概念 | 先这样理解 |
|---|---|
| **Observe** | 我新知道了什么？ |
| **State** | 现在世界是什么样？ |
| **Verify** | 原来的判断还成立吗，哪些地方要更新？ |
| **Act** | 当前是否具备进入下一步的条件？真的执行了吗？ |

此时不用记任何 Artifact 名称。

### 5—10 分钟：运行一次完整变化

生成一个可修改的 Reference Agent 工作目录：

```bash
geotask agent demo --output ./geotask-reference-agent
cd geotask-reference-agent
```

如果需要再次运行固定成功场景：

```bash
python replay.py --scenario success --check-expected
```

第一次不要试图读懂全部 JSON，只找下面几类结果：

```text
distance_m = 70.0
obstacle_clearance_pass = true
report_update_eligible = true
production_report_refreshed = false
action_authorized = false
action_executed = false
```

它们共同表达：新事实已经被接受；受影响的判断已经重新计算；当前条件允许外部系统继续考虑报告更新；**但 GeoTask 没有替你刷新生产报告，也没有获得现实动作授权。**

```text
eligible != authorized != executed
```

### 10—15 分钟：自己改一个输入

复制固定成功场景：

```bash
cp scenarios/success.json /tmp/geotask-reference-60m.json
```

然后：

1. 把 `scenario.id` 从 `success` 改成 `developer-60m`；
2. 把障碍物坐标从 `[70, 0]` 改成 `[60, 0]`；
3. 删除可选的固定 `expected` 区块。

运行：

```bash
python replay.py --scenario-file /tmp/geotask-reference-60m.json
```

你应该看到确定性结果随输入变化，例如：

```text
distance_m = 60.0
report_update_eligible = true
production_report_refreshed = false
```

如果你已经能解释下面三句话，就完成了第一次 GeoTask 体验：

1. **输入事实变了，所以世界状态也必须留下变化记录；**
2. **不是所有旧结论都要重算，只更新被这个变化影响的部分；**
3. **技术上具备下一步条件，不等于现实动作已经被授权或执行。**

到这里，不要求你准确说出 `rev1 → rev2 → rev3`，也不要求记住所有注册 Artifact。准确解释完整 revision 生命周期、Discrepancy、Correction、Impact Graph、Materialization 等机制，属于后续 **Advanced Comprehension**。

## 5. 模型输出与本地验证

GeoTask Core 本身不会调用大模型，但可以验证模型产生的候选结果：

```bash
geotask normalize examples/deepseek_output_sample.txt
geotask eval examples/core/v1_minimal_distance.yaml examples/deepseek_output_sample.txt
```

基本关系是：

```text
模型生成候选结果
＋
本地确定性执行结果
→
verified / contradicted / need_review
```

模型表达流畅不代表结果已经验证。GeoTask 的作用之一，就是把“模型说了什么”和“按照明确对象、规则与证据实际能确认什么”分开。

## 6. 什么时候再读规范和案例

完成上面的最小任务或 15 分钟体验后，再按需要深入：

- [P1 陌生开发者激活协议 v0.2](../reference/developer-activation-protocol-v0.2.md) —— **当前简化盲测协议**；首次激活硬门槛聚焦“固定场景可运行、自定义输入可修改、bounded impact 与 `eligible != executed` 可理解”，15 分钟完成情况和 `rev1 → rev2 → rev3` 作为度量继续记录，但不单独阻断首次 Product Activation。
- [P1 陌生开发者激活协议 v0.1](../reference/developer-activation-protocol-v0.1.md) —— **历史证据基线**；仅用于解释既有 v0.1 参与者记录，v0.2 不回写或重新解释这些历史证据。
- [Reference Agent 从头到尾教程](reference-agent.zh-CN.md) —— 学习 Observation、World State、Discrepancy、Correction、Impact、Reevaluation 和 revision 生命周期；
- [GeoTask 白皮书](../whitepaper/GeoTask_White_Paper_v0.1.md) —— 理解整体思想与长期方向；
- [当前实现语言与执行规范](../spec/geotask-language-spec-v1.0.md) —— 编写正式 GeoTask 文件；
- [证据、冲突、阻断与恢复](../reference/evidence-and-recovery.md) —— 理解 Unknown、Evidence 与 fail-closed；
- [GT01—GT20 中文案例手册](../cookbook/gt01-gt20.zh-CN.md) —— 从确定性空间关系逐步进入证据与行动约束；
- [GeoTask Architecture Series](../articles/architecture-series/README.zh-CN.md) —— 从 Agent 架构角度理解 Trusted World State。

如果你的目标是参与 Core 开发，再使用源码安装：

```bash
git clone https://github.com/stpku/GeoTask.git
cd GeoTask
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
```

## 7. 当前边界

公共 Core 不包含模型 API、生产编排、行业 Domain Pack、客户数据连接器和自动设备控制。Reference Agent 和公开案例使用虚构或固定输入，用来演示和验证机器契约，不代表现实业务授权。

尤其需要保持：

```text
技术验证通过 != 现实事实自动成立
eligible != authorized != executed
```

GeoTask 可以帮助 Agent 知道当前事实、影响和行动条件，但不会因为一个技术结果为 `true` 就自动获得现实世界的执行权限。
