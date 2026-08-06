# GeoTask中文术语规范

## 目标

GeoTask面向人的中文页面和中文文档应以中文为主，不在普通叙述中混用英文术语。机器协议、命令、文件名、类名、字段名和稳定制品标识继续使用英文，以保证兼容性和开发者工具一致性。

## 使用规则

1. 中文页面正文使用本规范中的中文术语。
2. 英文页面正文使用对应英文术语。
3. 首次解释协议时可以在术语表中建立中英文映射，但不在每个段落反复使用“中文（English）”形式。
4. 代码块、命令、JSON字段和制品标识保持原始英文，不做翻译。
5. 产品名称GeoTask、编程语言名、标准名和商标名可以保留原文。
6. 中文页面中的导航、按钮、图题、指标和说明不得使用仅用于装饰的英文标签。
7. 英文`contract`不得机械翻译为“合同”。软件组件之间可校验的输入、输出、责任和不变量使用“契约”；正式结构与行为定义使用“规范”；多方消息交换和协同顺序使用“协议”；只有法律、采购和商业责任场景使用“合同”。
8. 面向公众和行业用户时优先使用自然中文；开发者文档首次出现时可以建立中英文映射；机器标识、字段名和枚举值保持不变。

## 契约、规范、协议与合同

| 中文标准术语 | 使用范围 | 推荐示例 | 避免示例 |
|---|---|---|---|
| 契约 | 组件之间可校验的输入、输出、责任和不变量 | 算子契约、接口契约、输出契约 | 算子合同、公共合同 |
| 规范 | 对数据结构、字段、语义和行为的正式定义 | 世界状态规范、对象身份归并提案规范 | 世界状态合同 |
| 协议 | 多方交换消息、协同执行和恢复的顺序规则 | 可验证时空任务协议、运行时交互协议 | 把单个Schema称为协议 |
| 合同 | 法律、采购、商业服务和责任约定 | 商业服务合同、采购合同 | 用于描述Schema、API或算子 |

下列词组不应机械保留`contract`的字面形式：

- `space contract`根据上下文写成“空间参考与单位约束”或“空间执行约束”；
- `state contract`面向规范文档写成“状态规范”，强调组件责任时才写“状态契约”；
- `task contract`面向公众写成“结构化任务定义”，面向开发者可写“任务契约”；
- `provider contract`写成“验证提供方接口契约”或“验证提供方请求适配检查”。

## 核心术语映射

