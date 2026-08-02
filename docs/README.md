# GeoTask文档导航

**简体中文** | [English](README.en.md)

GeoTask文档按照“理解世界模型定位、开始使用、查阅规范、扩展状态演化”四类组织。第一次接触GeoTask，建议先阅读白皮书理解“显式、可验证时空世界模型”的本体定位，再通过中文快速入门和GT01—GT20案例掌握当前公共Core已经实现的世界模型基础与能力边界。

## 从这里开始

- [GeoTask白皮书v0.1](whitepaper/GeoTask_White_Paper_v0.1.md)：为什么智能体需要显式、可验证的时空世界模型，GeoTask与隐式神经世界模型有何区别，以及当前实现和目标状态演化能力的边界。
- [白皮书英文摘要](whitepaper/GeoTask_White_Paper_v0.1.md#english-abstract)：在同一份非规范性白皮书中提供结构一致的英文摘要与核心术语映射。
- [白皮书构建说明](whitepaper/README.md)：从Markdown生成HTML、DOCX和可选PDF。
- [中文快速入门](tutorials/quickstart.zh-CN.md)：安装、验证、执行和检查第一个任务。
- [GT01—GT20中文案例手册](cookbook/gt01-gt20.zh-CN.md)：从距离计算逐步进入证据治理、对象相关可行性、应急调度、设备能力约束和高风险动作门控。
- [当前实现语言与执行规范v1.0](spec/geotask-language-spec-v1.0.md)：当前公共Core真正实现的规范性文本。
- [标准执行结果v1.0](spec/geotask-result-v1.0.md)：定义`GeotaskResult.to_dict()`、结果JSON Schema和`geotask result validate`命令。
- [Observation v0.1](spec/geotask-observation-v0.1.md)：用于表达带来源、时间、生产者和不确定性的世界命题，但不宣称命题真实，也不自动更新World State。
- [World State v0.1](spec/geotask-world-state-v0.1.md)：用于表达某一时刻版本化的世界对象、属性、关系、有效时间、不确定性及Observation/Evidence引用闭包，但不自动合并Observation或物化后续状态。
- [State Transition v0.1](spec/geotask-state-transition-v0.1.md)：以前后World State语义指纹绑定快照，记录Observation支持的逐路径、关系和行动资格变化，但不自动计算差异、应用补丁或授权行动。
- [Verification Session v0.1](spec/geotask-verification-session-v0.1.md)：将一个World State与任务、结果、控制、State Transition、行动资格和复核触发条件固化为可审计快照，并支持状态指纹与引用文件SHA-256绑定校验。
- [Discrepancy Report v0.1](spec/geotask-discrepancy-report-v0.1.md)：绑定World State与精确来源制品，记录差异类型、期望/观测值、影响范围及可变/不可变修订路径，但不自动比较、传播或纠正。
- [Correction Request v0.1](spec/geotask-correction-request-v0.1.md)：绑定不可变基准World State与Discrepancy Report，限定后继状态的允许变更、验收标准、不可变路径保护及输出/行动门禁，但不应用修订或物化状态。
- [Impact Graph v0.1](spec/geotask-impact-graph-v0.1.md)：将差异、修订、状态路径、断言、输出、动作与复核目标组织为来源绑定的有向无环图，但不自动发现或执行影响传播。
- [World State Materialization Result v0.1](spec/geotask-world-state-materialization-result-v0.1.md)：由不可变基准World State、已绑定Correction Request和显式重算值确定性生成后继快照，记录精确字节与逐项变更，同时保留输出/动作门禁。
- [Incremental Reevaluation Result v0.1](spec/geotask-incremental-reevaluation-result-v0.1.md)：绑定基准/后继World State、Impact Graph与精确来源文件，记录节点、目标、验收条件、差异消解及输出/动作门禁结果，但不执行复核或授权动作。
- [制品注册表v1.0](spec/geotask-artifact-registry-v1.0.md)：通过`geotask inspect schemas`统一发现21类公共Artifact的Schema、版本及操作命令。
- [统一制品校验v1.0](spec/geotask-artifact-validation-v1.0.md)：通过`geotask artifact validate`按稳定Artifact ID校验21类公共制品，包括Observation、World State、State Transition、Verification Session、Discrepancy Report、Correction Request、Impact Graph、World State Materialization Result、Incremental Reevaluation Result、Agent报告、Runtime消息、Core基准报告与验证报告自身，并输出统一文本/JSON报告。
- [版本化载荷校验v1.0](spec/geotask-versioned-payload-validation-v1.0.md)：统一执行结果与控制结果的严格加载、Schema元数据、诊断和文本/JSON报告。
- [控制扩展Profile v1.0](spec/geotask-control-extension-profile-v1.0.md)：对证据请求、证据冲突、决策规则和任务门控进行版本化校验。
- [控制表达式语言v1.0](spec/geotask-control-expression-language-v1.0.md)：定义安全有限语法、三值逻辑、比较语义和公共解析求值API。
- [控制评估结果v1.0](spec/geotask-control-evaluation-v1.0.md)：将断言结果和显式领域状态绑定为只读上下文，输出门控状态、未知变量和仍被阻断的输出。
- [Agent集成Profile v0.1](spec/geotask-agent-integration-profile-v0.1.md)：定义Agent调用四类公共工具、机械修复生成草稿、执行修订差异门禁、验证四类Agent报告Artifact、处理unknown/blocked状态以及补证据后重新执行的边界。
- [Runtime接口Profile v0.1](spec/geotask-runtime-interface-profile-v0.1.md)：定义Core与外部Runtime之间的Descriptor、Request、Response、授权、幂等、审计及副作用边界，并提供公共安全的HTTP Adapter、回环Endpoint、Provider-neutral模型Adapter以及首个OpenAI Responses Provider包。
- [GeoTask Core Agent Skill](../skills/geotask-core/SKILL.md)：可直接注入Agent的模型无关操作指令与安全约束。
- [VS Code Schema配置示例](../.vscode/settings.json)：将本地任务文件关联到仓库内JSON Schema。
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
