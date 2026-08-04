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
| 可信保证档案 | Assurance Profile | `geotask.assurance-profile` |
| 行业能力包 | Domain Pack | 行业扩展接口 |
| 语义指纹 | Semantic Fingerprint | `semantic_fingerprint` |
| 失败关闭 | Fail-closed | 安全处理原则 |
| 行动资格 | Action Eligibility | 控制评估结果 |
| 外部副作用 | External Side Effect | 外部读写或现实动作 |

## 推荐写法

- 推荐：“系统接收一条新的观测记录，并形成新的世界状态。”
- 不推荐：“系统接收一条新Observation，并形成新的World State。”
- 推荐：“验证提供方返回验证响应，但不能自行声明已经完成独立验证。”
- 不推荐：“Provider返回Response，并把Assurance升级为verified。”
- 推荐：“运行时负责连接外部系统，核心负责校验公共合同。”
- 不推荐：“Runtime连接外部系统，Core负责校验Artifact。”

## 版本与维护

术语表是公开文档体系和项目主页的语言基线。新增公共制品或架构概念时，应同时更新本中文术语规范和对应英文术语规范，并通过文档测试检查中文主页中是否出现未豁免的英文术语。