| 中文标准术语 | 英文标准术语 | 机器标识示例 |
|---|---|---|
| 观测记录 | Observation | `geotask.observation` |
| 世界状态 | World State | `geotask.world-state` |
| 状态转换 | State Transition | `geotask.state-transition` |
| 验证会话 | Verification Session | `geotask.verification-session` |
| 差异报告 | Discrepancy Report | `geotask.discrepancy-report` |
| 纠偏请求 | Correction Request | `geotask.correction-request` |
| 影响图 | Impact Graph | `geotask.impact-graph` |
| 观测合并结果 | Observation Merge Result | `geotask.observation-merge-result` |
| 重算推导结果 | Recompute Derivation Result | `geotask.recompute-derivation-result` |
| 世界状态物化结果 | World State Materialization Result | `geotask.world-state-materialization-result` |
| 增量复核结果 | Incremental Reevaluation Result | `geotask.incremental-reevaluation-result` |
| 执行结果 | Execution Result | `geotask.execution-result` |
| 控制评估 | Control Evaluation | `geotask.control-evaluation` |
| 制品 | Artifact | `artifact_id` |
| 核心 | Core | `geotask_core` |
| 运行时 | Runtime | `geotask.runtime-*` |
| 验证提供方 | Verification Provider | `geotask.verification-provider-*` |
| 验证提供方描述符 | Verification Provider Descriptor | `geotask.verification-provider-descriptor` |
| 验证请求 | Verification Request | `geotask.verification-request` |
| 验证响应 | Verification Response | `geotask.verification-response` |
| 可信保证策略 | Assurance Profile | `geotask.assurance-profile` |
| 领域扩展包 | Domain Pack | 领域扩展接口 |
| 语义指纹 | Semantic Fingerprint | `semantic_fingerprint` |
| 校验失败即阻断 | Fail-closed | 安全处理原则 |
| 行动准入状态 | Action Eligibility | 控制评估结果 |
| 外部副作用 | External Side Effect | 外部读写或现实动作 |
| 对象同一性候选 | Identity Candidate | `same_object_candidate` |
| 对象同一性审定 | Identity Adjudication | `geotask.trajectory-identity-adjudication` |
| 对象身份归并提案 | Identity Merge Proposal | `geotask.identity-merge-proposal` |
| 对象身份归并审批记录 | Identity Merge Approval Record | `geotask.identity-merge-approval-record` |
| 对象关系图变更请求 | Object Graph Change Request | `geotask.object-graph-change-request` |
| 对象关系图变更应用审批记录 | Object Graph Change Application Approval Record | `geotask.object-graph-change-application-approval-record` |
| 变更操作 | Change Operation | `change_operations` |
| 应用前置条件 | Application Precondition | `preconditions` |
| 验收条件 | Acceptance Criterion | `acceptance_criteria` |
| 应用审批完成 | Application Approval Complete | `application_approval_complete` |
| 变更应用具备条件 | Change Application Eligible | `change_application_eligible` |
| 应用授权 | Application Authorization | `application_authorized` |
| 回退方案 | Rollback Plan | `rollback_plan` |
| 提案审批完成 | Proposal Approval Complete | `proposal_approval_complete` |
| 变更请求具备条件 | Change Request Eligible | `change_request_eligible` |
| 主对象引用 | Canonical Subject Reference | `canonical_subject_ref` |
| 拟归并对象 | Merge Subject | `merge_subject_ref` |
| 保留别名 | Retained Alias | `retained_aliases` |
| 拟停用标识 | Proposed Retired Identifier | `proposed_retired_subject_refs` |
| 提案阻断条件 | Proposal Blocking Condition | `blocking_conditions` |
| 提案撤销条件 | Proposal Withdrawal Condition | `withdrawal_conditions` |
| 归并回退方案 | Merge Reversal Plan | `reversal_plan` |

## 推荐写法

- 推荐：“系统接收一条新的观测记录，并形成新的世界状态。”
- 不推荐：“系统接收一条新Observation，并形成新的World State。”
- 推荐：“验证提供方返回验证响应，但不能自行声明已经完成独立验证。”
- 不推荐：“Provider返回Response，并把Assurance升级为verified。”
- 推荐：“运行时负责连接外部系统，核心负责校验公共接口契约。”
- 不推荐：“Runtime连接外部系统，Core负责校验Artifact。”
- 推荐：“两个独立来源满足可信保证策略后，系统形成对象同一性审定结果，但只提出对象身份归并复核建议。”
- 不推荐：“两个Provider满足Assurance Profile后，Core直接完成身份裁决和自动合并。”
- 推荐：“GT39生成对象身份归并提案，声明主对象引用、保留别名、阻断条件和归并回退方案。”
- 不推荐：“GT39生成身份合并合同，并废弃旧身份。”
- 推荐：“GT40记录对象身份归并审批结果；提案审批完成只表示后续变更请求具备条件，不表示归并已经执行。”
- 不推荐：“GT40审批通过后，核心自动合并身份并更新世界状态。”
- 推荐：“GT41形成对象关系图变更请求，声明唯一变更操作、应用前置条件、验收条件和回退方案；请求仍需独立应用审批。”
- 不推荐：“GT41生成变更请求后，核心立即改写对象关系图。”
- 推荐：“GT42记录对象关系图变更应用审批结果；应用审批完成只表示后续受限应用制品具备条件，不表示核心已授权或变更已经应用。”
- 不推荐：“GT42审批通过后，核心自动改写主体引用并更新世界状态。”

## 版本与维护

术语表是公开文档体系和项目主页的语言基线。新增公共制品或架构概念时，应同时更新本中文术语规范和对应英文术语规范，并通过文档测试检查中文主页中是否出现未豁免的英文术语。历史发布说明可以保留发布时的原始措辞；当前README、白皮书、规范、案例页面和路线图应使用现行术语。
