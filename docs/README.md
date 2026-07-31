# GeoTask文档导航

**简体中文** | [English](README.en.md)

GeoTask文档按照“理解项目、开始使用、查阅规范、扩展开发”四类组织。第一次接触GeoTask，建议先阅读白皮书和中文快速入门，再结合GT01—GT20案例理解完整工作方式。

## 从这里开始

- [GeoTask白皮书v0.1](whitepaper/GeoTask_White_Paper_v0.1.md)：项目为什么存在、核心架构、可信执行、应用模式和公开边界。
- [白皮书构建说明](whitepaper/README.md)：从Markdown生成HTML、DOCX和可选PDF。
- [中文快速入门](tutorials/quickstart.zh-CN.md)：安装、验证、执行和检查第一个任务。
- [GT01—GT20中文案例手册](cookbook/gt01-gt20.zh-CN.md)：从距离计算逐步进入证据治理、对象相关可行性、应急调度、设备能力约束和高风险动作门控。
- [当前实现语言与执行规范v1.0](spec/geotask-language-spec-v1.0.md)：当前公共Core真正实现的规范性文本。
- [标准执行结果v1.0](spec/geotask-result-v1.0.md)：定义`GeotaskResult.to_dict()`、结果JSON Schema和`geotask result validate`命令。
- [制品注册表v1.0](spec/geotask-artifact-registry-v1.0.md)：通过`geotask inspect schemas`统一发现11类公共Artifact的Schema、版本及操作命令。
- [统一制品校验v1.0](spec/geotask-artifact-validation-v1.0.md)：通过`geotask artifact validate`按稳定Artifact ID校验11类公共制品，包括Agent报告、Runtime消息与验证报告自身，并输出统一文本/JSON报告。
- [版本化载荷校验v1.0](spec/geotask-versioned-payload-validation-v1.0.md)：统一执行结果与控制结果的严格加载、Schema元数据、诊断和文本/JSON报告。
- [控制扩展Profile v1.0](spec/geotask-control-extension-profile-v1.0.md)：对证据请求、证据冲突、决策规则和任务门控进行版本化校验。
- [控制表达式语言v1.0](spec/geotask-control-expression-language-v1.0.md)：定义安全有限语法、三值逻辑、比较语义和公共解析求值API。
- [控制评估结果v1.0](spec/geotask-control-evaluation-v1.0.md)：将断言结果和显式领域状态绑定为只读上下文，输出门控状态、未知变量和仍被阻断的输出。
- [Agent集成Profile v0.1](spec/geotask-agent-integration-profile-v0.1.md)：定义Agent调用四类公共工具、机械修复生成草稿、执行修订差异门禁、验证四类Agent报告Artifact、处理unknown/blocked状态以及补证据后重新执行的边界。
- [Runtime接口Profile v0.1](spec/geotask-runtime-interface-profile-v0.1.md)：定义Core与外部Runtime之间的Descriptor、Request、Response、授权、幂等、审计及副作用边界，并提供公共安全的外部HTTP JSON Adapter示例。
- [GeoTask Core Agent Skill](../skills/geotask-core/SKILL.md)：可直接注入Agent的模型无关操作指令与安全约束。
- [v0.3.0 Agent集成版发布说明](release_v0_3_0.md)：新增Agent生成任务准备、受约束修订、补证据恢复、四类Agent报告Artifact及8类Artifact/9份Schema统一验证。
- [v0.2.0制品契约版发布说明](release_v0_2_0.md)：新增Artifact Registry、离线Schema Bundle、统一制品校验和验证报告自验证。
- [v0.1.1 PyPI修正版发布说明](release_v0_1_1.md)：修正发行元数据与模块版本不一致，并完成PyPI安装验证。
- [v0.1.0 Public Preview发布说明](release_v0_1_0.md)：首个固定版本的能力、资产和验证状态。
- [公共路线图](../ROADMAP.md)：面向协议、Core、工具和生态的后续方向。
- [英文Quickstart](tutorials/quickstart.md)与[英文Cookbook](cookbook/gt01-gt20.md)。

## 工程参考

- [算子注册表](operator_registry.md)
- [状态与可信等级](reference/status-model.md)
- [证据、冲突、阻断与恢复](reference/evidence-and-recovery.md)
- [CLI使用说明](cli_usage.md)
- [架构说明](architecture.md)
- [算子扩展指南](operator-guide.md)
- 机器可读Schema：[制品注册表](../schemas/geotask-artifact-registry-v1.0.schema.json)、[制品验证报告](../schemas/geotask-artifact-validation-v1.0.schema.json)、[Agent补证据恢复报告](../schemas/geotask-agent-integration-v0.1.schema.json)、[任务文档](../schemas/geotask-v1.0.schema.json)、[标准执行结果](../schemas/geotask-result-v1.0.schema.json)、[控制评估结果](../schemas/geotask-control-evaluation-v1.0.schema.json)

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
