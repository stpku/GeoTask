# 参与GeoTask Core

[English](CONTRIBUTING.md) | **简体中文**

感谢你关注GeoTask。公共Core保持轻量、确定和可复现，主要包括任务格式、Canonical IR、结构验证、确定性算子、结果可信等级、CLI和公开案例。

## 开发环境

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

安装开发依赖：

```bash
pip install -e ".[dev]"
```

开发依赖包括`pytest`、`jsonschema`和`matplotlib`。Core运行时只依赖PyYAML。

## 运行测试

```bash
pytest
pytest tests/ -v
pytest tests/ -x
pytest tests/test_documentation_system.py -q
```

新增能力必须同时增加相应测试。新算子至少应覆盖正常情况、边界情况、错误输入和对象类型不匹配。

## 欢迎哪些贡献

- 修复解析、验证、执行和结果组装问题；
- 改进结构化诊断和错误信息；
- 提出具有通用稳定语义的确定性算子；
- 改进中英文文档、教程和示例；
- 提交新的机器人、无人机、自动驾驶、GIS或城市治理案例；
- 改进JSON Schema和规范一致性测试；
- 修复移动端体验页和无障碍问题。

## Core范围

属于Core的内容：

- YAML/JSON任务格式；
- Canonical IR；
- 结构和引用验证；
- 无网络、无随机性的确定性算子；
- 结果、状态和Assurance元数据；
- CLI和公共一致性测试。

不属于公共Core的内容：

- 大模型API调用和密钥；
- 生产任务编排、模型路由和成本治理；
- 行业规则、客户阈值和私有Domain Pack；
- 客户数据、真实连接器和审批工作流；
- 未公开的专利敏感实现；
- 自动控制真实设备的代码。

不确定时，请先提交Issue说明问题、通用价值和建议边界。

## 代码约束

1. `ir.py`和`enums.py`保持纯叶子模块；
2. `ops.py`保持纯数学模块，不进行I/O；
3. `geotask_core`不能依赖私有Runtime和Domain Pack；
4. 验证和算子必须对相同输入产生相同结果；
5. 公共函数使用类型标注；
6. 数据容器优先使用dataclass；
7. 不在Core中引入重量级GIS依赖；
8. 不提交客户数据、密钥、真实凭据或专利材料。

## Pull Request流程

1. 对较大功能先提交Issue；
2. Fork仓库并创建聚焦分支；
3. 修改代码、文档和测试；
4. 在本地运行`pytest`；
5. 提交PR到`main`；
6. 在PR中说明问题、方案、测试结果和边界影响。

跨多个文件并不自动意味着PR过大。文档双语化、Schema更新和完整案例通常需要同时修改若干文件；关键是主题单一、差异清楚、测试完整。

## 新算子建议

一个适合进入Core的新算子应当：

- 具有跨行业通用意义；
- 输入和输出类型明确；
- 单位和边界语义明确；
- 不依赖外部网络和私有数据；
- 对相同输入具有确定结果；
- 能够给出正常、边界和错误测试；
- 不只是为了某一个演示页面方便。

## 新GT案例建议

案例应包含一个具体应用问题、显式对象和约束、可复用Core断言、多个候选动作、本地验证路径、安全阻断或恢复条件，以及真实应用边界说明。

可参考[GT01—GT20中文案例手册](docs/cookbook/gt01-gt20.zh-CN.md)。

## 行为规范与安全问题

参与项目即表示同意遵守[社区行为准则](CODE_OF_CONDUCT.md)。安全漏洞不要公开提交普通Issue，请按照[SECURITY.md](SECURITY.md)中的方式处理。
