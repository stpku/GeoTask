# GeoTask文档导航

**简体中文** | [English](README.en.md)

GeoTask文档按照“理解项目、开始使用、查阅规范、扩展开发”四类组织。第一次接触GeoTask，建议先阅读白皮书和中文快速入门，再结合GT01—GT13案例理解完整工作方式。

## 从这里开始

- [GeoTask白皮书v0.1](whitepaper/GeoTask_White_Paper_v0.1.md)：项目为什么存在、核心架构、可信执行、应用模式和公开边界。
- [白皮书构建说明](whitepaper/README.md)：从Markdown生成HTML、DOCX和可选PDF。
- [中文快速入门](tutorials/quickstart.zh-CN.md)：安装、验证、执行和检查第一个任务。
- [GT01—GT13中文案例手册](cookbook/gt01-gt13.zh-CN.md)：从距离计算逐步进入证据治理、机器人协同和对象相关可行性。
- [当前实现语言与执行规范v1.0](spec/geotask-language-spec-v1.0.md)：当前公共Core真正实现的规范性文本。
- [英文Quickstart](tutorials/quickstart.md)与[英文Cookbook](cookbook/gt01-gt13.md)。

## 工程参考

- [算子注册表](operator_registry.md)
- [状态与可信等级](reference/status-model.md)
- [证据、冲突、阻断与恢复](reference/evidence-and-recovery.md)
- [CLI使用说明](cli_usage.md)
- [架构说明](architecture.md)
- [算子扩展指南](operator-guide.md)
- [机器可读JSON Schema](../schemas/geotask-v1.0.schema.json)

## 三层规范关系

GeoTask明确区分三层文档：

1. **当前公共实现规范。**`spec/geotask-language-spec-v1.0.md`描述当前公共Core能够解析、验证、规范化和执行的字段与语义。
2. **体系级目标方向。**[目标规范状态](spec/target-specification-status.md)说明未来Runtime、Domain Pack、治理能力和协议扩展与当前实现的关系，不代表规划能力已经全部完成。
3. **历史兼容格式。**[早期格式说明](format_spec.md)和[旧版YAML Schema说明](geotask_yaml_schema.md)用于`0.x`和`v0.1-lite`迁移兼容。

当文档之间出现差异时，以当前源码、测试、v1.0实现规范和机器可读Schema为公共Core的权威依据。

## 设计与边界

- [设计原则](design_principles.md)
- [评估规范](eval_spec.md)
- [Normalizer v0.2设计](normalizer_v0_2_design.md)
- [开源边界](open_source_boundary.md)
- [开源Core与商业Runtime边界](open_core_commercial_runtime_boundary.md)
- [产品架构v0.1](product_architecture_v0_1.md)
- [ADR-001：Core、Runtime与Domain Pack分层](architecture_decisions/ADR-001-core-runtime-domain-pack.md)
- [ADR-002：私有Runtime边界](architecture_decisions/ADR-002-private-runtime-boundary.md)
- [ADR-003：Domain Pack契约](architecture_decisions/ADR-003-domain-pack-plugin-contract.md)
- [ADR-004：专利与开源边界](architecture_decisions/ADR-004-patent-and-open-source-boundary.md)

## 公共和私有边界

公共仓库提供通用任务表示、确定性算子、结构验证、结果可信等级、示例和一致性测试。行业规则、客户数据、审批阈值、模型凭据、商业路由和专利敏感优化不属于公共Core。

项目不会通过白皮书和规范公开客户规则、私有Runtime实现或尚未披露的专利敏感细节。更多说明见[ADR-004](architecture_decisions/ADR-004-patent-and-open-source-boundary.md)和[开源Core边界](open_core_commercial_runtime_boundary.md)。
