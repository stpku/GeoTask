# GeoTask中文快速入门

[English](quickstart.md) | **简体中文**

本教程使用当前公共GeoTask Core，完成安装、验证、执行、查看结果和检查算子五个步骤。公共Core完全离线运行，不调用大模型，也不需要模型密钥。

## 1. 在全新虚拟环境中安装

要求Python 3.10及以上。推荐为首次验证创建独立虚拟环境：

```bash
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

从PyPI安装固定版本，并检查CLI与算子注册表：

```bash
python -m pip install --no-cache-dir geotask-core==0.4.0
geotask --help
geotask inspect operators
```

检查已安装的发行版本：

```bash
python -c "from importlib.metadata import version; print(version('geotask-core'))"
```

预期输出为`0.4.0`。

## 2. 检查安装结果

`geotask --help`应列出`validate`、`run`、`inspect`、`normalize`和`eval`等命令；`geotask inspect operators`应列出当前公共Core注册的14个确定性算子。完成这一步后即可创建并运行自己的GeoTask文件。

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

公共Core当前提供九个确定性算子：

- `distance_2d`
- `line_intersects_rect`
- `multi_polyline_intersects_rect`
- `point_in_polygon`
- `polygon_contains_point`
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

发布前可运行离线Core门禁：

```bash
geotask benchmark core --enforce-performance --output core-benchmark.json
geotask artifact validate geotask.core-benchmark-report core-benchmark.json
```

其中性能阈值只用于同一受控环境下的本机回归检查，不应将不同硬件上的报告作为性能排名。

通过以下命令可获取全部公共Artifact的Schema及文件匹配模式：

```bash
geotask inspect schemas --format json
```

仓库已经提供可直接复用的[`.vscode/settings.json`](../../.vscode/settings.json)。例如VS Code配合YAML语言支持时，可将`geotask.document`返回的`schema_id`和`ide_file_patterns`转为：

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

该配置仅使用本地Schema文件，不依赖远程Schema服务。旧版`0.2/0.3`示例未统一套用v1 Schema，避免编辑器产生误报。

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

## 7. 学习GT01—GT20

建议按照四个阶段学习：

1. **GT01—GT03：空间关系**——距离、边界和多段路线；
2. **GT04—GT06：时空组合**——高度、时间和显式组合规则；
3. **GT07—GT09：不确定性与证据**——不知道、补证据和证据冲突；
4. **GT10—GT20：行动与可行性**——机器人协同、可达性、能源余量、车辆空间包络、应急救援调度、实时环境状态、多机时空冲突、城市事件去重、设备能力约束和高风险动作门控。

详见[GT01—GT20中文案例手册](../cookbook/gt01-gt20.zh-CN.md)。

## 8. 参与开发（源码安装）

仅在修改GeoTask源码、运行完整测试或提交贡献时使用可编辑安装：

```bash
git clone https://github.com/stpku/GeoTask.git
cd GeoTask
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
```

## 9. 运行测试

源码开发环境中可运行：

```bash
pytest
```

只运行文档和Schema测试：

```bash
pytest tests/test_documentation_system.py -q
```

## 10. 当前边界

公共Core不包含模型API、生产编排、行业Domain Pack、客户数据连接器和自动设备控制。案例中的`blocked`、`conflicted`、`resume_when`等主要是放在`extensions`中的工作流扩展语义，不应被误认为当前Core已经实现的全部基础状态。

下一步可阅读：

- [GeoTask白皮书](../whitepaper/GeoTask_White_Paper_v0.1.md)
- [当前实现语言与执行规范](../spec/geotask-language-spec-v1.0.md)
- [状态与可信等级](../reference/status-model.md)
- [证据、冲突、阻断与恢复](../reference/evidence-and-recovery.md)
