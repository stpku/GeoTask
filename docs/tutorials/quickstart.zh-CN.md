# GeoTask中文快速入门

[English](quickstart.md) | **简体中文**

本教程使用当前公共GeoTask Core，完成安装、验证、执行、查看结果和检查算子五个步骤。公共Core完全离线运行，不调用大模型，也不需要模型密钥。

## 1. 环境要求

- Python 3.10及以上；
- Git；
- 推荐使用独立虚拟环境。

```bash
git clone https://github.com/stpku/GeoTask.git
cd GeoTask
python -m venv .venv
```

Linux或macOS：

```bash
source .venv/bin/activate
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

安装Core和开发依赖：

```bash
pip install -e ".[dev]"
```

## 2. 运行第一个任务

仓库已经提供一个3-4-5距离案例：

```bash
geotask validate examples/core/v1_minimal_distance.yaml
geotask run examples/core/v1_minimal_distance.yaml
```

任务使用两个点：

```yaml
objects:
  point_a:
    type: point
    coordinates: [0, 0]
  point_b:
    type: point
    coordinates: [3, 4]
```

断言把对象与确定性算子显式绑定：

```yaml
assertions:
  - id: ab_distance
    operator: distance_2d
    object_refs: [point_a, point_b]
    unit: meter
```

本地执行结果应包含：

```text
ab_distance = 5.0 meter
assurance_level = local_deterministic
```

## 3. 自己创建一个任务

新建`my_distance.yaml`：

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
    goal: 计算start与end之间的二维欧氏距离
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

执行：

```bash
geotask validate my_distance.yaml
geotask run my_distance.yaml
```

预期距离为10米。

## 4. 查看当前算子

```bash
geotask inspect operators
```

公共Core当前提供六个确定性算子：

- `distance_2d`
- `line_intersects_rect`
- `point_to_line_distance_2d`
- `rect_contains_point`
- `time_overlap`
- `altitude_overlap`

每个算子都有明确的输入对象类型、输出类型和边界语义。不要仅为了某个演示方便就新增Core算子；只有稳定、通用、可测试的语义才适合进入Core。

## 5. 使用JSON Schema

机器可读Schema位于：

```text
schemas/geotask-v1.0.schema.json
```

可以在IDE、CI或自己的工具中验证GeoTask YAML/JSON结构。仓库测试会使用该Schema检查公开v1案例，防止规范与示例漂移。

## 6. 模型输出与本地验证

GeoTask Core不会调用大模型，但可以处理模型输出：

```bash
geotask normalize examples/deepseek_output_sample.txt
geotask eval examples/core/v1_minimal_distance.yaml examples/deepseek_output_sample.txt
```

基本流程是：

```text
模型生成候选结果
＋
本地确定性执行结果
→
verified / contradicted / need_review
```

模型表达流畅不代表结果已经验证。本地执行器的作用是使用同一对象、同一算子和同一单位重新计算。

## 7. 学习GT01—GT13

建议按照四个阶段学习：

1. **GT01—GT03：空间关系**——距离、边界和多段路线；
2. **GT04—GT06：时空组合**——高度、时间和显式组合规则；
3. **GT07—GT09：不确定性与证据**——不知道、补证据和证据冲突；
4. **GT10—GT13：行动与可行性**——机器人协同、可达性、能源余量和车辆空间包络。

详见[GT01—GT13中文案例手册](../cookbook/gt01-gt13.zh-CN.md)。

## 8. 运行测试

```bash
pytest
```

只运行文档和Schema测试：

```bash
pytest tests/test_documentation_system.py -q
```

## 9. 当前边界

公共Core不包含模型API、生产编排、行业Domain Pack、客户数据连接器和自动设备控制。案例中的`blocked`、`conflicted`、`resume_when`等主要是放在`extensions`中的工作流扩展语义，不应被误认为当前Core已经实现的全部基础状态。

下一步可阅读：

- [GeoTask白皮书](../whitepaper/GeoTask_White_Paper_v0.1.md)
- [当前实现语言与执行规范](../spec/geotask-language-spec-v1.0.md)
- [状态与可信等级](../reference/status-model.md)
- [证据、冲突、阻断与恢复](../reference/evidence-and-recovery.md)
