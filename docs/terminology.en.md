# GeoTask English Terminology Guide

## Purpose

English-facing GeoTask pages and documents should use consistent English terminology. Chinese-facing pages and documents should use the mapped Chinese terms instead of mixing English concepts into ordinary Chinese prose. Machine identifiers, commands, filenames, class names, and field names remain stable English contracts in both languages.

## Usage rules

1. English pages use the English terms in this guide.
2. Chinese pages use the mapped Chinese terms in the Chinese terminology guide.
3. Use bilingual mappings in terminology tables, not repeatedly inside normal prose.
4. Keep code blocks, commands, JSON fields, Artifact IDs, and schema IDs unchanged.
5. Product names, programming-language names, standards, and trademarks may remain in their original form.
6. Do not use untranslated Chinese labels in English navigation, buttons, diagrams, metrics, or explanatory prose.
7. In Chinese materials, translate software `contract` according to function: 契约 for component obligations and invariants, 规范 for formal structural or behavioral definitions, 协议 for multi-party exchanges, and 合同 only for legal or commercial agreements.

## Core terminology map

| English standard term | Chinese standard term | Machine identifier example |
|---|---|---|
| Observation | 观测记录 | `geotask.observation` |
| World State | 世界状态 | `geotask.world-state` |
| State Transition | 状态转换 | `geotask.state-transition` |
| Verification Session | 验证会话 | `geotask.verification-session` |
| Discrepancy Report | 差异报告 | `geotask.discrepancy-report` |
| Correction Request | 纠偏请求 | `geotask.correction-request` |
| Impact Graph | 影响图 | `geotask.impact-graph` |
| Observation Merge Result | 观测合并结果 | `geotask.observation-merge-result` |
| Recompute Derivation Result | 重算推导结果 | `geotask.recompute-derivation-result` |
| World State Materialization Result | 世界状态物化结果 | `geotask.world-state-materialization-result` |
| Incremental Reevaluation Result | 增量复核结果 | `geotask.incremental-reevaluation-result` |
| Execution Result | 执行结果 | `geotask.execution-result` |
| Control Evaluation | 控制评估 | `geotask.control-evaluation` |
| Artifact | 制品 | `artifact_id` |
| Core | 核心 | `geotask_core` |
| Runtime | 运行时 | `geotask.runtime-*` |
| Verification Provider | 验证提供方 | `geotask.verification-provider-*` |
| Verification Provider Descriptor | 验证提供方描述符 | `geotask.verification-provider-descriptor` |
| Verification Request | 验证请求 | `geotask.verification-request` |
| Verification Response | 验证响应 | `geotask.verification-response` |
| Assurance Profile | 可信保证策略 | `geotask.assurance-profile` |
| Domain Pack | 领域扩展包 | domain extension interface |
| Semantic Fingerprint | 语义指纹 | `semantic_fingerprint` |
| Fail-closed | 校验失败即阻断 | safety handling principle |
| Action Eligibility | 行动准入状态 | control outcome |
| External Side Effect | 外部副作用 | external read, write, or real-world action |
| Identity Candidate | 对象同一性候选 | `same_object_candidate` |
| Identity Adjudication | 对象同一性审定 | `geotask.trajectory-identity-adjudication` |
| Identity Merge Proposal | 对象身份归并提案 | `geotask.identity-merge-proposal` |
| Identity Merge Approval Record | 对象身份归并审批记录 | `geotask.identity-merge-approval-record` |
| Object Graph Change Request | 对象关系图变更请求 | `geotask.object-graph-change-request` |
| Change Operation | 变更操作 | `change_operations` |
| Application Precondition | 应用前置条件 | `preconditions` |
| Acceptance Criterion | 验收条件 | `acceptance_criteria` |
| Application Approval | 应用审批 | `application_authorized` |
| Rollback Plan | 回退方案 | `rollback_plan` |
| Proposal Approval Complete | 提案审批完成 | `proposal_approval_complete` |
| Change Request Eligible | 变更请求具备条件 | `change_request_eligible` |
| Canonical Subject Reference | 主对象引用 | `canonical_subject_ref` |
| Merge Subject | 拟归并对象 | `merge_subject_ref` |
| Retained Alias | 保留别名 | `retained_aliases` |
| Proposed Retired Identifier | 拟停用标识 | `proposed_retired_subject_refs` |
| Proposal Blocking Condition | 提案阻断条件 | `blocking_conditions` |
| Proposal Withdrawal Condition | 提案撤销条件 | `withdrawal_conditions` |
| Merge Reversal Plan | 归并回退方案 | `reversal_plan` |

## Recommended style

- Recommended: “The system receives a new Observation and forms a new World State.”
- Avoid: “The system receives a new 观测记录 and forms a new 世界状态.”
- Recommended: “A Verification Provider returns a Verification Response but cannot declare that independent verification is complete.”
- Avoid: “The 验证提供方 returns a Response and upgrades the 可信保证等级.”
- Recommended Chinese equivalent: “GT39生成对象身份归并提案，声明主对象引用、保留别名、阻断条件和归并回退方案。”

## Maintenance

This guide is the language baseline for the English documentation system and English project homepage. Every new public Artifact or architecture concept should update both terminology guides, and documentation tests should check that the English entry points do not contain untranslated Chinese prose. Historical release notes may preserve the terminology used at release time; current README, white paper, specifications, case pages, and roadmap should use the active terminology baseline.
