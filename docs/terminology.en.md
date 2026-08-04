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
| Assurance Profile | 可信保证档案 | `geotask.assurance-profile` |
| Domain Pack | 行业能力包 | industry extension interface |
| Semantic Fingerprint | 语义指纹 | `semantic_fingerprint` |
| Fail-closed | 失败关闭 | safety handling principle |
| Action Eligibility | 行动资格 | control outcome |
| External Side Effect | 外部副作用 | external read, write, or real-world action |

## Recommended style

- Recommended: “The system receives a new Observation and forms a new World State.”
- Avoid: “The system receives a new 观测记录 and forms a new 世界状态.”
- Recommended: “A Verification Provider returns a Verification Response but cannot declare that independent verification is complete.”
- Avoid: “The 验证提供方 returns a Response and upgrades the 可信保证等级.”

## Maintenance

This guide is the language baseline for the English documentation system and English project homepage. Every new public Artifact or architecture concept should update both terminology guides, and documentation tests should check that the English entry points do not contain untranslated Chinese prose.
