# GeoTask文档导航

**简体中文** | [English](README.en.md)

GeoTask文档按照“理解定位、开始使用、查阅规范、构建端到端闭环、扩展状态演化”组织。当前公共事实是：GeoTask是面向AI智能体的可验证时空任务协议与确定性Core；“可信世界状态运行时”是近期产品目标，而不是把尚未完成的生产能力当成现状。42个公开参考例用于证明Capability Track，其中GT38—GT42共同构成五阶段无人机身份治理复合案例；产品成熟度另按P0—P5 Track管理。

## 从这里开始

- [架构宣言 v1](architecture_manifesto_v1.md)：冻结“当前事实—近期产品目标—长期愿景”三层定位，以及Context、Tool Result、World State、Unknown、Impact和Action Boundary等核心架构原则。
- [Reference Agent v0.1规格](reference/reference-agent-v0.1.md)：定义首个端到端公共参考Agent——虚构低空设施评估更新闭环及五类正负场景。
- [GeoTask ↔ Lowa-GT Integration Contract v0.1](reference/lowa-gt-integration-contract-v0.1.md)：定义Lowa-GT作为低空业务System of Record、GeoTask作为Trust Control Plane的只读优先协同边界；S1只读exporter与S2精确传输合同已经对齐。
- [Cross-Line Promotion Gate v0.1](reference/cross-line-promotion-gate-v0.1.md)：冻结GeoTask Core、Lowa Product、Lowa-GT Integration三线独立原则；Integration负责验证候选能力，Core负责通用抽象，Lowa负责业务事实，任何能力所有权跨线迁移都必须有显式Promotion决定。
- [Core Distribution Boundary v0.1](reference/core-distribution-boundary-v0.1.md)：进一步把三线独立落实到发行物；同仓库不等于同产品线，Core公共导出保留治理契约和Reference Agent，但不携带Lowa-GT Integration验证实现、研究协议或Integration测试。
- [产品架构 v0.2](product_architecture_v0_2.md)、[Open Core边界 v0.2](open_core_boundary_v0_2.md)与[产品化路线图 v0.2](productization_roadmap_v0_2.md)：以GT42真实能力基线重建P0—P5 Product Track，并暂停为编号而新增GT。
- [GeoTask白皮书v0.1](whitepaper/GeoTask_White_Paper_v0.1.md)：为什么智能体需要显式、可验证的时空世界模型，GeoTask与隐式神经世界模型有何区别，以及当前实现和目标状态演化能力的边界。
- [白皮书英文摘要](whitepaper/GeoTask_White_Paper_v0.1.md#english-abstract)：在同一份非规范性白皮书中提供结构一致的英文摘要与核心术语映射。
- [白皮书构建说明](whitepaper/README.md)：从Markdown生成HTML、DOCX和可选PDF。
- [中文快速入门](tutorials/quickstart.zh-CN.md)：安装、验证、执行和检查第一个任务。
- [Reference Agent从零教程](tutorials/reference-agent.zh-CN.md)：不阅读GT01—GT42也可以从新证据开始，完整运行rev1→rev2→Discrepancy/Correction/Impact→rev3→Control，并修改一个自定义场景输入。
- [P1陌生开发者激活协议](reference/developer-activation-protocol-v0.1.md)：用标准化30分钟任务记录首次运行、自定义输入、三版本状态理解和`eligible != executed`理解情况；外部结果尚未产生前不得宣称P1采用验证完成。
- [Verification Quality Benchmark v0.1](reference/verification-quality-benchmark-v0.1.md)：以五个固定虚构Reference Agent场景测量验错、漏检、误阻断、有限纠偏、影响范围和副作用边界；100%固定基准结果不得外推为真实低空安全或跨域准确率。
- [0.4.0发布范围命名冻结](reference/p2-release-contract-freeze-v0.4.md)：用机器快照锁定当前包名、CLI、14个算子、32类Artifact与33份Schema；该文件不代表0.4.0已发布。
- [0.4.0安装与迁移矩阵](reference/install-migration-matrix-v0.4.md)：分开记录Python声明支持、CI配置覆盖和本轮真实clean-room验证，并列出0.3.x→0.4.0发布前迁移门槛。
- [Core 0.4.0 RC Readiness Gate v0.1](reference/core-0.4-rc-readiness-v0.1.md)：把版本元数据、最终wheel/sdist、33-Schema Bundle、Python 3.10—3.13真实CI证据、公共导出与Reference Agent重放升级为机器可审计Gate；当前0.3.0状态应明确返回`pending`而非伪装成0.4.0已就绪。
- [GT01—GT20中文案例手册](cookbook/gt01-gt20.zh-CN.md)：从距离计算逐步进入证据治理、对象相关可行性、应急调度、设备能力约束和高风险动作门控。
- [GT21—GT28世界状态循环案例手册](cookbook/gt21-gt28.zh-CN.md)：从同目标Observation冲突开始，逐步进入快照、变化、影响、纠偏、增量复核和行动资格。
- [GT38—GT42无人机身份治理复合案例](cookbook/gt38-gt42-uav-identity-governance.zh-CN.md)：用UAV-017短暂失联后被重新编号的连续场景解释对象同一性审定、归并提案、审批、变更请求和应用审批。
- [当前实现语言与执行规范v1.0](spec/geotask-language-spec-v1.0.md)：当前公共Core真正实现的规范性文本。
- [标准执行结果v1.0](spec/geotask-result-v1.0.md)：定义`GeotaskResult.to_dict()`、结果JSON Schema和`geotask result validate`命令。
- [Observation v0.1](spec/geotask-observation-v0.1.md)：用于表达带来源、时间、生产者和不确定性的世界命题，但不宣称命题真实，也不自动更新World State。
- [World State v0.1](spec/geotask-world-state-v0.1.md)：用于表达某一时刻版本化的世界对象、属性、关系、有效时间、不确定性及Observation/Evidence引用闭包，但不自动合并Observation或物化后续状态。
- [Observation Merge Result v0.1](spec/geotask-observation-merge-result-v0.1.md)：将精确Observation字节按完整显式映射写入既有属性或关系；同一目标出现多条命题时，仅按调用方声明的语义相等合并或完整显式优先级生成规范化后继版本，不推断身份、不发明优先级、不解决未声明策略的歧义冲突，也不计算State Transition。
- [State Transition v0.1](spec/geotask-state-transition-v0.1.md)：以前后World State语义指纹绑定快照，记录Observation支持的逐路径、关系和行动资格变化，但不自动计算差异、应用补丁或授权行动。
- [Verification Session v0.1](spec/geotask-verification-session-v0.1.md)：将一个World State与任务、结果、控制、State Transition、行动资格和复核触发条件固化为可审计快照，并支持状态指纹与引用文件SHA-256绑定校验。
- [Discrepancy Report v0.1](spec/geotask-discrepancy-report-v0.1.md)：绑定World State与精确来源制品，记录差异类型、期望/观测值、影响范围及可变/不可变修订路径，但不自动比较、传播或纠正。
- [Correction Request v0.1](spec/geotask-correction-request-v0.1.md)：绑定不可变基准World State与Discrepancy Report，限定后继状态的允许变更、验收标准、不可变路径保护及输出/行动门禁，但不应用修订或物化状态。
- [Impact Graph v0.1](spec/geotask-impact-graph-v0.1.md)：将差异、修订、状态路径、断言、输出、动作与复核目标组织为来源绑定的有向无环图，但不自动发现或执行影响传播。
- [Recompute Derivation Result v0.1](spec/geotask-recompute-derivation-result-v0.1.md)：将Correction Request中的每个`recompute`变更绑定到精确Observation/任务文档路径，通过受限确定性方法生成完整重算值映射，不执行任意表达式、模型调用或状态物化。
- [World State Materialization Result v0.1](spec/geotask-world-state-materialization-result-v0.1.md)：由不可变基准World State、已绑定Correction Request和显式重算值确定性生成后继快照，记录精确字节与逐项变更，同时保留输出/动作门禁。
- [Incremental Reevaluation Result v0.1](spec/geotask-incremental-reevaluation-result-v0.1.md)：绑定基准/后继World State、Impact Graph与精确来源文件，记录节点、目标、验收条件、差异消解及输出/动作门禁结果，但不执行复核或授权动作。
- [制品注册表v1.0](spec/geotask-artifact-registry-v1.0.md)：通过`geotask inspect schemas`统一发现32类公共制品、33份结构规范、版本及操作命令。
- [验证提供方接口规范v0.1](spec/geotask-verification-provider-profile-v0.1.zh-CN.md)：定义验证提供方描述符、验证请求、验证响应、可信保证策略及只读命令行接口。
- [轨迹与移动对象Profile v0.1](spec/geotask-trajectory-profile-v0.1.zh-CN.md)：定义身份与位置观测分离、严格递增带时区样本、相邻分段指标、调用方显式分类、对象同一性候选与审定、身份归并提案、审批记录、对象关系图变更请求和应用审批记录，以及GT33—GT42非预测/非执行边界。
- [Trajectory Identity Adjudication v0.1](spec/geotask-trajectory-identity-adjudication-v0.1.md)：原始字节级绑定GT37候选、验证请求、可信保证策略、验证提供方描述符与响应，形成对象同一性审定与归并复核建议，但不修改对象关系图。
- [Identity Merge Proposal v0.1](spec/geotask-identity-merge-proposal-v0.1.md)：从GT38审定结果生成受限对象身份归并提案，声明主对象引用、保留别名、审批要求和归并回退方案，但不审批或执行归并。
- [Identity Merge Approval Record v0.1](spec/geotask-identity-merge-approval-record-v0.1.md)：原始字节级绑定GT39提案，为每个必需角色记录批准、拒绝或补证据决定，但不执行归并或修改对象关系图。
- [Object Graph Change Request v0.1](spec/geotask-object-graph-change-request-v0.1.md)：原始字节级绑定GT39提案与GT40审批记录，派生唯一的轨迹引用改写、保留别名、应用前置条件、验收条件和回退要求，但不授权或应用变更。
- [Object Graph Change Application Approval Record v0.1](spec/geotask-object-graph-change-application-approval-record-v0.1.md)：原始字节级绑定GT41变更请求，为每个调用方声明的应用审批角色记录批准、拒绝或补证据决定；全部批准只使后续受限应用制品具备条件，不授权或应用变更。
- [中文术语规范](terminology.zh-CN.md)：建立中英文术语映射，并约束中文页面和中文文档避免不必要的中英文混编。
- [统一制品校验v1.0](spec/geotask-artifact-validation-v1.0.md)：通过`geotask artifact validate`按稳定制品标识校验32类公共制品，包括对象同一性审定、对象身份归并提案、归并审批记录、对象关系图变更请求、变更应用审批记录、观测记录、世界状态、观测合并结果、状态转换、验证会话、差异报告、纠偏请求、影响图、重算推导结果、世界状态物化结果、增量复核结果、智能体报告、运行时消息、验证提供方制品、核心基准报告与验证报告自身，并输出统一文本或JSON报告。
- [版本化载荷校验v1.0](spec/geotask-versioned-payload-validation-v1.0.md)：统一执行结果与控制结果的严格加载、Schema元数据、诊断和文本/JSON报告。
- [控制扩展Profile v1.0](spec/geotask-control-extension-profile-v1.0.md)：对证据请求、证据冲突、决策规则和任务门控进行版本化校验。
- [控制表达式语言v1.0](spec/geotask-control-expression-language-v1.0.md)：定义安全有限语法、三值逻辑、比较语义和公共解析求值API。
- [控制评估结果v1.0](spec/geotask-control-evaluation-v1.0.md)：将断言结果和显式领域状态绑定为只读上下文，输出门控状态、未知变量和仍被阻断的输出。
- [Agent集成Profile v0.1](spec/geotask-agent-integration-profile-v0.1.md)：定义Agent调用四类公共工具、机械修复生成草稿、执行修订差异门禁、验证四类Agent报告Artifact、处理unknown/blocked状态以及补证据后重新执行的边界。
- [Runtime接口Profile v0.1](spec/geotask-runtime-interface-profile-v0.1.md)：定义Core与外部Runtime之间的Descriptor、Request、Response、授权、幂等、审计及副作用边界，并提供公共安全的HTTP Adapter、回环Endpoint、Provider-neutral模型Adapter以及首个OpenAI Responses Provider包。
- [GeoTask Core Agent Skill](../skills/geotask-core/SKILL.md)：可直接注入Agent的模型无关操作指令与安全约束。
- [VS Code Schema配置示例](../.vscode/settings.json)：将本地任务文件关联到仓库内JSON Schema。
- [v0.4.0 Core产品化与Reference Agent发布说明](release_v0_4_0.md)
- [v0.3.0 Agent集成版发布说明](release_v0_3_0.md)：新增Agent生成任务准备、受约束修订、补证据恢复、四类Agent报告Artifact及8类Artifact/9份Schema统一验证。
- [v0.2.0制品契约版发布说明](release_v0_2_0.md)：新增Artifact Registry、离线Schema Bundle、统一制品校验和验证报告自验证。
- [v0.1.1 PyPI修正版发布说明](release_v0_1_1.md)：修正发行元数据与模块版本不一致，并完成PyPI安装验证。
- [v0.1.0 Public Preview发布说明](release_v0_1_0.md)：首个固定版本的能力、资产和验证状态。
- [公共路线图](../ROADMAP.md)：面向协议、Core、工具和生态的后续方向。
- [英文Quickstart](tutorials/quickstart.md)、[GT01—GT20英文Cookbook](cookbook/gt01-gt20.md)与[GT21—GT28英文世界状态Cookbook](cookbook/gt21-gt28.md)。

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

- [架构说明](architecture.md)
- [设计原则](design_principles.md)
- [评估规范](eval_spec.md)
- [Normalizer v0.2设计](normalizer_v0_2_design.md)
- [算子注册表](operator_registry.md)
- [中文术语规范](terminology.zh-CN.md)
- [安全说明](../SECURITY.md)

## 公共和私有边界

公共仓库提供通用任务表示、确定性算子、结构验证、结果可信等级、示例和一致性测试。行业规则、客户数据、审批阈值、模型凭据、商业路由和专利敏感优化不属于公共Core。

项目不会通过白皮书和规范公开客户规则、私有运行时实现或尚未披露的专利敏感细节。公共文档只描述开放协议、开发者接口和安全边界。
