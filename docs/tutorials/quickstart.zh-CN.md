# GeoTask 中文快速入门

[English](quickstart.md) | **简体中文**

第一次接触 GeoTask 时，不需要先读完规范、Artifact 或 GT01—GT42。先根据你的目标选择一条路径：

- **想先知道 GeoTask 解决什么问题：**直接进入 [15 分钟第一次体验](first-15-minutes.zh-CN.md)，用一个会变化的 Reference Agent 场景理解“事实变化 → 有限影响 → 受控下一步”。
- **想先学习 GeoTask Core 文件和 CLI：**继续本页，用一个最小距离任务完成安装、验证和确定性执行。

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

检查实际安装版本：

```bash
python -c "from importlib.metadata import version; print(version('geotask-core'))"
```

预期输出：

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

文档中的示例用于帮助理解，不应代替 Registry 充当静态能力清单。这样可以避免版本升级后，教程里的数量或名称与实际安装包漂移。

如果你只想看看一个算子的输入、输出和边界语义，可以从 `geotask inspect operators` 的结果开始，而不必先阅读全部语言规范。

## 4. 如果你的目标是 Agent 世界状态更新

最小距离任务只能说明 GeoTask 能进行显式、确定性的任务验证；它还没有展示 GeoTask 更重要的“世界会变化”问题。

接下来运行：

```bash
geotask agent demo --output ./geotask-reference-agent
```

然后进入：

- [15 分钟第一次体验](first-15-minutes.zh-CN.md) —— 先理解产品价值和最小闭环；
- [Reference Agent 从头到尾教程](reference-agent.zh-CN.md) —— 再学习 Observation、World State、Discrepancy、Correction、Impact、Reevaluation 和 revision 生命周期。

建议顺序是：**先跑通，再理解闭环，最后学习正式 Artifact。**

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
